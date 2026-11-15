"""Punto de entrada de la aplicación Social UNA."""

import tkinter as tk

from gui.estilo import aplicar_estilo
from gui.ventana_conexion import VentanaConexion
from cliente import ClienteSocial


def main() -> None:
    """Inicia la aplicación cliente."""
    root = tk.Tk()
    root.title("Social UNA")
    root.geometry("900x600")
    aplicar_estilo(root)

    cliente = ClienteSocial()
    VentanaConexion(root, cliente)

    root.mainloop()


if __name__ == "__main__":
    main()