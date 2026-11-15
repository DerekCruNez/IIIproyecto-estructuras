"""Pestaña Chat: sala general y conversaciones privadas con amigos."""
import tkinter as tk

from gui import estilo as E
from gui.estilo import MarcoScroll, alerta_aviso, respuesta_ok
from gui.widgets import Avatar, Boton, Campo, Tarjeta

SALA = "#general"
FONDO_CHAT = "#f6faf9"


class FilaConversacion(tk.Frame):
    """Elemento clicable de la lista de conversaciones."""

    def __init__(self, padre, clave, nombre, estado, en_linea, sin_leer, activa, comando):
        self.activa = activa
        self.normal = E.CLARO if activa else E.BLANCO
        super().__init__(padre, bg=self.normal, cursor="hand2")
        fila = tk.Frame(self, bg=self.normal)
        fila.pack(fill="x", padx=14, pady=10)
        Avatar(fila, "#" if clave == SALA else nombre, clave, lado=38, fondo=self.normal).pack(side="left")
        datos = tk.Frame(fila, bg=self.normal)
        datos.pack(side="left", padx=(10, 0))
        arriba = tk.Frame(datos, bg=self.normal)
        arriba.pack(anchor="w")
        tk.Label(arriba, text=nombre, font=E.F_NEG, fg=E.TEXTO, bg=self.normal).pack(side="left")
        if en_linea is not None:
            tk.Label(arriba, text="  ●", font=E.F_PEQ, bg=self.normal,
                     fg=E.VERDE if en_linea else E.GRIS_CLARO).pack(side="left")
        tk.Label(datos, text=estado, font=E.F_PEQ, fg=E.SUAVE, bg=self.normal).pack(anchor="w")
        if sin_leer:
            tk.Label(fila, text="  nuevo  ", font=E.F_PEQ_NEG, fg=E.MARINO, bg=E.DESTACADO).pack(side="right")
        tk.Frame(self, bg=E.BORDE, height=1).pack(fill="x", side="bottom")

        def hover(valor):
            if not self.activa:
                self._color(E.FONDO if valor else E.BLANCO)

        self._widgets = [self]
        self._recolectar(self)
        for w in self._widgets:
            w.bind("<Button-1>", lambda _e: comando())
            w.bind("<Enter>", lambda _e: hover(True))
            w.bind("<Leave>", lambda _e: hover(False))

    def _recolectar(self, w):
        for h in w.winfo_children():
            self._widgets.append(h)
            self._recolectar(h)

    def _color(self, color):
        for w in self._widgets:
            if isinstance(w, tk.Label) and w.cget("bg") == E.DESTACADO:
                continue          # no pintar la insignia "nuevo"
            if isinstance(w, tk.Frame) and w.cget("height") == 1 and w is not self:
                continue          # ni la línea separadora
            w.config(bg=color)


class PestanaChat(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.actual = None            # clave de la conversación abierta
        self.datos = []               # [(clave, nombre, estado, en_linea)]
        self.no_leidos = set()
        self._burbujas = []

        izq = Tarjeta(self, width=300)
        izq.pack(side="left", fill="y", padx=(0, 16))
        izq.pack_propagate(False)
        tk.Label(izq, text="Conversaciones", font=E.F_H3, fg=E.TEXTO, bg=E.BLANCO).pack(
            anchor="w", padx=18, pady=(16, 10))
        tk.Frame(izq, bg=E.BORDE, height=1).pack(fill="x")
        self.lista = MarcoScroll(izq, fondo=E.BLANCO)
        self.lista.pack(fill="both", expand=True)

        der = Tarjeta(self)
        der.pack(side="left", fill="both", expand=True)
        self.cabecera = tk.Frame(der, bg=E.BLANCO)
        self.cabecera.pack(fill="x", padx=18, pady=12)
        self.av_cab = Avatar(self.cabecera, "#", "#general", lado=38, fondo=E.BLANCO)
        self.av_cab.pack(side="left")
        datos_cab = tk.Frame(self.cabecera, bg=E.BLANCO)
        datos_cab.pack(side="left", padx=(12, 0))
        self.lbl_titulo = tk.Label(datos_cab, text="Elige una conversación", font=E.F_H3,
                                   fg=E.TEXTO, bg=E.BLANCO)
        self.lbl_titulo.pack(anchor="w")
        self.lbl_estado = tk.Label(datos_cab, text="", font=E.F_PEQ, fg=E.SUAVE, bg=E.BLANCO)
        self.lbl_estado.pack(anchor="w")
        tk.Frame(der, bg=E.BORDE, height=1).pack(fill="x")

        marco = tk.Frame(der, bg=FONDO_CHAT)
        marco.pack(fill="both", expand=True)
        self.texto = tk.Text(marco, state="disabled", wrap="word", relief="flat", bd=0,
                             highlightthickness=0, bg=FONDO_CHAT, padx=18, pady=12, cursor="arrow",
                             font=E.F_NORMAL)
        self.texto.pack(fill="both", expand=True)
        self.texto.tag_configure("meta_yo", foreground=E.SUAVE, justify="right",
                                 font=(E.FAMILIA, 8), spacing1=10, spacing3=2)
        self.texto.tag_configure("meta_otro", foreground=E.SUAVE, justify="left",
                                 font=(E.FAMILIA, 8), spacing1=10, spacing3=2)
        self.texto.tag_configure("linea_yo", justify="right")
        self.texto.tag_configure("linea_otro", justify="left")

        tk.Frame(der, bg=E.BORDE, height=1).pack(fill="x")
        envio = tk.Frame(der, bg=E.BLANCO)
        envio.pack(fill="x", padx=18, pady=14)
        self.campo = Campo(envio, placeholder="Escribe un mensaje…", fondo=E.BLANCO)
        self.campo.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.campo.al_presionar_enter(self._enviar)
        Boton(envio, "Enviar", self._enviar, "primario", padx=26, pady=9, fondo=E.BLANCO).pack(side="left")

    # --------------------------------------------------------- conversaciones
    def refrescar(self):
        resp = self.app.cliente.listar_amigos()
        if not respuesta_ok(resp, "No se pudo cargar la lista de conversaciones."):
            return
        self.datos = [(SALA, "Sala general", "Todos los usuarios", None)]
        for a in resp.get("amigos", []):
            self.datos.append((a["usuario"], a["nombre"],
                               "En línea" if a.get("en_linea") else "Desconectado",
                               bool(a.get("en_linea"))))
        self._pintar_lista()
        if self.actual is None:
            self._abrir_clave(SALA)

    def _pintar_lista(self):
        self.lista.limpiar()
        for clave, nombre, estado, en_linea in self.datos:
            FilaConversacion(self.lista.interior, clave, nombre, estado, en_linea,
                             clave in self.no_leidos, clave == self.actual,
                             lambda c=clave: self._abrir_clave(c)).pack(fill="x")

    def abrir(self, usuario):
        """Usada por la pestaña Amigos para abrir un chat privado."""
        self.refrescar()
        self._abrir_clave(usuario)

    def _abrir_clave(self, clave):
        self.actual = clave
        self.no_leidos.discard(clave)
        self._pintar_lista()
        for c, nombre, estado, _en in self.datos:
            if c == clave:
                self.lbl_titulo.config(text=nombre)
                self.lbl_estado.config(text=estado)
                self.av_cab.cambiar("#" if c == SALA else nombre, c, None, 38)
        resp = self.app.cliente.obtener_chat(clave)
        if not respuesta_ok(resp, "No se pudo cargar el historial."):
            return
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        for b in self._burbujas:
            b.destroy()
        self._burbujas = []
        self.texto.config(state="disabled")
        mensajes = resp.get("mensajes", [])
        if not mensajes:
            self.texto.config(state="normal")
            self.texto.insert("end", "\nAún no hay mensajes. ¡Escribe el primero!", "meta_otro")
            self.texto.config(state="disabled")
        for m in mensajes:
            self._agregar(m)

    # ---------------------------------------------------------------- mensajes
    def _agregar(self, m):
        yo = m["emisor"] == self.app.perfil["usuario"]
        hora = m["fecha"][11:16] if len(m.get("fecha", "")) >= 16 else m.get("fecha", "")
        t = self.texto
        t.config(state="normal")
        if t.get("1.0", "end").strip().startswith("Aún no hay mensajes"):
            t.delete("1.0", "end")
        t.insert("end", f"{'Tú' if yo else '@' + m['emisor']}  ·  {hora}\n",
                 "meta_yo" if yo else "meta_otro")
        burbuja = tk.Label(t, text=m["texto"], font=(E.FAMILIA, 10), wraplength=400, justify="left",
                           padx=14, pady=9, bd=0,
                           bg=E.ACENTO if yo else "white", fg="white" if yo else E.TEXTO,
                           highlightthickness=0 if yo else 1, highlightbackground=E.BORDE)
        inicio = t.index("end-1c")
        t.window_create("end", window=burbuja)
        t.tag_add("linea_yo" if yo else "linea_otro", inicio, "end-1c")
        t.insert("end", "\n")
        self._burbujas.append(burbuja)
        t.config(state="disabled")
        t.see("end")

    def _enviar(self):
        texto = self.campo.get().strip()
        if self.actual is None:
            alerta_aviso("Elige una conversación primero.")
            return
        if not texto:
            alerta_aviso("Escribe un mensaje antes de enviar.")
            return
        resp = self.app.cliente.enviar_chat(self.actual, texto)
        if respuesta_ok(resp, "No se pudo enviar el mensaje."):
            self.campo.set("")
            self._agregar(resp.get("mensaje") or {
                "emisor": self.app.perfil["usuario"], "texto": texto, "fecha": ""})

    def recibir(self, ev):
        """Mensaje de chat en vivo enviado por el servidor."""
        if ev.get("emisor") == self.app.perfil["usuario"]:
            return
        clave = SALA if ev.get("receptor") == SALA else ev.get("emisor")
        if clave == self.actual:
            self._agregar(ev)
        else:
            self.no_leidos.add(clave)
            self._pintar_lista()
