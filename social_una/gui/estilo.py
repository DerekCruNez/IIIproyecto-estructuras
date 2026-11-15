"""Sistema de diseño de Social UNA: colores, fuentes, alertas y utilidades compartidas."""
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import webbrowser

# ------------------------------------------------------------------ colores
# Paleta "Bosque y ámbar": verde azulado profundo + acento ámbar.
MARINO = "#0a2a2e"        # panel lateral y panel de marca (verde azulado muy oscuro)
MARINO_2 = "#12414a"
ACENTO = "#0f766e"        # botones y elementos principales
ACENTO_HOVER = "#115e59"
DESTACADO = "#f5a524"     # ámbar: avisos, detalles y logo
CLARO = "#e4f4f1"         # fondo de elementos seleccionados
FONDO = "#f3f6f5"
BLANCO = "#ffffff"
BORDE = "#dbe5e2"
TEXTO = "#0e1f1d"
SUAVE = "#587069"
GRIS_PH = "#8ea39d"
GRIS_CLARO = "#c3d0cc"
LATERAL_TEXTO = "#cfe3df"  # texto sobre fondos oscuros
LATERAL_SUAVE = "#8fb0aa"
BOTON_SEC = "#e2eae8"
BOTON_SEC_HOVER = "#cfdbd8"
ROJO = "#dc2626"
VERDE = "#16a34a"

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


def aplicar_estilo(raiz):
    raiz.configure(bg=FONDO)
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nombre).configure(family=FAMILIA, size=10)
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure("Vertical.TScrollbar", troughcolor=FONDO, background=GRIS_CLARO, bordercolor=FONDO,
                lightcolor=GRIS_CLARO, darkcolor=GRIS_CLARO, arrowcolor=GRIS_PH, gripcount=0, width=10)
    s.map("Vertical.TScrollbar", background=[("active", GRIS_PH)])


def etiqueta(padre, texto="", fuente=F_NORMAL, color=TEXTO, fondo=None, **kw):
    """tk.Label con colores del sistema; el fondo por defecto es el del contenedor."""
    return tk.Label(padre, text=texto, font=fuente, fg=color, bg=fondo or padre.cget("bg"), **kw)


# ----------------------------------------------------------------- alertas
def alerta_error(mensaje, titulo="Error"):
    messagebox.showerror(titulo, mensaje)


def alerta_aviso(mensaje, titulo="Atención"):
    messagebox.showwarning(titulo, mensaje)


def alerta_info(mensaje, titulo="Social UNA"):
    messagebox.showinfo(titulo, mensaje)


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


# --------------------------------------------------- marco con barra de scroll
class MarcoScroll(tk.Frame):
    """Contenedor desplazable. Los widgets se agregan en `.interior`."""

    def __init__(self, padre, fondo=FONDO):
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

    def limpiar(self):
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        self.canvas.yview_moveto(0)
