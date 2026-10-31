"""Servidor de Social UNA.

Atiende conexiones TCP de clientes, despacha peticiones y gestiona
sesiones de usuario en línea.
"""

import socket
import threading
from typing import Any

from almacen import Almacen
from protocolo import (
    HOST_DEFECTO, PUERTO_DEFECTO, enviar_mensaje, recibir_mensaje,
)


class Servidor:
    """Servidor TCP de la red social Social UNA."""

    def __init__(self, almacen: Almacen) -> None:
        self.almacen = almacen
        self.socket_servidor: socket.socket | None = None
        self.en_linea: dict[str, socket.socket] = {}
        self.lock_en_linea = threading.Lock()
        self._ejecutando = False

    def iniciar(self, host: str = HOST_DEFECTO,
                puerto: int = PUERTO_DEFECTO) -> None:
        """Inicia el servidor y comienza a escuchar conexiones."""
        raise NotImplementedError

    def aceptar_clientes(self) -> None:
        """Bucle principal de aceptación de conexiones entrantes."""
        raise NotImplementedError

    def atender_cliente(self, sock: socket.socket, addr: tuple[str, int]) -> None:
        """Atiende a un cliente conectado en un hilo dedicado.

        Lee peticiones del socket, las despacha y envía respuestas.
        Maneja desconexiones inesperadas.
        """
        raise NotImplementedError

    def despachar(self, peticion: dict, sesion: dict[str, Any]) -> dict:
        """Despacha una petición a la acción correspondiente.

        Utiliza un dict que mapea nombres de acción a métodos del servidor.
        """
        raise NotImplementedError

    def enviar_a_usuario(self, usuario: str, mensaje: dict) -> bool:
        """Envía un mensaje (evento) a un usuario si está en línea."""
        raise NotImplementedError

    def cerrar_cliente(self, sock: socket.socket,
                       usuario: str | None = None) -> None:
        """Cierra la conexión de un cliente y limpia su sesión."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Acciones (stubs)
    # ------------------------------------------------------------------
    def accion_registrar(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_login(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_logout(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_buscar_usuarios(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_ver_perfil(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_editar_perfil(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_enviar_solicitud(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_responder_solicitud(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_listar_solicitudes(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_listar_amigos(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_publicar(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_obtener_muro(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_dar_like(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_enviar_chat(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_obtener_chat(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError

    def accion_sugerencias(self, datos: dict, sesion: dict) -> dict:
        raise NotImplementedError


if __name__ == "__main__":
    # TODO: iniciar servidor con valores por defecto
    pass