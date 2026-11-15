"""Ventana principal: panel lateral de navegación + barra superior con el título de la sección."""
import tkinter as tk

from gui import estilo as E
from gui import textos as T
from gui.imagenes import logo
from gui.widgets import Boton, Avatar
from gui.muro import PestanaMuro
from gui.amigos import PestanaAmigos
from gui.buscar import PestanaBuscar
from gui.chat import PestanaChat
from gui.perfil import PestanaPerfil
from gui.apariencia import PestanaApariencia
from gui.juegos import PestanaJuegos


class ItemNav(tk.Frame):
    """Opción del menú lateral con barra de acento, resaltado y aviso de novedades."""

    def __init__(self, padre, texto, comando):
        super().__init__(padre, bg=E.MARINO, cursor="hand2")
        self.comando = comando
        self.activo = False
        self.barra = tk.Frame(self, bg=E.MARINO, width=4)
        self.barra.pack(side="left", fill="y")
        self.texto = tk.Label(self, text=texto, font=(E.FAMILIA, 11), fg=E.LATERAL_TEXTO, bg=E.MARINO,
                              anchor="w", padx=20, pady=12)
        self.texto.pack(side="left", fill="x", expand=True)
        # insignia de novedades: un número (mensajes, solicitudes...) o un punto
        self.aviso = tk.Label(self, font=E.F_PEQ_NEG, fg=E.MARINO, bg=E.DESTACADO, padx=6)
        self.cantidad = 0
        for w in (self, self.barra, self.texto, self.aviso):
            w.bind("<Button-1>", lambda _e: self.comando())
            w.bind("<Enter>", lambda _e: self._pintar(True))
            w.bind("<Leave>", lambda _e: self._pintar(False))

    def _pintar(self, hover=False):
        fondo = E.MARINO_2 if (self.activo or hover) else E.MARINO
        for w in (self, self.texto):
            w.config(bg=fondo)
        self.barra.config(bg=E.DESTACADO if self.activo else fondo)
        self.texto.config(fg="white" if self.activo else E.LATERAL_TEXTO,
                          font=(E.FAMILIA, 11, "bold") if self.activo else (E.FAMILIA, 11))

    def activar(self, valor):
        self.activo = valor
        self._pintar()

    def avisar(self, valor):
        """valor: False/0 = quitar; True = sumar uno al contador."""
        self.cantidad = self.cantidad + 1 if valor else 0
        if self.cantidad:
            self.aviso.config(text="9+" if self.cantidad > 9 else str(self.cantidad))
            self.aviso.pack(side="right", padx=(0, 14))
        else:
            self.aviso.pack_forget()


class Principal(tk.Frame):
    NAV = ("Muro", "Amigos", "Buscar", "Chat", "Juegos", "Perfil", "Personalizar")
    TITULOS = T.TITULOS_SECCION

    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.actual = None

        # ---------------------------------------------------- panel lateral
        lateral = tk.Frame(self, bg=E.MARINO, width=240)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        marca = tk.Frame(lateral, bg=E.MARINO)
        marca.pack(anchor="w", padx=20, pady=(26, 24))
        self.logo = logo(38)
        tk.Label(marca, image=self.logo, bg=E.MARINO, bd=0).pack(side="left")
        tk.Label(marca, text="Social ", font=(E.FAMILIA, 16, "bold"), fg="white",
                 bg=E.MARINO).pack(side="left", padx=(10, 0))
        tk.Label(marca, text="UNA", font=(E.FAMILIA, 16, "bold"), fg=E.DESTACADO,
                 bg=E.MARINO).pack(side="left")
        self.nav = {}
        for nombre in self.NAV:
            item = ItemNav(lateral, nombre, lambda n=nombre: self.ir(n))
            item.pack(fill="x")
            self.nav[nombre] = item

        pie = tk.Frame(lateral, bg=E.MARINO)
        pie.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Frame(pie, bg=E.MARINO_2, height=1).pack(fill="x", pady=(0, 14))
        fila = tk.Frame(pie, bg=E.MARINO)
        fila.pack(fill="x")
        self.av_lateral = Avatar(fila, "", "", lado=40, fondo=E.MARINO, animado=True)
        self.av_lateral.config(cursor="hand2")
        self.av_lateral.bind("<Button-1>", lambda _e: self.ir("Perfil"))
        self.av_lateral.pack(side="left")
        datos = tk.Frame(fila, bg=E.MARINO)
        datos.pack(side="left", padx=(10, 0))
        self.lbl_nombre = tk.Label(datos, font=E.F_NEG, fg="white", bg=E.MARINO, anchor="w")
        self.lbl_nombre.pack(anchor="w")
        self.lbl_usuario = tk.Label(datos, font=E.F_PEQ, fg=E.LATERAL_SUAVE, bg=E.MARINO, anchor="w")
        self.lbl_usuario.pack(anchor="w")
        Boton(pie, "Cerrar sesión", app.cerrar_sesion, "oscuro", fondo=E.MARINO, pady=8).pack(
            fill="x", pady=(14, 0))

        # ------------------------------------------------------- contenido
        contenido = tk.Frame(self, bg=E.FONDO)
        contenido.pack(side="left", fill="both", expand=True)
        barra = tk.Frame(contenido, bg=E.BLANCO, height=68)
        barra.pack(fill="x")
        barra.pack_propagate(False)
        self.lbl_titulo = tk.Label(barra, font=E.F_H2, fg=E.TEXTO, bg=E.BLANCO)
        self.lbl_titulo.pack(side="left", padx=28)
        tk.Frame(contenido, bg=E.BORDE, height=1).pack(fill="x")

        zona = tk.Frame(contenido, bg=E.FONDO)
        zona.pack(fill="both", expand=True, padx=28, pady=22)
        self.pestanas = {
            "Muro": PestanaMuro(zona, app),
            "Amigos": PestanaAmigos(zona, app),
            "Buscar": PestanaBuscar(zona, app),
            "Chat": PestanaChat(zona, app),
            "Perfil": PestanaPerfil(zona, app),
            "Personalizar": PestanaApariencia(zona, app),
            "Juegos": PestanaJuegos(zona, app),
        }
        self.actualizar_usuario()
        self.ir("Muro")

    # ------------------------------------------------------------ usuario
    def actualizar_usuario(self):
        p = self.app.perfil
        ruta = self.app.ruta_foto(p)
        self.av_lateral.cambiar(p["nombre"], p["usuario"], ruta, 40)
        self.lbl_nombre.config(text=p["nombre"])
        self.lbl_usuario.config(text="@" + p["usuario"])

    # --------------------------------------------------------- navegación
    def ir(self, nombre):
        if nombre == self.actual:
            self.pestanas[nombre].refrescar()
            return
        if self.actual:
            self.pestanas[self.actual].pack_forget()
            self.nav[self.actual].activar(False)
        self.actual = nombre
        self.pestanas[nombre].pack(fill="both", expand=True)
        self.nav[nombre].activar(True)
        self.nav[nombre].avisar(False)
        self.lbl_titulo.config(text=self.TITULOS[nombre])
        self.pestanas[nombre].refrescar()

    def abrir_chat(self, usuario):
        self.ir("Chat")
        self.pestanas["Chat"].abrir(usuario)

    # eventos enviados por el servidor sin que el usuario los pida
    def manejar_evento(self, ev):
        tipo = ev.get("tipo")
        toast = E.Toast
        if tipo == "chat":
            self.pestanas["Chat"].recibir(ev)
            if self.actual != "Chat":
                from gui.chat import resumen
                m = ev.get("mensaje") or ev
                self.nav["Chat"].avisar(True)
                donde = " en la sala general" if m.get("receptor") == "#general" else ""
                toast(self.app, f"@{m.get('emisor')}{donde}: {resumen(m)[:60]}",
                      icono="💬", comando=lambda: self.ir("Chat"))
        elif tipo == "invitacion_juego":
            self.pestanas["Juegos"].invitacion(ev)
        elif tipo == "juego_rechazado":
            toast(self.app, f"@{ev.get('usuario')} rechazó el reto", icono="🎮")
        elif tipo == "partida":
            self.pestanas["Juegos"].partida(ev)
        elif tipo == "mensaje_actualizado":
            self.pestanas["Chat"].actualizar(ev)
        elif tipo == "en_linea":
            if ev.get("en_linea"):
                toast(self.app, f"@{ev.get('usuario')} se conectó", icono="●")
            if self.actual in ("Amigos", "Chat"):
                self.pestanas[self.actual].refrescar()
        elif tipo == "solicitud":
            toast(self.app, f"@{ev.get('usuario')} quiere ser tu amigo", icono="👋",
                  comando=lambda: self.ir("Amigos"))
            if self.actual == "Amigos":
                self.pestanas["Amigos"].refrescar()
            else:
                self.nav["Amigos"].avisar(True)
        elif tipo == "publicacion":
            if self.actual == "Muro":
                self.pestanas["Muro"].refrescar()
            else:
                self.nav["Muro"].avisar(True)
                toast(self.app, f"@{ev.get('autor')} publicó algo nuevo", icono="📝",
                      comando=lambda: self.ir("Muro"))
