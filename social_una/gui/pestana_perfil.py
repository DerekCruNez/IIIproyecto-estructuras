"""Pestaña de perfil de usuario."""

import tkinter as tk
from tkinter import ttk


class PestanaPerfil:
    """Pestaña de edición y visualización del perfil."""

    def __init__(self, notebook: ttk.Notebook, cliente) -> None:
        self.notebook = notebook
        self.cliente = cliente
        self.frame = ttk.Frame(notebook)
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la pestaña de perfil."""
        raise NotImplementedError

    def cargar_perfil(self, usuario: str) -> None:
        """Carga y muestra el perfil del usuario."""
        raise NotImplementedError

    def editar_perfil(self, bio: str, foto: str, link: str) -> None:
        """Edita el perfil del usuario."""
        raise NotImplementedError