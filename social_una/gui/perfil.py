"""Pestaña Perfil (estilo Discord): banner, foto (también GIF animado), bio y link.

También define `CabeceraPerfil` (banner + avatar superpuesto) y `mostrar_perfil`,
la ventanita que se abre al hacer clic en el nombre o la foto de otra persona.
"""
import tkinter as tk

from gui import estilo as E
from gui.estilo import MarcoScroll, alerta_aviso, alerta_info, respuesta_ok
from gui.imagenes import avatar, banner, cuadros_avatar
from gui.muro import elegir_imagen
from gui.widgets import AreaTexto, Boton, Campo, Tarjeta

MAX_BIO = 190   # igual que el servidor


class CabeceraPerfil(tk.Canvas):
    """Banner con el avatar redondo encima del borde inferior, como en Discord.

    Con ancho=None ocupa todo el ancho disponible y se redibuja al cambiar.
    """

    def __init__(self, padre, app, ancho=None, alto_banner=140, lado=96, animado=True):
        self.app = app
        self.alto_banner, self.lado, self.animado = alto_banner, lado, animado
        self.ancho = ancho or 600
        super().__init__(padre, width=self.ancho, height=alto_banner + lado // 2 + 10,
                         bg=E.BLANCO, highlightthickness=0, bd=0)
        self._datos = None
        self._turno = 0
        if ancho is None:
            self.bind("<Configure>", self._redimensionar)

    def _redimensionar(self, e):
        # de 40 en 40 px (redondeado hacia arriba): no recalcula en cada píxel
        nuevo = max(300, (e.width // 40 + 1) * 40)
        if nuevo != self.ancho:
            self.ancho = nuevo
            if self._datos:
                self.mostrar(*self._datos)

    def mostrar(self, perfil, ruta_foto=None, ruta_banner=None, color=None):
        """Dibuja el perfil. ruta_*/color sirven para la vista previa antes de guardar."""
        self._datos = (perfil, ruta_foto, ruta_banner, color)
        ruta_imagen = self.app.cliente.ruta_imagen
        if ruta_banner is None:
            ruta_banner = ruta_imagen(perfil.get("banner")) if perfil.get("banner") else ""
        if ruta_foto is None:
            ruta_foto = ruta_imagen(perfil.get("foto")) if perfil.get("foto") else ""
        color = color or perfil.get("color_perfil") or E.ACENTO
        self._turno += 1
        self.delete("all")
        self._banner = banner(ruta_banner or None, color, self.ancho, self.alto_banner)
        self.create_image(0, 0, image=self._banner, anchor="nw")
        x, y = 22, self.alto_banner - self.lado // 2
        borde = 5   # aro del color de la tarjeta alrededor de la foto
        self.create_oval(x - borde, y - borde, x + self.lado + borde, y + self.lado + borde,
                         fill=E.BLANCO, outline="")
        self._foto = avatar(perfil.get("nombre", ""), perfil.get("usuario", ""),
                            ruta_foto or None, self.lado)
        self._item = self.create_image(x, y, image=self._foto, anchor="nw")
        cuadros = cuadros_avatar(ruta_foto, self.lado) if (self.animado and ruta_foto) else None
        if cuadros:
            self._animar(cuadros, 0, self._turno)

    def _animar(self, cuadros, i, turno):
        if turno != self._turno or not self.winfo_exists():
            return
        imagenes, tiempos = cuadros
        self.itemconfigure(self._item, image=imagenes[i])
        self.after(tiempos[i], lambda: self._animar(cuadros, (i + 1) % len(imagenes), turno))


class Muestras(tk.Canvas):
    """Fila de círculos de color para elegir el color del banner."""

    def __init__(self, padre, colores, al_elegir, lado=26):
        super().__init__(padre, height=lado + 8, width=len(colores) * (lado + 10),
                         bg=padre.cget("bg"), highlightthickness=0, bd=0, cursor="hand2")
        self.colores, self.al_elegir, self.lado = colores, al_elegir, lado
        self.elegido = None
        self.bind("<Button-1>", self._click)
        self.pintar()

    def pintar(self, elegido=None):
        self.elegido = elegido
        self.delete("all")
        for i, color in enumerate(self.colores):
            x = 4 + i * (self.lado + 10)
            if color == elegido:
                self.create_oval(x - 3, 1, x + self.lado + 3, self.lado + 7, outline=E.TEXTO, width=2)
            self.create_oval(x, 4, x + self.lado, 4 + self.lado, fill=color, outline="")

    def _click(self, e):
        i = int((e.x - 4) // (self.lado + 10))
        if 0 <= i < len(self.colores):
            self.pintar(self.colores[i])
            self.al_elegir(self.colores[i])


class PestanaPerfil(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self._limpiar_cambios()

        marco = MarcoScroll(self)
        marco.pack(fill="both", expand=True)
        tarjeta = Tarjeta(marco.interior)
        tarjeta.pack(fill="x", padx=(0, 10))

        self.cabecera = CabeceraPerfil(tarjeta, app, alto_banner=150, lado=110)
        self.cabecera.pack(fill="x")
        cuerpo = tk.Frame(tarjeta, bg=E.BLANCO)
        cuerpo.pack(fill="x", padx=32, pady=(4, 28))
        self.lbl_nombre = tk.Label(cuerpo, font=E.F_H1, fg=E.TEXTO, bg=E.BLANCO)
        self.lbl_nombre.pack(anchor="w")
        self.lbl_usuario = tk.Label(cuerpo, font=(E.FAMILIA, 11), fg=E.SUAVE, bg=E.BLANCO)
        self.lbl_usuario.pack(anchor="w", pady=(0, 18))

        # ---- foto
        self._titulo(cuerpo, "Foto de perfil")
        fila = tk.Frame(cuerpo, bg=E.BLANCO)
        fila.pack(fill="x")
        Boton(fila, "Cambiar foto", self._cambiar_foto, "secundario", padx=14, pady=7,
              fondo=E.BLANCO).pack(side="left")
        Boton(fila, "Quitar", self._quitar_foto, "fantasma", padx=12, pady=7,
              fondo=E.BLANCO).pack(side="left", padx=(6, 0))
        E.etiqueta(fila, "PNG, JPG o GIF · máx. 2 MB · los GIF se animan", E.F_PEQ, E.SUAVE,
                   E.BLANCO).pack(side="left", padx=(12, 0))

        # ---- banner
        self._titulo(cuerpo, "Banner")
        fila = tk.Frame(cuerpo, bg=E.BLANCO)
        fila.pack(fill="x")
        Boton(fila, "Imagen de banner", self._cambiar_banner, "secundario", padx=14, pady=7,
              fondo=E.BLANCO).pack(side="left")
        Boton(fila, "Quitar imagen", self._quitar_banner, "fantasma", padx=12, pady=7,
              fondo=E.BLANCO).pack(side="left", padx=(6, 0))
        E.etiqueta(fila, "o elige un color:", E.F_PEQ, E.SUAVE, E.BLANCO).pack(side="left", padx=(14, 8))
        self.muestras = Muestras(fila, E.COLORES_BANNER, self._elegir_color)
        self.muestras.pack(side="left")

        # ---- bio con contador
        cab_bio = tk.Frame(cuerpo, bg=E.BLANCO)
        cab_bio.pack(fill="x", pady=(18, 4))
        tk.Label(cab_bio, text="Bio", font=E.F_PEQ_NEG, fg=E.SUAVE, bg=E.BLANCO).pack(side="left")
        self.lbl_cuenta = tk.Label(cab_bio, font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO)
        self.lbl_cuenta.pack(side="right")
        self.bio = AreaTexto(cuerpo, alto=4)
        self.bio.pack(fill="x")
        self.bio.texto.bind("<KeyRelease>", lambda _e: self._contar())
        self.link = Campo(cuerpo, "Link", placeholder="https://…", fondo=E.BLANCO)
        self.link.pack(fill="x", pady=(16, 0))
        Boton(cuerpo, "Guardar cambios", self._guardar, "primario", padx=24, pady=9,
              fondo=E.BLANCO).pack(anchor="e", pady=(20, 0))

    def _titulo(self, padre, texto):
        tk.Label(padre, text=texto, font=E.F_PEQ_NEG, fg=E.SUAVE, bg=E.BLANCO).pack(
            anchor="w", pady=(14, 6))

    def _limpiar_cambios(self):
        # None = sin cambio; "" = quitar; ruta = archivo nuevo
        self.ruta_foto_nueva = None
        self.ruta_banner_nueva = None
        self.color_nuevo = None

    def _contar(self):
        n = len(self.bio.get())
        self.lbl_cuenta.config(text=f"{n}/{MAX_BIO}", fg=E.ROJO if n > MAX_BIO else E.SUAVE)

    def _vista_previa(self):
        self.cabecera.mostrar(self.app.perfil, self.ruta_foto_nueva, self.ruta_banner_nueva,
                              self.color_nuevo)

    def refrescar(self):
        resp = self.app.cliente.ver_perfil(self.app.perfil["usuario"])
        if not respuesta_ok(resp, "No se pudo cargar el perfil."):
            return
        p = resp["usuario"]
        self.app.perfil.update(p)
        self._limpiar_cambios()
        self.lbl_nombre.config(text=p["nombre"])
        self.lbl_usuario.config(text="@" + p["usuario"])
        self.bio.set(p.get("bio", ""))
        self.link.set(p.get("link", ""))
        self.muestras.pintar(p.get("color_perfil") or None)
        self._contar()
        self._vista_previa()

    def _cambiar_foto(self):
        ruta = elegir_imagen()
        if ruta:
            self.ruta_foto_nueva = ruta
            self._vista_previa()

    def _quitar_foto(self):
        self.ruta_foto_nueva = ""
        self._vista_previa()

    def _cambiar_banner(self):
        ruta = elegir_imagen()
        if ruta:
            self.ruta_banner_nueva = ruta
            self._vista_previa()

    def _quitar_banner(self):
        self.ruta_banner_nueva = ""
        self._vista_previa()

    def _elegir_color(self, color):
        self.color_nuevo = color
        if self.ruta_banner_nueva or self.app.perfil.get("banner"):
            self.ruta_banner_nueva = ""   # elegir un color reemplaza la imagen
        self._vista_previa()

    def _guardar(self):
        bio = self.bio.get()
        if len(bio) > MAX_BIO:
            alerta_aviso(f"La bio puede tener como máximo {MAX_BIO} caracteres.")
            return
        link = E.normalizar_link(self.link.get())
        resp = self.app.cliente.editar_perfil(bio, self.ruta_foto_nueva, link,
                                              ruta_banner=self.ruta_banner_nueva,
                                              color_perfil=self.color_nuevo)
        if respuesta_ok(resp, "No se pudo guardar el perfil."):
            alerta_info("Perfil actualizado.")
            self.app.perfiles.pop(self.app.perfil["usuario"], None)
            self.refrescar()
            self.app.vista.actualizar_usuario()


# ---------------------------------------------------------------------------
# Ventanita de perfil de otra persona
# ---------------------------------------------------------------------------
def mostrar_perfil(app, usuario):
    """Abre una tarjeta flotante con el perfil de `usuario` (una sola a la vez)."""
    previa = getattr(app, "_ventana_perfil", None)
    if previa is not None and previa[1].winfo_exists():
        if previa[0] == usuario:
            previa[1].deiconify()
            previa[1].lift()
            previa[1].focus_force()
            return      # ya está abierto: no se abre otra vez
        previa[1].destroy()
    p = app.perfil_de(usuario, recargar=True)
    if p is None:
        alerta_aviso("No se pudo cargar ese perfil.")
        return
    ancho = 420
    ven = tk.Toplevel(app, bg=E.BLANCO)
    app._ventana_perfil = (usuario, ven)
    ven.title(f"@{usuario}")
    ven.resizable(False, False)
    ven.transient(app)
    ven.bind("<Escape>", lambda _e: ven.destroy())
    cab = CabeceraPerfil(ven, app, ancho=ancho, alto_banner=130, lado=92)
    cab.pack()
    cab.mostrar(p)

    cuerpo = tk.Frame(ven, bg=E.BLANCO)
    cuerpo.pack(fill="x", padx=24, pady=(2, 22))
    tk.Label(cuerpo, text=p["nombre"], font=E.F_H2, fg=E.TEXTO, bg=E.BLANCO).pack(anchor="w")
    tk.Label(cuerpo, text="@" + usuario, font=E.F_NORMAL, fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w")
    if p.get("bio"):
        tk.Frame(cuerpo, bg=E.BORDE, height=1).pack(fill="x", pady=12)
        tk.Label(cuerpo, text="SOBRE MÍ", font=E.F_PEQ_NEG, fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w")
        tk.Label(cuerpo, text=p["bio"], font=E.F_NORMAL, fg=E.TEXTO, bg=E.BLANCO, wraplength=ancho - 48,
                 justify="left").pack(anchor="w", pady=(4, 0))
    if p.get("link"):
        chip = tk.Label(cuerpo, text="↗  " + p["link"], font=(E.FAMILIA, 10, "underline"),
                        fg=E.ACENTO if E.TEMA == "claro" else E.LATERAL_TEXTO, bg=E.CLARO,
                        padx=12, pady=6, cursor="hand2")
        chip.pack(anchor="w", pady=(12, 0))
        chip.bind("<Button-1>", lambda _e: E.abrir_link(p["link"]))

    acciones = tk.Frame(cuerpo, bg=E.BLANCO)
    acciones.pack(fill="x", pady=(18, 0))

    def ir(seccion, *args):
        ven.destroy()
        if seccion == "chat":
            app.vista.abrir_chat(*args)
        else:
            app.vista.ir(seccion)

    if usuario == app.perfil["usuario"]:
        Boton(acciones, "Editar mi perfil", lambda: ir("Perfil"), "primario",
              fondo=E.BLANCO).pack(side="left")
    else:
        resp = app.cliente.buscar_usuarios(usuario)
        info = next((u for u in resp.get("usuarios", []) if u["usuario"] == usuario), {})
        if info.get("amigo"):
            Boton(acciones, "Enviar mensaje", lambda: ir("chat", usuario), "primario",
                  fondo=E.BLANCO).pack(side="left")
        elif info.get("pendiente"):
            E.etiqueta(acciones, "Solicitud enviada", E.F_PEQ_NEG, E.SUAVE, E.BLANCO).pack(side="left")
        else:
            def agregar():
                if respuesta_ok(app.cliente.enviar_solicitud(usuario)):
                    alerta_info(f"Solicitud de amistad enviada a @{usuario}.")
                    ven.destroy()
            Boton(acciones, "Agregar amigo", agregar, "primario", fondo=E.BLANCO).pack(side="left")
    Boton(acciones, "Cerrar", ven.destroy, "secundario", fondo=E.BLANCO).pack(side="right")

    ven.update_idletasks()
    x = app.winfo_rootx() + (app.winfo_width() - ven.winfo_width()) // 2
    y = app.winfo_rooty() + (app.winfo_height() - ven.winfo_height()) // 3
    ven.geometry(f"+{max(0, x)}+{max(0, y)}")
    ven.focus_set()
