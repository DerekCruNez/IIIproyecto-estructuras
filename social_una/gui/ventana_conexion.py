"""Ventana de conexión al servidor."""

import tkinter as tk
from tkinter import ttk, messagebox


class VentanaConexion:
    """Pantalla inicial para conectar al servidor."""

    def __init__(self, root: tk.Tk, cliente) -> None:
        self.root = root
        self.cliente = cliente
        self.frame = ttk.Frame(root)
        self.entrada_host: ttk.Entry | None = None
        self.entrada_puerto: ttk.Entry | None = None
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye los widgets de la ventana de conexión."""
        raise NotImplementedError

    def conectar(self) -> None:
        """Intenta conectar al servidor usando los datos ingresados."""
        raise NotImplementedError