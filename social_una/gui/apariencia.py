"""Pestaña Personalizar: modo claro/oscuro, paleta de colores, sonido y GIFs.

Solo se ofrecen paletas ya probadas (no un selector libre de colores) para que
cualquier combinación se lea bien. El tema y la paleta se guardan en el perfil,
así que te siguen si entras desde otra computadora.
"""
import os
import shutil
import tkinter as tk
from tkinter import filedialog

from gui import estilo as E
from gui import sonidos as S
from gui.estilo import MarcoScroll, alerta_aviso, respuesta_ok
from gui.widgets import Boton, Campo, Tarjeta


class Opcion(tk.Canvas):
    """Tarjeta clicable con una mini vista previa de un tema o paleta."""

    ANCHO, ALTO = 196, 140

    def __init__(self, padre, titulo, subtitulo, colores, elegida, comando):
        super().__init__(padre, width=self.ANCHO, height=self.ALTO, bg=E.BLANCO,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.titulo, self.subtitulo, self.c = titulo, subtitulo, colores
        self.elegida, self.comando = elegida, comando
        self.bind("<Enter>", lambda _e: self._pintar(True))
        self.bind("<Leave>", lambda _e: self._pintar(False))
        self.bind("<ButtonRelease-1>", lambda _e: comando())
        self._pintar(False)

    def _pintar(self, hover):
        c, w, h = self.c, self.ANCHO, self.ALTO
        self.delete("all")
        borde = E.ACENTO if self.elegida else (E.GRIS_PH if hover else E.BORDE)
        self.create_rectangle(1, 1, w - 2, h - 2, outline=borde, width=3 if self.elegida else 1)
        # mini ventana: barra lateral, fondo, tarjeta, botón y detalle
        x0, y0, x1, y1 = 12, 12, w - 12, 72
        self.create_rectangle(x0, y0, x1, y1, fill=c["FONDO"], outline=c["BORDE"])
        self.create_rectangle(x0, y0, x0 + 40, y1, fill=c["MARINO"], outline="")
        self.create_rectangle(x0 + 8, y0 + 10, x0 + 11, y0 + 20, fill=c["DESTACADO"], outline="")
        self.create_rectangle(x0 + 14, y0 + 12, x0 + 34, y0 + 17, fill=c["LATERAL_SUAVE"], outline="")
        self.create_rectangle(x0 + 50, y0 + 8, x1 - 8, y1 - 8, fill=c["BLANCO"], outline=c["BORDE"])
        self.create_rectangle(x0 + 58, y0 + 16, x1 - 40, y0 + 21, fill=c["TEXTO"], outline="")
        self.create_rectangle(x0 + 58, y0 + 26, x1 - 60, y0 + 30, fill=c["SUAVE"], outline="")
        self.create_rectangle(x1 - 44, y1 - 22, x1 - 14, y1 - 13, fill=c["ACENTO"], outline="")
        self.create_text(12, 88, text=self.titulo + ("   ✓" if self.elegida else ""),
                         font=E.F_NEG, fill=E.TEXTO, anchor="w")
        self.create_text(12, 99, text=self.subtitulo, font=E.F_PEQ, fill=E.SUAVE, anchor="nw",
                         width=w - 20)


class PestanaApariencia(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.marco = MarcoScroll(self)
        self.marco.pack(fill="both", expand=True)
        self.interior = self.marco.interior

    def _seccion(self, titulo, descripcion):
        t = Tarjeta(self.interior)
        t.pack(fill="x", pady=(0, 14), padx=(0, 10))
        tk.Label(t, text=titulo, font=E.F_H3, fg=E.TEXTO, bg=E.BLANCO).pack(anchor="w", padx=20,
                                                                           pady=(16, 0))
        tk.Label(t, text=descripcion, font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w", padx=20)
        fila = tk.Frame(t, bg=E.BLANCO)
        fila.pack(fill="x", padx=20, pady=(12, 18))
        return fila

    def refrescar(self):
        # Se recuerda el scroll para que al repintar no salte hasta arriba.
        posicion = self.marco.canvas.yview()[0]
        self._repintar()
        self.update_idletasks()
        self.marco.canvas.configure(scrollregion=self.marco.canvas.bbox("all"))
        self.marco.canvas.yview_moveto(posicion)

    def _repintar(self):
        for w in self.interior.winfo_children():
            w.destroy()

        fila = self._seccion("Modo", "Claro para el día, oscuro para descansar la vista.")
        for tema, titulo, sub in (("claro", "☀  Claro", "Fondo luminoso"),
                                  ("oscuro", "☾  Oscuro", "Fondo oscuro, menos brillo")):
            Opcion(fila, titulo, sub, E.colores_tema(tema, E.PALETA), tema == E.TEMA,
                   lambda t=tema: self._elegir(t, E.PALETA)).pack(side="left", padx=(0, 14))

        fila = self._seccion("Paleta de colores",
                             "Cada paleta combina colores opuestos en la rueda de color, "
                             "así contrastan sin chocar.")
        cuadricula = tk.Frame(fila, bg=E.BLANCO)
        cuadricula.pack(anchor="w")
        for i, (clave, p) in enumerate(E.PALETAS.items()):
            Opcion(cuadricula, p["nombre"], p["teoria"], E.colores_tema(E.TEMA, clave),
                   clave == E.PALETA, lambda c=clave: self._elegir(E.TEMA, c)).grid(
                row=i // 3, column=i % 3, padx=(0, 14), pady=(0, 14))

        fila = self._seccion("Sonido de notificación",
                             "Elige un tono (▶ para escucharlo) o usa tu propio .wav de hasta 5 s.")
        self.btn_sonido = Boton(fila, "", self._alternar_sonido, "secundario", ancho=190,
                                fondo=E.BLANCO)
        self.btn_sonido.pack(side="left", anchor="n")
        tonos = tk.Frame(fila, bg=E.BLANCO)
        tonos.pack(side="left", padx=(18, 0))
        prefs = self.app.prefs
        self._filas_tono = {}
        for nombre in S.TONOS:
            f = tk.Frame(tonos, bg=E.BLANCO, cursor="hand2")
            f.pack(fill="x")
            play = tk.Label(f, text="▶", font=E.F_NEG, fg=E.ACENTO if E.TEMA == "claro"
                            else E.LATERAL_TEXTO, bg=f.cget("bg"), padx=8, cursor="hand2")
            play.pack(side="left")
            play.bind("<Button-1>", lambda _e, n=nombre: S.reproducir(S.ruta_tono(n)))
            nom = tk.Label(f, text=nombre, font=E.F_NORMAL, fg=E.TEXTO, bg=f.cget("bg"),
                           padx=6, pady=4)
            nom.pack(side="left")
            for w in (f, nom):
                w.bind("<Button-1>", lambda _e, n=nombre: self._elegir_tono(n))
            self._filas_tono[nombre] = (f, play, nom)
        fila_propio = tk.Frame(tonos, bg=E.BLANCO)
        fila_propio.pack(fill="x", pady=(8, 0))
        Boton(fila_propio, "Usar mi propio .wav", self._tono_propio, "secundario", padx=12,
              pady=5, fondo=E.BLANCO).pack(side="left")
        self.lbl_propio = tk.Label(fila_propio, text="", font=E.F_PEQ_NEG, fg=E.TEXTO, bg=E.BLANCO)
        self.lbl_propio.pack(side="left", padx=8)
        self._pintar_tonos()
        self._pintar_sonido()

        fila = self._seccion("GIFs en línea",
                             "Para buscar GIFs en el chat pega tu clave gratuita de GIPHY "
                             "(developers.giphy.com). Se guarda solo en esta computadora.")
        self.clave_giphy = Campo(fila, valor=prefs.get("giphy_key", ""), oculto=True,
                                 placeholder="Clave de GIPHY", fondo=E.BLANCO)
        self.clave_giphy.pack(side="left", fill="x", expand=True, padx=(0, 10))
        Boton(fila, "Guardar clave", self._guardar_giphy, "primario", fondo=E.BLANCO).pack(side="left")

    def _guardar_prefs_y_pintar(self):
        """Guarda y actualiza solo los tonos y el botón de sonido, sin reconstruir la
        pestaña (reconstruirla hacía parpadear y saltar la pantalla)."""
        S.guardar_prefs(self.app.prefs)
        self._pintar_tonos()
        self._pintar_sonido()

    def _pintar_tonos(self):
        prefs = self.app.prefs
        for nombre, (f, play, nom) in self._filas_tono.items():
            activo = not prefs.get("tono_propio") and prefs.get("tono") == nombre
            fondo = E.CLARO if activo else E.BLANCO
            for w in (f, play, nom):
                w.config(bg=fondo)
            nom.config(text=nombre + ("   ✓" if activo else ""),
                       font=E.F_NEG if activo else E.F_NORMAL)
        propio = prefs.get("tono_propio")
        self.lbl_propio.config(text=("✓ " + os.path.basename(propio)) if propio else "")

    def _pintar_sonido(self):
        activo = self.app.prefs.get("sonido")
        self.btn_sonido.configurar("🔔  Sonido activado" if activo else "🔕  Sonido apagado")
        self.btn_sonido.cambiar_estilo("primario" if activo else "secundario")

    def _alternar_sonido(self):
        self.app.prefs["sonido"] = not self.app.prefs.get("sonido")
        S.guardar_prefs(self.app.prefs)
        self._pintar_sonido()

    def _elegir_tono(self, nombre):
        self.app.prefs.update(tono=nombre, tono_propio="", sonido=True)
        S.reproducir(S.ruta_tono(nombre))
        self._guardar_prefs_y_pintar()

    def _tono_propio(self):
        ruta = filedialog.askopenfilename(parent=self.app, title="Sonido de notificación",
                                          filetypes=[("Sonido WAV", "*.wav")])
        if not ruta:
            return
        error = S.validar_tono_propio(ruta)
        if error:
            alerta_aviso(error)
            return
        # se copia a la carpeta de la app: así sigue funcionando si se mueve el original
        destino = os.path.join(S.CARPETA, "tono_propio.wav")
        os.makedirs(S.CARPETA, exist_ok=True)
        shutil.copyfile(ruta, destino)
        self.app.prefs.update(tono_propio=destino, sonido=True)
        S.reproducir(destino)
        self._guardar_prefs_y_pintar()

    def _guardar_giphy(self):
        self.app.prefs["giphy_key"] = self.clave_giphy.get().strip()
        S.guardar_prefs(self.app.prefs)
        E.alerta_info("Clave de GIPHY guardada")

    def _elegir(self, tema, paleta):
        if (tema, paleta) == (E.TEMA, E.PALETA):
            return
        if respuesta_ok(self.app.cliente.guardar_apariencia(tema, paleta),
                        "No se pudo guardar la apariencia."):
            self.app.perfil.update(tema=tema, paleta=paleta)
            # después del clic: la vista se reconstruye con los colores nuevos
            self.app.after(10, lambda: self.app.cambiar_tema(tema, paleta))
