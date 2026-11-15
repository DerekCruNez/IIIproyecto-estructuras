"""Estilos visuales compartidos para la GUI de Social UNA.

Define la paleta de colores, fuentes y la función para aplicar el
estilo ttk a la ventana raíz.
"""

import tkinter as tk
from tkinter import ttk


# --------------------------------------------------------------------------
# Paleta de colores
# --------------------------------------------------------------------------

COLOR_PRIMARIO = "#3b82f6"
COLOR_PRIMARIO_HOVER = "#2563eb"
COLOR_SECUNDARIO = "#64748b"
COLOR_FONDO = "#f8fafc"
COLOR_FONDO_TARJETA = "#ffffff"
COLOR_TEXTO = "#1e293b"
COLOR_TEXTO_SECUNDARIO = "#64748b"
COLOR_BORDE = "#e2e8f0"
COLOR_EXITO = "#10b981"
COLOR_ERROR = "#ef4444"
COLOR_ADVERTENCIA = "#f59e0b"


# --------------------------------------------------------------------------
# Fuentes
# --------------------------------------------------------------------------

FUENTE_TITULO = ("Segoe UI", 16, "bold")
FUENTE_SUBTITULO = ("Segoe UI", 12, "bold")
FUENTE_NORMAL = ("Segoe UI", 10)
FUENTE_PEQUENA = ("Segoe UI", 9)


# --------------------------------------------------------------------------
# Aplicación de estilos
# --------------------------------------------------------------------------

def aplicar_estilo(root: tk.Tk) -> None:
    """Aplica el estilo visual a la aplicación ttk."""
    estilo = ttk.Style(root)
    estilo.theme_use("clam")

    estilo.configure("TFrame", background=COLOR_FONDO)
    estilo.configure("TLabel", background=COLOR_FONDO, foreground=COLOR_TEXTO,
                     font=FUENTE_NORMAL)
    estilo.configure("TButton", font=FUENTE_NORMAL, padding=6)
    estilo.configure("TEntry", font=FUENTE_NORMAL, padding=4)
    estilo.configure("TNotebook", background=COLOR_FONDO, borderwidth=0)
    estilo.configure("TNotebook.Tab", background=COLOR_BORDE,
                     foreground=COLOR_TEXTO, padding=[12, 6],
                     font=FUENTE_NORMAL)
    estilo.map("TNotebook.Tab",
               background=[("selected", COLOR_FONDO_TARJETA)])

    estilo.configure("Titulo.TLabel", font=FUENTE_TITULO,
                     foreground=COLOR_PRIMARIO)
    estilo.configure("Subtitulo.TLabel", font=FUENTE_SUBTITULO,
                     foreground=COLOR_TEXTO)