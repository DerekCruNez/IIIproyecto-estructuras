"""Pestaña del muro cronológico."""

import tkinter as tk
from tkinter import ttk


class PestanaMuro:
    """Pestaña que muestra el muro de publicaciones."""

    def __init__(self, notebook: ttk.Notebook, cliente) -> None:
        self.notebook = notebook
        self.cliente = cliente
        self.frame = ttk.Frame(notebook)
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la pestaña del muro."""
        raise NotImplementedError

    def cargar_muro(self, usuario: str) -> None:
        """Carga y muestra el muro del usuario."""
        raise NotImplementedError

    def publicar(self) -> None:
        """Publica una nueva entrada en el muro."""
        raise NotImplementedError

    def dar_like(self, id_publicacion: str) -> None:
        """Da like a una publicación."""
        raise NotImplementedError