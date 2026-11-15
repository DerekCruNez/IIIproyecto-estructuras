"""Servidor TCP de Social UNA.

Cada conexión se atiende en un hilo y conserva su propio estado de sesión.
El almacenamiento serializa las operaciones para mantener consistentes sus
estructuras compartidas. Los mensajes se enmarcan exclusivamente mediante las
funciones definidas en :mod:`protocolo`.
"""

import base64
import binascii
import json
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

    def _almacen(self, metodo: str, *args: Any) -> tuple[bool, Any]:
        """Serializa las operaciones de negocio sobre Almacen."""
        with self._lock_almacen:
            return getattr(self.almacen, metodo)(*args)

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
            if usuario_sesion and self.en_linea.get(usuario_sesion) is sock:
                del self.en_linea[usuario_sesion]
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError as exc:
            print(f"Error cerrando socket de cliente: {exc}")

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
        ok, resultado = self._almacen(
            "registrar_usuario", str(uuid.uuid4()), nombre, usuario, clave
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
            if self.en_linea.get(usuario) is sock:
                del self.en_linea[usuario]
            sesion["usuario"] = None
        return self._respuesta(True, {"mensaje": "Sesión cerrada."})

    def accion_buscar_usuarios(self, datos: dict, sesion: dict) -> dict:
        try:
            texto = self._texto(datos, "texto", requerido=False)
        except ValueError as exc:
            return self._respuesta(False, error=str(exc))
        ok, usuarios = self._almacen("buscar_usuarios", texto)
        return self._respuesta(ok, {"usuarios": self._resultado(usuarios)} if ok else {},
                               "" if ok else str(usuarios))

    def accion_ver_perfil(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._texto(datos, "usuario")
        except ValueError as exc:
            return self._respuesta(False, error=str(exc))
        ok, perfil = self._almacen("obtener_perfil", usuario)
        return self._respuesta(ok, {"perfil": self._resultado(perfil)} if ok else {},
                               "" if ok else str(perfil))

    def accion_editar_perfil(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            campos = [self._texto(datos, campo, requerido=False)
                      for campo in ("bio", "foto", "link")]
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("editar_perfil", usuario, *campos)
        return self._respuesta(ok, {"mensaje": str(resultado)} if ok else {},
                               "" if ok else str(resultado))

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

    def accion_listar_solicitudes(self, datos: dict, sesion: dict) -> dict:
        return self._protegida(sesion,
            lambda usuario: self._almacen("listar_solicitudes", usuario), "solicitudes")

    def accion_listar_amigos(self, datos: dict, sesion: dict) -> dict:
        return self._protegida(sesion,
            lambda usuario: self._almacen("listar_amigos", usuario), "amigos")

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
            texto = self._texto(datos, "texto")
            link = self._texto(datos, "link", requerido=False)
            extra = self._texto(datos, "extra", requerido=False)
            imagen = self._guardar_imagen(datos.get("imagen", ""))
        except (PermissionError, ValueError, TypeError, binascii.Error) as exc:
            return self._respuesta(False, error=str(exc))
        ok, resultado = self._almacen("crear_publicacion", autor, texto, imagen, link, extra)
        if not ok:
            return self._respuesta(False, error=str(resultado))
        publicacion = self._resultado(resultado)
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
        return guardar_imagen(imagen, str(self.almacen.carpeta_datos / "imagenes"))

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

    def accion_enviar_chat(self, datos: dict, sesion: dict) -> dict:
        try:
            emisor = self._requiere_login(sesion)
            receptor = self._texto(datos, "receptor")
            texto = self._texto(datos, "texto")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok_amigos, amigos = self._almacen("listar_amigos", emisor)
        if not ok_amigos or receptor not in amigos:
            return self._respuesta(False, error="Solo puedes enviar mensajes a tus amigos.")
        with self._lock_almacen:
            ok, resultado = self.almacen.guardar_chat(emisor, receptor, texto)
            if not ok:
                return self._respuesta(False, error=str(resultado))
            _, historial = self.almacen.obtener_chat(emisor, receptor)
            mensaje = historial[-1]
        entregado = self.enviar_a_usuario(receptor, {"evento": "nuevo_mensaje",
                                                     "datos": mensaje})
        return self._respuesta(True, {"mensaje": "Mensaje guardado.",
                                     "entregado": entregado})

    def accion_obtener_chat(self, datos: dict, sesion: dict) -> dict:
        try:
            usuario = self._requiere_login(sesion)
            interlocutor = self._texto(datos, "b")
        except (PermissionError, ValueError) as exc:
            return self._respuesta(False, error=str(exc))
        ok_amigos, amigos = self._almacen("listar_amigos", usuario)
        if not ok_amigos or interlocutor not in amigos:
            return self._respuesta(False, error="El historial está disponible entre amigos.")
        ok, mensajes = self._almacen("obtener_chat", usuario, interlocutor)
        return self._respuesta(ok, {"mensajes": self._resultado(mensajes)} if ok else {},
                               "" if ok else str(mensajes))

    def accion_sugerencias(self, datos: dict, sesion: dict) -> dict:
        return self._protegida(sesion,
            lambda usuario: self._almacen("sugerir_amigos", usuario), "sugerencias")


if __name__ == "__main__":
    servidor = Servidor(Almacen())
    try:
        servidor.iniciar()
    except KeyboardInterrupt:
        print("Deteniendo servidor Social UNA...")
        servidor.detener()
