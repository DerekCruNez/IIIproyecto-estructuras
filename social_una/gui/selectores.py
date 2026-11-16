"""Ventanitas para elegir emojis, stickers y GIFs (como en Discord o WhatsApp)."""
import json
import os
import queue
import tempfile
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
from tkinter import filedialog

from PIL import Image, ImageTk

from gui import estilo as E
from gui import emojis as EM
from gui.estilo import MarcoScroll, alerta_aviso
from gui.widgets import Boton, Campo

LIMITE = 2 * 1024 * 1024
CARPETA_GIFS = os.path.join(tempfile.gettempdir(), "social_una_gifs")


class Emergente(tk.Toplevel):
    """Ventana sin bordes que aparece sobre un botón y se cierra al hacer clic afuera."""
    abierta = None      # selector visible en este momento
    cierre = (None, 0.0)  # (botón, instante) del último cierre

    @classmethod
    def alternar(cls, ancla, crear):
        """Si el selector de este botón está abierto lo cierra; si no, lo abre con crear()."""
        actual = cls.abierta
        if actual is not None and actual.winfo_exists():
            mismo = actual.ancla is ancla
            actual.destroy()
            if mismo:
                return
        boton, t = cls.cierre
        if boton is ancla and time.monotonic() - t < 0.35:
            return      # el clic en el botón ya lo cerró (pérdida de foco)
        cls.abierta = crear()
        cls._instalar_clic_fuera(cls.abierta.app)

    _clic_instalado = False

    @classmethod
    def _instalar_clic_fuera(cls, app):
        """Un clic en cualquier otra parte de la ventana cierra el selector abierto."""
        if not Emergente._clic_instalado:
            app.bind("<Button-1>", Emergente._clic_global, add="+")
            Emergente._clic_instalado = True

    @staticmethod
    def _clic_global(e):
        p = Emergente.abierta
        try:
            if (p is None or not p.winfo_exists() or e.widget is p.ancla
                    or str(e.widget).startswith(str(p))
                    or time.monotonic() - p._creado < 0.25):
                return
            p.destroy()
        except tk.TclError:
            pass

    def __init__(self, app, ancla, ancho, alto):
        super().__init__(app, bg=E.BORDE)
        self.app = app
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.interior = tk.Frame(self, bg=E.BLANCO)
        self.interior.pack(fill="both", expand=True, padx=1, pady=1)
        ancla.update_idletasks()
        x = min(ancla.winfo_rootx() + ancla.winfo_width() - ancho,
                app.winfo_rootx() + app.winfo_width() - ancho - 10)
        # Arriba del botón si cabe; si no (p. ej. en el Muro, donde el botón está arriba),
        # abajo. Nunca encima del botón: así se puede volver a tocar para cerrarlo.
        sobre = ancla.winfo_rooty()
        bajo = self.winfo_screenheight() - (sobre + ancla.winfo_height())
        if sobre >= alto + 8:
            y = sobre - alto - 8
        elif bajo >= alto + 8 or bajo > sobre:
            alto = min(alto, max(200, bajo - 16))
            y = sobre + ancla.winfo_height() + 8
        else:
            alto = max(200, sobre - 16)
            y = sobre - alto - 8
        self.geometry(f"{ancho}x{alto}+{max(0, x)}+{max(0, y)}")
        self.ancla = ancla
        self._creado = time.monotonic()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<FocusOut>", lambda _e: self.after(120, self._quizas_cerrar))
        self.focus_force()

    def destroy(self):
        # Se anota cuándo se cerró para que un clic en el mismo botón no lo reabra.
        Emergente.cierre = (self.ancla, time.monotonic())
        if Emergente.abierta is self:
            Emergente.abierta = None
        super().destroy()

    def _quizas_cerrar(self):
        if not self.winfo_exists():
            return
        foco = self.focus_get()
        if foco is None or not str(foco).startswith(str(self)):
            self.destroy()


def _celda(padre, imagen, comando, tam):
    lbl = tk.Label(padre, image=imagen, bg=padre.cget("bg"), cursor="hand2",
                   width=tam, height=tam)
    lbl.bind("<Button-1>", lambda _e: comando())
    lbl.bind("<Enter>", lambda _e: lbl.config(bg=E.BOTON_SEC))
    lbl.bind("<Leave>", lambda _e: lbl.config(bg=padre.cget("bg")))
    return lbl


# ------------------------------------------------------------------ emojis
class SelectorEmoji(Emergente):
    """Emojis a color por categorías. al_elegir(emoji)."""

    COLUMNAS = 8          # 8 x 40 px caben con la barra de desplazamiento

    def __init__(self, app, ancla, al_elegir):
        super().__init__(app, ancla, 380, 360)
        self.al_elegir = al_elegir
        pestanas = tk.Frame(self.interior, bg=E.BOTON_SEC)
        pestanas.pack(fill="x")
        self.botones = {}
        for icono, (nombre, _) in EM.CATEGORIAS.items():
            b = tk.Label(pestanas, image=EM.foto_emoji(icono, 20), bg=E.BOTON_SEC, padx=8, pady=6,
                         cursor="hand2")
            b.pack(side="left")
            b.bind("<Button-1>", lambda _e, i=icono: self.mostrar(i))
            self.botones[icono] = b
        self.titulo = tk.Label(self.interior, font=E.F_PEQ_NEG, fg=E.SUAVE, bg=E.BLANCO, anchor="w")
        self.titulo.pack(fill="x", padx=12, pady=(8, 2))
        self.marco = MarcoScroll(self.interior, fondo=E.BLANCO)
        self.marco.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.mostrar(next(iter(EM.CATEGORIAS)))

    def mostrar(self, icono):
        nombre, cadena = EM.CATEGORIAS[icono]
        for i, b in self.botones.items():
            b.config(bg=E.CLARO if i == icono else E.BOTON_SEC)
        self.titulo.config(text=nombre.upper())
        self.marco.limpiar()
        for n, emoji in enumerate(EM.separar(cadena)):
            _celda(self.marco.interior, EM.foto_emoji(emoji, 26), lambda e=emoji: self.al_elegir(e),
                   36).grid(row=n // self.COLUMNAS, column=n % self.COLUMNAS, padx=1, pady=1)


# ---------------------------------------------------------------- stickers
class SelectorSticker(Emergente):
    """Stickers propios y de emojis. al_elegir(ruta_png)."""

    def __init__(self, app, ancla, al_elegir):
        super().__init__(app, ancla, 430, 400)
        self.al_elegir = al_elegir
        self._fotos = []
        barra = tk.Frame(self.interior, bg=E.BLANCO)
        barra.pack(fill="x", padx=12, pady=10)
        tk.Label(barra, text="Stickers", font=E.F_H3, fg=E.TEXTO, bg=E.BLANCO).pack(side="left")
        Boton(barra, "＋ Crear desde imagen", self._crear, "secundario", padx=10, pady=5,
              fondo=E.BLANCO).pack(side="right")
        self.marco = MarcoScroll(self.interior, fondo=E.BLANCO)
        self.marco.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._pintar()

    def _miniatura(self, ruta, lado=78):
        with Image.open(ruta) as img:
            img = img.convert("RGBA")
            img.thumbnail((lado, lado))
            foto = ImageTk.PhotoImage(img)
        self._fotos.append(foto)
        return foto

    def _pintar(self):
        self.marco.limpiar()
        rutas = EM.stickers_propios() + [EM.sticker_de_emoji(e) for e in EM.separar(EM.STICKERS_BASE)]
        for n, ruta in enumerate(rutas):
            _celda(self.marco.interior, self._miniatura(ruta), lambda r=ruta: self._elegir(r),
                   88).grid(row=n // 4, column=n % 4, padx=2, pady=2)

    def _elegir(self, ruta):
        self.destroy()
        self.al_elegir(ruta)

    def _crear(self):
        ruta = filedialog.askopenfilename(parent=self.app, title="Imagen para el sticker",
                                          filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif")])
        if not ruta:
            return
        try:
            EM.crear_sticker(ruta)
        except Exception:
            alerta_aviso("No se pudo convertir esa imagen en sticker.")
            return
        E.alerta_info("Sticker creado")
        self._pintar()


# -------------------------------------------------------------------- GIFs
class SelectorGif(Emergente):
    """GIFs: búsqueda en GIPHY (si hay clave), desde la PC o recientes. al_elegir(ruta)."""

    def __init__(self, app, ancla, al_elegir, prefs):
        super().__init__(app, ancla, 480, 420)
        self.al_elegir, self.prefs = al_elegir, prefs
        self._fotos = []
        self._cola = queue.Queue()
        barra = tk.Frame(self.interior, bg=E.BLANCO)
        barra.pack(fill="x", padx=12, pady=(10, 6))
        self.campo = Campo(barra, placeholder="Buscar GIFs en GIPHY", fondo=E.BLANCO)
        self.campo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.campo.al_presionar_enter(self._buscar)
        Boton(barra, "Desde tu PC", self._desde_pc, "secundario", padx=10, pady=6,
              fondo=E.BLANCO).pack(side="right")
        self.estado = tk.Label(self.interior, font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO, anchor="w",
                               justify="left", wraplength=400)
        self.estado.pack(fill="x", padx=12)
        self.marco = MarcoScroll(self.interior, fondo=E.BLANCO)
        self.marco.pack(fill="both", expand=True, padx=6, pady=6)
        self._revisar_cola()
        if self.prefs.get("giphy_key"):
            self._buscar(tendencias=True)
        else:
            self._recientes("Para buscar GIFs en línea agrega tu clave gratuita de GIPHY en "
                            "Personalizar. Mientras tanto: GIFs recientes o desde tu PC.")

    # --- recientes y PC
    def _recientes(self, mensaje):
        rutas = [r for r in self.prefs.get("gifs_recientes", []) if os.path.isfile(r)]
        self.estado.config(text=mensaje if rutas or "GIPHY" in mensaje else "Aún no hay GIFs recientes.")
        self._pintar([(r, r) for r in rutas])

    def _desde_pc(self):
        ruta = filedialog.askopenfilename(parent=self.app, title="Elegir GIF",
                                          filetypes=[("GIF", "*.gif")])
        if ruta:
            if os.path.getsize(ruta) > LIMITE:
                alerta_aviso("El GIF pesa más de 2 MB.")
                return
            self._elegir(ruta)

    # --- GIPHY (en un hilo: la ventana no se congela mientras descarga)
    def _buscar(self, tendencias=False):
        clave = self.prefs.get("giphy_key")
        if not clave:
            self._recientes("Agrega tu clave de GIPHY en Personalizar para buscar en línea.")
            return
        texto = "" if tendencias else self.campo.get().strip()
        self.estado.config(text="Buscando…")
        params = {"api_key": clave, "limit": 18, "rating": "g", "lang": "es"}
        if texto:
            params["q"] = texto
        url = ("https://api.giphy.com/v1/gifs/" + ("search" if texto else "trending") + "?"
               + urllib.parse.urlencode(params))
        threading.Thread(target=self._descargar_lista, args=(url,), daemon=True).start()

    def _descargar_lista(self, url):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                datos = json.load(r)["data"]
            os.makedirs(CARPETA_GIFS, exist_ok=True)
            resultados = []
            for g in datos:
                img = g["images"]
                mini = os.path.join(CARPETA_GIFS, f"mini_{g['id']}.gif")
                if not os.path.isfile(mini):
                    urllib.request.urlretrieve(img["fixed_width_small_still"]["url"], mini)
                resultados.append((mini, img["downsized"]["url"], g["id"]))
            self._cola.put(("lista", resultados))
        except Exception as exc:
            self._cola.put(("error", f"No se pudo buscar en GIPHY: {exc}"))

    def _descargar_gif(self, url, id_gif):
        try:
            ruta = os.path.join(CARPETA_GIFS, f"{id_gif}.gif")
            if not os.path.isfile(ruta):
                urllib.request.urlretrieve(url, ruta)
            self._cola.put(("gif", ruta))
        except Exception as exc:
            self._cola.put(("error", f"No se pudo descargar el GIF: {exc}"))

    def _revisar_cola(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                tipo, valor = self._cola.get_nowait()
                if tipo == "lista":
                    self.estado.config(text="Con la tecnología de GIPHY")
                    self._pintar([(mini, (url, i)) for mini, url, i in valor])
                elif tipo == "gif":
                    if os.path.getsize(valor) > LIMITE:
                        alerta_aviso("Ese GIF pesa más de 2 MB. Elige otro.")
                    else:
                        self._elegir(valor)
                        return
                else:
                    self.estado.config(text=valor)
        except queue.Empty:
            pass
        self.after(150, self._revisar_cola)

    def _pintar(self, elementos):
        self.marco.limpiar()
        self._fotos = []
        for n, (mini, destino) in enumerate(elementos):
            try:
                with Image.open(mini) as img:
                    img = img.convert("RGB")
                    img.thumbnail((128, 96))
                    foto = ImageTk.PhotoImage(img)
            except Exception:
                continue
            self._fotos.append(foto)
            _celda(self.marco.interior, foto, lambda d=destino: self._clic(d), 132).grid(
                row=n // 3, column=n % 3, padx=2, pady=2)

    def _clic(self, destino):
        if isinstance(destino, tuple):        # resultado de GIPHY: hay que descargarlo
            self.estado.config(text="Descargando GIF…")
            threading.Thread(target=self._descargar_gif, args=destino, daemon=True).start()
        else:
            self._elegir(destino)

    def _elegir(self, ruta):
        recientes = [ruta] + [r for r in self.prefs.get("gifs_recientes", []) if r != ruta]
        self.prefs["gifs_recientes"] = recientes[:12]
        self.destroy()
        self.al_elegir(ruta)
