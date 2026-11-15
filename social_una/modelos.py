"""Modelos de datos para Social UNA.

Define las clases Usuario, Publicacion y Mensaje con serialización
a diccionario y reconstrucción desde diccionario.
"""

from datetime import datetime
from typing import Any


class Usuario:
    """Representa un usuario de la red social.

    La contraseña nunca se almacena en texto plano. El campo
    ``hash_password`` contiene el hash SHA-256 de la contraseña.
    """

    def __init__(
        self,
        id: str,
        nombre: str,
        usuario: str,
        hash_password: str,
        bio: str = "",
        foto: str = "",
        link: str = "",
    ) -> None:
        if not id or not id.strip():
            raise ValueError("El id del usuario no puede estar vacío.")
        if not nombre or not nombre.strip():
            raise ValueError("El nombre del usuario no puede estar vacío.")
        if not usuario or not usuario.strip():
            raise ValueError("El nombre de usuario no puede estar vacío.")
        if not hash_password or not hash_password.strip():
            raise ValueError("El hash de contraseña no puede estar vacío.")

        self.id = id.strip()
        self.nombre = nombre.strip()
        self.usuario = usuario.strip()
        self.hash_password = hash_password.strip()
        self.bio = bio or ""
        self.foto = foto or ""
        self.link = link or ""

    def a_dict(self) -> dict[str, Any]:
        """Convierte el usuario a un diccionario serializable."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "hash_password": self.hash_password,
            "bio": self.bio,
            "foto": self.foto,
            "link": self.link,
        }

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "Usuario":
        """Crea un Usuario a partir de un diccionario."""
        return cls(
            id=datos["id"],
            nombre=datos["nombre"],
            usuario=datos["usuario"],
            hash_password=datos["hash_password"],
            bio=datos.get("bio", ""),
            foto=datos.get("foto", ""),
            link=datos.get("link", ""),
        )

    def __repr__(self) -> str:
        return (
            f"Usuario(id={self.id!r}, nombre={self.nombre!r}, "
            f"usuario={self.usuario!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Usuario):
            return NotImplemented
        return self.id == other.id


class Publicacion:
    """Representa una publicación en el muro.

    La imagen y el link son opcionales y almacenan nombres de archivo
    o URLs, nunca datos binarios. Los likes son una lista de nombres
    de usuario que dieron like.
    """

    def __init__(
        self,
        id: str,
        autor: str,
        texto: str,
        imagen: str = "",
        link: str = "",
        fecha: datetime | str | None = None,
        likes: list[str] | None = None,
        extra: str = "",
    ) -> None:
        if not id or not id.strip():
            raise ValueError("El id de la publicación no puede estar vacío.")
        if not autor or not autor.strip():
            raise ValueError("El autor de la publicación no puede estar vacío.")
        if texto is None:
            raise ValueError("El texto de la publicación no puede ser None.")

        self.id = id.strip()
        self.autor = autor.strip()
        self.texto = texto
        self.imagen = imagen or ""
        self.link = link or ""
        self.extra = extra or ""

        if fecha is None:
            self.fecha = datetime.now()
        elif isinstance(fecha, str):
            self.fecha = datetime.fromisoformat(fecha)
        else:
            self.fecha = fecha

        self.likes = list(likes) if likes is not None else []

    def agregar_like(self, usuario_id: str) -> None:
        """Agrega un like si el usuario aún no ha dado like."""
        if usuario_id and usuario_id not in self.likes:
            self.likes.append(usuario_id)

    def quitar_like(self, usuario_id: str) -> None:
        """Quita un like si el usuario lo había dado previamente."""
        if usuario_id in self.likes:
            self.likes.remove(usuario_id)

    def a_dict(self) -> dict[str, Any]:
        """Convierte la publicación a un diccionario serializable."""
        return {
            "id": self.id,
            "autor": self.autor,
            "texto": self.texto,
            "imagen": self.imagen,
            "link": self.link,
            "fecha": self.fecha.isoformat()
            if isinstance(self.fecha, datetime)
            else self.fecha,
            "likes": self.likes,
            "extra": self.extra,
        }

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "Publicacion":
        """Crea una Publicacion a partir de un diccionario."""
        fecha = datos.get("fecha", "")
        if isinstance(fecha, str) and fecha:
            fecha = datetime.fromisoformat(fecha)
        elif not fecha:
            fecha = datetime.now()

        return cls(
            id=datos["id"],
            autor=datos["autor"],
            texto=datos.get("texto", ""),
            imagen=datos.get("imagen", ""),
            link=datos.get("link", ""),
            fecha=fecha,
            likes=datos.get("likes", []),
            extra=datos.get("extra", ""),
        )

    def __repr__(self) -> str:
        return (
            f"Publicacion(id={self.id!r}, autor={self.autor!r}, "
            f"fecha={self.fecha.isoformat()!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Publicacion):
            return NotImplemented
        return self.id == other.id


class Mensaje:
    """Representa un mensaje de chat entre dos usuarios."""

    def __init__(
        self,
        emisor: str,
        receptor: str,
        texto: str,
        fecha: datetime | str | None = None,
    ) -> None:
        if not emisor or not emisor.strip():
            raise ValueError("El emisor del mensaje no puede estar vacío.")
        if not receptor or not receptor.strip():
            raise ValueError("El receptor del mensaje no puede estar vacío.")
        if texto is None:
            raise ValueError("El texto del mensaje no puede ser None.")

        self.emisor = emisor.strip()
        self.receptor = receptor.strip()
        self.texto = texto

        if fecha is None:
            self.fecha = datetime.now()
        elif isinstance(fecha, str):
            self.fecha = datetime.fromisoformat(fecha)
        else:
            self.fecha = fecha

    def a_dict(self) -> dict[str, Any]:
        """Convierte el mensaje a un diccionario serializable."""
        return {
            "emisor": self.emisor,
            "receptor": self.receptor,
            "texto": self.texto,
            "fecha": self.fecha.isoformat()
            if isinstance(self.fecha, datetime)
            else self.fecha,
        }

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "Mensaje":
        """Crea un Mensaje a partir de un diccionario."""
        fecha = datos.get("fecha", "")
        if isinstance(fecha, str) and fecha:
            fecha = datetime.fromisoformat(fecha)
        elif not fecha:
            fecha = datetime.now()

        return cls(
            emisor=datos["emisor"],
            receptor=datos["receptor"],
            texto=datos.get("texto", ""),
            fecha=fecha,
        )

    def __repr__(self) -> str:
        return (
            f"Mensaje(emisor={self.emisor!r}, receptor={self.receptor!r}, "
            f"fecha={self.fecha.isoformat()!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mensaje):
            return NotImplemented
        return (
            self.emisor == other.emisor
            and self.receptor == other.receptor
            and self.texto == other.texto
            and self.fecha == other.fecha
        )