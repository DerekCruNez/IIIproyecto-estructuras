"""Protocolo de comunicación para Social UNA.

Define el formato de mensaje, helpers de envío y recepción sobre sockets TCP
y utilidades para codificar/decodificar imágenes en base64.

Cada mensaje se envía como: 4 bytes (big-endian) con el largo del payload +
JSON codificado en UTF-8.
"""

import base64
import json
import os
import socket
import struct
import uuid


# --------------------------------------------------------------------------
# Constantes de red
# --------------------------------------------------------------------------

HOST_DEFECTO = "127.0.0.1"
PUERTO_DEFECTO = 5000

# --------------------------------------------------------------------------
# Límites
# --------------------------------------------------------------------------

MAX_LONGITUD_MENSAJE = 3 * 1024 * 1024   # 3 MB
MAX_IMAGEN_BYTES = 2 * 1024 * 1024       # 2 MB


# --------------------------------------------------------------------------
# Envío y recepción de mensajes
# --------------------------------------------------------------------------

def enviar_mensaje(sock: socket.socket, mensaje: dict) -> None:
    """Envía un diccionario como JSON a través del socket.

    El formato es: 4 bytes big-endian con el largo del payload + JSON en UTF-8.

    Args:
        sock: Socket de conexión.
        mensaje: Diccionario con el mensaje a enviar.
    """
    payload = json.dumps(mensaje, ensure_ascii=False).encode("utf-8")
    largo = len(payload)
    if largo > MAX_LONGITUD_MENSAJE:
        raise ValueError("El mensaje excede el límite máximo permitido")
    sock.sendall(struct.pack(">I", largo) + payload)


def _leer_exactamente(sock: socket.socket, n: int) -> bytes | None:
    """Lee exactamente n bytes del socket en un bucle.

    Devuelve None si el socket se cierra antes de leer los n bytes completos.

    Args:
        sock: Socket de conexión.
        n: Número de bytes a leer.

    Returns:
        Bytes leídos o None si el socket se cerró.
    """
    datos = bytearray()
    while len(datos) < n:
        fragmento = sock.recv(n - len(datos))
        if not fragmento:
            return None
        datos.extend(fragmento)
    return bytes(datos)


def recibir_mensaje(sock: socket.socket) -> dict | None:
    """Recibe un mensaje del socket y lo devuelve como diccionario.

    Primero lee 4 bytes con el largo del payload, luego lee exactamente ese
    número de bytes y decodifica el JSON. Devuelve None si el socket se cierra.

    Args:
        sock: Socket de conexión.

    Returns:
        Diccionario con el mensaje recibido o None si el socket se cerró.
    """
    largo_bytes = _leer_exactamente(sock, 4)
    if largo_bytes is None:
        return None

    largo = struct.unpack(">I", largo_bytes)[0]
    if largo > MAX_LONGITUD_MENSAJE:
        return None

    payload_bytes = _leer_exactamente(sock, largo)
    if payload_bytes is None:
        return None

    return json.loads(payload_bytes.decode("utf-8"))


# --------------------------------------------------------------------------
# Utilidades de imagen
# --------------------------------------------------------------------------

def codificar_imagen(ruta: str) -> str:
    """Codifica un archivo de imagen en una cadena base64.

    Args:
        ruta: Ruta al archivo de imagen en disco.

    Returns:
        Cadena base64 con el contenido de la imagen.
    """
    with open(ruta, "rb") as archivo:
        return base64.b64encode(archivo.read()).decode("ascii")


def guardar_imagen(base64_str: str, carpeta: str) -> str:
    """Guarda una cadena base64 como archivo de imagen con nombre único.

    Args:
        base64_str: Contenido de la imagen en base64.
        carpeta: Carpeta de destino donde se guardará la imagen.

    Returns:
        Nombre del archivo guardado (sin incluir la carpeta).
    """
    os.makedirs(carpeta, exist_ok=True)
    nombre_archivo = f"{uuid.uuid4().hex}.jpg"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    datos = base64.b64decode(base64_str)
    with open(ruta_completa, "wb") as archivo:
        archivo.write(datos)
    return nombre_archivo