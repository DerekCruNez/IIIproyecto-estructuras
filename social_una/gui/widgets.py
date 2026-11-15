"""Componentes propios reutilizables: botón, campo de texto, tarjeta, avatar y fila de usuario."""
import tkinter as tk
from tkinter import font as tkfont

from gui import estilo as E
from gui.imagenes import avatar as _avatar


def _rect_redondeado(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Boton(tk.Canvas):
    """Botón con esquinas redondeadas y efecto hover.

    estilos: primario, secundario, fantasma (sin fondo), peligro, oscuro (sobre el panel lateral)
    """
    # (fondo normal, fondo hover, color del texto)
    ESTILOS = {
        "primario": (E.ACENTO, E.ACENTO_HOVER, "#ffffff"),
        "secundario": (E.BOTON_SEC, E.BOTON_SEC_HOVER, E.TEXTO),
        "fantasma": (None, E.BOTON_SEC, E.ACENTO),
        "peligro": ("#fee2e2", "#fecaca", E.ROJO),
        "oscuro": (E.MARINO_2, "#1b5863", "#ffffff"),
    }

    def __init__(self, padre, texto, comando=None, estilo="primario", ancho=None,
                 padx=18, pady=9, fuente=None, fondo=None):
        self._fuente = fuente or E.F_BOTON
        f = tkfont.Font(font=self._fuente)
        self._padx = padx
        self._ancho_fijo = ancho
        w = ancho or f.measure(texto) + 2 * padx
        h = f.metrics("linespace") + 2 * pady
        super().__init__(padre, width=w, height=h, bg=fondo or padre.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        self.comando = comando
        self.estilo = estilo
        self.texto = texto
        self.habilitado = True
        self._ancho, self._alto = w, h
        self._hover = False
        self.bind("<Enter>", lambda _e: self._cambiar_hover(True))
        self.bind("<Leave>", lambda _e: self._cambiar_hover(False))
        self.bind("<ButtonRelease-1>", self._soltar)
        self._pintar()

    def _cambiar_hover(self, valor):
        self._hover = valor
        self._pintar()

    def _pintar(self):
        normal, hover, color = self.ESTILOS[self.estilo]
        if not self.habilitado:
            fondo, color = (E.BOTON_SEC if normal else None), E.GRIS_PH
        else:
            fondo = hover if self._hover else normal
        self.delete("all")
        if fondo:
            _rect_redondeado(self, 1, 1, self._ancho - 1, self._alto - 1, 8, fill=fondo, outline=fondo)
        self.create_text(self._ancho / 2, self._alto / 2, text=self.texto, font=self._fuente, fill=color)
        self.configure(cursor="hand2" if self.habilitado else "arrow")

    def _soltar(self, e):
        if self.habilitado and self.comando and 0 <= e.x <= self._ancho and 0 <= e.y <= self._alto:
            self.comando()

    def configurar(self, texto=None):
        if texto is not None:
            self.texto = texto
            if not self._ancho_fijo:
                self._ancho = tkfont.Font(font=self._fuente).measure(texto) + 2 * self._padx
                self.configure(width=self._ancho)
            self._pintar()

    def habilitar(self, valor=True):
        self.habilitado = valor
        self._pintar()


class Campo(tk.Frame):
    """Campo de una línea con etiqueta opcional, borde que cambia al enfocar y placeholder."""

    def __init__(self, padre, etiqueta=None, oculto=False, valor="", placeholder="", fondo=None):
        fondo = fondo or padre.cget("bg")
        super().__init__(padre, bg=fondo)
        if etiqueta:
            tk.Label(self, text=etiqueta, font=E.F_PEQ_NEG, fg=E.SUAVE, bg=fondo,
                     anchor="w").pack(fill="x", pady=(0, 4))
        self._oculto = "•" if oculto else ""
        self._placeholder = placeholder
        self._ph_activo = False
        self.borde = tk.Frame(self, bg=E.BORDE, padx=1, pady=1)
        self.borde.pack(fill="x")
        interior = tk.Frame(self.borde, bg="white")
        interior.pack(fill="x")
        self.var = tk.StringVar(value=valor)
        self.entrada = tk.Entry(interior, textvariable=self.var, relief="flat", bd=0, font=E.F_NORMAL,
                                bg="white", fg=E.TEXTO, insertbackground=E.TEXTO,
                                highlightthickness=0, show=self._oculto)
        self.entrada.pack(fill="x", padx=10, ipady=7)
        self.entrada.bind("<FocusIn>", self._al_enfocar)
        self.entrada.bind("<FocusOut>", self._al_desenfocar)
        if placeholder and not valor:
            self._poner_ph()

    def _poner_ph(self):
        self._ph_activo = True
        self.entrada.config(fg=E.GRIS_PH, show="")
        self.var.set(self._placeholder)

    def _al_enfocar(self, _e):
        self.borde.config(bg=E.ACENTO)
        if self._ph_activo:
            self._ph_activo = False
            self.var.set("")
            self.entrada.config(fg=E.TEXTO, show=self._oculto)

    def _al_desenfocar(self, _e):
        self.borde.config(bg=E.BORDE)
        if not self.var.get() and self._placeholder:
            self._poner_ph()

    def get(self):
        return "" if self._ph_activo else self.var.get()

    def set(self, valor):
        self._ph_activo = False
        self.entrada.config(fg=E.TEXTO, show=self._oculto)
        self.var.set(valor)
        if not valor and self._placeholder and self.focus_get() is not self.entrada:
            self._poner_ph()

    def focus(self):
        self.entrada.focus_set()

    def al_presionar_enter(self, funcion):
        self.entrada.bind("<Return>", lambda _e: funcion())


class AreaTexto(tk.Frame):
    """Cuadro de texto de varias líneas con borde que cambia al enfocar."""

    def __init__(self, padre, alto=3, fondo=None):
        super().__init__(padre, bg=fondo or padre.cget("bg"))
        self.borde = tk.Frame(self, bg=E.BORDE, padx=1, pady=1)
        self.borde.pack(fill="both", expand=True)
        self.texto = tk.Text(self.borde, height=alto, wrap="word", relief="flat", bd=0,
                             font=E.F_NORMAL, bg="white", fg=E.TEXTO, insertbackground=E.TEXTO,
                             highlightthickness=0, padx=10, pady=8, undo=True)
        self.texto.pack(fill="both", expand=True)
        self.texto.bind("<FocusIn>", lambda _e: self.borde.config(bg=E.ACENTO))
        self.texto.bind("<FocusOut>", lambda _e: self.borde.config(bg=E.BORDE))

    def get(self):
        return self.texto.get("1.0", "end").strip()

    def set(self, valor):
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", valor)

    def limpiar(self):
        self.texto.delete("1.0", "end")


class Tarjeta(tk.Frame):
    """Contenedor blanco con borde fino."""

    def __init__(self, padre, **kw):
        super().__init__(padre, bg=E.BLANCO, highlightbackground=E.BORDE,
                         highlightcolor=E.BORDE, highlightthickness=1, **kw)


class Avatar(tk.Label):
    def __init__(self, padre, nombre, usuario, ruta=None, lado=40, fondo=None):
        self._foto = _avatar(nombre, usuario, ruta, lado)
        super().__init__(padre, image=self._foto, bg=fondo or padre.cget("bg"), bd=0)

    def cambiar(self, nombre, usuario, ruta=None, lado=40):
        self._foto = _avatar(nombre, usuario, ruta, lado)
        self.config(image=self._foto)


def vacio(padre, mensaje, fondo=None):
    """Mensaje centrado para listas sin elementos."""
    return E.etiqueta(padre, mensaje, E.F_NORMAL, E.SUAVE, fondo or padre.cget("bg"),
                      justify="center", pady=26)


class FilaUsuario(tk.Frame):
    """Fila de lista: avatar, nombre, subtítulo y botones de acción a la derecha."""

    def __init__(self, padre, usuario, nombre, subtitulo="", en_linea=None, acciones=(), etiqueta=""):
        fondo = padre.cget("bg")
        super().__init__(padre, bg=fondo)
        fila = tk.Frame(self, bg=fondo)
        fila.pack(fill="x", padx=14, pady=10)
        Avatar(fila, nombre, usuario, lado=42, fondo=fondo).pack(side="left")

        texto = tk.Frame(fila, bg=fondo)
        texto.pack(side="left", padx=(12, 0))
        arriba = tk.Frame(texto, bg=fondo)
        arriba.pack(anchor="w")
        E.etiqueta(arriba, nombre, E.F_NEG, E.TEXTO, fondo).pack(side="left")
        if en_linea is not None:
            E.etiqueta(arriba, "  ●", E.F_PEQ, E.VERDE if en_linea else E.GRIS_CLARO, fondo).pack(side="left")
        sub = subtitulo or f"@{usuario}"
        E.etiqueta(texto, sub, E.F_PEQ, E.SUAVE, fondo).pack(anchor="w")

        for txt, cmd, est in reversed(list(acciones)):
            Boton(fila, txt, cmd, est, padx=14, pady=5, fondo=fondo).pack(side="right", padx=(6, 0))
        if etiqueta:
            E.etiqueta(fila, etiqueta, E.F_PEQ_NEG, E.SUAVE, fondo).pack(side="right")
        tk.Frame(self, bg=E.BORDE, height=1).pack(fill="x", side="bottom")
