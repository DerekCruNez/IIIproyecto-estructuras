"""Cliente de Social UNA (Daniel).

Puente entre la GUI y el servidor: la GUI llama métodos simples y nunca toca
sockets. Cumple docs/CONTRATO_CLIENTE.md:

- Todos los métodos devuelven {"ok": True, ...} o {"ok": False, "error": "..."}.
- `cola` (queue.Queue) recibe los eventos del servidor ya traducidos:
  {"tipo": "chat"|"solicitud"|"en_linea"|"publicacion"|"desconectado", ...}.
  La GUI la revisa con after().

Un hilo escucha el socket: las respuestas van a una cola interna y los eventos
a `cola`, así una petición nunca se mezcla con un chat que llega en vivo.

Prueba sin GUI:  python cliente.py [ip] [puerto]
"""

import base64
import os
import queue
import socket
import sys
import tempfile
import threading
from datetime import datetime

from protocolo import (
    HOST_DEFECTO, MAX_IMAGEN_BYTES, PUERTO_DEFECTO, codificar_imagen,
    enviar_mensaje, recibir_mensaje,
)

SALA = "#general"
# Igual que el servidor: archivos que se ejecutarían al abrirlos.
EXTENSIONES_BLOQUEADAS = (".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".vbs",
                          ".js", ".jse", ".wsf", ".lnk", ".reg", ".dll", ".hta", ".jar")
TIEMPO_ESPERA = 15  # segundos máximos esperando una respuesta
CARPETA_IMAGENES = os.path.join(tempfile.gettempdir(), "social_una_imagenes")
FIRMAS_IMAGEN = (b"\x89PNG", b"\xff\xd8", b"GIF8")  # PNG, JPG, GIF


def _error(mensaje):
    return {"ok": False, "error": mensaje}


def _fecha(texto):
    """ISO del servidor -> 'AAAA-MM-DD HH:MM:SS' que espera la GUI."""
    try:
        return datetime.fromisoformat(texto).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return texto or ""


def _mensaje_gui(m):
    """Mensaje del servidor con la fecha en el formato de la GUI y todos sus campos."""
    return {"id": m.get("id", ""), "emisor": m.get("emisor", ""),
            "receptor": m.get("receptor", ""), "texto": m.get("texto", ""),
            "fecha": _fecha(m.get("fecha")), "tipo": m.get("tipo", "texto"),
            "adjunto": m.get("adjunto", ""), "nombre_archivo": m.get("nombre_archivo", ""),
            "editado": m.get("editado", False), "reacciones": m.get("reacciones") or {},
            "responde_a": m.get("responde_a"), "encuesta": m.get("encuesta")}


def validar_imagen(ruta):
    """Devuelve un texto de error o None si la imagen se puede enviar."""
    if not ruta or not os.path.isfile(ruta):
        return "No se encontró la imagen."
    if os.path.getsize(ruta) > MAX_IMAGEN_BYTES:
        return "La imagen supera el límite de 2 MB."
    with open(ruta, "rb") as archivo:
        if not archivo.read(4).startswith(FIRMAS_IMAGEN):
            return "Formato no permitido: usa PNG, JPG o GIF."
    return None


def validar_archivo(ruta):
    """Error o None para un archivo del chat (≤ 2 MB y que no sea ejecutable)."""
    if not ruta or not os.path.isfile(ruta):
        return "No se encontró el archivo."
    if os.path.getsize(ruta) > MAX_IMAGEN_BYTES:
        return "El archivo supera el límite de 2 MB."
    if os.path.splitext(ruta)[1].lower() in EXTENSIONES_BLOQUEADAS:
        return "Por seguridad no se pueden enviar programas ni scripts."
    return None


class Cliente:
    """Cliente TCP de Social UNA. Constructor sin argumentos."""

    def __init__(self):
        self.cola = queue.Queue()          # eventos para la GUI
        self._respuestas = queue.Queue()   # respuestas a peticiones
        self._sock = None
        self._lock = threading.Lock()      # una petición a la vez
        self.usuario = None                # perfil del usuario con sesión
        self._sin_imagen = set()           # imágenes que el servidor no tiene
        os.makedirs(CARPETA_IMAGENES, exist_ok=True)

    # ------------------------------------------------------------- conexión
    def conectar(self, ip=HOST_DEFECTO, puerto=PUERTO_DEFECTO):
        self.desconectar()
        try:
            sock = socket.create_connection((ip, int(puerto)), timeout=5)
        except (OSError, ValueError) as exc:
            return _error(f"No se pudo conectar a {ip}:{puerto}. "
                          f"¿Está encendido el servidor? ({exc})")
        sock.settimeout(None)
        self._sock = sock
        self._respuestas = queue.Queue()
        threading.Thread(target=self._escuchar, args=(sock, self._respuestas),
                         daemon=True).start()
        return {"ok": True}

    def desconectar(self):
        sock, self._sock = self._sock, None
        self.usuario = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def _escuchar(self, sock, respuestas):
        """Hilo: separa respuestas de eventos hasta que el socket se cierre."""
        while True:
            try:
                msg = recibir_mensaje(sock)
            except (OSError, ValueError):
                msg = None
            if msg is None:
                break
            if "evento" in msg:
                evento = self._traducir_evento(msg)
                if evento:
                    self.cola.put(evento)
            else:
                respuestas.put(msg)
        respuestas.put(None)  # despierta a una petición en espera
        if self._sock is sock:  # no fue un desconectar() voluntario
            self._sock = None
            self.usuario = None
            self.cola.put({"tipo": "desconectado",
                           "mensaje": "Se perdió la conexión con el servidor."})

    @staticmethod
    def _traducir_evento(msg):
        datos = msg.get("datos") or {}
        tipo = msg["evento"]
        if tipo == "nuevo_mensaje":
            # campos del mensaje arriba (compatibilidad) y "tipo" del evento al final
            return {**_mensaje_gui(datos), "mensaje": _mensaje_gui(datos), "tipo": "chat"}
        if tipo == "mensaje_actualizado":
            return {"tipo": "mensaje_actualizado", "mensaje": _mensaje_gui(datos)}
        if tipo == "nueva_solicitud":
            return {"tipo": "solicitud", "usuario": datos.get("origen", "")}
        if tipo == "en_linea":
            return {"tipo": "en_linea", "usuario": datos.get("usuario", ""),
                    "en_linea": bool(datos.get("en_linea"))}
        if tipo == "invitacion_juego":
            return {"tipo": "invitacion_juego", "usuario": datos.get("origen", ""),
                    "juego": datos.get("juego", "")}
        if tipo == "juego_rechazado":
            return {"tipo": "juego_rechazado", "usuario": datos.get("usuario", "")}
        if tipo == "partida":
            return {"tipo": "partida", "partida": datos}
        if tipo == "nueva_publicacion":
            return {"tipo": "publicacion", "autor": datos.get("autor", "")}
        if tipo == "perfil_actualizado":
            return {"tipo": "perfil_actualizado", "usuario": datos.get("usuario", "")}
        return None

    def _pedir(self, nombre_accion, **datos):
        """Envía una petición y devuelve {"ok": True, **datos} o un error."""
        with self._lock:
            if self._sock is None:
                return _error("No hay conexión con el servidor.")
            try:
                enviar_mensaje(self._sock, {"accion": nombre_accion, "datos": datos})
                resp = self._respuestas.get(timeout=TIEMPO_ESPERA)
            except queue.Empty:
                return _error("El servidor no respondió a tiempo.")
            except (OSError, ValueError) as exc:
                return _error(f"No se pudo enviar la petición: {exc}")
        if resp is None:
            return _error("Se perdió la conexión con el servidor.")
        if not resp.get("ok"):
            return _error(resp.get("error") or "Error desconocido del servidor.")
        return {"ok": True, **(resp.get("datos") or {})}

    @staticmethod
    def _solo_ok(r):
        return {"ok": True} if r["ok"] else r

    # --------------------------------------------------------------- sesión
    def registrar(self, id_, nombre, usuario, clave):
        return self._solo_ok(self._pedir("registrar", id=id_, nombre=nombre,
                                         usuario=usuario, clave=clave))

    def login(self, usuario, clave):
        r = self._pedir("login", usuario=usuario, clave=clave)
        if not r["ok"]:
            return r
        self.usuario = r["usuario"]
        return {"ok": True, "usuario": self.usuario}

    def logout(self):
        r = self._pedir("logout")
        self.usuario = None
        return self._solo_ok(r)

    # --------------------------------------------------------------- perfil
    def ver_perfil(self, usuario):
        r = self._pedir("ver_perfil", usuario=usuario)
        return {"ok": True, "usuario": r["perfil"]} if r["ok"] else r

    def _subir(self, ruta):
        """Sube una imagen al servidor. Devuelve (nombre, None) o (None, error)."""
        error = validar_imagen(ruta)
        if error:
            return None, error
        r = self._pedir("subir_imagen", imagen=codificar_imagen(ruta))
        if not r["ok"]:
            return None, r["error"]
        self._copiar_a_cache(ruta, r["nombre"])
        return r["nombre"], None

    def editar_perfil(self, bio, ruta_foto, link, ruta_banner=None, **apariencia):
        """Edita el perfil. ruta_foto/ruta_banner: archivo nuevo, None = sin cambio,
        "" = quitar. apariencia: color_perfil, tema, paleta (None = sin cambio)."""
        cambios = {"bio": bio, "link": link,
                   **{k: v for k, v in apariencia.items() if v is not None}}
        for campo, ruta in (("foto", ruta_foto), ("banner", ruta_banner)):
            if ruta == "":
                cambios[campo] = ""
            elif ruta:
                nombre, error = self._subir(ruta)
                if error:
                    return _error(error)
                cambios[campo] = nombre
        cambios = {k: v for k, v in cambios.items() if v is not None}
        r = self._pedir("editar_perfil", **cambios)
        if not r["ok"]:
            return r
        if not self.usuario:
            return {"ok": True}
        r = self.ver_perfil(self.usuario["usuario"])
        if r["ok"]:
            self.usuario = r["usuario"]
        return r

    def guardar_apariencia(self, tema, paleta):
        """Guarda el tema y la paleta en el perfil (te siguen a otra computadora)."""
        r = self._pedir("editar_perfil", tema=tema, paleta=paleta)
        if r["ok"] and self.usuario:
            self.usuario.update(tema=tema, paleta=paleta)
        return self._solo_ok(r)

    def ruta_imagen(self, nombre):
        """Ruta local de una imagen del servidor; la descarga si hace falta."""
        if not nombre:
            return None
        nombre = os.path.basename(nombre)
        ruta = os.path.join(CARPETA_IMAGENES, nombre)
        if os.path.isfile(ruta):
            return ruta
        if nombre in self._sin_imagen:
            return None
        r = self._pedir("obtener_imagen", nombre=nombre)
        if not r["ok"]:
            self._sin_imagen.add(nombre)
            return None
        with open(ruta, "wb") as archivo:
            archivo.write(base64.b64decode(r["imagen"]))
        return ruta

    @staticmethod
    def _copiar_a_cache(ruta, nombre):
        """Así quien sube una imagen no tiene que volver a descargarla."""
        with open(ruta, "rb") as origen, \
                open(os.path.join(CARPETA_IMAGENES, nombre), "wb") as destino:
            destino.write(origen.read())

    # ------------------------------------------------------------- usuarios
    def buscar_usuarios(self, texto):
        r = self._pedir("buscar_usuarios", texto=texto)
        if not r["ok"]:
            return r
        yo = (self.usuario or {}).get("usuario")
        return {"ok": True, "usuarios": [
            {"usuario": u["usuario"], "nombre": u["nombre"], "foto": u.get("foto", ""),
             "amigo": u.get("amigo", False), "pendiente": u.get("pendiente", False)}
            for u in r["usuarios"] if u["usuario"] != yo]}

    def enviar_solicitud(self, usuario):
        return self._solo_ok(self._pedir("enviar_solicitud", destino=usuario))

    def responder_solicitud(self, usuario, acepta):
        return self._solo_ok(self._pedir("responder_solicitud", origen=usuario,
                                         aceptar=bool(acepta)))

    def eliminar_amigo(self, usuario):
        return self._solo_ok(self._pedir("eliminar_amigo", amigo=usuario))

    def listar_amigos(self):
        r = self._pedir("listar_amigos")
        if not r["ok"]:
            return r
        s = self._pedir("listar_solicitudes")
        if not s["ok"]:
            return s
        return {"ok": True,
                "amigos": sorted(r["amigos"], key=lambda a: (not a["en_linea"], a["nombre"])),
                "solicitudes": s["solicitudes"]}

    def sugerencias(self):
        r = self._pedir("sugerencias")
        if not r["ok"]:
            return r
        return {"ok": True, "sugerencias": [
            {"usuario": u["usuario"], "nombre": u["nombre"], "foto": u.get("foto", ""),
             "en_comun": u.get("en_comun", 0)}
            for u in r["sugerencias"]]}

    # -------------------------------------------------------- publicaciones
    def publicar(self, texto, ruta_imagen, link, ruta_archivo=None):
        """Publica en el muro con imagen/GIF, link y archivo adjunto opcionales."""
        datos = {"texto": (texto or "").strip(), "link": link or "", "extra": ""}
        if ruta_imagen:
            error = validar_imagen(ruta_imagen)
            if error:
                return _error(error)
            datos["imagen"] = codificar_imagen(ruta_imagen)
        if ruta_archivo:
            error = validar_archivo(ruta_archivo)
            if error:
                return _error(error)
            # un mensaje no puede pasar de 3 MB (protocolo) y base64 ocupa 4/3 del archivo
            if ruta_imagen and os.path.getsize(ruta_imagen) + os.path.getsize(ruta_archivo)                     > MAX_IMAGEN_BYTES:
                return _error("La imagen y el archivo juntos no pueden pasar de 2 MB.")
            datos["archivo"] = codificar_imagen(ruta_archivo)
            datos["nombre_archivo"] = os.path.basename(ruta_archivo)
        r = self._pedir("publicar", **datos)
        if not r["ok"]:
            return r
        for ruta, campo in ((ruta_imagen, "imagen"), (ruta_archivo, "archivo")):
            if ruta and r["publicacion"].get(campo):
                self._copiar_a_cache(ruta, r["publicacion"][campo])
        return {"ok": True}

    def editar_publicacion(self, id_publicacion, texto):
        return self._solo_ok(self._pedir("editar_publicacion", id_publicacion=str(id_publicacion),
                                         texto=texto))

    def eliminar_publicacion(self, id_publicacion):
        return self._solo_ok(self._pedir("eliminar_publicacion",
                                         id_publicacion=str(id_publicacion)))

    def poner_apodo(self, amigo, apodo):
        """Apodo que solo tú ves para un amigo ("" para quitarlo)."""
        return self._solo_ok(self._pedir("poner_apodo", amigo=amigo, apodo=apodo))

    def obtener_muro(self):
        r = self._pedir("obtener_muro")
        if not r["ok"]:
            return r
        return {"ok": True, "publicaciones": [
            {"id": p["id"], "autor": p["autor"], "texto": p["texto"],
             "imagen": p.get("imagen", ""), "link": p.get("link", ""),
             "fecha": _fecha(p.get("fecha")), "likes": p.get("likes", []),
             "reacciones": p.get("reacciones", {}), "archivo": p.get("archivo", ""),
             "nombre_archivo": p.get("nombre_archivo", ""), "editado": p.get("editado", False)}
            for p in r["publicaciones"]]}

    def dar_like(self, id_publicacion):
        return self._solo_ok(self._pedir("dar_like", id_publicacion=str(id_publicacion)))

    def reaccionar(self, id_publicacion, emoji):
        return self._solo_ok(self._pedir("reaccionar", id_publicacion=str(id_publicacion),
                                         emoji=emoji))

    # ----------------------------------------------------------------- chat
    def enviar_chat(self, receptor, texto, tipo="texto", ruta=None, responde_a=None,
                    encuesta=None):
        """Envía un mensaje. tipo: texto, imagen, sticker, archivo, audio o encuesta.

        ruta: archivo local para imagen/sticker/archivo/audio (≤ 2 MB).
        responde_a: id del mensaje al que se responde.
        encuesta: {"pregunta": str, "opciones": [str, ...]} (2 a 4 opciones).
        """
        datos = {"receptor": receptor, "texto": texto or "", "tipo": tipo}
        if responde_a:
            datos["responde_a"] = responde_a
        if encuesta:
            datos["encuesta"] = encuesta
        if ruta:
            error = validar_imagen(ruta) if tipo in ("imagen", "sticker") else validar_archivo(ruta)
            if error:
                return _error(error)
            datos["adjunto"] = codificar_imagen(ruta)
            datos["nombre_archivo"] = os.path.basename(ruta)
        r = self._pedir("enviar_chat", **datos)
        if not r["ok"]:
            return r
        mensaje = _mensaje_gui(r["chat"])
        if ruta and mensaje["adjunto"]:
            self._copiar_a_cache(ruta, mensaje["adjunto"])
        return {"ok": True, "mensaje": mensaje}

    def actualizar_mensaje(self, con, id_mensaje, accion, valor=None):
        """accion: editar (valor=texto), eliminar, reaccionar (valor=emoji), votar (valor=índice)."""
        r = self._pedir("actualizar_mensaje", con=con, id=id_mensaje, accion=accion, valor=valor)
        return {"ok": True, "mensaje": _mensaje_gui(r["chat"])} if r["ok"] else r

    def obtener_chat(self, con):
        r = self._pedir("obtener_chat", b=con)
        if not r["ok"]:
            return r
        return {"ok": True, "mensajes": [_mensaje_gui(m) for m in r["mensajes"]]}


    # ---------------------------------------------------------------- juegos
    def enviar_puntaje(self, juego, puntos):
        """serpiente o buscaminas. Devuelve {"ok", "mejor"} (tu mejor puntaje)."""
        return self._pedir("enviar_puntaje", juego=juego, puntos=int(puntos))

    def leaderboard(self, juego):
        """{"ok", "tabla": [{usuario, nombre, foto, puntos}], "jugando": [...], "duelos": [[x, o]]}"""
        return self._pedir("leaderboard", juego=juego)

    def jugando(self, juego=""):
        """Avisa que estás jugando (juego vacío = ya no)."""
        return self._solo_ok(self._pedir("jugando", juego=juego))

    def invitar_juego(self, amigo):
        return self._solo_ok(self._pedir("invitar_juego", amigo=amigo))

    def responder_juego(self, origen, aceptar):
        return self._pedir("responder_juego", origen=origen, aceptar=bool(aceptar))

    def jugada(self, id_partida, casilla):
        return self._pedir("jugada", id=id_partida, casilla=int(casilla))

    def abandonar_juego(self, id_partida):
        return self._solo_ok(self._pedir("abandonar_juego", id=id_partida))


# Nombre del contrato original (docs/CONTRATO_FUNCIONES.md); main.py lo importa así.
ClienteSocial = Cliente


# --------------------------------------------------------------------------
# Consola de prueba (sin GUI)
# --------------------------------------------------------------------------
def _consola():
    ip = sys.argv[1] if len(sys.argv) > 1 else HOST_DEFECTO
    puerto = int(sys.argv[2]) if len(sys.argv) > 2 else PUERTO_DEFECTO
    c = Cliente()
    print(c.conectar(ip, puerto))
    print("Comandos: registrar id nombre usuario clave | login usuario clave | muro |"
          " publicar texto | amigos | buscar texto | solicitar usuario |"
          " aceptar usuario | chat usuario texto | historial usuario | salir")
    while True:
        while not c.cola.empty():
            print("[evento]", c.cola.get())
        try:
            partes = input("> ").split(" ", 1)
        except EOFError:
            break
        cmd, resto = partes[0], (partes[1] if len(partes) > 1 else "")
        a = resto.split(" ")
        if cmd == "salir":
            break
        acciones = {
            "registrar": lambda: c.registrar(a[0], a[1], a[2], a[3]),
            "login": lambda: c.login(a[0], a[1]),
            "muro": c.obtener_muro,
            "publicar": lambda: c.publicar(resto, None, ""),
            "amigos": c.listar_amigos,
            "buscar": lambda: c.buscar_usuarios(resto),
            "solicitar": lambda: c.enviar_solicitud(resto),
            "aceptar": lambda: c.responder_solicitud(resto, True),
            "chat": lambda: c.enviar_chat(a[0], resto.split(" ", 1)[1]),
            "historial": lambda: c.obtener_chat(resto),
        }
        try:
            print(acciones[cmd]() if cmd in acciones else "Comando desconocido")
        except IndexError:
            print("Faltan datos para ese comando")
    c.desconectar()


if __name__ == "__main__":
    _consola()
