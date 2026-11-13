"""Pestaña Perfil: foto, bio y link (editable)."""
import tkinter as tk

from gui import estilo as E
from gui.estilo import respuesta_ok, alerta_info
from gui.muro import elegir_imagen
from gui.widgets import Avatar, Boton, Campo, AreaTexto, Tarjeta


class PestanaPerfil(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.ruta_foto_nueva = None

        tarjeta = Tarjeta(self)
        tarjeta.pack(fill="x")
        cuerpo = tk.Frame(tarjeta, bg=E.BLANCO)
        cuerpo.pack(fill="x", padx=32, pady=28)

        izq = tk.Frame(cuerpo, bg=E.BLANCO)
        izq.pack(side="left", anchor="n", padx=(0, 36))
        p = app.perfil
        self.avatar = Avatar(izq, p["nombre"], p["usuario"], lado=130, fondo=E.BLANCO)
        self.avatar.pack()
        Boton(izq, "Cambiar foto", self._cambiar_foto, "secundario", padx=14, pady=7,
              fondo=E.BLANCO).pack(pady=(14, 0))

        der = tk.Frame(cuerpo, bg=E.BLANCO)
        der.pack(side="left", fill="x", expand=True)
        self.lbl_nombre = tk.Label(der, font=E.F_H1, fg=E.TEXTO, bg=E.BLANCO)
        self.lbl_nombre.pack(anchor="w")
        self.lbl_usuario = tk.Label(der, font=(E.FAMILIA, 11), fg=E.SUAVE, bg=E.BLANCO)
        self.lbl_usuario.pack(anchor="w", pady=(0, 20))

        tk.Label(der, text="Bio", font=E.F_PEQ_NEG, fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w", pady=(0, 4))
        self.bio = AreaTexto(der, alto=5)
        self.bio.pack(fill="x")
        self.link = Campo(der, "Link", placeholder="https://…", fondo=E.BLANCO)
        self.link.pack(fill="x", pady=(16, 0))
        Boton(der, "Guardar cambios", self._guardar, "primario", padx=24, pady=9,
              fondo=E.BLANCO).pack(anchor="e", pady=(20, 0))

    def refrescar(self):
        resp = self.app.cliente.ver_perfil(self.app.perfil["usuario"])
        if not respuesta_ok(resp, "No se pudo cargar el perfil."):
            return
        p = resp["usuario"]
        self.app.perfil.update(p)
        self.ruta_foto_nueva = None
        self.lbl_nombre.config(text=p["nombre"])
        self.lbl_usuario.config(text="@" + p["usuario"])
        self.bio.set(p.get("bio", ""))
        self.link.set(p.get("link", ""))
        ruta = self.app.cliente.ruta_imagen(p.get("foto")) if p.get("foto") else None
        self.avatar.cambiar(p["nombre"], p["usuario"], ruta, 130)

    def _cambiar_foto(self):
        ruta = elegir_imagen()
        if ruta:
            self.ruta_foto_nueva = ruta
            p = self.app.perfil
            self.avatar.cambiar(p["nombre"], p["usuario"], ruta, 130)

    def _guardar(self):
        link = E.normalizar_link(self.link.get())
        resp = self.app.cliente.editar_perfil(self.bio.get(), self.ruta_foto_nueva, link)
        if respuesta_ok(resp, "No se pudo guardar el perfil."):
            alerta_info("Perfil actualizado.")
            self.refrescar()
            self.app.vista.actualizar_usuario()
