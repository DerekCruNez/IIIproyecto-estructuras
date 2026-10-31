"""Modelos de datos para Social UNA.

Define las clases Usuario, Publicacion y Mensaje con serialización
a diccionario y reconstrucción desde diccionario.
"""

from datetime import datetime


class Usuario:
    """Representa un usuario de la red social."""

    def __init__(self, id: str, nombre: str, usuario: str, clave_hash: str,
                 bio: str = "", foto: str = "", link: str = "") -> None:
        self.id = id
        self.nombre = nombre
        self.usuario = usuario
        self.clave_hash = clave_hash
        self.bio = bio
        self.foto = foto
        self.link = link

    def a_dict(self) -> dict:
        """Convierte el usuario a un diccionario serializable."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "clave_hash": self.clave_hash,
            "bio": self.bio,
            "foto": self.foto,
            "link": self.link,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Usuario":
        """Crea un Usuario a partir de un diccionario."""
        return cls(
            id=datos["id"],
            nombre=datos["nombre"],
            usuario=datos["usuario"],
            clave_hash=datos["clave_hash"],
            bio=datos.get("bio", ""),
            foto=datos.get("foto", ""),
            link=datos.get("link", ""),
        )


class Publicacion:
    """Representa una publicación en el muro."""

    def __init__(self, id: str, autor: str, texto: str, imagen: str = "",
                 link: str = "", fecha: str = "", likes: list | None = None,
                 extra: str = "") -> None:
        self.id = id
        self.autor = autor
        self.texto = texto
        self.imagen = imagen
        self.link = link
        self.fecha = fecha or datetime.now().isoformat()
        self.likes = likes if likes is not None else []
        self.extra = extra

    def a_dict(self) -> dict:
        """Convierte la publicación a un diccionario serializable."""
        return {
            "id": self.id,
            "autor": self.autor,
            "texto": self.texto,
            "imagen": self.imagen,
            "link": self.link,
            "fecha": self.fecha,
            "likes": self.likes,
            "extra": self.extra,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Publicacion":
        """Crea una Publicacion a partir de un diccionario."""
        return cls(
            id=datos["id"],
            autor=datos["autor"],
            texto=datos["texto"],
            imagen=datos.get("imagen", ""),
            link=datos.get("link", ""),
            fecha=datos.get("fecha", ""),
            likes=datos.get("likes", []),
            extra=datos.get("extra", ""),
        )


class Mensaje:
    """Representa un mensaje de chat."""

    def __init__(self, emisor: str, receptor: str, texto: str,
                 fecha: str = "") -> None:
        self.emisor = emisor
        self.receptor = receptor  # puede ser "#general" o un nombre de usuario
        self.texto = texto
        self.fecha = fecha or datetime.now().isoformat()

    def a_dict(self) -> dict:
        """Convierte el mensaje a un diccionario serializable."""
        return {
            "emisor": self.emisor,
            "receptor": self.receptor,
            "texto": self.texto,
            "fecha": self.fecha,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Mensaje":
        """Crea un Mensaje a partir de un diccionario."""
        return cls(
            emisor=datos["emisor"],
            receptor=datos["receptor"],
            texto=datos["texto"],
            fecha=datos.get("fecha", ""),
        )