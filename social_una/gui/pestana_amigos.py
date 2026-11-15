"""Pestaña de amigos y solicitudes."""

import tkinter as tk
from tkinter import ttk


class PestanaAmigos:
    """Pestaña de gestión de amistades."""

    def __init__(self, notebook: ttk.Notebook, cliente) -> None:
        self.notebook = notebook
        self.cliente = cliente
        self.frame = ttk.Frame(notebook)
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la pestaña de amigos."""
        raise NotImplementedError

    def cargar_amigos(self, usuario: str) -> None:
        """Carga la lista de amigos del usuario."""
        raise NotImplementedError

    def cargar_solicitudes(self, usuario: str) -> None:
        """Carga las solicitudes de amistad pendientes."""
        raise NotImplementedError

    def enviar_solicitud(self, destino: str) -> None:
        """Envía una solicitud de amistad."""
        raise NotImplementedError

    def responder_solicitud(self, origen: str, aceptar: bool) -> None:
        """Acepta o rechaza una solicitud de amistad."""
        raise NotImplementedError

    def eliminar_amigo(self, amigo: str) -> None:
        """Elimina una amistad."""
        raise NotImplementedError