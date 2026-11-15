"""Pestaña Juegos: Serpiente, Buscaminas y 3 en raya (duelo con un amigo).

Cada juego tiene su leaderboard con medallas según el puesto:
1.º rubí, 2.º diamante, 3.º esmeralda, 4.º platino, 5.º oro, 6.º bronce.
"""
import random
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from gui import estilo as E
from gui.emojis import foto_emoji, separar
from gui.estilo import MarcoScroll, alerta_aviso, respuesta_ok
from gui.widgets import Avatar, Boton, Tarjeta, vacio

JUEGOS = {
    "serpiente": ("🐍", "Serpiente", "Come manzanas y no choques. Flechas o WASD."),
    "buscaminas": ("💣", "Buscaminas", "Despeja el tablero 9×9 sin tocar las 10 minas."),
    "tres_en_raya": ("⭕", "3 en raya", "Duelo contra un amigo conectado. Gana 3 pts, empate 1."),
}
# (nombre, color principal, brillo) por puesto
MEDALLAS = (("Rubí", "#e0115f", "#ff8fb8"), ("Diamante", "#4fc3f7", "#e1f5fe"),
            ("Esmeralda", "#10b981", "#a7f3d0"), ("Platino", "#94a3b8", "#f1f5f9"),
            ("Oro", "#f5b301", "#fff3b0"), ("Bronce", "#b26a2d", "#f0c79a"))
_cache = {}


def medalla(puesto, lado=34):
    """Medalla dibujada: gema facetada sobre un círculo con cinta (None si no tiene)."""
    if puesto >= len(MEDALLAS):
        return None
    clave = (puesto, lado)
    if clave in _cache:
        return _cache[clave]
    _, color, brillo = MEDALLAS[puesto]
    g = lado * 4
    img = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # cinta
    d.polygon([(g * .30, 0), (g * .45, 0), (g * .55, g * .45), (g * .40, g * .45)], fill="#334155")
    d.polygon([(g * .55, 0), (g * .70, 0), (g * .60, g * .45), (g * .45, g * .45)], fill="#475569")
    # disco
    c, r = (g / 2, g * .62), g * .36
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=E.mezclar(color, "#000000", 0.35))
    r2 = r * .86
    d.ellipse((c[0] - r2, c[1] - r2, c[0] + r2, c[1] + r2), fill=color)
    # gema hexagonal con facetas
    rg = r * .58
    pts = [(c[0] + rg * dx, c[1] + rg * dy) for dx, dy in
           ((0, -1), (.87, -.5), (.87, .5), (0, 1), (-.87, .5), (-.87, -.5))]
    d.polygon(pts, fill=brillo)
    d.polygon([pts[0], pts[1], (c[0], c[1]), pts[5]], fill="#ffffff")
    d.polygon([(c[0], c[1]), pts[2], pts[3], pts[4]], fill=E.mezclar(color, "#000000", 0.15))
    _cache[clave] = ImageTk.PhotoImage(img.resize((lado, lado), Image.LANCZOS))
    return _cache[clave]


def con_emoji(etiqueta, texto, tam=20, **kw):
    """Pone el texto en la etiqueta; si empieza con un emoji, lo muestra a color."""
    emojis = separar(texto)
    if emojis and texto.startswith(emojis[0]):
        etiqueta.config(image=foto_emoji(emojis[0], tam), compound="left",
                        text="  " + texto[len(emojis[0]):].strip(), **kw)
    else:
        etiqueta.config(image="", text=texto, **kw)
    return etiqueta


class Leaderboard(tk.Frame):
    """Podio + lista con medallas, y quién está jugando ahora."""

    def __init__(self, padre, app, juego, fondo=None):
        fondo = fondo or E.BLANCO
        super().__init__(padre, bg=fondo)
        self.app, self.juego, self.fondo = app, juego, fondo

    def refrescar(self):
        for w in self.winfo_children():
            w.destroy()
        resp = self.app.cliente.leaderboard(self.juego)
        if not (resp and resp.get("ok")):
            vacio(self, "No se pudo cargar el leaderboard.", self.fondo).pack()
            return
        tabla, yo = resp.get("tabla", []), self.app.perfil["usuario"]
        tk.Label(self, image=foto_emoji("🏆", 18), text="  Leaderboard", compound="left",
                 font=E.F_H3, fg=E.TEXTO, bg=self.fondo).pack(anchor="w", pady=(0, 8))
        if not tabla:
            vacio(self, "Nadie ha jugado todavía.\n¡Sé el primero!", self.fondo).pack()
        for i, fila in enumerate(tabla):
            mia = fila["usuario"] == yo
            f = tk.Frame(self, bg=E.CLARO if mia else self.fondo)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=f"{i + 1}", width=2, font=E.F_NEG, fg=E.SUAVE,
                     bg=f.cget("bg")).pack(side="left", padx=(4, 2))
            m = medalla(i)
            tk.Label(f, image=m, bg=f.cget("bg"), width=36).pack(side="left") if m else \
                tk.Label(f, width=5, bg=f.cget("bg")).pack(side="left")
            Avatar(f, fila["nombre"], fila["usuario"], self.app.ruta_foto(fila), lado=28,
                   fondo=f.cget("bg")).pack(side="left", padx=4, pady=4)
            datos = tk.Frame(f, bg=f.cget("bg"))
            datos.pack(side="left", padx=4)
            tk.Label(datos, text=fila["nombre"] + ("  (tú)" if mia else ""), font=E.F_NEG,
                     fg=E.TEXTO, bg=f.cget("bg")).pack(anchor="w")
            sub = MEDALLAS[i][0] if i < len(MEDALLAS) else f"@{fila['usuario']}"
            tk.Label(datos, text=sub, font=E.F_PEQ, fg=E.SUAVE, bg=f.cget("bg")).pack(anchor="w")
            tk.Label(f, text=f"{fila['puntos']} pts", font=E.F_NEG, fg=E.TEXTO,
                     bg=f.cget("bg")).pack(side="right", padx=8)
        ahora = [f"@{a} vs @{b}" for a, b in resp.get("duelos", [])] or \
                [f"@{u}" for u in resp.get("jugando", [])]
        con_emoji(tk.Label(self, font=E.F_PEQ, fg=E.SUAVE, bg=self.fondo, wraplength=300,
                           justify="left"),
                  "🎮 Jugando ahora: " + (", ".join(ahora) if ahora else "nadie"),
                  16).pack(anchor="w", pady=(10, 0))


class VentanaJuego(tk.Toplevel):
    """Ventana base: juego a la izquierda, leaderboard a la derecha."""

    def __init__(self, app, juego):
        super().__init__(app, bg=E.FONDO)
        self.app, self.juego = app, juego
        icono, nombre, _ = JUEGOS[juego]
        self.title(f"{nombre} · Social UNA")
        self.resizable(False, False)
        self.transient(app)
        cab = tk.Frame(self, bg=E.MARINO)
        cab.pack(fill="x")
        tk.Label(cab, image=foto_emoji(icono, 26), text=f"  {nombre}", compound="left",
                 font=E.F_H2, fg="white", bg=E.MARINO).pack(side="left", padx=16, pady=10)
        self.lbl_info = tk.Label(cab, font=E.F_NEG, fg=E.DESTACADO, bg=E.MARINO)
        self.lbl_info.pack(side="right", padx=16)
        cuerpo = tk.Frame(self, bg=E.FONDO)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=16)
        self.zona = Tarjeta(cuerpo)
        self.zona.pack(side="left", anchor="n")
        lado = Tarjeta(cuerpo, width=330)
        lado.pack(side="left", fill="y", padx=(16, 0))
        lado.pack_propagate(False)
        self.tabla = Leaderboard(lado, app, juego)
        self.tabla.pack(fill="both", expand=True, padx=14, pady=14)
        self.tabla.refrescar()
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        app.cliente.jugando(juego)

    def compartir(self, texto):
        if respuesta_ok(self.app.cliente.publicar(texto, None, "")):
            E.alerta_info("Compartido en el muro")

    def cerrar(self):
        try:
            self.app.cliente.jugando("")
        except Exception:
            pass
        self.destroy()

    def final(self, titulo, detalle, puntos=None):
        """Panel de fin de partida con jugar otra vez y compartir."""
        capa = tk.Frame(self.zona, bg=E.BLANCO, highlightthickness=2,
                        highlightbackground=E.ACENTO)
        capa.place(relx=.5, rely=.5, anchor="center")
        con_emoji(tk.Label(capa, font=E.F_H2, fg=E.TEXTO, bg=E.BLANCO), titulo,
                  28).pack(padx=30, pady=(18, 4))
        tk.Label(capa, text=detalle, font=E.F_NORMAL, fg=E.SUAVE, bg=E.BLANCO).pack(padx=30)
        botones = tk.Frame(capa, bg=E.BLANCO)
        botones.pack(pady=16, padx=20)
        Boton(botones, "Jugar otra vez", lambda: (capa.destroy(), self.reiniciar()), "primario",
              fondo=E.BLANCO).pack(side="left")
        if puntos:
            nombre = JUEGOS[self.juego][1]
            Boton(botones, "Compartir en el muro", lambda: self.compartir(
                f"{JUEGOS[self.juego][0]} Saqué {puntos} puntos en {nombre} en Social UNA. "
                f"¿Me superas?"), "secundario", fondo=E.BLANCO).pack(side="left", padx=(8, 0))
        self.tabla.refrescar()

    def reiniciar(self):
        raise NotImplementedError


# ------------------------------------------------------------------ serpiente
class Serpiente(VentanaJuego):
    CELDAS, LADO = 18, 24

    def __init__(self, app):
        super().__init__(app, "serpiente")
        tam = self.CELDAS * self.LADO
        self.canvas = tk.Canvas(self.zona, width=tam, height=tam, bg=E.FONDO_CHAT,
                                highlightthickness=0)
        self.canvas.pack(padx=12, pady=12)
        for tecla, dir_ in (("Up", (0, -1)), ("Down", (0, 1)), ("Left", (-1, 0)), ("Right", (1, 0)),
                            ("w", (0, -1)), ("s", (0, 1)), ("a", (-1, 0)), ("d", (1, 0))):
            self.bind(f"<{tecla}>", lambda _e, d=dir_: self._girar(d))
        self.focus_force()
        self.reiniciar()

    def reiniciar(self):
        m = self.CELDAS // 2
        self.cuerpo = [(m, m), (m - 1, m), (m - 2, m)]
        self.dir = self.siguiente = (1, 0)
        self.puntos, self.vivo, self.ms = 0, True, 140
        self._comida()
        self._tic()

    def _comida(self):
        libres = [(x, y) for x in range(self.CELDAS) for y in range(self.CELDAS)
                  if (x, y) not in self.cuerpo]
        self.manzana = random.choice(libres)

    def _girar(self, d):
        if (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):   # no se puede dar media vuelta
            self.siguiente = d

    def _tic(self):
        if not self.vivo or not self.winfo_exists():
            return
        self.dir = self.siguiente
        x, y = self.cuerpo[0]
        cabeza = (x + self.dir[0], y + self.dir[1])
        fuera = not (0 <= cabeza[0] < self.CELDAS and 0 <= cabeza[1] < self.CELDAS)
        if fuera or cabeza in self.cuerpo[:-1]:
            self._morir()
            return
        self.cuerpo.insert(0, cabeza)
        if cabeza == self.manzana:
            self.puntos += 10
            self.ms = max(60, self.ms - 4)      # cada manzana va un poco más rápido
            self._comida()
        else:
            self.cuerpo.pop()
        self._dibujar()
        self.after(self.ms, self._tic)

    def _dibujar(self):
        c, L = self.canvas, self.LADO
        c.delete("all")
        for i in range(self.CELDAS):          # cuadrícula suave
            for j in range(self.CELDAS):
                if (i + j) % 2:
                    c.create_rectangle(i * L, j * L, i * L + L, j * L + L, outline="",
                                       fill=E.mezclar(E.FONDO_CHAT, E.BORDE, .5))
        mx, my = self.manzana
        c.create_image(mx * L + L / 2, my * L + L / 2, image=foto_emoji("🍎", L - 2))
        n = len(self.cuerpo)
        for k, (x, y) in enumerate(self.cuerpo):
            color = E.mezclar(E.ACENTO, E.DESTACADO, k / max(1, n - 1) * .6)
            c.create_rectangle(x * L + 2, y * L + 2, x * L + L - 2, y * L + L - 2,
                               fill=color, outline="")
        hx, hy = self.cuerpo[0]
        for ox, oy in ((.3, .35), (.7, .35)):     # ojitos
            c.create_oval(hx * L + L * ox - 3, hy * L + L * oy - 3, hx * L + L * ox + 3,
                          hy * L + L * oy + 3, fill="white", outline="")
        self.lbl_info.config(text=f"Puntos: {self.puntos}")

    def _morir(self):
        self.vivo = False
        resp = self.app.cliente.enviar_puntaje("serpiente", self.puntos)
        mejor = resp.get("mejor", self.puntos) if resp.get("ok") else self.puntos
        self.final("💥 ¡Chocaste!", f"Puntos: {self.puntos}   ·   Tu récord: {mejor}", self.puntos)


# ----------------------------------------------------------------- buscaminas
class Buscaminas(VentanaJuego):
    N, MINAS, LADO = 9, 10, 36
    COLORES = ("", "#2563eb", "#16a34a", "#dc2626", "#7c3aed", "#b45309", "#0891b2", "#111827",
               "#6b7280")

    def __init__(self, app):
        super().__init__(app, "buscaminas")
        tam = self.N * self.LADO
        self.canvas = tk.Canvas(self.zona, width=tam, height=tam, bg=E.BLANCO, highlightthickness=0)
        self.canvas.pack(padx=14, pady=14)
        self.canvas.bind("<Button-1>", lambda e: self._clic(e, False))
        self.canvas.bind("<Button-3>", lambda e: self._clic(e, True))
        tk.Label(self.zona, text="Clic: descubrir   ·   Clic derecho: bandera 🚩", font=E.F_PEQ,
                 fg=E.SUAVE, bg=E.BLANCO).pack(pady=(0, 10))
        self.reiniciar()

    def reiniciar(self):
        self.minas = set()
        self.abiertas, self.banderas = set(), set()
        self.jugando, self.inicio, self.segundos = True, False, 0
        self._dibujar()
        self._reloj()

    def _poner_minas(self, libre):
        """Las minas se ponen tras el primer clic: nunca se pierde en el primero."""
        casillas = [(x, y) for x in range(self.N) for y in range(self.N)
                    if abs(x - libre[0]) > 1 or abs(y - libre[1]) > 1]
        self.minas = set(random.sample(casillas, self.MINAS))

    def _vecinas(self, x, y):
        return [(i, j) for i in range(x - 1, x + 2) for j in range(y - 1, y + 2)
                if (i, j) != (x, y) and 0 <= i < self.N and 0 <= j < self.N]

    def _numero(self, c):
        return sum(v in self.minas for v in self._vecinas(*c))

    def _reloj(self):
        if self.jugando and self.winfo_exists():
            if self.inicio:
                self.segundos += 1
            self.lbl_info.config(text=f"⏱ {self.segundos} s   🚩 {self.MINAS - len(self.banderas)}")
            self.after(1000, self._reloj)

    def _clic(self, e, bandera):
        if not self.jugando:
            return
        c = (e.x // self.LADO, e.y // self.LADO)
        if not (0 <= c[0] < self.N and 0 <= c[1] < self.N) or c in self.abiertas:
            return
        if bandera:
            self.banderas ^= {c}
        elif c not in self.banderas:
            if not self.inicio:
                self.inicio = True
                self._poner_minas(c)
            if c in self.minas:
                self.jugando = False
                self.abiertas |= self.minas
                self._dibujar(explotada=c)
                self.final("💥 ¡Boom!", "Pisaste una mina. ¡Inténtalo de nuevo!")
                return
            self._abrir(c)
            if len(self.abiertas) == self.N * self.N - self.MINAS:
                self.jugando = False
                puntos = max(50, 1000 - self.segundos * 5)   # más rápido = más puntos
                resp = self.app.cliente.enviar_puntaje("buscaminas", puntos)
                self._dibujar()
                self.final("🎉 ¡Ganaste!", f"{self.segundos} s  ·  {puntos} puntos  ·  "
                           f"récord: {resp.get('mejor', puntos)}", puntos)
                return
        self._dibujar()

    def _abrir(self, c):
        pila = [c]
        while pila:                       # descubre en cadena las casillas sin número
            actual = pila.pop()
            if actual in self.abiertas or actual in self.banderas:
                continue
            self.abiertas.add(actual)
            if self._numero(actual) == 0:
                pila.extend(v for v in self._vecinas(*actual) if v not in self.abiertas)

    def _dibujar(self, explotada=None):
        c, L = self.canvas, self.LADO
        c.delete("all")
        for x in range(self.N):
            for y in range(self.N):
                x0, y0 = x * L + 1, y * L + 1
                if (x, y) in self.abiertas:
                    fondo = E.ROJO if (x, y) == explotada else E.FONDO_CHAT
                    c.create_rectangle(x0, y0, x0 + L - 2, y0 + L - 2, fill=fondo, outline=E.BORDE)
                    if (x, y) in self.minas:
                        c.create_image(x0 + L / 2 - 1, y0 + L / 2 - 1, image=foto_emoji("💣", L - 12))
                    elif self._numero((x, y)):
                        n = self._numero((x, y))
                        c.create_text(x0 + L / 2 - 1, y0 + L / 2 - 1, text=str(n),
                                      font=(E.FAMILIA, 13, "bold"), fill=self.COLORES[n])
                else:
                    c.create_rectangle(x0, y0, x0 + L - 2, y0 + L - 2, outline="",
                                       fill=E.mezclar(E.ACENTO, E.BLANCO, .35 if (x + y) % 2 else .45))
                    if (x, y) in self.banderas:
                        c.create_image(x0 + L / 2 - 1, y0 + L / 2 - 1, image=foto_emoji("🚩", L - 12))


# ---------------------------------------------------------------- 3 en raya
class TresEnRaya(VentanaJuego):
    LADO = 110

    def __init__(self, app, partida):
        super().__init__(app, "tres_en_raya")
        self.partida = partida
        yo = app.perfil["usuario"]
        self.ficha = "X" if partida["x"] == yo else "O"
        self.rival = partida["o"] if self.ficha == "X" else partida["x"]
        vs = tk.Frame(self.zona, bg=E.BLANCO)
        vs.pack(fill="x", padx=16, pady=(14, 0))
        for usuario, ficha, lado in ((yo, self.ficha, "left"), (self.rival,
                                                                "O" if self.ficha == "X" else "X",
                                                                "right")):
            perfil = app.perfil_de(usuario) or {"nombre": usuario}
            f = tk.Frame(vs, bg=E.BLANCO)
            f.pack(side=lado)
            Avatar(f, perfil.get("nombre", usuario), usuario, app.ruta_foto(perfil), lado=38,
                   fondo=E.BLANCO).pack(side="left" if lado == "left" else "right")
            tk.Label(f, text=f" {perfil.get('nombre', usuario)} ({ficha}) ", font=E.F_NEG,
                     fg=E.TEXTO, bg=E.BLANCO).pack(side="left" if lado == "left" else "right")
        tk.Label(vs, text="VS", font=E.F_H2, fg=E.DESTACADO, bg=E.BLANCO).pack()
        tam = 3 * self.LADO
        self.canvas = tk.Canvas(self.zona, width=tam, height=tam, bg=E.BLANCO, highlightthickness=0,
                                cursor="hand2")
        self.canvas.pack(padx=20, pady=16)
        self.canvas.bind("<Button-1>", self._clic)
        self.lbl_estado = tk.Label(self.zona, font=E.F_H3, fg=E.TEXTO, bg=E.BLANCO)
        self.lbl_estado.pack(pady=(0, 14))
        self.actualizar(partida)

    def actualizar(self, partida, animar=True):
        self.partida = partida
        yo = self.app.perfil["usuario"]
        g = partida["ganador"]
        if g:
            texto = ("🤝 ¡Empate! +1 punto" if g == "empate" else
                     "🏆 ¡Ganaste! +3 puntos" if g == yo else f"Ganó @{g}")
            if partida.get("abandono") and g == yo:
                texto = f"🏆 @{partida['abandono']} abandonó. ¡Ganaste! +3"
            con_emoji(self.lbl_estado, texto, 22, fg=E.ACENTO if g in (yo, "empate") else E.ROJO)
            self.lbl_info.config(text="Partida terminada")
            self.tabla.refrescar()
        else:
            mio = partida["turno"] == yo
            con_emoji(self.lbl_estado, "✨ Tu turno" if mio else f"⏳ Turno de @{partida['turno']}",
                      22, fg=E.TEXTO if mio else E.SUAVE)
            self.lbl_info.config(text=f"Tú juegas con {self.ficha}")
        self._dibujar()

    def _dibujar(self):
        c, L, p = self.canvas, self.LADO, self.partida
        c.delete("all")
        for i in (1, 2):
            c.create_line(i * L, 10, i * L, 3 * L - 10, fill=E.BORDE, width=4, capstyle="round")
            c.create_line(10, i * L, 3 * L - 10, i * L, fill=E.BORDE, width=4, capstyle="round")
        for k, f in enumerate(p["tablero"]):
            x, y, m = (k % 3) * L, (k // 3) * L, 28
            if f == "X":
                for a, b, cc, d in ((m, m, L - m, L - m), (L - m, m, m, L - m)):
                    c.create_line(x + a, y + b, x + cc, y + d, fill=E.ACENTO, width=10,
                                  capstyle="round")
            elif f == "O":
                c.create_oval(x + m, y + m, x + L - m, y + L - m, outline=E.DESTACADO, width=10)
        if p.get("linea"):
            a, b = p["linea"][0], p["linea"][2]
            centro = lambda k: ((k % 3) * L + L / 2, (k // 3) * L + L / 2)
            c.create_line(*centro(a), *centro(b), fill=E.ROJO, width=8, capstyle="round")

    def _clic(self, e):
        p = self.partida
        if p["ganador"] or p["turno"] != self.app.perfil["usuario"]:
            return
        casilla = (e.y // self.LADO) * 3 + e.x // self.LADO
        if 0 <= casilla <= 8 and not p["tablero"][casilla]:
            resp = self.app.cliente.jugada(p["id"], casilla)
            if respuesta_ok(resp):
                self.actualizar(resp["partida"])

    def reiniciar(self):
        self.app.cliente.invitar_juego(self.rival)
        E.alerta_info(f"Revancha enviada a @{self.rival}")

    def cerrar(self):
        if not self.partida["ganador"]:
            self.app.cliente.abandonar_juego(self.partida["id"])
        super().cerrar()


# --------------------------------------------------------------- pestaña
class PestanaJuegos(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.ventana_ttt = None
        marco = MarcoScroll(self)
        marco.pack(fill="both", expand=True)
        self.interior = marco.interior

    def refrescar(self):
        for w in self.interior.winfo_children():
            w.destroy()
        for clave, (icono, nombre, desc) in JUEGOS.items():
            t = Tarjeta(self.interior, hover=True)
            t.pack(fill="x", pady=(0, 14), padx=(0, 10))
            izq = tk.Frame(t, bg=E.BLANCO)
            izq.pack(side="left", fill="y", padx=20, pady=18)
            tk.Label(izq, image=foto_emoji(icono, 54), bg=E.BLANCO).pack(anchor="w")
            tk.Label(izq, text=nombre, font=E.F_H2, fg=E.TEXTO, bg=E.BLANCO).pack(anchor="w",
                                                                                pady=(8, 0))
            tk.Label(izq, text=desc, font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO, wraplength=230,
                     justify="left").pack(anchor="w", pady=(2, 12))
            if clave == "tres_en_raya":
                Boton(izq, "Retar a un amigo", self._elegir_rival, "primario",
                      fondo=E.BLANCO).pack(anchor="w")
            else:
                Boton(izq, "Jugar", lambda c=clave: self.abrir(c), "primario",
                      fondo=E.BLANCO).pack(anchor="w")
            tabla = Leaderboard(t, self.app, clave)
            tabla.pack(side="left", fill="both", expand=True, padx=(10, 20), pady=18)
            tabla.refrescar()

    def abrir(self, juego):
        (Serpiente if juego == "serpiente" else Buscaminas)(self.app)

    def _elegir_rival(self):
        resp = self.app.cliente.listar_amigos()
        if not respuesta_ok(resp):
            return
        conectados = [a for a in resp.get("amigos", []) if a.get("en_linea")]
        if not conectados:
            alerta_aviso("Ninguno de tus amigos está conectado ahora.")
            return
        menu = tk.Menu(self, tearoff=0, bg=E.BLANCO, fg=E.TEXTO, activebackground=E.CLARO,
                       activeforeground=E.TEXTO, font=E.F_NORMAL)
        for a in conectados:
            menu.add_command(label=f"● {a.get('apodo') or a['nombre']}  (@{a['usuario']})",
                             command=lambda u=a["usuario"]: self.retar(u))
        menu.tk_popup(*self.winfo_pointerxy())

    def retar(self, usuario):
        if respuesta_ok(self.app.cliente.invitar_juego(usuario)):
            E.alerta_info(f"Reto enviado a @{usuario}. Esperando respuesta…")

    # eventos que llegan del servidor (los reparte Principal)
    def invitacion(self, ev):
        from gui.estilo import confirmar
        quien = ev["usuario"]
        aceptar = confirmar(f"@{quien} te reta a 3 en raya. ¿Aceptas?", "Reto")
        resp = self.app.cliente.responder_juego(quien, aceptar)
        if aceptar and respuesta_ok(resp):
            self._abrir_partida(resp["partida"])

    def partida(self, ev):
        p = ev["partida"]
        v = self.ventana_ttt
        if v is not None and v.winfo_exists() and v.partida["id"] == p["id"]:
            v.actualizar(p)
        elif not p["ganador"]:
            self._abrir_partida(p)

    def _abrir_partida(self, p):
        if self.ventana_ttt is not None and self.ventana_ttt.winfo_exists():
            self.ventana_ttt.destroy()
        self.ventana_ttt = TresEnRaya(self.app, p)
