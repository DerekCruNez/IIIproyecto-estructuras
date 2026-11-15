"""Ventana de inicio de sesión."""

import tkinter as tk
from tkinter import ttk, messagebox


class VentanaLogin:
    """Pantalla de login de usuario."""

    def __init__(self, root: tk.Tk, cliente) -> None:
        self.root = root
        self.cliente = cliente
        self.frame = ttk.Frame(root)
        self.entrada_usuario: ttk.Entry | None = None
        self.entrada_clave: ttk.Entry | None = None
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la ventana de login."""
        raise NotImplementedError

    def iniciar_sesion(self) -> None:
        """Intenta iniciar sesión con las credenciales ingresadas."""
        raise NotImplementedError