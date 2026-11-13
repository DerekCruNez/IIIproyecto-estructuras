"""Pestaña Muro: publicar (texto, imagen, link) y ver las publicaciones."""
import os
import tkinter as tk
from tkinter import filedialog

from gui import estilo as E
from gui import textos as T
from gui.estilo import MarcoScroll, alerta_aviso, respuesta_ok
from gui.imagenes import miniatura
from gui.widgets import Boton, Campo, AreaTexto, Tarjeta, Avatar, vacio

LIMITE_IMAGEN = 2 * 1024 * 1024  # 2 MB


def elegir_imagen():
    """Pide una imagen al usuario y valida su tamaño. Devuelve la ruta o None."""
    ruta = filedialog.askopenfilename(
        title="Elegir imagen",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png"), ("Todos los archivos", "*.*")])
    if not ruta:
        return None
    if os.path.getsize(ruta) > LIMITE_IMAGEN:
        alerta_aviso("La imagen pesa más de 2 MB. Elige una más pequeña.")
        return None
    return ruta


class PestanaMuro(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.ruta_imagen = None

        # ------------------------------------------------ nueva publicación
        comp = Tarjeta(self)
        comp.pack(fill="x")
        fila = tk.Frame(comp, bg=E.BLANCO)
        fila.pack(fill="x", padx=18, pady=16)
        p = app.perfil
        Avatar(fila, p["nombre"], p["usuario"], lado=44, fondo=E.BLANCO).pack(side="left", anchor="n")
        der = tk.Frame(fila, bg=E.BLANCO)
        der.pack(side="left", fill="x", expand=True, padx=(14, 0))
        tk.Label(der, text=T.MURO_INVITACION, font=E.F_NEG, fg=E.TEXTO,
                 bg=E.BLANCO).pack(anchor="w", pady=(0, 6))
        self.texto = AreaTexto(der, alto=3)
        self.texto.pack(fill="x")

        opciones = tk.Frame(der, bg=E.BLANCO)
        opciones.pack(fill="x", pady=(12, 0))
        Boton(opciones, "Adjuntar imagen", self._adjuntar, "secundario", padx=14, pady=7,
              fondo=E.BLANCO).pack(side="left")
        self.lbl_imagen = tk.Label(opciones, font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO)
        self.lbl_imagen.pack(side="left", padx=(8, 0))
        Boton(opciones, "Publicar", self._publicar, "primario", padx=22, pady=7,
              fondo=E.BLANCO).pack(side="right")
        self.link = Campo(opciones, placeholder="Link (opcional)", fondo=E.BLANCO)
        self.link.pack(side="right", fill="x", expand=True, padx=14)

        # ------------------------------------------------------ publicaciones
        self.marco = MarcoScroll(self)
        self.marco.pack(fill="both", expand=True, pady=(16, 0))

    # ------------------------------------------------------------ acciones
    def _adjuntar(self):
        ruta = elegir_imagen()
        if ruta:
            self.ruta_imagen = ruta
            self.lbl_imagen.config(text="📎 " + os.path.basename(ruta))

    def _publicar(self):
        texto = self.texto.get()
        link = E.normalizar_link(self.link.get())
        if not texto and not self.ruta_imagen and not link:
            alerta_aviso("Escribe un mensaje, adjunta una imagen o agrega un link.")
            return
        resp = self.app.cliente.publicar(texto, self.ruta_imagen, link)
        if respuesta_ok(resp, "No se pudo publicar."):
            self.texto.limpiar()
            self.link.set("")
            self.ruta_imagen = None
            self.lbl_imagen.config(text="")
            self.refrescar()

    def _like(self, id_publicacion):
        if respuesta_ok(self.app.cliente.dar_like(id_publicacion)):
            self.refrescar()

    # ---------------------------------------------------------------- muro
    def refrescar(self):
        resp = self.app.cliente.obtener_muro()
        if not respuesta_ok(resp, "No se pudo cargar el muro."):
            return
        self.marco.limpiar()
        pubs = resp.get("publicaciones", [])
        if not pubs:
            vacio(self.marco.interior, "Todavía no hay publicaciones.\n"
                                       "Publica algo o agrega amigos para ver su muro.").pack(pady=30)
            return
        for p in pubs:
            self._tarjeta(p)

    def _tarjeta(self, p):
        t = Tarjeta(self.marco.interior)
        t.pack(fill="x", pady=(0, 12), padx=(0, 10))
        cuerpo = tk.Frame(t, bg=E.BLANCO)
        cuerpo.pack(fill="x", padx=18, pady=16)

        cab = tk.Frame(cuerpo, bg=E.BLANCO)
        cab.pack(fill="x")
        Avatar(cab, p["autor"], p["autor"], lado=40, fondo=E.BLANCO).pack(side="left")
        datos = tk.Frame(cab, bg=E.BLANCO)
        datos.pack(side="left", padx=(12, 0))
        tk.Label(datos, text="@" + p["autor"], font=E.F_NEG, fg=E.TEXTO, bg=E.BLANCO).pack(anchor="w")
        tk.Label(datos, text=p["fecha"], font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w")

        if p.get("texto"):
            tk.Label(cuerpo, text=p["texto"], font=(E.FAMILIA, 11), fg=E.TEXTO, bg=E.BLANCO,
                     wraplength=640, justify="left", anchor="w").pack(anchor="w", pady=(12, 0))
        if p.get("imagen"):
            foto = miniatura(self.app.cliente.ruta_imagen(p["imagen"]))
            if foto:
                tk.Label(cuerpo, image=foto, bg=E.BLANCO, bd=0).pack(anchor="w", pady=(12, 0))
            else:
                tk.Label(cuerpo, text="[imagen no disponible]", font=E.F_PEQ, fg=E.SUAVE,
                         bg=E.BLANCO).pack(anchor="w", pady=(12, 0))
        if p.get("link"):
            chip = tk.Label(cuerpo, text="↗  " + p["link"], font=(E.FAMILIA, 10, "underline"),
                            fg=E.ACENTO, bg=E.CLARO, padx=12, pady=6, cursor="hand2")
            chip.pack(anchor="w", pady=(12, 0))
            chip.bind("<Button-1>", lambda _e, u=p["link"]: E.abrir_link(u))

        likes = p.get("likes", [])
        yo = self.app.perfil["usuario"] in likes
        tk.Frame(cuerpo, bg=E.BORDE, height=1).pack(fill="x", pady=(14, 8))
        Boton(cuerpo, f"{'♥' if yo else '♡'}  Me gusta  ·  {len(likes)}",
              lambda i=p["id"]: self._like(i), "peligro" if yo else "fantasma",
              padx=12, pady=5, fondo=E.BLANCO).pack(anchor="w")
