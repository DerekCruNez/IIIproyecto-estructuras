"""Servidor TCP de Social UNA.

Cada conexión se atiende en un hilo y conserva su propio estado de sesión.
El almacenamiento serializa las operaciones para mantener consistentes sus
estructuras compartidas. Los mensajes se enmarcan exclusivamente mediante las
funciones definidas en :mod:`protocolo`.
"""

import base64
import binascii
import json
import os
import re
import socket
import threading
import uuid
from typing import Any, Callable

from almacen import Almacen
from protocolo import (
    HOST_DEFECTO,
    MAX_IMAGEN_BYTES,
    PUERTO_DEFECTO,
    enviar_mensaje,
    guardar_imagen,
    recibir_mensaje,
)


SALA = "#general"
EMOJIS_REACCION = ("😂", "🔥", "👏", "😮", "😢")
TIPOS_CHAT = ("texto", "imagen", "sticker", "archivo", "audio", "encuesta")
# Archivos que se podrían ejecutar al abrirlos: no se aceptan en el chat.
EXTENSIONES_BLOQUEADAS = (".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".vbs",
                          ".js", ".jse", ".wsf", ".lnk", ".reg", ".dll", ".hta", ".jar")
TEMAS = ("claro", "oscuro")
MAX_BIO = 190
# Firmas de los formatos de imagen aceptados -> extensión con la que se guardan.
FIRMAS_IMAGEN = ((b"\x89PNG", ".png"), (b"\xff\xd8", ".jpg"), (b"GIF8", ".gif"))


class Servidor:
    """Servidor TCP concurrente para la aplicación Social UNA.

    Una cuenta solo puede tener una conexión autenticada a la vez: un segundo
    login se rechaza hasta que la primera conexión cierre sesión o se corte.
    La identidad de una sesión se obtiene del estado asociado al socket, nunca
    de los nombres de usuario que envía el cliente en acciones protegidas.
    """

    def __init__(self, almacen: Almacen) -> None:
        self.almacen = almacen
        self.socket_servidor: socket.socket | None = None
        self.en_linea: dict[str, socket.socket] = {}
        self.lock_en_linea = threading.Lock()
        self._lock_almacen = threading.RLock()
        self._lock_conexiones = threading.Lock()
        self._conexiones: dict[socket.socket, dict[str, Any]] = {}
        self._hilos: set[threading.Thread] = set()
        self._ejecutando = threading.Event()
        self._hilo_aceptacion: threading.Thread | None = None
        self._lock_apagado = threading.Lock()
        self._apagado_en_curso = False
        self._apagado_completado = False
        self._apagado_finalizado = threading.Event()
        # juegos: quién está jugando a qué y partidas de 3 en raya en curso (en memoria)
        self.jugando: dict[str, str] = {}
        self.partidas: dict[str, dict[str, Any]] = {}
        self.invitaciones: set[tuple[str, str]] = set()
        self._lock_juegos = threading.Lock()
        self.host: str | None = None
        self.puerto: int | None = None

    def iniciar(self, host: str = HOST_DEFECTO,
                puerto: int = PUERTO_DEFECTO) -> None:
        """Carga datos y ejecuta el bucle de aceptación hasta detenerse."""
        if self._ejecutando.is_set():
            raise RuntimeError("El servidor ya está en ejecución.")
        with self._lock_apagado:
            if self._apagado_en_curso:
                raise RuntimeError("El servidor se está apagando.")
            self._apagado_completado = False
            self._apagado_finalizado.clear()
        self.almacen.cargar_todo()
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            servidor.bind((host, puerto))
            servidor.listen()
        except OSError:
            servidor.close()
            raise
        self.socket_servidor = servidor
        self.host, self.puerto = servidor.getsockname()[:2]
        self._hilo_aceptacion = threading.current_thread()
        self._ejecutando.set()
        print(f"Servidor Social UNA escuchando en {self.host}:{self.puerto}")
        try:
            self.aceptar_clientes()
        finally:
            self._ejecutando.clear()
            self._hilo_aceptacion = None

    def aceptar_clientes(self) -> None:
        """Acepta conexiones y crea un hilo dedicado por cliente."""
        servidor = self.socket_servidor
        if servidor is None:
            raise RuntimeError("El socket del servidor no está inicializado.")
        while self._ejecutando.is_set():
            try:
                sock, addr = servidor.accept()
            except OSError:
                if self._ejecutando.is_set():
                    raise
                break
            sesion: dict[str, Any] = {
                "usuario": None,
                "socket": sock,
                "lock_envio": threading.Lock(),
                "addr": addr,
            }
            with self._lock_conexiones:
                self._conexiones[sock] = sesion
            hilo = threading.Thread(
                target=self.atender_cliente,
                args=(sock, addr),
                name=f"cliente-{addr[0]}:{addr[1]}",
                daemon=True,
            )
            with self._lock_conexiones:
                self._hilos.add(hilo)
            hilo.start()

    def atender_cliente(self, sock: socket.socket, addr: tuple[str, int]) -> None:
        """Lee, valida y despacha peticiones de una conexión hasta cerrarla."""
        with self._lock_conexiones:
            sesion = self._conexiones.get(sock)
        if sesion is None:
            sesion = {"usuario": None, "socket": sock,
                      "lock_envio": threading.Lock(), "addr": addr}
            with self._lock_conexiones:
                self._conexiones[sock] = sesion
        try:
            while self._ejecutando.is_set():
                try:
                    peticion = recibir_mensaje(sock)
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                    self._enviar_respuesta(sock, sesion, self._respuesta(
                        False, error=f"Mensaje JSON inválido: {exc}"
                    ))
                    continue
                except (ConnectionError, OSError):
                    break
                if peticion is None:
                    break
                if not isinstance(peticion, dict):
                    respuesta = self._respuesta(False, error="La petición debe ser un objeto JSON.")
                else:
                    try:
                        respuesta = self.despachar(peticion, sesion)
                    except (KeyError, TypeError, ValueError) as exc:
                        respuesta = self._respuesta(False, error=f"Petición inválida: {exc}")
                    except Exception as exc:  # no deja que una operación tumbe el hilo/servidor
                        print(f"Error procesando petición de {addr}: {exc!r}")
                        respuesta = self._respuesta(False, error="Error interno al procesar la petición.")
                for campo in ("id", "request_id"):
                    if campo in peticion:
                        respuesta[campo] = peticion[campo]
                if not self._enviar_respuesta(sock, sesion, respuesta):
                    break
        finally:
            usuario = sesion.get("usuario")
            self.cerrar_cliente(sock, usuario)
            hilo_actual = threading.current_thread()
            with self._lock_conexiones:
                self._hilos.discard(hilo_actual)

    def despachar(self, peticion: dict, sesion: dict[str, Any]) -> dict:
        """Valida el sobre y ejecuta la acción solicitada."""
        accion = peticion.get("accion")
        datos = peticion.get("datos", {})
        if not isinstance(accion, str) or not accion.strip():
            return self._respuesta(False, error="Falta una acción válida.")
        if not isinstance(datos, dict):
            return self._respuesta(False, error="El campo 'datos' debe ser un objeto.")
        acciones: dict[str, Callable[[dict, dict], dict]] = {
            "registrar": self.accion_registrar,
            "login": self.accion_login,
            "logout": self.accion_logout,
            "buscar_usuarios": self.accion_buscar_usuarios,
            "ver_perfil": self.accion_ver_perfil,
            "editar_perfil": self.accion_editar_perfil,
            "enviar_solicitud": self.accion_enviar_solicitud,
            "responder_solicitud": self.accion_responder_solicitud,
            "listar_solicitudes": self.accion_listar_solicitudes,
            "listar_amigos": self.accion_listar_amigos,
            "eliminar_amigo": self.accion_eliminar_amigo,
            "publicar": self.accion_publicar,
            "obtener_muro": self.accion_obtener_muro,
            "dar_like": self.accion_dar_like,
            "enviar_chat": self.accion_enviar_chat,
            "obtener_chat": self.accion_obtener_chat,
            "sugerencias": self.accion_sugerencias,
            "reaccionar": self.accion_reaccionar,
            "subir_imagen": self.accion_subir_imagen,
            "obtener_imagen": self.accion_obtener_imagen,
            "actualizar_mensaje": self.accion_actualizar_mensaje,
            "editar_publicacion": self.accion_editar_publicacion,
            "eliminar_publicacion": self.accion_eliminar_publicacion,
            "poner_apodo": self.accion_poner_apodo,
            "enviar_puntaje": self.accion_enviar_puntaje,
            "leaderboard": self.accion_leaderboard,
            "jugando": self.accion_jugando,
            "invitar_juego": self.accion_invitar_juego,
            "responder_juego": self.accion_responder_juego,
            "jugada": self.accion_jugada,
            "abandonar_juego": self.accion_abandonar_juego,
        }
        metodo = acciones.get(accion)
        if metodo is None:
            return self._respuesta(False, error=f"Acción desconocida: {accion}")
        return metodo(datos, sesion)

    @staticmethod
    def _respuesta(ok: bool, datos: dict[str, Any] | None = None,
                   error: str = "") -> dict[str, Any]:
        return {"ok": ok, "datos": datos or {}, "error": error}

    @staticmethod
    def _texto(datos: dict, campo: str, requerido: bool = True) -> str:
        valor = datos.get(campo)
        if not requerido and valor is None:
            return ""
        if not isinstance(valor, str) or (requerido and not valor.strip()):
            raise ValueError(f"El campo '{campo}' debe ser texto" +
                             (" no vacío." if requerido else "."))
        return valor.strip() if requerido else valor

    @staticmethod
    def _resultado(resultado: Any) -> Any:
        """Convierte modelos conocidos a estructuras compatibles con JSON."""
        if hasattr(resultado, "a_dict") and callable(resultado.a_dict):
            return resultado.a_dict()
        if isinstance(resultado, list):
            return [Servidor._resultado(item) for item in resultado]
        if isinstance(resultado, tuple):
            return [Servidor._resultado(item) for item in resultado]
        if isinstance(resultado, dict):
            return {k: Servidor._resultado(v) for k, v in resultado.items()}
        return resultado

    def _almacen(self, metodo: str, *args: Any, **kwargs: Any) -> tuple[bool, Any]:
        """Serializa las operaciones de negocio sobre Almacen."""
        with self._lock_almacen:
            return getattr(self.almacen, metodo)(*args, **kwargs)

    @staticmethod
    def _requiere_login(sesion: dict) -> str:
        usuario = sesion.get("usuario")
        if not isinstance(usuario, str) or not usuario:
            raise PermissionError("Debes iniciar sesión para realizar esta acción.")
        return usuario

    def _protegida(self, sesion: dict, operacion: Callable[[str], tuple[bool, Any]],
                   campo: str = "resultado") -> dict:
        try:
            usuario = self._requiere_login(sesion)
        except PermissionError as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = operacion(usuario)
        return self._respuesta(ok, {campo: self._resultado(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def _enviar_respuesta(self, sock: socket.socket, sesion: dict,
                          mensaje: dict) -> bool:
        try:
            with sesion["lock_envio"]:
                enviar_mensaje(sock, mensaje)
            return True
        except (OSError, ConnectionError, ValueError) as exc:
            print(f"No se pudo enviar a {sesion.get('addr')}: {exc}")
            return False

    def enviar_a_usuario(self, usuario: str, mensaje: dict) -> bool:
        """Envía un evento sin mantener el bloqueo global durante la red."""
        with self.lock_en_linea:
            sock = self.en_linea.get(usuario)
        if sock is None:
            return False
        with self._lock_conexiones:
            sesion = self._conexiones.get(sock)
        if sesion is None:
            return False
        enviado = self._enviar_respuesta(sock, sesion, mensaje)
        if not enviado:
            self.cerrar_cliente(sock, usuario)
        return enviado

    def cerrar_cliente(self, sock: socket.socket,
                       usuario: str | None = None) -> None:
        """Cierra el socket y quita únicamente la sesión que le pertenece."""
        with self.lock_en_linea:
            usuario_sesion = usuario
            with self._lock_conexiones:
                sesion = self._conexiones.pop(sock, None)
            if sesion is not None:
                usuario_sesion = sesion.get("usuario") or usuario_sesion
            salio = bool(usuario_sesion and self.en_linea.get(usuario_sesion) is sock)
            if salio:
                del self.en_linea[usuario_sesion]
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError as exc:
            print(f"Error cerrando socket de cliente: {exc}")
        if salio and self._ejecutando.is_set():
            print(f"{usuario_sesion} se desconectó")
            self._avisar_presencia(usuario_sesion, False)
            # si estaba en una partida, gana el rival
            with self._lock_juegos:
                self.jugando.pop(usuario_sesion, None)
                ids = [i for i, p in self.partidas.items()
                       if usuario_sesion in (p["x"], p["o"])]
            for i in ids:
                self.accion_abandonar_juego({"id": i}, {"usuario": usuario_sesion})

    def _avisar_amigos(self, usuario: str, mensaje: dict) -> None:
        """Envía un evento a los amigos conectados de `usuario`."""
        ok, amigos = self._almacen("listar_amigos", usuario)
        for amigo in amigos if ok else []:
            self.enviar_a_usuario(amigo, mensaje)

    def _avisar_presencia(self, usuario: str, en_linea: bool) -> None:
        self._avisar_amigos(usuario, {"evento": "en_linea",
                                      "datos": {"usuario": usuario, "en_linea": en_linea}})

    def _resumen_usuarios(self, nombres: list[str], quien: str = "") -> list[dict]:
        """[{usuario, nombre, foto, en_linea, apodo}] para una lista de nombres de usuario.

        apodo: el que `quien` le puso a cada uno (vacío si no tiene)."""
        with self._lock_almacen:
            apodos = dict(self.almacen.apodos.get(quien, {}))
        with self.lock_en_linea:
            conectados = set(self.en_linea)
        resumen = []
        for nombre in nombres:
            ok, perfil = self._almacen("obtener_perfil", nombre)
            if ok:
                resumen.append({"usuario": nombre, "nombre": perfil["nombre"],
                                "foto": perfil["foto"], "en_linea": nombre in conectados,
                                "apodo": apodos.get(nombre, "")})
        return resumen

    def detener(self) -> None:
        """Cierra conexiones, espera los hilos y persiste tras sus operaciones."""
        with self._lock_apagado:
            if self._apagado_completado:
                return
            if self._apagado_en_curso:
                esperar_apagado = True
            else:
                self._apagado_en_curso = True
                self._apagado_finalizado.clear()
                esperar_apagado = False
        if esperar_apagado:
            self._apagado_finalizado.wait()
            return

        apagado_correcto = False
        try:
            # El estado de aceptación puede estar apagado si aceptar_clientes
            # terminó por una interrupción; la limpieza debe ejecutarse igual.
            self._ejecutando.clear()
            servidor = self.socket_servidor
            self.socket_servidor = None
            if servidor is not None:
                try:
                    servidor.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                servidor.close()
            hilo_aceptacion = self._hilo_aceptacion
            if (hilo_aceptacion is not None
                    and hilo_aceptacion is not threading.current_thread()):
                hilo_aceptacion.join()

            # Tras terminar accept() ya no pueden registrarse conexiones nuevas.
            with self._lock_conexiones:
                conexiones = list(self._conexiones.items())
            for sock, sesion in conexiones:
                self.cerrar_cliente(sock, sesion.get("usuario"))

            # Cerrar los sockets despierta los hilos bloqueados en recv/send.
            # Los joins esperan también a las operaciones que ya se despachaban.
            with self._lock_conexiones:
                hilos_clientes = list(self._hilos)
            for hilo in hilos_clientes:
                if hilo is not threading.current_thread():
                    hilo.join()

            # Ningún hilo de cliente queda escribiendo cuando se hace el guardado.
            with self._lock_almacen:
                self.almacen.guardar_todo()
            apagado_correcto = True
        finally:
            with self._lock_apagado:
                self._apagado_en_curso = False
                self._apagado_completado = apagado_correcto
                self._apagado_finalizado.set()

    def accion_registrar(self, datos: dict, sesion: dict) -> dict:
        try:
            nombre = self._texto(datos, "nombre")
            usuario = self._texto(datos, "usuario")
            clave = self._texto(datos, "clave")
        except ValueError as exc:
            return self._respuesta(False, error=str(exc))
        id_usuario = datos.get("id")
        if not isinstance(id_usuario, str) or not id_usuario.strip():
            id_usuario = str(uuid.uuid4())
        if " " in usuario:
            return self._respuesta(False, error="El usuario no puede tener espacios.")
        ok, resultado = self._almacen(
            "registrar_usuario", id_usuario.strip(), nombre, usuario, clave
        )
        return self._respuesta(ok, {"mensaje": "Usuario registrado exitosamente"}
                               if ok else {}, "" if ok else str(resultado))

    def accion_login(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._texto(datos, "usuario")
            clave = self._texto(datos, "clave")
        except ValueError as exc:
            return self._respuesta(False, error=str(exc))
        if sesion.get("usuario"):
            return self._respuesta(False, error="Esta conexión ya inició sesión.")
        ok, perfil = self._almacen("validar_login", usuario, clave)
        if not ok:
            return self._respuesta(False, error=str(perfil))
        with self._lock_conexiones:
            sock_sesion = next(
                (sock for sock, estado in self._conexiones.items()
                 if estado is sesion), None
            )
        if sock_sesion is None:
            return self._respuesta(False, error="La conexión ya no está activa.")
        with self.lock_en_linea:
            if usuario in self.en_linea:
                return self._respuesta(False, error="Este usuario ya tiene una sesión activa.")
            self.en_linea[usuario] = sock_sesion
            sesion["usuario"] = usuario
        print(f"{usuario} inició sesión desde {sesion.get('addr')}")
        self._avisar_presencia(usuario, True)
        return self._respuesta(True, {"usuario": self._resultado(perfil),
                                     "sesion": "autenticada"})

    def accion_logout(self, datos: dict, sesion: dict) -> dict:
        usuario = sesion.get("usuario")
        if not usuario:
            return self._respuesta(False, error="No hay una sesión iniciada.")
        # El socket ya está asociado a la sesión; no hace falta recorrer el
        # mapa de conexiones. Se mantiene el lock de presencia para actualizar
        # atómicamente en_linea y el estado autenticado.
        sock = sesion.get("socket")
        if sock is None:
            # Compatibilidad con sesiones creadas fuera del bucle normal. La
            # consulta queda protegida y libera este lock antes de tomar el
            # lock de presencia, evitando una inversión con cerrar_cliente().
            with self._lock_conexiones:
                sock = next((s for s, estado in self._conexiones.items()
                             if estado is sesion), None)
        with self.lock_en_linea:
            salio = self.en_linea.get(usuario) is sock
            if salio:
                del self.en_linea[usuario]
            sesion["usuario"] = None
        if salio:
            self._avisar_presencia(usuario, False)
        return self._respuesta(True, {"mensaje": "Sesión cerrada."})

    def accion_buscar_usuarios(self, datos: dict, sesion: dict) -> dict:
        try:
            texto = self._texto(datos, "texto", requerido=False)
        except ValueError as exc:
            return self._respuesta(False, error=str(exc))
        ok, usuarios = self._almacen("buscar_usuarios", texto)
        if not ok:
            return self._respuesta(False, error=str(usuarios))
        yo = sesion.get("usuario")
        if yo:
            _, amigos = self._almacen("listar_amigos", yo)
            _, enviadas = self._almacen("listar_solicitudes_enviadas", yo)
            for u in usuarios:
                u["amigo"] = u["usuario"] in amigos
                u["pendiente"] = u["usuario"] in enviadas
        return self._respuesta(True, {"usuarios": self._resultado(usuarios)})

    def accion_ver_perfil(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._texto(datos, "usuario")
        except ValueError as exc:
            return self._respuesta(False, error=str(exc))
        ok, perfil = self._almacen("obtener_perfil", usuario)
        return self._respuesta(ok, {"perfil": self._resultado(perfil)} if ok else {},
                               "" if ok else str(perfil))

    def accion_editar_perfil(self, datos: dict, sesion: dict) -> dict:
        """Solo cambia los campos que llegan; valida cada uno."""
        try:
            usuario = self._requiere_login(sesion)
            campos = {}
            for campo in ("bio", "foto", "link", "banner", "color_perfil", "tema", "paleta"):
                if datos.get(campo) is not None:
                    campos[campo] = self._texto(datos, campo, requerido=False).strip()
            self._validar_perfil(campos)
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("editar_perfil", usuario, **campos)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def _validar_perfil(self, campos: dict) -> None:
        if len(campos.get("bio", "")) > MAX_BIO:
            raise ValueError(f"La bio admite como máximo {MAX_BIO} caracteres.")
        if len(campos.get("link", "")) > 200:
            raise ValueError("El link es demasiado largo.")
        for campo in ("foto", "banner"):
            if campos.get(campo) and self._ruta_imagen(campos[campo]) is None:
                raise ValueError(f"La imagen de '{campo}' no existe en el servidor.")
        color = campos.get("color_perfil")
        if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("El color debe tener el formato #RRGGBB.")
        if campos.get("tema") and campos["tema"] not in TEMAS:
            raise ValueError("El tema debe ser 'claro' u 'oscuro'.")
        if len(campos.get("paleta", "")) > 20:
            raise ValueError("Nombre de paleta inválido.")

    def accion_enviar_solicitud(self, datos: dict, sesion: dict) -> dict:
        try:
            origen = self._requiere_login(sesion)
            destino = self._texto(datos, "destino")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("enviar_solicitud", origen, destino)
        if ok:
            self.enviar_a_usuario(destino, {"evento": "nueva_solicitud",
                                             "datos": {"origen": origen,
                                                       "destino": destino}})
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def accion_responder_solicitud(self, datos: dict, sesion: dict) -> dict:
        try:
            destino = self._requiere_login(sesion)
            origen = self._texto(datos, "origen")
            aceptar = datos.get("aceptar")
            if not isinstance(aceptar, bool):
                raise ValueError("El campo 'aceptar' debe ser booleano.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("responder_solicitud", destino, origen, aceptar)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def _lista_usuarios(self, sesion: dict, metodo: str, campo: str) -> dict:
        def operacion(usuario):
            ok, nombres = self._almacen(metodo, usuario)
            return (ok, self._resumen_usuarios(nombres, usuario) if ok else nombres)
        return self._protegida(sesion, operacion, campo)

    def accion_listar_solicitudes(self, datos: dict, sesion: dict) -> dict:
        return self._lista_usuarios(sesion, "listar_solicitudes", "solicitudes")

    def accion_listar_amigos(self, datos: dict, sesion: dict) -> dict:
        return self._lista_usuarios(sesion, "listar_amigos", "amigos")

    def accion_eliminar_amigo(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            amigo = self._texto(datos, "amigo")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("eliminar_amigo", usuario, amigo)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def accion_publicar(self, datos: dict, sesion: dict) -> dict:
        try:
            autor = self._requiere_login(sesion)
            texto = self._texto(datos, "texto", requerido=False).strip()
            link = self._texto(datos, "link", requerido=False)
            extra = self._texto(datos, "extra", requerido=False)
            imagen = self._guardar_imagen(datos.get("imagen", ""))
            archivo = nombre_archivo = ""
            if datos.get("archivo"):
                nombre_archivo = os.path.basename(self._texto(datos, "nombre_archivo"))[:120]
                archivo = self._guardar_adjunto(datos["archivo"], nombre_archivo)
        except (PermissionError, ValueError, TypeError, binascii.Error) as exc:
            return self._respuesta(False, error=str(exc))
        # el archivo va aparte solo si hay uno: así se respeta la firma original de 5 datos
        adjunto = (archivo, nombre_archivo) if archivo else ()
        ok, resultado = self._almacen("crear_publicacion", autor, texto, imagen, link, extra,
                                      *adjunto)
        if not ok:
            return self._respuesta(False, error=str(resultado))
        publicacion = self._resultado(resultado)
        self._avisar_amigos(autor, {"evento": "nueva_publicacion", "datos": {"autor": autor}})
        return self._respuesta(True, {"id_publicacion": publicacion["id"],
                                     "publicacion": publicacion})

    def _guardar_imagen(self, imagen: Any) -> str:
        """Guarda base64 en la carpeta de imágenes tras aplicar el límite."""
        if imagen in (None, ""):
            return ""
        if not isinstance(imagen, str):
            raise ValueError("El campo 'imagen' debe ser texto base64.")
        try:
            contenido = base64.b64decode(imagen, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("La imagen debe estar codificada en base64 válido.") from exc
        if len(contenido) > MAX_IMAGEN_BYTES:
            raise ValueError("La imagen excede el límite de 2 MB.")
        extension = next((ext for firma, ext in FIRMAS_IMAGEN
                          if contenido.startswith(firma)), None)
        if extension is None:
            raise ValueError("Formato no permitido: usa PNG, JPG o GIF.")
        carpeta = self.almacen.carpeta_datos / "imagenes"
        nombre = guardar_imagen(imagen, str(carpeta))
        if extension != ".jpg":
            nuevo = nombre[:-4] + extension
            os.replace(carpeta / nombre, carpeta / nuevo)
            nombre = nuevo
        return nombre

    def _ruta_imagen(self, nombre: str):
        """Ruta de una imagen guardada, o None. Rechaza rutas con carpetas."""
        if not nombre or os.path.basename(nombre) != nombre or nombre.startswith("."):
            return None
        ruta = self.almacen.carpeta_datos / "imagenes" / nombre
        return ruta if ruta.is_file() else None

    def accion_subir_imagen(self, datos: dict, sesion: dict) -> dict:
        """Guarda una imagen (foto de perfil o banner) y devuelve su nombre."""
        try:
            self._requiere_login(sesion)
            nombre = self._guardar_imagen(datos.get("imagen"))
            if not nombre:
                raise ValueError("Falta la imagen.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        return self._respuesta(True, {"nombre": nombre})

    def accion_obtener_imagen(self, datos: dict, sesion: dict) -> dict:
        """Devuelve una imagen guardada en base64 para que el cliente la muestre."""
        try:
            self._requiere_login(sesion)
            nombre = self._texto(datos, "nombre")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ruta = self._ruta_imagen(nombre)
        if ruta is None:
            return self._respuesta(False, error="La imagen no existe.")
        contenido = base64.b64encode(ruta.read_bytes()).decode("ascii")
        return self._respuesta(True, {"nombre": nombre, "imagen": contenido})

    def accion_obtener_muro(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
        except PermissionError as exc:
            return self._respuesta(False, error=str(exc))
        ok, muro = self._almacen("obtener_muro", usuario)
        return self._respuesta(ok, {"publicaciones": self._resultado(muro)} if ok else {},
                               "" if ok else str(muro))

    def accion_dar_like(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            id_publicacion = self._texto(datos, "id_publicacion")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("dar_like", id_publicacion, usuario)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def accion_editar_publicacion(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            id_publicacion = self._texto(datos, "id_publicacion")
            texto = self._texto(datos, "texto", requerido=False).strip()
            if len(texto) > 2000:
                raise ValueError("La publicación es demasiado larga.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("editar_publicacion", id_publicacion, usuario, texto)
        return self._respuesta(ok, {"publicacion": self._resultado(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def accion_eliminar_publicacion(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            id_publicacion = self._texto(datos, "id_publicacion")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("eliminar_publicacion", id_publicacion, usuario)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def accion_poner_apodo(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            amigo = self._texto(datos, "amigo")
            apodo = self._texto(datos, "apodo", requerido=False).strip()
            if len(apodo) > 32:
                raise ValueError("El apodo puede tener como máximo 32 caracteres.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("poner_apodo", usuario, amigo, apodo)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    # ------------------------------------------------------------------ juegos
    LIMITES_PUNTAJE = {"serpiente": 4000, "buscaminas": 1000}

    def accion_enviar_puntaje(self, datos: dict, sesion: dict) -> dict:
        """Puntaje de un juego de un jugador (serpiente o buscaminas)."""
        try:
            usuario = self._requiere_login(sesion)
            juego = self._texto(datos, "juego")
            puntos = datos.get("puntos")
            if juego not in self.LIMITES_PUNTAJE:
                raise ValueError("Juego desconocido.")
            if not isinstance(puntos, int) or not 0 <= puntos <= self.LIMITES_PUNTAJE[juego]:
                raise ValueError("Puntaje inválido.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, mejor = self._almacen("registrar_puntaje", juego, usuario, puntos)
        return self._respuesta(ok, {"mejor": mejor} if ok else {}, "" if ok else str(mejor))

    def accion_leaderboard(self, datos: dict, sesion: dict) -> dict:
        """Tabla del juego + quién lo está jugando ahora (y contra quién)."""
        try:
            self._requiere_login(sesion)
            juego = self._texto(datos, "juego")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, tabla = self._almacen("leaderboard", juego)
        if not ok:
            return self._respuesta(False, error=str(tabla))
        with self._lock_juegos:
            jugando = [u for u, j in self.jugando.items() if j == juego]
            duelos = [[p["x"], p["o"]] for p in self.partidas.values()
                      if not p["ganador"] and juego == "tres_en_raya"]
        return self._respuesta(True, {"tabla": tabla, "jugando": jugando, "duelos": duelos})

    def accion_jugando(self, datos: dict, sesion: dict) -> dict:
        """Marca (o quita, con juego vacío) que el usuario está jugando."""
        try:
            usuario = self._requiere_login(sesion)
            juego = self._texto(datos, "juego", requerido=False)
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        with self._lock_juegos:
            if juego:
                self.jugando[usuario] = juego
            else:
                self.jugando.pop(usuario, None)
        return self._respuesta(True)

    def accion_invitar_juego(self, datos: dict, sesion: dict) -> dict:
        try:
            origen = self._requiere_login(sesion)
            destino = self._texto(datos, "amigo")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        _, amigos = self._almacen("listar_amigos", origen)
        if destino not in amigos:
            return self._respuesta(False, error="Solo puedes retar a tus amigos.")
        with self.lock_en_linea:
            conectado = destino in self.en_linea
        if not conectado:
            return self._respuesta(False, error=f"@{destino} no está conectado.")
        with self._lock_juegos:
            self.invitaciones.add((origen, destino))
        self.enviar_a_usuario(destino, {"evento": "invitacion_juego",
                                        "datos": {"origen": origen, "juego": "tres_en_raya"}})
        return self._respuesta(True, {"mensaje": "Invitación enviada."})

    def accion_responder_juego(self, datos: dict, sesion: dict) -> dict:
        try:
            destino = self._requiere_login(sesion)
            origen = self._texto(datos, "origen")
            aceptar = bool(datos.get("aceptar"))
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        with self._lock_juegos:
            if (origen, destino) not in self.invitaciones:
                return self._respuesta(False, error="La invitación ya no existe.")
            self.invitaciones.discard((origen, destino))
            partida = None
            if aceptar:
                partida = {"id": uuid.uuid4().hex, "x": origen, "o": destino,
                           "tablero": [""] * 9, "turno": origen, "ganador": "", "linea": []}
                self.partidas[partida["id"]] = partida
                self.jugando[origen] = self.jugando[destino] = "tres_en_raya"
                partida = dict(partida)
        if not aceptar:
            self.enviar_a_usuario(origen, {"evento": "juego_rechazado", "datos": {"usuario": destino}})
            return self._respuesta(True)
        self.enviar_a_usuario(origen, {"evento": "partida", "datos": partida})
        return self._respuesta(True, {"partida": partida})

    LINEAS = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8),
              (0, 4, 8), (2, 4, 6))

    def _terminar_partida(self, p: dict, ganador: str) -> list:
        """Marca el final y devuelve [(usuario, puntos)]: gana 3, empate 1 a cada uno.
        Se llama con _lock_juegos tomado."""
        p["ganador"] = ganador
        for u in (p["x"], p["o"]):
            self.jugando.pop(u, None)
        if ganador == "empate":
            return [(p["x"], 1), (p["o"], 1)]
        return [(ganador, 3)]

    def accion_jugada(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            id_partida = self._texto(datos, "id")
            casilla = datos.get("casilla")
            if not isinstance(casilla, int) or not 0 <= casilla <= 8:
                raise ValueError("Casilla inválida.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        puntos = []
        with self._lock_juegos:
            p = self.partidas.get(id_partida)
            if p is None or usuario not in (p["x"], p["o"]):
                return self._respuesta(False, error="La partida no existe.")
            if p["ganador"]:
                return self._respuesta(False, error="La partida ya terminó.")
            if p["turno"] != usuario:
                return self._respuesta(False, error="No es tu turno.")
            if p["tablero"][casilla]:
                return self._respuesta(False, error="Esa casilla está ocupada.")
            ficha = "X" if usuario == p["x"] else "O"
            p["tablero"][casilla] = ficha
            linea = next((l for l in self.LINEAS if all(p["tablero"][i] == ficha for i in l)), None)
            if linea:
                p["linea"] = list(linea)
                puntos = self._terminar_partida(p, usuario)
            elif all(p["tablero"]):
                puntos = self._terminar_partida(p, "empate")
            else:
                p["turno"] = p["o"] if usuario == p["x"] else p["x"]
            copia = dict(p, tablero=list(p["tablero"]))
            if p["ganador"]:
                del self.partidas[id_partida]
        for u, n in puntos:
            self._almacen("registrar_puntaje", "tres_en_raya", u, n)
        rival = copia["o"] if usuario == copia["x"] else copia["x"]
        self.enviar_a_usuario(rival, {"evento": "partida", "datos": copia})
        return self._respuesta(True, {"partida": copia})

    def accion_abandonar_juego(self, datos: dict, sesion: dict) -> dict:
        """Cerrar la ventana a mitad de partida: gana el rival."""
        try:
            usuario = self._requiere_login(sesion)
            id_partida = self._texto(datos, "id")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        with self._lock_juegos:
            p = self.partidas.pop(id_partida, None)
            if p is None or usuario not in (p["x"], p["o"]) or p["ganador"]:
                return self._respuesta(True)
            rival = p["o"] if usuario == p["x"] else p["x"]
            self._terminar_partida(p, rival)
            p["abandono"] = usuario
            copia = dict(p)
        self._almacen("registrar_puntaje", "tres_en_raya", rival, 3)
        self.enviar_a_usuario(rival, {"evento": "partida", "datos": copia})
        return self._respuesta(True)

    def accion_reaccionar(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            id_publicacion = self._texto(datos, "id_publicacion")
            emoji = self._texto(datos, "emoji")
            if emoji not in EMOJIS_REACCION:
                raise ValueError("Reacción no permitida.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("reaccionar", id_publicacion, usuario, emoji)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

    def accion_enviar_chat(self, datos: dict, sesion: dict) -> dict:
        """Mensaje de texto, imagen, sticker, archivo, audio o encuesta."""
        try:
            emisor = self._requiere_login(sesion)
            receptor = self._texto(datos, "receptor")
            tipo = datos.get("tipo") or "texto"
            if tipo not in TIPOS_CHAT:
                raise ValueError("Tipo de mensaje no permitido.")
            texto = self._texto(datos, "texto", requerido=tipo == "texto")
            if len(texto) > 2000:
                raise ValueError("El mensaje es demasiado largo.")
            extra = {"tipo": tipo}
            if datos.get("responde_a"):
                extra["responde_a"] = self._texto(datos, "responde_a")
            if tipo in ("imagen", "sticker"):
                extra["adjunto"] = self._guardar_imagen(datos.get("adjunto"))
            elif tipo in ("archivo", "audio"):
                nombre = os.path.basename(self._texto(datos, "nombre_archivo"))[:120]
                extra["adjunto"] = self._guardar_adjunto(datos.get("adjunto"), nombre)
                extra["nombre_archivo"] = nombre
            elif tipo == "encuesta":
                extra["encuesta"] = self._validar_encuesta(datos.get("encuesta"))
            if tipo != "texto" and tipo != "encuesta" and not extra.get("adjunto"):
                raise ValueError("Falta el archivo adjunto.")
        except (PermissionError, ValueError, TypeError) as exc:
            return self._respuesta(False, error=str(exc))
        ok_amigos, amigos = self._almacen("listar_amigos", emisor)
        if receptor != SALA and (not ok_amigos or receptor not in amigos):
            return self._respuesta(False, error="Solo puedes enviar mensajes a tus amigos.")
        with self._lock_almacen:
            ok, resultado = self.almacen.guardar_chat(emisor, receptor, texto, **extra)
            if not ok:
                return self._respuesta(False, error=str(resultado))
            _, historial = self.almacen.obtener_chat(emisor, receptor)
            mensaje = historial[-1]
        entregado = self._difundir_chat(emisor, receptor,
                                        {"evento": "nuevo_mensaje", "datos": mensaje})
        return self._respuesta(True, {"mensaje": "Mensaje guardado.",
                                     "entregado": entregado, "chat": mensaje})

    def _difundir_chat(self, emisor: str, receptor: str, evento: dict) -> bool:
        """Envía un evento de chat al otro usuario o a todos en la sala general."""
        if receptor == SALA:
            with self.lock_en_linea:
                conectados = [u for u in self.en_linea if u != emisor]
            return any([self.enviar_a_usuario(u, evento) for u in conectados])
        return self.enviar_a_usuario(receptor, evento)

    def _guardar_adjunto(self, contenido_b64: Any, nombre: str) -> str:
        """Guarda un archivo del chat (≤ 2 MB, sin ejecutables) y devuelve su nombre."""
        if not isinstance(contenido_b64, str) or not contenido_b64:
            raise ValueError("Falta el archivo adjunto.")
        extension = os.path.splitext(nombre)[1].lower()
        if not nombre or extension in EXTENSIONES_BLOQUEADAS or len(extension) > 10:
            raise ValueError("Ese tipo de archivo no está permitido.")
        try:
            contenido = base64.b64decode(contenido_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("El archivo debe estar codificado en base64 válido.") from exc
        if len(contenido) > MAX_IMAGEN_BYTES:
            raise ValueError("El archivo excede el límite de 2 MB.")
        carpeta = self.almacen.carpeta_datos / "imagenes"
        carpeta.mkdir(parents=True, exist_ok=True)
        guardado = uuid.uuid4().hex + extension
        (carpeta / guardado).write_bytes(contenido)
        return guardado

    @staticmethod
    def _validar_encuesta(encuesta: Any) -> dict:
        if not isinstance(encuesta, dict):
            raise ValueError("Encuesta inválida.")
        pregunta = encuesta.get("pregunta")
        opciones = encuesta.get("opciones")
        if not isinstance(pregunta, str) or not pregunta.strip() or len(pregunta) > 200:
            raise ValueError("La pregunta debe tener entre 1 y 200 caracteres.")
        if not isinstance(opciones, list) or not 2 <= len(opciones) <= 4 or not all(
                isinstance(o, str) and o.strip() and len(o) <= 80 for o in opciones):
            raise ValueError("La encuesta necesita de 2 a 4 opciones (máx. 80 caracteres).")
        return {"pregunta": pregunta.strip(),
                "opciones": [{"texto": o.strip(), "votos": []} for o in opciones]}

    def accion_actualizar_mensaje(self, datos: dict, sesion: dict) -> dict:
        """editar / eliminar (solo el autor), reaccionar o votar en un mensaje."""
        try:
            usuario = self._requiere_login(sesion)
            con = self._texto(datos, "con")
            id_mensaje = self._texto(datos, "id")
            accion = self._texto(datos, "accion")
            valor = datos.get("valor")
            if accion == "editar":
                valor = self._texto(datos, "valor")
                if len(valor) > 2000:
                    raise ValueError("El mensaje es demasiado largo.")
            if accion == "reaccionar" and (not isinstance(valor, str) or not 0 < len(valor) <= 16):
                raise ValueError("Reacción inválida.")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok_amigos, amigos = self._almacen("listar_amigos", usuario)
        if con != SALA and (not ok_amigos or con not in amigos):
            return self._respuesta(False, error="Solo puedes usar el chat con tus amigos.")
        ok, mensaje = self._almacen("actualizar_mensaje", usuario, con, id_mensaje, accion, valor)
        if not ok:
            return self._respuesta(False, error=str(mensaje))
        self._difundir_chat(usuario, con, {"evento": "mensaje_actualizado", "datos": mensaje})
        return self._respuesta(True, {"chat": mensaje})

    def accion_obtener_chat(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            interlocutor = self._texto(datos, "b")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok_amigos, amigos = self._almacen("listar_amigos", usuario)
        if interlocutor != SALA and (not ok_amigos or interlocutor not in amigos):
            return self._respuesta(False, error="El historial está disponible entre amigos.")
        ok, mensajes = self._almacen("obtener_chat", usuario, interlocutor)
        return self._respuesta(ok, {"mensajes": self._resultado(mensajes)} if ok else {},
                               "" if ok else str(mensajes))

    def accion_sugerencias(self, datos: dict, sesion: dict) -> dict:
        return self._protegida(sesion,
            lambda usuario: self._almacen("sugerir_amigos", usuario), "sugerencias")


def _ip_local() -> str:
    """IP de esta computadora en la red local (la que escriben los demás)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no envía nada; solo elige la interfaz
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    servidor = Servidor(Almacen())
    print(f"Los clientes deben conectarse a la IP {_ip_local()} puerto {PUERTO_DEFECTO}")
    try:
        # 0.0.0.0 acepta conexiones de otras computadoras, no solo de esta.
        servidor.iniciar("0.0.0.0", PUERTO_DEFECTO)
    except KeyboardInterrupt:
        print("Deteniendo servidor Social UNA...")
        servidor.detener()
