"""Ventana principal con pestañas (Notebook)."""

import tkinter as tk
from tkinter import ttk

from gui.pestana_muro import PestanaMuro
from gui.pestana_amigos import PestanaAmigos
from gui.pestana_buscar import PestanaBuscar
from gui.pestana_chat import PestanaChat
from gui.pestana_perfil import PestanaPerfil


class VentanaPrincipal:
    """Ventana principal de la aplicación con el Notebook de pestañas."""

    def __init__(self, root: tk.Tk, cliente) -> None:
        self.root = root
        self.cliente = cliente
        self.notebook: ttk.Notebook | None = None
        self.pestana_muro: PestanaMuro | None = None
        self.pestana_amigos: PestanaAmigos | None = None
        self.pestana_buscar: PestanaBuscar | None = None
        self.pestana_chat: PestanaChat | None = None
        self.pestana_perfil: PestanaPerfil | None = None
        self.construir_widgets()

    def construir_widgets(self) -> None:
        """Construye el Notebook y las 5 pestañas."""
        raise NotImplementedError

    def revisar_eventos(self) -> None:
        """Revisa la cola de eventos del cliente y los procesa.

        Se programa a sí mismo cada 100 ms con root.after.
        """
        raise NotImplementedError