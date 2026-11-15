"""Ventana de registro de nuevo usuario."""

import tkinter as tk
from tkinter import ttk, messagebox


class VentanaRegistro:
    """Pantalla de registro de usuario."""

    def __init__(self, root: tk.Tk, cliente) -> None:
        self.root = root
        self.cliente = cliente
        self.frame = ttk.Frame(root)
        self.entrada_nombre: ttk.Entry | None = None
        self.entrada_usuario: ttk.Entry | None = None
        self.entrada_clave: ttk.Entry | None = None
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la ventana de registro."""
        raise NotImplementedError

    def registrar(self) -> None:
        """Intenta registrar al usuario con los datos ingresados."""
        raise NotImplementedError