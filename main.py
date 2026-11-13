"""Social UNA - punto de entrada de la interfaz gráfica.

Uso:
    python main.py          -> usa cliente.py (Daniel) si existe; si no, modo demostración
    python main.py --demo   -> fuerza el modo demostración (sin servidor)
"""
import sys
from tkinter import messagebox, Tk


def crear_cliente(forzar_demo=False):
    """Devuelve (cliente, es_demo)."""
    if not forzar_demo:
        try:
            from cliente import Cliente
            return Cliente(), False
        except ImportError:
            pass
    from gui.cliente_demo import ClienteDemo
    return ClienteDemo(), True


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        raiz = Tk()
        raiz.withdraw()
        messagebox.showerror("Falta Pillow", "Instala Pillow con:\n\npip install pillow")
        return

    from gui.app import App
    cliente, demo = crear_cliente("--demo" in sys.argv)
    App(cliente, demo).mainloop()


if __name__ == "__main__":
    main()
