"""Almacenamiento de datos en memoria y disco para Social UNA.

La clase Almacen gestiona usuarios, amistades, solicitudes, publicaciones
y chats. Todo se persiste en archivos JSON dentro de la carpeta datos/.

Estructuras de datos obligatorias:
- lista dinamica de objetos Usuario
- lista dinamica de objetos Publicacion
- grafo de amistades: dict[str, list[str]]
- solicitudes pendientes: dict[str, list[str]] (por destinatario)
- conversaciones: dict[str, list[Mensaje]] (clave por par ordenado)
"""

import hashlib
import json
import os
import shutil
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from modelos import Usuario, Publicacion, Mensaje


class Almacen:
    """Gestiona todos los datos de la red social en memoria y disco."""

    def __init__(self, carpeta_datos: str = "datos") -> None:
        # Ruta base relativa a la ubicación de este archivo, para que
        # funcione independientemente del directorio de trabajo.
        self._base_dir = Path(__file__).resolve().parent
        self.carpeta_datos = Path(carpeta_datos)
        if not self.carpeta_datos.is_absolute():
            self.carpeta_datos = self._base_dir / self.carpeta_datos

        self.usuarios: list[Usuario] = []
        self.publicaciones: list[Publicacion] = []
        self.amistades: dict[str, list[str]] = {}
        self.solicitudes: dict[str, list[str]] = {}
        self.chats: dict[str, list[Mensaje]] = {}
        self.lock = threading.Lock()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def cargar_todo(self) -> None:
        """Carga todos los datos desde los archivos JSON.

        Si un archivo no existe, se deja la estructura vacía.
        Si un archivo contiene JSON inválido, se informa y se omite
        ese archivo sin sobrescribirlo.
        """
        self.carpeta_datos.mkdir(parents=True, exist_ok=True)
        (self.carpeta_datos / "imagenes").mkdir(parents=True, exist_ok=True)

        self.usuarios = self._cargar_usuarios()
        self.amistades = self._cargar_json_dict("amistades.json", {})
        self.solicitudes = self._cargar_json_dict("solicitudes.json", {})
        self.publicaciones = self._cargar_publicaciones()
        self.chats = self._cargar_chats()

    def _ruta(self, nombre: str) -> Path:
        return self.carpeta_datos / nombre

    def _cargar_usuarios(self) -> list[Usuario]:
        ruta = self._ruta("usuarios.json")
        if not ruta.exists():
            return []
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, list):
                print(f"[ADVERTENCIA] {ruta} no contiene una lista. Se omite.")
                return []
            return [Usuario.desde_dict(item) for item in datos]
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] No se pudo leer {ruta}: {e}. Archivo no modificado.")
            return []

    def _cargar_publicaciones(self) -> list[Publicacion]:
        ruta = self._ruta("publicaciones.json")
        if not ruta.exists():
            return []
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, list):
                print(f"[ADVERTENCIA] {ruta} no contiene una lista. Se omite.")
                return []
            return [Publicacion.desde_dict(item) for item in datos]
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] No se pudo leer {ruta}: {e}. Archivo no modificado.")
            return []

    def _cargar_chats(self) -> dict[str, list[Mensaje]]:
        ruta = self._ruta("chats.json")
        if not ruta.exists():
            return {}
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict):
                print(f"[ADVERTENCIA] {ruta} no contiene un objeto. Se omite.")
                return {}
            resultado: dict[str, list[Mensaje]] = {}
            for clave, lista in datos.items():
                if isinstance(lista, list):
                    resultado[clave] = [Mensaje.desde_dict(item) for item in lista]
            return resultado
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] No se pudo leer {ruta}: {e}. Archivo no modificado.")
            return {}

    def _cargar_json_dict(self, nombre: str, defecto: Any) -> Any:
        ruta = self._ruta(nombre)
        if not ruta.exists():
            return defecto
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            return datos if datos is not None else defecto
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] No se pudo leer {ruta}: {e}. Archivo no modificado.")
            return defecto

    def guardar_todo(self) -> None:
        """Guarda todos los datos en archivos JSON protegido por lock.

        Cada archivo se escribe primero en un archivo temporal y luego
        se reemplaza de forma atómica para evitar corrupción si el
        programa se interrumpe durante la escritura.
        """
        with self.lock:
            self.carpeta_datos.mkdir(parents=True, exist_ok=True)
            (self.carpeta_datos / "imagenes").mkdir(parents=True, exist_ok=True)

            self._guardar_archivo_atomico("usuarios.json",
                                          [u.a_dict() for u in self.usuarios])
            self._guardar_archivo_atomico("publicaciones.json",
                                          [p.a_dict() for p in self.publicaciones])
            self._guardar_archivo_atomico("amistades.json", self.amistades)
            self._guardar_archivo_atomico("solicitudes.json", self.solicitudes)
            self._guardar_archivo_atomico("chats.json",
                                          {k: [m.a_dict() for m in v]
                                           for k, v in self.chats.items()})

    def _guardar_archivo_atomico(self, nombre: str, datos: Any) -> None:
        """Escribe datos en un archivo temporal y lo reemplaza atómicamente."""
        ruta_final = self._ruta(nombre)
        fd, ruta_temp = tempfile.mkstemp(
            dir=str(self.carpeta_datos), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            # En Windows, eliminar el destino antes de reemplazar evita
            # errores de acceso denegado cuando el archivo ya existe.
            if ruta_final.exists():
                ruta_final.unlink()
            os.replace(ruta_temp, ruta_final)
        except Exception:
            try:
                os.unlink(ruta_temp)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def hash_clave(clave: str) -> str:
        """Devuelve el hash SHA-256 de una contraseña."""
        import hashlib
        return hashlib.sha256(clave.encode("utf-8")).hexdigest()

    def _buscar_usuario_por_nombre(self, usuario: str) -> Usuario | None:
        for u in self.usuarios:
            if u.usuario == usuario:
                return u
        return None

    def _indice_usuario_por_nombre(self, usuario: str) -> int | None:
        for i, u in enumerate(self.usuarios):
            if u.usuario == usuario:
                return i
        return None

    def _clave_chat(self, a: str, b: str) -> str:
        """Clave consistente para una conversación entre dos usuarios."""
        ordenados = sorted([a, b])
        return f"{ordenados[0]}:{ordenados[1]}"

    def registrar_usuario(self, id: str, nombre: str, usuario: str,
                          clave: str) -> tuple[bool, Any]:
        """Registra un nuevo usuario.

        Retorna (True, Usuario) si tuvo exito, o (False, mensaje_error).
        """
        if not id or not id.strip():
            return False, "El id no puede estar vacio."
        if not nombre or not nombre.strip():
            return False, "El nombre no puede estar vacio."
        if not usuario or not usuario.strip():
            return False, "El nombre de usuario no puede estar vacio."
        if not clave or not clave.strip():
            return False, "La clave no puede estar vacia."

        usuario = usuario.strip()
        if self._buscar_usuario_por_nombre(usuario) is not None:
            return False, "El usuario ya existe."

        nuevo = Usuario(
            id=id.strip(),
            nombre=nombre.strip(),
            usuario=usuario,
            hash_password=self.hash_clave(clave),
        )
        self.usuarios.append(nuevo)
        self.guardar_todo()
        return True, nuevo

    def validar_login(self, usuario: str, clave: str) -> tuple[bool, Any]:
        """Valida las credenciales de login.

        Retorna (True, perfil_sin_hash) si es correcto, o (False, error).
        """
        u = self._buscar_usuario_por_nombre(usuario)
        if u is None:
            return False, "Usuario no encontrado."
        esperado = self.hash_clave(clave)
        if u.hash_password != esperado:
            return False, "Clave incorrecta."
        return True, {
            "id": u.id,
            "nombre": u.nombre,
            "usuario": u.usuario,
            "bio": u.bio,
            "foto": u.foto,
            "link": u.link,
        }

    def obtener_perfil(self, usuario: str) -> tuple[bool, Any]:
        """Devuelve el perfil publico de un usuario (sin hash de clave)."""
        u = self._buscar_usuario_por_nombre(usuario)
        if u is None:
            return False, "Usuario no encontrado."
        return True, {
            "id": u.id,
            "nombre": u.nombre,
            "usuario": u.usuario,
            "bio": u.bio,
            "foto": u.foto,
            "link": u.link,
        }

    def editar_perfil(self, usuario: str, bio: str, foto: str,
                      link: str) -> tuple[bool, Any]:
        """Edita los campos opcionales del perfil de un usuario."""
        u = self._buscar_usuario_por_nombre(usuario)
        if u is None:
            return False, "Usuario no encontrado."
        u.bio = bio or ""
        u.foto = foto or ""
        u.link = link or ""
        self.guardar_todo()
        return True, "Perfil actualizado."

    def buscar_usuarios(self, texto: str) -> tuple[bool, Any]:
        """Busca usuarios por nombre o nombre de usuario (case-insensitive)."""
        texto_lower = texto.lower().strip()
        resultados = []
        for u in self.usuarios:
            if texto_lower in u.usuario.lower() or texto_lower in u.nombre.lower():
                resultados.append({
                    "id": u.id,
                    "nombre": u.nombre,
                    "usuario": u.usuario,
                    "bio": u.bio,
                    "foto": u.foto,
                    "link": u.link,
                })
        return True, resultados

    # ------------------------------------------------------------------
    # Amistades y solicitudes
    # ------------------------------------------------------------------
    def _agregar_amistad_bidireccional(self, a: str, b: str) -> None:
        """Agrega amistad entre a y b en ambas direcciones sin duplicados."""
        if a not in self.amistades:
            self.amistades[a] = []
        if b not in self.amistades:
            self.amistades[b] = []
        if b not in self.amistades[a]:
            self.amistades[a].append(b)
        if a not in self.amistades[b]:
            self.amistades[b].append(a)

    def _remover_amistad_bidireccional(self, a: str, b: str) -> None:
        """Remueve la amistad entre a y b en ambas direcciones."""
        if a in self.amistades and b in self.amistades[a]:
            self.amistades[a].remove(b)
        if b in self.amistades and a in self.amistades[b]:
            self.amistades[b].remove(a)

    def enviar_solicitud(self, origen: str, destino: str) -> tuple[bool, Any]:
        """Envía una solicitud de amistad de origen a destino.

        Retorna (True, mensaje) o (False, error).
        """
        if not origen or not destino:
            return False, "Origen y destino son obligatorios."
        if origen == destino:
            return False, "No puedes enviarte una solicitud a ti mismo."

        if self._buscar_usuario_por_nombre(origen) is None:
            return False, "El usuario origen no existe."
        if self._buscar_usuario_por_nombre(destino) is None:
            return False, "El usuario destino no existe."

        # Ya son amigos
        if destino in self.amistades.get(origen, []):
            return False, "Ya son amigos."

        # Solicitud ya pendiente
        pendientes = self.solicitudes.get(destino, [])
        if origen in pendientes:
            return False, "Ya existe una solicitud pendiente hacia este usuario."

        if destino not in self.solicitudes:
            self.solicitudes[destino] = []
        self.solicitudes[destino].append(origen)
        self.guardar_todo()
        return True, "Solicitud enviada."

    def responder_solicitud(self, destino: str, origen: str,
                            aceptar: bool) -> tuple[bool, Any]:
        """Acepta o rechaza una solicitud de amistad.

        Si aceptar=True, crea la amistad bidireccional.
        Siempre elimina la solicitud pendiente.
        """
        pendientes = self.solicitudes.get(destino, [])
        if origen not in pendientes:
            return False, "No existe una solicitud pendiente de este usuario."

        if aceptar:
            self._agregar_amistad_bidireccional(origen, destino)

        self.solicitudes[destino].remove(origen)
        if not self.solicitudes[destino]:
            del self.solicitudes[destino]
        self.guardar_todo()

        if aceptar:
            return True, "Solicitud aceptada. Ahora son amigos."
        return True, "Solicitud rechazada."

    def listar_solicitudes(self, usuario: str) -> tuple[bool, Any]:
        """Lista las solicitudes de amistad pendientes recibidas por un usuario."""
        return True, list(self.solicitudes.get(usuario, []))

    def listar_amigos(self, usuario: str) -> tuple[bool, Any]:
        """Lista los amigos de un usuario."""
        return True, list(self.amistades.get(usuario, []))

    def eliminar_amigo(self, a: str, b: str) -> tuple[bool, Any]:
        """Elimina la amistad entre dos usuarios en ambas direcciones."""
        if a not in self.amistades or b not in self.amistades.get(a, []):
            return False, "No existen como amigos."
        self._remover_amistad_bidireccional(a, b)
        self.guardar_todo()
        return True, "Amistad eliminada."

    def amigos_en_comun(self, a: str, b: str) -> tuple[bool, Any]:
        """Devuelve los amigos en común entre dos usuarios."""
        amigos_a = set(self.amistades.get(a, []))
        amigos_b = set(self.amistades.get(b, []))
        comunes = sorted(amigos_a & amigos_b)
        return True, comunes

    # ------------------------------------------------------------------
    # Publicaciones y muro
    # ------------------------------------------------------------------
    def crear_publicacion(self, autor: str, texto: str, imagen: str,
                          link: str, extra: str) -> tuple[bool, Any]:
        """Crea una nueva publicación.

        Retorna (True, Publicacion) o (False, error).
        """
        if not autor or not autor.strip():
            return False, "El autor es obligatorio."
        if texto is None or texto == "":
            return False, "El texto no puede estar vacio."

        if self._buscar_usuario_por_nombre(autor) is None:
            return False, "El autor no existe."

        nueva = Publicacion(
            id=str(uuid.uuid4()),
            autor=autor.strip(),
            texto=texto,
            imagen=imagen or "",
            link=link or "",
            extra=extra or "",
        )
        self.publicaciones.append(nueva)
        self.guardar_todo()
        return True, nueva

    def _buscar_publicacion_por_id(self, id_publicacion: str) -> Publicacion | None:
        for p in self.publicaciones:
            if p.id == id_publicacion:
                return p
        return None

    def obtener_muro(self, usuario: str) -> tuple[bool, Any]:
        """Devuelve publicaciones propias y de amigos, ordenadas reciente -> antigua."""
        if self._buscar_usuario_por_nombre(usuario) is None:
            return False, "Usuario no encontrado."

        amigos = set(self.amistades.get(usuario, []))
        amigos.add(usuario)  # incluir propias

        muro = [
            p for p in self.publicaciones
            if p.autor in amigos
        ]

        # Ordenar por fecha descendente (mas reciente primero)
        muro.sort(key=lambda p: p.fecha, reverse=True)

        return True, [p.a_dict() for p in muro]

    def dar_like(self, id_publicacion: str, usuario: str) -> tuple[bool, Any]:
        """Agrega o quita un like de una publicación (toggle)."""
        p = self._buscar_publicacion_por_id(id_publicacion)
        if p is None:
            return False, "Publicacion no encontrada."

        if usuario in p.likes:
            p.quitar_like(usuario)
            self.guardar_todo()
            return True, "Like eliminado."
        else:
            p.agregar_like(usuario)
            self.guardar_todo()
            return True, "Like agregado."

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def guardar_chat(self, emisor: str, receptor: str, texto: str
                     ) -> tuple[bool, Any]:
        """Guarda un mensaje de chat en la conversación correspondiente."""
        if not emisor or not receptor:
            return False, "Emisor y receptor son obligatorios."
        if texto is None or texto == "":
            return False, "El texto no puede estar vacio."

        mensaje = Mensaje(
            emisor=emisor.strip(),
            receptor=receptor.strip(),
            texto=texto,
        )

        clave = self._clave_chat(emisor, receptor)
        if clave not in self.chats:
            self.chats[clave] = []
        self.chats[clave].append(mensaje)
        self.guardar_todo()
        return True, "Mensaje guardado."

    def obtener_chat(self, a: str, b: str) -> tuple[bool, Any]:
        """Devuelve el historial de conversación entre dos usuarios."""
        clave = self._clave_chat(a, b)
        mensajes = self.chats.get(clave, [])
        return True, [m.a_dict() for m in mensajes]

    # ------------------------------------------------------------------
    # Sugerencias
    # ------------------------------------------------------------------
    def sugerir_amigos(self, usuario: str) -> tuple[bool, Any]:
        """Sugiere amigos basados en amigos de amigos.

        No sugiere al propio usuario, a sus amigos actuales ni a usuarios
        que no existan. Prioriza a quienes tengan más amigos en común.
        """
        if self._buscar_usuario_por_nombre(usuario) is None:
            return False, "Usuario no encontrado."

        amigos_directos = set(self.amistades.get(usuario, []))
        sugerencias: dict[str, int] = {}

        for amigo in amigos_directos:
            for amigo_de_amigo in self.amistades.get(amigo, []):
                if amigo_de_amigo == usuario:
                    continue
                if amigo_de_amigo in amigos_directos:
                    continue
                if self._buscar_usuario_por_nombre(amigo_de_amigo) is None:
                    continue
                sugerencias[amigo_de_amigo] = (
                    sugerencias.get(amigo_de_amigo, 0) + 1
                )

        # Ordenar por cantidad de amigos en común (descendente)
        sugeridas_ordenadas = sorted(
            sugerencias.items(), key=lambda x: x[1], reverse=True
        )

        resultado = []
        for nombre_usuario, _ in sugeridas_ordenadas:
            u = self._buscar_usuario_por_nombre(nombre_usuario)
            if u is not None:
                resultado.append({
                    "id": u.id,
                    "nombre": u.nombre,
                    "usuario": u.usuario,
                    "bio": u.bio,
                    "foto": u.foto,
                    "link": u.link,
                })

        return True, resultado
