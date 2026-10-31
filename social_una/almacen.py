"""Almacenamiento de datos en memoria y disco para Social UNA.

La clase Almacen gestiona usuarios, amistades, solicitudes, publicaciones
y chats. Todo se persiste en archivos JSON dentro de la carpeta datos/.
"""

import json
import os
import threading
import uuid
from datetime import datetime
from typing import Any

from modelos import Usuario, Publicacion, Mensaje


class Almacen:
    """Gestiona todos los datos de la red social en memoria y disco."""

    def __init__(self, carpeta_datos: str = "datos") -> None:
        self.carpeta_datos = carpeta_datos
        self.usuarios: list[Usuario] = []
        self.amistades: dict[str, list[str]] = {}
        self.solicitudes: dict[str, list[str]] = {}
        self.publicaciones: list[Publicacion] = []
        self.chats: dict[str, list[Mensaje]] = {}
        self.lock = threading.Lock()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def cargar_todo(self) -> None:
        """Carga todos los datos desde los archivos JSON."""
        raise NotImplementedError

    def guardar_todo(self) -> None:
        """Guarda todos los datos en los archivos JSON."""
        raise NotImplementedError

    @staticmethod
    def hash_clave(clave: str) -> str:
        """Devuelve el hash de una clave."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Usuarios y perfil
    # ------------------------------------------------------------------
    def registrar_usuario(self, id: str, nombre: str, usuario: str,
                          clave: str) -> tuple[bool, Any]:
        """Registra un nuevo usuario."""
        raise NotImplementedError

    def validar_login(self, usuario: str, clave: str) -> tuple[bool, Any]:
        """Valida las credenciales de login."""
        raise NotImplementedError

    def obtener_perfil(self, usuario: str) -> tuple[bool, Any]:
        """Devuelve el perfil de un usuario."""
        raise NotImplementedError

    def editar_perfil(self, usuario: str, bio: str, foto: str,
                      link: str) -> tuple[bool, Any]:
        """Edita el perfil de un usuario."""
        raise NotImplementedError

    def buscar_usuarios(self, texto: str) -> tuple[bool, Any]:
        """Busca usuarios por nombre o nombre de usuario."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Amistades y solicitudes
    # ------------------------------------------------------------------
    def enviar_solicitud(self, origen: str, destino: str) -> tuple[bool, Any]:
        """Envía una solicitud de amistad."""
        raise NotImplementedError

    def responder_solicitud(self, destino: str, origen: str,
                            aceptar: bool) -> tuple[bool, Any]:
        """Acepta o rechaza una solicitud de amistad."""
        raise NotImplementedError

    def listar_solicitudes(self, usuario: str) -> tuple[bool, Any]:
        """Lista las solicitudes de amistad pendientes de un usuario."""
        raise NotImplementedError

    def listar_amigos(self, usuario: str) -> tuple[bool, Any]:
        """Lista los amigos de un usuario."""
        raise NotImplementedError

    def eliminar_amigo(self, a: str, b: str) -> tuple[bool, Any]:
        """Elimina la amistad entre dos usuarios."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Publicaciones y muro
    # ------------------------------------------------------------------
    def crear_publicacion(self, autor: str, texto: str, imagen: str,
                          link: str, extra: str) -> tuple[bool, Any]:
        """Crea una nueva publicación."""
        raise NotImplementedError

    def obtener_muro(self, usuario: str) -> tuple[bool, Any]:
        """Devuelve las publicaciones del muro de un usuario (propias +
        de amigos), de la más reciente a la más antigua."""
        raise NotImplementedError

    def dar_like(self, id_publicacion: str, usuario: str) -> tuple[bool, Any]:
        """Agrega o quita un like de una publicación."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def guardar_chat(self, emisor: str, receptor: str, texto: str
                     ) -> tuple[bool, Any]:
        """Guarda un mensaje de chat."""
        raise NotImplementedError

    def obtener_chat(self, a: str, b: str) -> tuple[bool, Any]:
        """Devuelve la conversación entre dos usuarios."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Sugerencias
    # ------------------------------------------------------------------
    def sugerir_amigos(self, usuario: str) -> tuple[bool, Any]:
        """Sugiere amigos basados en amigos de amigos."""
        raise NotImplementedError

    def amigos_en_comun(self, a: str, b: str) -> tuple[bool, Any]:
        """Devuelve los amigos en común entre dos usuarios."""
        raise NotImplementedError