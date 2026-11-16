"""Pestaña Muro: publicar (texto, imagen, link) y ver las publicaciones.

Cada publicación tiene "me gusta" con animación y reacciones rápidas. Los cambios
se pintan al momento en la tarjeta (sin recargar todo el muro).
"""
import os
import time
import shutil
import tkinter as tk
import webbrowser
from tkinter import filedialog

from gui import estilo as E
from gui import textos as T
from gui.estilo import MarcoScroll, alerta_aviso, confirmar, respuesta_ok
from gui.imagenes import cuadros_imagen, miniatura
from gui.widgets import Boton, Campo, AreaTexto, Tarjeta, Avatar, vacio, pulso, animar, marcar_foco_programado
from gui.emojis import burbuja, foto_emoji, latido, separar
from gui.selectores import Emergente, SelectorEmoji

LIMITE_IMAGEN = 2 * 1024 * 1024  # 2 MB
FIRMAS = (b"\x89PNG", b"\xff\xd8", b"GIF8")
REACCIONES = ("😂", "🔥", "👏", "😮", "😢")   # las mismas que acepta el servidor
# Igual que el servidor: no se envían ni se abren programas o scripts.
EXTENSIONES_BLOQUEADAS = (".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".vbs",
                          ".js", ".jse", ".wsf", ".lnk", ".reg", ".dll", ".hta", ".jar")


def elegir_archivo():
    """Pide un archivo de hasta 2 MB que no sea un programa. Devuelve la ruta o None."""
    ruta = filedialog.askopenfilename(title="Adjuntar archivo (máx. 2 MB)")
    if not ruta:
        return None
    if os.path.getsize(ruta) > LIMITE_IMAGEN:
        alerta_aviso("El archivo pesa más de 2 MB.")
        return None
    if os.path.splitext(ruta)[1].lower() in EXTENSIONES_BLOQUEADAS:
        alerta_aviso("Por seguridad no se pueden adjuntar programas ni scripts.")
        return None
    return ruta


def abrir_archivo(ruta):
    """Abre un archivo descargado con el programa del sistema."""
    if os.path.splitext(ruta)[1].lower() in EXTENSIONES_BLOQUEADAS:
        alerta_aviso("Por seguridad, ese archivo no se abre desde aquí.")
        return
    try:
        os.startfile(ruta)          # Windows
    except AttributeError:
        webbrowser.open("file://" + ruta)


def tarjeta_archivo(padre, app, nombre_archivo, adjunto, fondo):
    """Tarjeta 📄 nombre + Abrir / Guardar para un archivo del servidor (muro y chat)."""
    from gui.emojis import foto_emoji
    t = tk.Frame(padre, bg=fondo, highlightthickness=1, highlightbackground=E.BORDE)
    tk.Label(t, image=foto_emoji("📄", 30), bg=fondo).pack(side="left", padx=(12, 8), pady=10)
    datos = tk.Frame(t, bg=fondo)
    datos.pack(side="left", padx=(0, 12), pady=8)
    tk.Label(datos, text=nombre_archivo or "archivo", font=E.F_NEG, fg=E.TEXTO,
             bg=fondo).pack(anchor="w")
    botones = tk.Frame(datos, bg=fondo)
    botones.pack(anchor="w", pady=(4, 0))

    def ruta():
        r = app.cliente.ruta_imagen(adjunto)
        if not r:
            alerta_aviso("No se pudo descargar el archivo.")
        return r

    def abrir():
        r = ruta()
        if r:
            abrir_archivo(r)

    def guardar():
        r = ruta()
        if r:
            destino = filedialog.asksaveasfilename(parent=app, initialfile=nombre_archivo)
            if destino:
                shutil.copyfile(r, destino)
                E.alerta_info("Archivo guardado")
    Boton(botones, "Abrir", abrir, "primario", padx=12, pady=4, fondo=fondo).pack(side="left")
    Boton(botones, "Guardar", guardar, "secundario", padx=12, pady=4,
          fondo=fondo).pack(side="left", padx=(6, 0))
    return t


def elegir_imagen():
    """Pide una imagen al usuario y valida tamaño y formato. Devuelve la ruta o None."""
    ruta = filedialog.askopenfilename(
        title="Elegir imagen",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.gif"), ("Todos los archivos", "*.*")])
    if not ruta:
        return None
    if os.path.getsize(ruta) > LIMITE_IMAGEN:
        alerta_aviso("La imagen pesa más de 2 MB. Elige una más pequeña.")
        return None
    with open(ruta, "rb") as archivo:
        if not archivo.read(4).startswith(FIRMAS):
            alerta_aviso("Formato no permitido. Usa PNG, JPG o GIF.")
            return None
    return ruta


class MeGusta(tk.Frame):
    """Corazón + contador. Al darle like el corazón "late"."""

    def __init__(self, padre, app, publicacion):
        super().__init__(padre, bg=padre.cget("bg"), cursor="hand2")
        self.app, self.p = app, publicacion
        self.corazon = tk.Label(self, bg=self.cget("bg"), width=2)
        self.corazon.pack(side="left")
        self.cuenta = tk.Label(self, font=E.F_PEQ_NEG, bg=self.cget("bg"))
        self.cuenta.pack(side="left")
        for w in (self, self.corazon, self.cuenta):
            w.bind("<Button-1>", lambda _e: self._click())
        self._pintar()

    def _pintar(self):
        yo = self.app.perfil["usuario"] in self.p["likes"]
        self.corazon.config(text="♥" if yo else "♡", fg=E.ROJO if yo else E.SUAVE,
                            font=(E.FAMILIA, 14))
        n = len(self.p["likes"])
        self.cuenta.config(text=f"{n} me gusta" if n else "Me gusta", fg=E.ROJO if yo else E.SUAVE)

    def _click(self):
        if not respuesta_ok(self.app.cliente.dar_like(self.p["id"])):
            return
        yo = self.app.perfil["usuario"]
        if yo in self.p["likes"]:
            self.p["likes"].remove(yo)
            self._pintar()
        else:
            self.p["likes"].append(yo)
            self._pintar()
            pulso(self.corazon, (17, 21, 18, 14))


_selector = {"abierto": None, "root": None}   # la fila de reacciones con el selector visible


def _clic_global(e):
    """Un clic fuera del selector ☺+ lo cierra."""
    r = _selector["abierto"]
    if r is None or r.selector is None:
        return
    w = e.widget
    while w is not None:
        if w is r.selector or w is r.boton:
            return
        w = getattr(w, "master", None)
    r._cerrar_selector()


class Reacciones(tk.Frame):
    """Chips con las reacciones de la publicación y un selector de emojis."""

    def __init__(self, padre, app, publicacion):
        super().__init__(padre, bg=padre.cget("bg"))
        self.app, self.p = app, publicacion
        self.selector = None
        self._pintar()

    def _pintar(self, animar=None):
        for w in self.winfo_children():
            w.destroy()
        self.selector = None
        yo = self.app.perfil["usuario"]
        fondo = self.cget("bg")
        for emoji, usuarios in self.p.get("reacciones", {}).items():
            mio = yo in usuarios
            chip = tk.Label(self, image=foto_emoji(emoji, 18), text=f" {len(usuarios)}",
                            compound="left", font=E.F_PEQ_NEG,
                            bg=E.CLARO if mio else E.BOTON_SEC, fg=E.TEXTO, padx=8, pady=2,
                            cursor="hand2", highlightthickness=1,
                            highlightbackground=E.ACENTO if mio else E.BOTON_SEC)
            chip.pack(side="left", padx=(0, 6))
            chip.bind("<Button-1>", lambda _e, em=emoji: self._reaccionar(em))
            if emoji == animar:
                latido(chip, emoji, (22, 26, 20, 18))
        self.boton = tk.Label(self, text="☺+", font=(E.FAMILIA, 11), fg=E.SUAVE, bg=fondo,
                              padx=6, cursor="hand2")
        self.boton.pack(side="left")
        self.boton.bind("<Button-1>", lambda _e: self._alternar_selector())
        self.boton.bind("<Enter>", lambda _e: self.boton.config(fg=E.TEXTO))
        self.boton.bind("<Leave>", lambda _e: self.boton.config(fg=E.SUAVE))

    def _cerrar_selector(self):
        if self.selector is not None:
            try:
                self.selector.destroy()
            except tk.TclError:
                pass
            self.selector = None
        if _selector["abierto"] is self:
            _selector["abierto"] = None

    def _alternar_selector(self):
        if self.selector is not None:
            self._cerrar_selector()
            return
        anterior = _selector["abierto"]
        if anterior is not None and anterior is not self:
            try:
                anterior._cerrar_selector()     # solo uno abierto a la vez
            except tk.TclError:
                pass
        _selector["abierto"] = self
        if _selector["root"] is None:
            _selector["root"] = self.winfo_toplevel()
            _selector["root"].bind("<Button-1>", _clic_global, add="+")
        self.selector = tk.Frame(self, bg=E.BOTON_SEC, padx=4, pady=2)
        self.selector.pack(side="left", padx=(4, 0))
        for emoji in REACCIONES:
            lbl = tk.Label(self.selector, image=foto_emoji(emoji, 22), bg=E.BOTON_SEC,
                           cursor="hand2", padx=3, width=30, height=30)
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda _e, em=emoji: self._reaccionar(em))
            # los emojis crecen al pasar el mouse
            lbl.bind("<Enter>", lambda _e, w=lbl, em=emoji: w.config(image=foto_emoji(em, 28)))
            lbl.bind("<Leave>", lambda _e, w=lbl, em=emoji: w.config(image=foto_emoji(em, 22)))

    def _reaccionar(self, emoji):
        if not respuesta_ok(self.app.cliente.reaccionar(self.p["id"], emoji)):
            return
        yo = self.app.perfil["usuario"]
        reacciones = self.p.setdefault("reacciones", {})
        lista = reacciones.setdefault(emoji, [])
        if yo in lista:
            lista.remove(yo)
            if not lista:
                del reacciones[emoji]
            self._pintar()
        else:
            lista.append(yo)
            self._pintar(animar=emoji)


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
        self.avatar = Avatar(fila, p["nombre"], p["usuario"], app.ruta_foto(p), lado=44,
                             fondo=E.BLANCO)
        self.avatar.pack(side="left", anchor="n")
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
        self.btn_gif = Boton(opciones, "GIF", self._adjuntar_gif, "secundario", padx=12, pady=7,
                             fondo=E.BLANCO)
        self.btn_gif.pack(side="left", padx=(6, 0))
        Boton(opciones, "Archivo", self._adjuntar_archivo, "secundario", padx=12, pady=7,
              fondo=E.BLANCO).pack(side="left", padx=(6, 0))
        self.btn_emoji = tk.Label(opciones, image=foto_emoji("🙂", 22), bg=E.BLANCO,
                                  cursor="hand2", padx=6)
        self.btn_emoji.pack(side="left", padx=(6, 0))
        self.btn_emoji.bind("<Button-1>", lambda _e: Emergente.alternar(
            self.btn_emoji, lambda: SelectorEmoji(self.app, self.btn_emoji, self.texto.insertar)))
        Boton(opciones, "Publicar", self._publicar, "primario", padx=22, pady=7,
              fondo=E.BLANCO).pack(side="right")
        self.link = Campo(opciones, placeholder="Link (opcional)", fondo=E.BLANCO)
        self.link.pack(side="right", fill="x", expand=True, padx=14)
        # lo adjuntado se muestra debajo, con una ✕ para quitarlo
        self.adjuntos = tk.Frame(der, bg=E.BLANCO)
        self.adjuntos.pack(fill="x")
        self.ruta_archivo = None

        # ------------------------------------------------------ publicaciones
        self.marco = MarcoScroll(self)
        self.marco.pack(fill="both", expand=True, pady=(16, 0))

    # ------------------------------------------------------------ acciones
    def _adjuntar(self):
        ruta = elegir_imagen()
        if ruta:
            self.ruta_imagen = ruta
            self._pintar_adjuntos()

    def _adjuntar_gif(self):
        from gui.selectores import SelectorGif
        from gui.sonidos import guardar_prefs

        def elegido(ruta):
            guardar_prefs(self.app.prefs)
            self.ruta_imagen = ruta
            self._pintar_adjuntos()
        Emergente.alternar(self.btn_gif, lambda: SelectorGif(
            self.app, self.btn_gif, elegido, self.app.prefs))

    def _adjuntar_archivo(self):
        ruta = elegir_archivo()
        if ruta:
            self.ruta_archivo = ruta
            self._pintar_adjuntos()

    def _pintar_adjuntos(self):
        for w in self.adjuntos.winfo_children():
            w.destroy()
        for ruta, quitar in ((self.ruta_imagen, "imagen"), (self.ruta_archivo, "archivo")):
            if not ruta:
                continue
            chip = tk.Frame(self.adjuntos, bg=E.BOTON_SEC)
            chip.pack(side="left", padx=(0, 6), pady=(8, 0))
            icono = "🖼 " if quitar == "imagen" else "📎 "
            tk.Label(chip, text=icono + os.path.basename(ruta), font=E.F_PEQ, fg=E.TEXTO,
                     bg=E.BOTON_SEC, padx=8, pady=3).pack(side="left")
            x = tk.Label(chip, text="✕", font=E.F_PEQ_NEG, fg=E.SUAVE, bg=E.BOTON_SEC,
                         cursor="hand2", padx=6)
            x.pack(side="left")
            x.bind("<Button-1>", lambda _e, q=quitar: self._quitar_adjunto(q))

    def _quitar_adjunto(self, cual):
        setattr(self, "ruta_imagen" if cual == "imagen" else "ruta_archivo", None)
        self._pintar_adjuntos()

    def _publicar(self):
        texto = self.texto.get()
        link = E.normalizar_link(self.link.get())
        if not texto and not self.ruta_imagen and not link and not self.ruta_archivo:
            alerta_aviso("Escribe un mensaje, adjunta una imagen o agrega un link.")
            return
        resp = self.app.cliente.publicar(texto, self.ruta_imagen, link, self.ruta_archivo)
        if respuesta_ok(resp, "No se pudo publicar."):
            self.texto.limpiar()
            self.link.set("")
            self.ruta_imagen = self.ruta_archivo = None
            self._pintar_adjuntos()
            E.alerta_info("Publicado")
            self.refrescar()

    # ---------------------------------------------------------------- muro
    def refrescar(self):
        # la foto propia y las de los autores pueden haber cambiado
        p = self.app.perfil
        self.avatar.cambiar(p["nombre"], p["usuario"], self.app.ruta_foto(p), 44)
        self.app.perfiles.clear()
        resp = self.app.cliente.obtener_muro()
        if not respuesta_ok(resp, "No se pudo cargar el muro."):
            return
        self.marco.limpiar(conservar=True)
        pubs = resp.get("publicaciones", [])
        if not pubs:
            vacio(self.marco.interior, "Todavía no hay publicaciones.\n"
                                       "Publica algo o agrega amigos para ver su muro.").pack(pady=30)
            return
        for p in pubs:
            self._tarjeta(p)

    def _tarjeta(self, p):
        t = Tarjeta(self.marco.interior, hover=True)
        t.pack(fill="x", pady=(0, 12), padx=(0, 10))
        cuerpo = tk.Frame(t, bg=E.BLANCO)
        cuerpo.pack(fill="x", padx=18, pady=16)

        autor = self.app.perfil_de(p["autor"]) or {"nombre": p["autor"], "usuario": p["autor"]}
        cab = tk.Frame(cuerpo, bg=E.BLANCO)
        cab.pack(fill="x")
        av = Avatar(cab, autor["nombre"], p["autor"], self.app.ruta_foto(autor), lado=40,
                    fondo=E.BLANCO)
        av.pack(side="left")
        datos = tk.Frame(cab, bg=E.BLANCO)
        datos.pack(side="left", padx=(12, 0))
        arriba = tk.Frame(datos, bg=E.BLANCO)
        arriba.pack(anchor="w")
        nombre = tk.Label(arriba, text=autor["nombre"], font=E.F_NEG, fg=E.TEXTO, bg=E.BLANCO)
        nombre.pack(side="left")
        tk.Label(arriba, text=f"  @{p['autor']}", font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO).pack(side="left")
        cuando = E.tiempo_relativo(p["fecha"]) + ("  ·  (editado)" if p.get("editado") else "")
        tk.Label(datos, text=cuando, font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w")
        if p["autor"] == self.app.perfil["usuario"]:
            mas = tk.Label(cab, text="⋯", font=(E.FAMILIA, 16, "bold"), fg=E.SUAVE, bg=E.BLANCO,
                           cursor="hand2", padx=8)
            mas.pack(side="right", anchor="n")
            mas.bind("<Button-1>", lambda e: self._menu_publicacion(e, p, t, zona_texto))
        for w in (av, nombre):   # clic en el autor: ver su perfil
            w.config(cursor="hand2")
            w.bind("<Button-1>", lambda _e, u=p["autor"]: self.app.ver_perfil(u))
        nombre.bind("<Enter>", lambda _e: nombre.config(font=(E.FAMILIA, 10, "bold underline")))
        nombre.bind("<Leave>", lambda _e: nombre.config(font=E.F_NEG))

        zona_texto = tk.Frame(cuerpo, bg=E.BLANCO)
        zona_texto.pack(fill="x")
        self._pintar_texto(zona_texto, p["texto"])
        if p.get("imagen"):
            ruta = self.app.cliente.ruta_imagen(p["imagen"])
            cuadros = cuadros_imagen(ruta, (520, 340))
            foto = None if cuadros else miniatura(ruta)
            if cuadros or foto:
                lbl = tk.Label(cuerpo, image=foto, bg=E.BLANCO, bd=0)
                lbl.pack(anchor="w", pady=(12, 0))
                if cuadros:          # los GIF se ven animados
                    animar(lbl, cuadros)
            else:
                tk.Label(cuerpo, text="[imagen no disponible]", font=E.F_PEQ, fg=E.SUAVE,
                         bg=E.BLANCO).pack(anchor="w", pady=(12, 0))
        if p.get("link"):
            chip = tk.Label(cuerpo, text="↗  " + p["link"], font=(E.FAMILIA, 10, "underline"),
                            fg=E.ACENTO if E.TEMA == "claro" else E.LATERAL_TEXTO, bg=E.CLARO,
                            padx=12, pady=6, cursor="hand2")
            chip.pack(anchor="w", pady=(12, 0))
            chip.bind("<Button-1>", lambda _e, u=p["link"]: E.abrir_link(u))

        if p.get("archivo"):
            tarjeta_archivo(cuerpo, self.app, p.get("nombre_archivo"), p["archivo"],
                            E.BLANCO).pack(anchor="w", pady=(12, 0))

        tk.Frame(cuerpo, bg=E.BORDE, height=1).pack(fill="x", pady=(14, 8))
        pie = tk.Frame(cuerpo, bg=E.BLANCO)
        pie.pack(fill="x")
        MeGusta(pie, self.app, p).pack(side="left")
        Reacciones(pie, self.app, p).pack(side="left", padx=(18, 0))

    # ------------------------------------------------- editar / eliminar
    def _pintar_texto(self, zona, texto):
        for w in zona.winfo_children():
            w.destroy()
        if texto and separar(texto):   # con emojis: se dibuja a color
            tk.Label(zona, image=burbuja(texto, None, E.TEXTO, 680, 15, relleno=(0, 0)),
                     bg=E.BLANCO, bd=0).pack(anchor="w", pady=(12, 0))
        elif texto:
            tk.Label(zona, text=texto, font=(E.FAMILIA, 11), fg=E.TEXTO, bg=E.BLANCO,
                     wraplength=640, justify="left", anchor="w").pack(anchor="w", pady=(12, 0))

    def _menu_publicacion(self, e, p, tarjeta, zona_texto):
        if time.monotonic() - getattr(self, "_menu_cierre", 0.0) < 0.35:
            return      # el clic en ⋯ con el menú abierto solo lo cierra
        menu = tk.Menu(self, tearoff=0, bg=E.BLANCO, fg=E.TEXTO, activebackground=E.CLARO,
                       activeforeground=E.TEXTO, font=E.F_NORMAL)
        menu.add_command(label="Editar publicación", command=lambda: self._editar(p, zona_texto))
        menu.add_separator()
        menu.add_command(label="Eliminar publicación", foreground=E.ROJO,
                         command=lambda: self._eliminar(p, tarjeta))
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()
            self._menu_cierre = time.monotonic()

    def _editar(self, p, zona):
        """Cambia el texto por un cuadro editable con Guardar y Cancelar."""
        for w in zona.winfo_children():
            w.destroy()
        area = AreaTexto(zona, alto=3)
        area.pack(fill="x", pady=(12, 0))
        area.set(p["texto"])
        marcar_foco_programado()
        area.texto.focus_set()
        botones = tk.Frame(zona, bg=E.BLANCO)
        botones.pack(anchor="e", pady=(8, 0))
        emoji = tk.Label(botones, image=foto_emoji("🙂", 20), bg=E.BLANCO, cursor="hand2", padx=6)
        emoji.pack(side="left")
        emoji.bind("<Button-1>", lambda _e: Emergente.alternar(
            emoji, lambda: SelectorEmoji(self.app, emoji, area.insertar)))

        def guardar():
            texto = area.get()
            if respuesta_ok(self.app.cliente.editar_publicacion(p["id"], texto),
                            "No se pudo editar la publicación."):
                p.update(texto=texto, editado=True)
                self._pintar_texto(zona, texto)
                E.alerta_info("Publicación editada")
        Boton(botones, "Cancelar", lambda: self._pintar_texto(zona, p["texto"]), "secundario",
              padx=12, pady=5, fondo=E.BLANCO).pack(side="left", padx=(6, 0))
        Boton(botones, "Guardar", guardar, "primario", padx=14, pady=5,
              fondo=E.BLANCO).pack(side="left", padx=(6, 0))

    def _eliminar(self, p, tarjeta):
        if confirmar("¿Eliminar esta publicación? No se puede deshacer."):
            if respuesta_ok(self.app.cliente.eliminar_publicacion(p["id"]),
                            "No se pudo eliminar la publicación."):
                tarjeta.destroy()
                E.alerta_info("Publicación eliminada")
