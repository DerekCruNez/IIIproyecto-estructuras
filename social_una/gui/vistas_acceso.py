"""Pantallas de acceso: conexión al servidor, inicio de sesión y registro."""
import tkinter as tk
from tkinter import font as tkfont

from gui import estilo as E
from gui import textos as T
from gui.estilo import alerta_aviso, alerta_info, respuesta_ok
from gui.imagenes import constelacion, logo
from gui.widgets import Boton, Campo

ANCHO_FORM = 360


class PanelMarca(tk.Canvas):
    """Panel izquierdo: fondo de red de nodos, logo, lema y ventajas."""

    ANCHO = 420

    def __init__(self, padre):
        super().__init__(padre, width=self.ANCHO, bg=E.MARINO, highlightthickness=0, bd=0)
        self.fondo = constelacion(self.ANCHO, 1100)
        self.logo = logo(76)
        self.create_image(0, 0, image=self.fondo, anchor="nw")
        self.i_logo = self.create_image(0, 0, image=self.logo, anchor="nw")
        fuente_marca = (E.FAMILIA, 30, "bold")
        self.i_social = self.create_text(0, 0, text="Social ", font=fuente_marca, fill="white", anchor="w")
        self.i_una = self.create_text(0, 0, text="UNA", font=fuente_marca, fill=E.DESTACADO, anchor="w")
        self.ancho_social = tkfont.Font(font=fuente_marca).measure("Social ")
        self.i_lema = self.create_text(0, 0, text=T.LEMA, font=(E.FAMILIA, 20, "bold"), fill="white",
                                      anchor="nw", width=340)
        self.i_desc = self.create_text(0, 0, text=T.DESCRIPCION, font=(E.FAMILIA, 11),
                                       fill=E.LATERAL_SUAVE, anchor="nw", width=340)
        self.i_puntos, self.i_ventajas = [], []
        for ventaja in T.VENTAJAS:
            self.i_puntos.append(self.create_oval(0, 0, 8, 8, fill=E.DESTACADO, outline=""))
            self.i_ventajas.append(self.create_text(0, 0, text=ventaja, font=(E.FAMILIA, 11),
                                                    fill=E.LATERAL_TEXTO, anchor="w"))
        self.i_pie = self.create_text(0, 0, text=T.PIE, font=E.F_PEQ, fill=E.LATERAL_SUAVE, anchor="w")
        self.bind("<Configure>", self._colocar)

    def _colocar(self, e):
        x, alto_bloque = 56, 430
        y = max(48, (e.height - alto_bloque) // 2)
        self.coords(self.i_logo, x, y)
        self.coords(self.i_social, x + 92, y + 38)
        self.coords(self.i_una, x + 92 + self.ancho_social, y + 38)
        self.coords(self.i_lema, x, y + 120)
        self.coords(self.i_desc, x, y + 214)
        for i, (punto, texto) in enumerate(zip(self.i_puntos, self.i_ventajas)):
            cy = y + 310 + i * 38
            self.coords(punto, x, cy - 4, x + 8, cy + 4)
            self.coords(texto, x + 24, cy)
        self.coords(self.i_pie, x, e.height - 30)


class _Acceso(tk.Frame):
    """Panel de marca a la izquierda y formulario centrado a la derecha."""

    titulo = ""
    subtitulo = ""
    volver = None   # función a la que regresa el botón "Volver" (None = sin botón)

    def __init__(self, padre, app):
        super().__init__(padre, bg=E.BLANCO)
        self.app = app
        self.campos = {}

        # ---- panel de marca
        PanelMarca(self).pack(side="left", fill="y")

        # ---- formulario
        der = tk.Frame(self, bg=E.BLANCO)
        der.pack(side="left", fill="both", expand=True)
        if self.volver:
            Boton(der, "←  Volver", self.volver, "secundario", padx=14, pady=6,
                  fondo=E.BLANCO).place(x=28, y=26)
        self.centro = tk.Frame(der, bg=E.BLANCO)
        self.centro.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(self.centro, text=self.titulo, font=E.F_H1, fg=E.TEXTO, bg=E.BLANCO).pack(anchor="w")
        tk.Label(self.centro, text=self.subtitulo, font=E.F_NORMAL, fg=E.SUAVE, bg=E.BLANCO).pack(
            anchor="w", pady=(2, 20))

    def campo(self, clave, etiqueta, oculto=False, valor="", placeholder=""):
        c = Campo(self.centro, etiqueta, oculto=oculto, valor=valor, placeholder=placeholder)
        c.pack(fill="x", pady=7)
        c.al_presionar_enter(self.enviar)
        self.campos[clave] = c
        return c

    def boton(self, texto, comando, principal=True):
        b = Boton(self.centro, texto, comando, "primario" if principal else "secundario",
                  ancho=ANCHO_FORM, pady=10)
        b.pack(pady=(16, 0) if principal else (8, 0))
        return b

    def valor(self, clave):
        return self.campos[clave].get().strip()

    def enviar(self):
        raise NotImplementedError


class VistaConexion(_Acceso):
    titulo = T.CONEXION_TITULO
    subtitulo = T.CONEXION_SUBTITULO

    def __init__(self, padre, app):
        super().__init__(padre, app)
        primer = self.campo("ip", "IP del servidor", valor="127.0.0.1")
        self.campo("puerto", "Puerto", valor="5000")
        self.boton("Conectar", self.enviar)
        if app.modo_demo:
            nota = tk.Frame(self.centro, bg="#fef3c7", padx=12, pady=10)
            nota.pack(fill="x", pady=(18, 0))
            tk.Label(nota, bg="#fef3c7", fg="#92400e", font=E.F_PEQ, justify="left", anchor="w",
                     text="Modo demostración: no hay servidor real.\n"
                          "Cualquier IP funciona. Usuarios: ana, luis, maria\ny pedro (clave 1234).").pack(anchor="w")
        primer.focus()

    def enviar(self):
        ip, puerto = self.valor("ip"), self.valor("puerto")
        if not ip or not puerto:
            alerta_aviso("Escribe la IP y el puerto del servidor.")
            return
        if not puerto.isdigit() or not (1 <= int(puerto) <= 65535):
            alerta_aviso("El puerto debe ser un número entre 1 y 65535.")
            return
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            resp = self.app.cliente.conectar(ip, int(puerto))
        except Exception as e:
            resp = {"ok": False, "error": f"No se pudo conectar: {e}"}
        self.config(cursor="")
        if respuesta_ok(resp, "No se pudo conectar con el servidor."):
            self.app.mostrar_login()


class VistaLogin(_Acceso):
    titulo = T.LOGIN_TITULO
    subtitulo = T.LOGIN_SUBTITULO

    def __init__(self, padre, app):
        self.volver = app.mostrar_conexion
        super().__init__(padre, app)
        primer = self.campo("usuario", "Usuario")
        self.campo("clave", "Contraseña", oculto=True)
        self.boton("Entrar", self.enviar)
        self.boton("Crear cuenta nueva", self.app.mostrar_registro, principal=False)
        primer.focus()

    def enviar(self):
        usuario, clave = self.valor("usuario"), self.campos["clave"].get()
        if not usuario or not clave:
            alerta_aviso("Escribe tu usuario y tu contraseña.")
            return
        resp = self.app.cliente.login(usuario, clave)
        if respuesta_ok(resp, "Usuario o contraseña incorrectos."):
            self.app.perfil = resp["usuario"]
            self.app.mostrar_principal()


class VistaRegistro(_Acceso):
    titulo = T.REGISTRO_TITULO
    subtitulo = T.REGISTRO_SUBTITULO

    def __init__(self, padre, app):
        self.volver = app.mostrar_login
        super().__init__(padre, app)
        self.centro.place_configure(rely=0.55)
        primer = self.campo("id", "ID")
        self.campo("nombre", "Nombre completo")
        self.campo("usuario", "Usuario")
        self.campo("clave", "Contraseña", oculto=True)
        self.campo("clave2", "Repetir contraseña", oculto=True)
        self.boton("Registrarme", self.enviar)
        primer.focus()

    def enviar(self):
        id_, nombre, usuario = self.valor("id"), self.valor("nombre"), self.valor("usuario")
        clave, clave2 = self.campos["clave"].get(), self.campos["clave2"].get()
        if not (id_ and nombre and usuario and clave and clave2):
            alerta_aviso("Completa todos los campos.")
            return
        if " " in usuario:
            alerta_aviso("El usuario no puede tener espacios.")
            return
        if clave != clave2:
            alerta_aviso("Las contraseñas no coinciden.")
            return
        resp = self.app.cliente.registrar(id_, nombre, usuario, clave)
        if respuesta_ok(resp, "No se pudo registrar el usuario."):
            alerta_info("Cuenta creada. Ya puedes iniciar sesión.")
            self.app.mostrar_login()
