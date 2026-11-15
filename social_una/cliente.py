"""Cliente de Social UNA.

Se conecta al servidor mediante TCP, envía peticiones y recibe
eventos asincrónicos a través de una cola pública.
"""

import queue
import socket
import threading
from typing import Any

from protocolo import (
    HOST_DEFECTO, PUERTO_DEFECTO, enviar_mensaje, recibir_mensaje,
)


class ClienteSocial:
    """Cliente de la red social Social UNA."""

    def __init__(self) -> None:
        self.socket: socket.socket | None = None
        self.cola_eventos: queue.Queue[dict] = queue.Queue()
        self._hilo_escucha: threading.Thread | None = None
        self._ejecutando = False

    def conectar(self, host: str = HOST_DEFECTO,
                 puerto: int = PUERTO_DEFECTO) -> bool:
        """Conecta al servidor y lanza el hilo de escucha."""
        raise NotImplementedError

    def desconectar(self) -> None:
        """Desconecta del servidor y detiene el hilo de escucha."""
        raise NotImplementedError

    def enviar_peticion(self, accion: str, datos: dict) -> dict | None:
        """Envía una petición al servidor y espera su respuesta."""
        raise NotImplementedError

    def _escuchar(self) -> None:
        """Hilo de escucha: recibe mensajes y los mete en cola_eventos."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Métodos públicos para la GUI
    # ------------------------------------------------------------------
    def registrar(self, nombre: str, usuario: str, clave: str) -> dict | None:
        raise NotImplementedError

    def login(self, usuario: str, clave: str) -> dict | None:
        raise NotImplementedError

    def logout(self) -> dict | None:
        raise NotImplementedError

    def buscar_usuarios(self, texto: str) -> dict | None:
        raise NotImplementedError

    def ver_perfil(self, usuario: str) -> dict | None:
        raise NotImplementedError

    def editar_perfil(self, bio: str, foto: str, link: str) -> dict | None:
        raise NotImplementedError

    def enviar_solicitud(self, origen: str, destino: str) -> dict | None:
        raise NotImplementedError

    def responder_solicitud(self, destino: str, origen: str,
                            aceptar: bool) -> dict | None:
        raise NotImplementedError

    def listar_amigos(self, usuario: str) -> dict | None:
        raise NotImplementedError

    def publicar(self, texto: str, ruta_imagen: str, link: str
                 ) -> dict | None:
        raise NotImplementedError

    def obtener_muro(self, usuario: str) -> dict | None:
        raise NotImplementedError

    def dar_like(self, id_publicacion: str, usuario: str) -> dict | None:
        raise NotImplementedError

    def enviar_chat(self, emisor: str, receptor: str, texto: str
                    ) -> dict | None:
        raise NotImplementedError

    def obtener_chat(self, a: str, b: str) -> dict | None:
        raise NotImplementedError

    def sugerencias(self, usuario: str) -> dict | None:
        raise NotImplementedError


if __name__ == "__main__":
    # TODO: prueba rápida por consola
    pass