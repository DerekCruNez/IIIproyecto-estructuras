"""Cliente de demostración: imita a cliente.py (Daniel) sin red ni archivos.

Sirve para probar toda la interfaz antes de que el servidor y el cliente reales
estén listos. Tiene exactamente los mismos métodos que debe ofrecer cliente.Cliente
(ver CONTRATO_CLIENTE.md). Los datos viven solo en memoria.
"""
import os
import queue
import threading
from datetime import datetime

SALA = "#general"


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ok(**datos):
    return {"ok": True, **datos}


def _error(mensaje):
    return {"ok": False, "error": mensaje}


class ClienteDemo:
    def __init__(self):
        self.cola = queue.Queue()
        self.actual = None
        self._sig = 1
        self.usuarios = {
            "ana": {"id": "1", "nombre": "Ana Mora", "clave": "1234", "bio": "Estudiante de informática.",
                    "foto": "", "link": "https://una.ac.cr"},
            "luis": {"id": "2", "nombre": "Luis Vargas", "clave": "1234", "bio": "Me gusta la música.",
                     "foto": "", "link": ""},
            "maria": {"id": "3", "nombre": "María Rojas", "clave": "1234", "bio": "", "foto": "", "link": ""},
            "pedro": {"id": "4", "nombre": "Pedro Solís", "clave": "1234", "bio": "", "foto": "", "link": ""},
        }
        self.amigos = {"ana": {"luis"}, "luis": {"ana", "pedro"}, "maria": set(), "pedro": {"luis"}}
        self.solicitudes = {"ana": {"maria"}, "luis": set(), "maria": set(), "pedro": set()}
        self.en_linea = {"luis"}
        self.publicaciones = []
        self.apodos = {}
        self.puntajes = {"serpiente": {"luis": 180, "pedro": 90}, "buscaminas": {"luis": 640}}
        self.chats = {}
        self._publicar_como("luis", "¡Hola a todos! Este es mi primer post en Social UNA.", None, "")
        self._publicar_como("ana", "Estudiando estructuras de datos 📚", None, "https://docs.python.org")
        self._publicar_como("pedro", "Alguien para el proyecto del martes?", None, "")
        self.chats[SALA] = [self._nuevo_mensaje("luis", SALA, "Bienvenidos a la sala general 👋")]

    # ---------------------------------------------------------------- sesión
    def conectar(self, ip, puerto):
        return _ok()

    def registrar(self, id_, nombre, usuario, clave):
        if usuario in self.usuarios:
            return _error("Ese usuario ya existe.")
        self.usuarios[usuario] = {"id": id_, "nombre": nombre, "clave": clave, "bio": "", "foto": "", "link": ""}
        self.amigos[usuario] = set()
        self.solicitudes[usuario] = set()
        return _ok()

    def login(self, usuario, clave):
        u = self.usuarios.get(usuario)
        if not u or u["clave"] != clave:
            return _error("Usuario o contraseña incorrectos.")
        self.actual = usuario
        self.en_linea.add(usuario)
        return _ok(usuario=self._perfil(usuario))

    def logout(self):
        self.en_linea.discard(self.actual)
        self.actual = None
        return _ok()

    def _perfil(self, usuario):
        u = self.usuarios[usuario]
        return {"id": u["id"], "usuario": usuario, "nombre": u["nombre"], "bio": u["bio"],
                "foto": u["foto"], "link": u["link"], "banner": u.get("banner", ""),
                "color_perfil": u.get("color_perfil", ""), "tema": u.get("tema", "claro"),
                "paleta": u.get("paleta", "bosque")}

    # ----------------------------------------------------------------- perfil
    def ver_perfil(self, usuario):
        if usuario not in self.usuarios:
            return _error("Usuario no encontrado.")
        return _ok(usuario=self._perfil(usuario))

    def editar_perfil(self, bio, ruta_foto, link, ruta_banner=None, **apariencia):
        u = self.usuarios[self.actual]
        u["bio"], u["link"] = bio, link
        if ruta_foto is not None:
            u["foto"] = ruta_foto            # en la demo el "nombre" es la ruta completa
        if ruta_banner is not None:
            u["banner"] = ruta_banner
        u.update({k: v for k, v in apariencia.items() if v is not None})   # incluye nombre
        return _ok(usuario=self._perfil(self.actual))

    def guardar_apariencia(self, tema, paleta):
        self.usuarios[self.actual].update(tema=tema, paleta=paleta)
        return _ok()

    def ruta_imagen(self, nombre):
        return nombre if nombre and os.path.isfile(nombre) else None

    # ---------------------------------------------------------------- usuarios
    def buscar_usuarios(self, texto):
        t = texto.lower()
        res = []
        for usuario, u in self.usuarios.items():
            if usuario == self.actual:
                continue
            if t in usuario.lower() or t in u["nombre"].lower():
                res.append({"usuario": usuario, "nombre": u["nombre"],
                            "amigo": usuario in self.amigos[self.actual],
                            "pendiente": self.actual in self.solicitudes[usuario]})
        return _ok(usuarios=res)

    def enviar_solicitud(self, usuario):
        if usuario in self.amigos[self.actual]:
            return _error("Ya son amigos.")
        if self.actual in self.solicitudes[usuario]:
            return _error("Ya enviaste una solicitud a ese usuario.")
        self.solicitudes[usuario].add(self.actual)
        return _ok()

    def responder_solicitud(self, usuario, acepta):
        self.solicitudes[self.actual].discard(usuario)
        if acepta:
            self.amigos[self.actual].add(usuario)
            self.amigos[usuario].add(self.actual)
        return _ok()

    def eliminar_amigo(self, usuario):
        self.amigos[self.actual].discard(usuario)
        self.amigos[usuario].discard(self.actual)
        return _ok()

    def listar_amigos(self):
        return _ok(
            amigos=[{"usuario": a, "nombre": self.usuarios[a]["nombre"], "en_linea": a in self.en_linea,
                     "apodo": self.apodos.get(self.actual, {}).get(a, "")}
                    for a in sorted(self.amigos[self.actual])],
            solicitudes=[{"usuario": s, "nombre": self.usuarios[s]["nombre"]}
                         for s in sorted(self.solicitudes[self.actual])])

    def sugerencias(self):
        mios = self.amigos[self.actual]
        cuenta = {}
        for amigo in mios:
            for otro in self.amigos[amigo]:
                if otro != self.actual and otro not in mios:
                    cuenta[otro] = cuenta.get(otro, 0) + 1
        for u in sorted(self.usuarios):
            if u != self.actual and u not in mios:
                cuenta.setdefault(u, 0)
        return _ok(sugerencias=[{"usuario": u, "nombre": self.usuarios[u]["nombre"], "en_comun": n}
                                for u, n in sorted(cuenta.items(), key=lambda x: -x[1])])

    # ------------------------------------------------------------ publicaciones
    def _publicar_como(self, autor, texto, ruta_imagen, link):
        self.publicaciones.append({"id": self._sig, "autor": autor, "texto": texto,
                                   "imagen": ruta_imagen or "", "link": link, "fecha": _ahora(), "likes": [],
                                   "reacciones": {}})
        self._sig += 1

    def publicar(self, texto, ruta_imagen, link, ruta_archivo=None):
        self._publicar_como(self.actual, texto, ruta_imagen, link)
        if ruta_archivo:
            self.publicaciones[-1].update(archivo=ruta_archivo,
                                          nombre_archivo=os.path.basename(ruta_archivo))
        return _ok()

    def _publicacion(self, id_publicacion):
        return next((p for p in self.publicaciones if p["id"] == id_publicacion), None)

    def editar_publicacion(self, id_publicacion, texto):
        p = self._publicacion(id_publicacion)
        if not p or p["autor"] != self.actual:
            return _error("Solo puedes editar tus publicaciones.")
        p.update(texto=texto, editado=True)
        return _ok()

    def eliminar_publicacion(self, id_publicacion):
        p = self._publicacion(id_publicacion)
        if not p or p["autor"] != self.actual:
            return _error("Solo puedes eliminar tus publicaciones.")
        self.publicaciones.remove(p)
        return _ok()

    def poner_apodo(self, amigo, apodo):
        self.apodos.setdefault(self.actual, {})[amigo] = apodo.strip()
        return _ok()

    def obtener_muro(self):
        visibles = self.amigos[self.actual] | {self.actual}
        pubs = [p for p in self.publicaciones if p["autor"] in visibles]
        return _ok(publicaciones=sorted(pubs, key=lambda p: (p["fecha"], p["id"]), reverse=True))

    def dar_like(self, id_publicacion):
        for p in self.publicaciones:
            if p["id"] == id_publicacion:
                if self.actual in p["likes"]:
                    p["likes"].remove(self.actual)
                else:
                    p["likes"].append(self.actual)
                return _ok()
        return _error("La publicación no existe.")

    def reaccionar(self, id_publicacion, emoji):
        for p in self.publicaciones:
            if p["id"] == id_publicacion:
                lista = p["reacciones"].setdefault(emoji, [])
                if self.actual in lista:
                    lista.remove(self.actual)
                    if not lista:
                        del p["reacciones"][emoji]
                else:
                    lista.append(self.actual)
                return _ok()
        return _error("La publicación no existe.")

    # ------------------------------------------------------------------- juegos
    def enviar_puntaje(self, juego, puntos):
        tabla = self.puntajes.setdefault(juego, {})
        tabla[self.actual] = max(tabla.get(self.actual, 0), puntos)
        return _ok(mejor=tabla[self.actual])

    def leaderboard(self, juego):
        filas = [{"usuario": u, "nombre": self.usuarios[u]["nombre"], "foto": "", "puntos": p}
                 for u, p in self.puntajes.get(juego, {}).items()]
        return _ok(tabla=sorted(filas, key=lambda f: -f["puntos"]), jugando=[], duelos=[])

    def jugando(self, juego=""):
        return _ok()

    def invitar_juego(self, amigo):
        return _error("El 3 en raya en línea necesita el servidor real.")

    # --------------------------------------------------------------------- chat
    @staticmethod
    def _clave(a, b):
        return "|".join(sorted((a, b)))

    def obtener_chat(self, con):
        clave = SALA if con == SALA else self._clave(self.actual, con)
        return _ok(mensajes=list(self.chats.get(clave, [])))

    def _nuevo_mensaje(self, emisor, receptor, texto, tipo="texto", adjunto="", nombre="",
                       responde_a=None, encuesta=None):
        self._sig += 1
        return {"id": str(self._sig), "emisor": emisor, "receptor": receptor, "texto": texto,
                "fecha": _ahora(), "tipo": tipo, "adjunto": adjunto, "nombre_archivo": nombre,
                "editado": False, "reacciones": {}, "responde_a": responde_a, "encuesta": encuesta}

    def enviar_chat(self, receptor, texto, tipo="texto", ruta=None, responde_a=None, encuesta=None):
        clave = SALA if receptor == SALA else self._clave(self.actual, receptor)
        lista = self.chats.setdefault(clave, [])
        cita = next(({"id": m["id"], "emisor": m["emisor"], "texto": m["texto"][:80],
                      "tipo": m["tipo"]} for m in lista if m.get("id") == responde_a), None)
        if encuesta:
            encuesta = {"pregunta": encuesta["pregunta"],
                        "opciones": [{"texto": o, "votos": []} for o in encuesta["opciones"]]}
        msg = self._nuevo_mensaje(self.actual, receptor, texto, tipo, ruta or "",
                                  os.path.basename(ruta or ""), cita, encuesta)
        lista.append(msg)
        if receptor != SALA:
            # simula la respuesta en vivo de un amigo (llega por la cola, como con el servidor)
            def responder():
                r = self._nuevo_mensaje(receptor, self.actual,
                                        "¡Recibido! 😄 (respuesta automática de la demo)")
                lista.append(r)
                self.cola.put({**r, "mensaje": r, "tipo": "chat"})
            t = threading.Timer(1.5, responder)
            t.daemon = True
            t.start()
        return _ok(mensaje=msg)

    def actualizar_mensaje(self, con, id_mensaje, accion, valor=None):
        clave = SALA if con == SALA else self._clave(self.actual, con)
        for m in self.chats.get(clave, []):
            if m.get("id") == id_mensaje:
                if accion == "editar":
                    m["texto"], m["editado"] = valor, True
                elif accion == "eliminar":
                    m.update(tipo="eliminado", texto="", adjunto="", encuesta=None, reacciones={})
                elif accion == "reaccionar":
                    lista = m["reacciones"].setdefault(valor, [])
                    lista.remove(self.actual) if self.actual in lista else lista.append(self.actual)
                    if not lista:
                        del m["reacciones"][valor]
                elif accion == "votar":
                    for i, o in enumerate(m["encuesta"]["opciones"]):
                        ya = self.actual in o["votos"]
                        if ya:
                            o["votos"].remove(self.actual)
                        elif i == valor:
                            o["votos"].append(self.actual)
                return _ok(mensaje=m)
        return _error("El mensaje no existe.")
