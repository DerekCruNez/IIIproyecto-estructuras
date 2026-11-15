"""Ventana raíz: maneja la navegación entre pantallas y los eventos del servidor."""
import queue
import tkinter as tk
from tkinter import messagebox

from gui.estilo import aplicar_estilo, FONDO
from gui.imagenes import logo
from gui.vistas_acceso import VistaConexion, VistaLogin, VistaRegistro
from gui.principal import Principal


class App(tk.Tk):
    def __init__(self, cliente, modo_demo=False):
        super().__init__()
        self.title("Social UNA")
        self.geometry("1120x720")
        self.minsize(980, 640)
        aplicar_estilo(self)
        self._icono = logo(64)
        self.iconphoto(True, self._icono)

        self.cliente = cliente
        self.modo_demo = modo_demo
        self.perfil = None          # diccionario del usuario con sesión iniciada
        self.vista = None

        self.contenedor = tk.Frame(self, bg=FONDO)
        self.contenedor.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.mostrar_conexion()
        self.after(200, self._revisar_cola)

    # ---------------------------------------------------------- navegación
    def _mostrar(self, clase):
        if self.vista is not None:
            self.vista.destroy()
        self.vista = clase(self.contenedor, self)
        self.vista.pack(fill="both", expand=True)

    def mostrar_conexion(self):
        self._mostrar(VistaConexion)

    def mostrar_login(self):
        self._mostrar(VistaLogin)

    def mostrar_registro(self):
        self._mostrar(VistaRegistro)

    def mostrar_principal(self):
        self._mostrar(Principal)

    def cerrar_sesion(self):
        try:
            self.cliente.logout()
        except Exception:
            pass
        self.perfil = None
        self.mostrar_login()

    # ------------------------------------------- eventos que envía el servidor
    def _revisar_cola(self):
        """La GUI revisa la queue del cliente con after(): nunca se bloquea."""
        cola = getattr(self.cliente, "cola", None)
        if cola is not None:
            try:
                while True:
                    self._despachar(cola.get_nowait())
            except queue.Empty:
                pass
        self.after(200, self._revisar_cola)

    def _despachar(self, evento):
        if evento.get("tipo") == "desconectado":
            self.perfil = None
            messagebox.showwarning("Conexión perdida",
                                   evento.get("mensaje") or "Se perdió la conexión con el servidor.")
            self.mostrar_conexion()
        elif isinstance(self.vista, Principal):
            self.vista.manejar_evento(evento)

    def cerrar(self):
        if self.perfil:
            try:
                self.cliente.logout()
            except Exception:
                pass
        self.destroy()
