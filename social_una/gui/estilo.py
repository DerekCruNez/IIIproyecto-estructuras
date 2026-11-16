"""Sistema de diseño de Social UNA: colores, temas, fuentes, alertas y utilidades compartidas.

Los colores son variables del módulo (E.ACENTO, E.FONDO, ...). `aplicar_tema()`
las cambia según el tema (claro/oscuro) y la paleta elegida; después la App
reconstruye la vista para que todo tome los colores nuevos.
"""
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import webbrowser
from datetime import datetime


# ------------------------------------------------------------------ paletas
# Cada paleta une un color principal con un acento de la rueda de color:
# así los botones (ACENTO) y los detalles (DESTACADO) contrastan sin chocar.
# El texto blanco sobre ACENTO cumple contraste AA en todas.
PALETAS = {
    "bosque": {
        "nombre": "Bosque y ámbar",
        "teoria": "Complementarios divididos: verde azulado + ámbar",
        "ACENTO": "#0f766e", "DESTACADO": "#f5a524", "MARINO": "#0a2a2e", "MARINO_2": "#12414a",
    },
    "oceano": {
        "nombre": "Océano",
        "teoria": "Complementarios: azul + naranja",
        "ACENTO": "#1d4ed8", "DESTACADO": "#fb923c", "MARINO": "#0b1a3a", "MARINO_2": "#172c5c",
    },
    "uva": {
        "nombre": "Uva",
        "teoria": "Complementarios: violeta + amarillo",
        "ACENTO": "#7c3aed", "DESTACADO": "#facc15", "MARINO": "#1d1236", "MARINO_2": "#2f1f55",
    },
    "atardecer": {
        "nombre": "Atardecer",
        "teoria": "Complementarios: carmesí + turquesa",
        "ACENTO": "#be123c", "DESTACADO": "#2dd4bf", "MARINO": "#2a0f19", "MARINO_2": "#47192b",
    },
    "grafito": {
        "nombre": "Grafito",
        "teoria": "Monocromático frío con un acento celeste",
        "ACENTO": "#475569", "DESTACADO": "#38bdf8", "MARINO": "#0f172a", "MARINO_2": "#1e293b",
    },
}
PALETA_DEFECTO = "bosque"
TEMAS = ("claro", "oscuro")

# Grises base de cada tema; se tiñen un poco con el color de la paleta para que
# fondos y bordes "pertenezcan" a ella (armonía por tinte).
_NEUTROS = {
    "claro": {
        "FONDO": "#f3f5f5", "BLANCO": "#ffffff", "CAMPO": "#ffffff", "BORDE": "#dde4e3",
        "TEXTO": "#0e1f1d", "SUAVE": "#587069", "GRIS_PH": "#8ea39d", "GRIS_CLARO": "#c3d0cc",
        "BOTON_SEC": "#e2eae8", "BOTON_SEC_HOVER": "#cfdbd8", "FONDO_CHAT": "#f6faf9",
        "BURBUJA": "#ffffff", "ROJO": "#dc2626", "VERDE": "#16a34a",
        "PELIGRO_FONDO": "#fee2e2", "PELIGRO_HOVER": "#fecaca",
        "AVISO_FONDO": "#fef3c7", "AVISO_TEXTO": "#92400e",
    },
    "oscuro": {
        "FONDO": "#0f1316", "BLANCO": "#181d21", "CAMPO": "#11161a", "BORDE": "#2a3237",
        "TEXTO": "#e7eef0", "SUAVE": "#9aa8ad", "GRIS_PH": "#6c7a80", "GRIS_CLARO": "#3b464c",
        "BOTON_SEC": "#232a2f", "BOTON_SEC_HOVER": "#2e373d", "FONDO_CHAT": "#13181b",
        "BURBUJA": "#252d33", "ROJO": "#f87171", "VERDE": "#22c55e",
        "PELIGRO_FONDO": "#3b1a1d", "PELIGRO_HOVER": "#4a2125",
        "AVISO_FONDO": "#3a2e12", "AVISO_TEXTO": "#fcd34d",
    },
}

# Colores para el banner del perfil: los principales de las paletas y algunos
# vecinos en la rueda, todos con buen contraste para texto blanco.
COLORES_BANNER = ("#0f766e", "#1d4ed8", "#7c3aed", "#be123c", "#475569",
                  "#b45309", "#db2777", "#0891b2")


def mezclar(color1, color2, t):
    """Color entre color1 (t=0) y color2 (t=1)."""
    a = [int(color1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def colores_tema(tema="claro", paleta=PALETA_DEFECTO):
    """Diccionario con todos los colores de un tema y paleta (sin aplicarlos)."""
    tema = tema if tema in TEMAS else "claro"
    p = PALETAS.get(paleta, PALETAS[PALETA_DEFECTO])
    oscuro = tema == "oscuro"
    c = {k: v for k, v in _NEUTROS[tema].items()}
    for k in ("FONDO", "BORDE", "BOTON_SEC", "BOTON_SEC_HOVER", "FONDO_CHAT", "GRIS_CLARO"):
        c[k] = mezclar(c[k], p["ACENTO"], 0.05)
    c.update({k: p[k] for k in ("ACENTO", "DESTACADO", "MARINO", "MARINO_2")})
    c["ACENTO_HOVER"] = mezclar(p["ACENTO"], "#ffffff" if oscuro else "#000000", 0.15)
    c["CLARO"] = mezclar(c["BLANCO"], p["ACENTO"], 0.25 if oscuro else 0.12)
    c["LATERAL_TEXTO"] = mezclar("#ffffff", p["ACENTO"], 0.15)
    c["LATERAL_SUAVE"] = mezclar("#ffffff", p["MARINO"], 0.42)
    c["OSCURO_HOVER"] = mezclar(p["MARINO_2"], "#ffffff", 0.1)
    return c


def aplicar_tema(tema="claro", paleta=PALETA_DEFECTO):
    """Cambia los colores del módulo. Los widgets nuevos usarán estos colores."""
    global TEMA, PALETA
    TEMA = tema if tema in TEMAS else "claro"
    PALETA = paleta if paleta in PALETAS else PALETA_DEFECTO
    globals().update(colores_tema(TEMA, PALETA))


TEMA, PALETA = "claro", PALETA_DEFECTO
# Valores iniciales (el editor también los ve como nombres del módulo).
FONDO = BLANCO = CAMPO = BORDE = TEXTO = SUAVE = GRIS_PH = GRIS_CLARO = ""
BOTON_SEC = BOTON_SEC_HOVER = FONDO_CHAT = BURBUJA = ROJO = VERDE = ""
PELIGRO_FONDO = PELIGRO_HOVER = AVISO_FONDO = AVISO_TEXTO = ""
ACENTO = ACENTO_HOVER = DESTACADO = MARINO = MARINO_2 = CLARO = ""
LATERAL_TEXTO = LATERAL_SUAVE = OSCURO_HOVER = ""
aplicar_tema()

# ------------------------------------------------------------------ fuentes
FAMILIA = "Segoe UI"
F_NORMAL = (FAMILIA, 10)
F_NEG = (FAMILIA, 10, "bold")
F_PEQ = (FAMILIA, 9)
F_PEQ_NEG = (FAMILIA, 9, "bold")
F_BOTON = (FAMILIA, 10, "bold")
F_H1 = (FAMILIA, 22, "bold")
F_H2 = (FAMILIA, 15, "bold")
F_H3 = (FAMILIA, 11, "bold")
F_MARCA = (FAMILIA, 30, "bold")
F_EMOJI = ("Segoe UI Emoji", 12)


def aplicar_estilo(raiz):
    raiz.configure(bg=FONDO)
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nombre).configure(family=FAMILIA, size=10)
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure("Vertical.TScrollbar", troughcolor=FONDO, background=GRIS_CLARO, bordercolor=FONDO,
                lightcolor=GRIS_CLARO, darkcolor=GRIS_CLARO, arrowcolor=GRIS_PH, gripcount=0, width=10)
    s.map("Vertical.TScrollbar", background=[("active", GRIS_PH)])
    s.configure("TCombobox", fieldbackground=CAMPO, background=BOTON_SEC, foreground=TEXTO,
                arrowcolor=TEXTO, bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE, padding=6)
    s.map("TCombobox", fieldbackground=[("readonly", CAMPO)], foreground=[("readonly", TEXTO)],
          selectbackground=[("readonly", CAMPO)], selectforeground=[("readonly", TEXTO)])
    raiz.option_add("*TCombobox*Listbox.background", CAMPO)
    raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
    raiz.option_add("*TCombobox*Listbox.selectForeground", "white")


def etiqueta(padre, texto="", fuente=F_NORMAL, color=None, fondo=None, **kw):
    """tk.Label con colores del sistema; el fondo por defecto es el del contenedor."""
    return tk.Label(padre, text=texto, font=fuente, fg=color or TEXTO,
                    bg=fondo or padre.cget("bg"), **kw)


# ----------------------------------------------------------------- alertas
_raiz_avisos = None   # la App se registra aquí para mostrar avisos flotantes


def registrar_raiz(raiz):
    global _raiz_avisos
    _raiz_avisos = raiz


def alerta_error(mensaje, titulo="Error"):
    messagebox.showerror(titulo, mensaje)


def alerta_aviso(mensaje, titulo="Atención", parent=None):
    messagebox.showwarning(titulo, mensaje, parent=parent)


def alerta_info(mensaje, titulo="Social UNA"):
    """Avisos de éxito: un mensaje flotante que se va solo (no interrumpe)."""
    if _raiz_avisos is not None and _raiz_avisos.winfo_exists():
        Toast(_raiz_avisos, mensaje)
    else:
        messagebox.showinfo(titulo, mensaje)


def confirmar(mensaje, titulo="Confirmar"):
    return messagebox.askyesno(titulo, mensaje)


class Toast(tk.Frame):
    """Aviso flotante en la esquina inferior derecha que se cierra solo."""

    _activos = []

    def __init__(self, raiz, mensaje, icono="✓", duracion=2600, comando=None):
        super().__init__(raiz, bg=MARINO, padx=16, pady=10, cursor="hand2" if comando else "")
        tk.Label(self, text=icono, font=F_NEG, fg=DESTACADO, bg=MARINO).pack(side="left")
        tk.Label(self, text=mensaje, font=F_NORMAL, fg="white", bg=MARINO,
                 wraplength=300, justify="left").pack(side="left", padx=(10, 0))
        for w in (self, *self.winfo_children()):
            w.bind("<Button-1>", lambda _e: self._click(comando))
        Toast._activos.append(self)
        self._y = 30
        self._recolocar()
        self._entrar(0)
        self.after(duracion, self.cerrar)

    @classmethod
    def _recolocar(cls):
        y = -20
        for t in reversed(cls._activos):
            t.place(relx=1.0, rely=1.0, x=-24, y=y + t._y, anchor="se")
            t.lift()
            y -= 56

    def _entrar(self, paso):
        """Pequeña animación: el aviso sube unos píxeles al aparecer."""
        if paso <= 6 and self.winfo_exists():
            self._y = 30 - paso * 5
            Toast._recolocar()
            self.after(16, lambda: self._entrar(paso + 1))

    def _click(self, comando):
        if comando:
            comando()
        self.cerrar()

    def cerrar(self):
        if self in Toast._activos:
            Toast._activos.remove(self)
        if self.winfo_exists():
            self.destroy()
        Toast._recolocar()


def respuesta_ok(resp, mensaje_por_defecto="No se pudo completar la acción."):
    """True si la respuesta del servidor es ok; si no, muestra la alerta de error."""
    if resp and resp.get("ok"):
        return True
    alerta_error((resp or {}).get("error") or mensaje_por_defecto)
    return False


def normalizar_link(url):
    url = (url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url


def abrir_link(url):
    url = normalizar_link(url)
    if url:
        webbrowser.open(url)


MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def tiempo_relativo(fecha, ahora=None):
    """'AAAA-MM-DD HH:MM:SS' -> 'ahora', 'hace 5 min', 'hace 2 h', 'ayer', '12 nov'."""
    try:
        f = datetime.strptime(fecha[:19], "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return fecha or ""
    ahora = ahora or datetime.now()
    seg = (ahora - f).total_seconds()
    if seg < 60:
        return "ahora"
    if seg < 3600:
        return f"hace {int(seg // 60)} min"
    if f.date() == ahora.date():
        return f"hace {int(seg // 3600)} h"
    if (ahora.date() - f.date()).days == 1:
        return "ayer"
    texto = f"{f.day} {MESES[f.month - 1]}"
    return texto if f.year == ahora.year else f"{texto} {f.year}"


# --------------------------------------------------- marco con barra de scroll
class MarcoScroll(tk.Frame):
    """Contenedor desplazable. Los widgets se agregan en `.interior`."""

    def __init__(self, padre, fondo=None):
        fondo = fondo or FONDO
        super().__init__(padre, bg=fondo)
        self.fondo = fondo
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=fondo)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = tk.Frame(self.canvas, bg=fondo)
        self._ventana = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>",
                           lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._ventana, width=e.width))
        self.canvas.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(evento, self._rueda, add="+")

    def _rueda(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):
            return
        while w is not None:
            if w is self:
                break
            w = w.master
        else:
            return
        if e.num == 4:
            paso = -1
        elif e.num == 5:
            paso = 1
        else:
            paso = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(paso, "units")

    def limpiar(self, conservar=False):
        """Borra el contenido. Con conservar=True mantiene la posición del scroll
        al volver a pintar (si no, vuelve arriba)."""
        pos = self.canvas.yview()[0]
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        self.canvas.yview_moveto(0)
        if conservar and pos > 0:
            self.after_idle(self._restaurar, pos)

    def _restaurar(self, pos):
        try:
            self.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.yview_moveto(pos)
        except tk.TclError:
            pass


if __name__ == "__main__":
    # Comprobación rápida: python -m gui.estilo
    base = datetime(2026, 11, 15, 12, 0, 0)
    assert tiempo_relativo("2026-11-15 11:59:30", base) == "ahora"
    assert tiempo_relativo("2026-11-15 11:55:00", base) == "hace 5 min"
    assert tiempo_relativo("2026-11-15 09:00:00", base) == "hace 3 h"
    assert tiempo_relativo("2026-11-14 23:00:00", base) == "ayer"
    assert tiempo_relativo("2026-11-02 08:00:00", base) == "2 nov"
    assert tiempo_relativo("2025-03-02 08:00:00", base) == "2 mar 2025"
    for t in TEMAS:
        for p in PALETAS:
            assert all(v.startswith("#") and len(v) == 7 for v in colores_tema(t, p).values())
    print("estilo OK")
