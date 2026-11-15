"""Pestaña de búsqueda de usuarios."""

import tkinter as tk
from tkinter import ttk


class PestanaBuscar:
    """Pestaña para buscar usuarios y ver sugerencias de amistad."""

    def __init__(self, notebook: ttk.Notebook, cliente) -> None:
        self.notebook = notebook
        self.cliente = cliente
        self.frame = ttk.Frame(notebook)
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la pestaña de búsqueda."""
        raise NotImplementedError

    def buscar(self, texto: str) -> None:
        """Busca usuarios por nombre o usuario."""
        raise NotImplementedError

    def cargar_sugerencias(self, usuario: str) -> None:
        """Carga sugerencias de amigos de amigos."""
        raise NotImplementedError