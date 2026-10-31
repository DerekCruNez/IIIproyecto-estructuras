"""Pestaña de chat en vivo."""

import tkinter as tk
from tkinter import ttk


class PestanaChat:
    """Pestaña de chat en tiempo real."""

    def __init__(self, notebook: ttk.Notebook, cliente) -> None:
        self.notebook = notebook
        self.cliente = cliente
        self.frame = ttk.Frame(notebook)
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la pestaña de chat."""
        raise NotImplementedError

    def cargar_conversacion(self, interlocutor: str) -> None:
        """Carga la conversación con un usuario."""
        raise NotImplementedError

    def enviar_mensaje(self, receptor: str, texto: str) -> None:
        """Envía un mensaje de chat."""
        raise NotImplementedError