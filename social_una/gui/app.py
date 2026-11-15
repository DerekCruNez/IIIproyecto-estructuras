"""Ventana raíz: maneja la navegación entre pantallas, el tema y los eventos del servidor."""
import queue
import tkinter as tk
from tkinter import messagebox

from gui import estilo as E
from gui.estilo import aplicar_estilo
from gui.imagenes import logo
from gui.vistas_acceso import VistaConexion, VistaLogin, VistaRegistro
from gui.principal import Principal
from gui.sonidos import cargar_prefs, notificar


class App(tk.Tk):
    def __init__(self, cliente, modo_demo=False):
        super().__init__()
        self.title("Social UNA")
        self.geometry("1120x720")
        self.minsize(980, 640)
        aplicar_estilo(self)
        E.registrar_raiz(self)          # los avisos de éxito salen como toasts
        self._icono = logo(64)
        self.iconphoto(True, self._icono)

        self.cliente = cliente
        self.modo_demo = modo_demo
        self.perfil = None          # diccionario del usuario con sesión iniciada
        self.perfiles = {}          # caché de perfiles de otros usuarios (por sesión)
        self.prefs = cargar_prefs()  # sonido, tono, clave de GIPHY (en ~/.social_una)
        self.vista = None

        self.contenedor = tk.Frame(self, bg=E.FONDO)
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

    def entrar(self, perfil):
        """Tras el login: aplica el tema guardado en el perfil y abre la ventana principal."""
        self.perfil = perfil
        self.perfiles = {}
        self.cambiar_tema(perfil.get("tema", "claro"), perfil.get("paleta", E.PALETA_DEFECTO),
                          reconstruir=False)
        self.mostrar_principal()

    def cerrar_sesion(self):
        try:
            self.cliente.logout()
        except Exception:
            pass
        self.perfil = None
        self.cambiar_tema("claro", E.PALETA_DEFECTO, reconstruir=False)
        self.mostrar_login()

    # --------------------------------------------------------------- tema
    def cambiar_tema(self, tema, paleta, reconstruir=True):
        """Aplica tema y paleta. Reconstruye la vista para que todo tome los colores."""
        E.aplicar_tema(tema, paleta)
        aplicar_estilo(self)
        self.contenedor.config(bg=E.FONDO)
        self._icono = logo(64)
        self.iconphoto(True, self._icono)
        if reconstruir and isinstance(self.vista, Principal):
            seccion = self.vista.actual
            self.mostrar_principal()
            self.vista.ir(seccion)

    # ----------------------------------------------------------- perfiles
    def perfil_de(self, usuario, recargar=False):
        """Perfil de cualquier usuario (con caché), o None si no existe."""
        if recargar or usuario not in self.perfiles:
            resp = self.cliente.ver_perfil(usuario)
            if not (resp and resp.get("ok")):
                return self.perfiles.get(usuario)
            self.perfiles[usuario] = resp["usuario"]
        return self.perfiles[usuario]

    def ruta_foto(self, perfil):
        """Ruta local de la foto de un perfil (o None)."""
        foto = (perfil or {}).get("foto")
        return self.cliente.ruta_imagen(foto) if foto else None

    def ver_perfil(self, usuario):
        from gui.perfil import mostrar_perfil   # aquí: perfil importa muro, que usa la App
        mostrar_perfil(self, usuario)

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
            self.cambiar_tema("claro", E.PALETA_DEFECTO, reconstruir=False)
            self.mostrar_conexion()
        elif isinstance(self.vista, Principal):
            if evento.get("tipo") == "chat":
                notificar(self.prefs, self)
            self.vista.manejar_evento(evento)

    def cerrar(self):
        if self.perfil:
            try:
                self.cliente.logout()
            except Exception:
                pass
        self.destroy()
