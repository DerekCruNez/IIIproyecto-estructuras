"""Pestaña Chat: sala general y conversaciones privadas con amigos.

Como en Discord/WhatsApp: emojis a color, GIFs, stickers, imágenes, archivos,
mensajes de voz, encuestas, responder, editar, eliminar y reaccionar (barra que
aparece al pasar el mouse sobre un mensaje).
"""
import os
import tempfile
import tkinter as tk
from datetime import datetime

from gui import emojis as EM
from gui import estilo as E
from gui.estilo import MarcoScroll, alerta_aviso, confirmar, respuesta_ok
from gui.imagenes import cuadros_imagen, miniatura
from gui.muro import abrir_archivo, elegir_archivo, elegir_imagen, tarjeta_archivo
from gui.selectores import SelectorEmoji, SelectorGif, SelectorSticker
from gui.sonidos import (MAX_SEGUNDOS_VOZ, Grabadora, duracion, guardar_prefs, reproducir,
                         detener as detener_sonido)
from gui.widgets import Avatar, Boton, Campo, Tarjeta, animar, vacio


SALA = "#general"


class FilaConversacion(tk.Frame):
    """Elemento clicable de la lista de conversaciones."""

    def __init__(self, padre, clave, nombre, estado, en_linea, sin_leer, activa, comando,
                 ruta_foto=None):
        self.activa = activa
        self.normal = E.CLARO if activa else E.BLANCO
        super().__init__(padre, bg=self.normal, cursor="hand2")
        fila = tk.Frame(self, bg=self.normal)
        fila.pack(fill="x", padx=14, pady=10)
        Avatar(fila, "#" if clave == SALA else nombre, clave, ruta_foto, lado=38,
               fondo=self.normal).pack(side="left")
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
            tk.Label(fila, text=f" {sin_leer if sin_leer < 100 else '99+'} ", font=E.F_PEQ_NEG,
                     fg=E.MARINO, bg=E.DESTACADO).pack(side="right")
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


class Dialogo(tk.Toplevel):
    """Ventanita modal sencilla con el estilo de la app."""

    def __init__(self, app, titulo):
        super().__init__(app, bg=E.BLANCO)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(app)
        self.cuerpo = tk.Frame(self, bg=E.BLANCO)
        self.cuerpo.pack(fill="both", expand=True, padx=22, pady=18)
        tk.Label(self.cuerpo, text=titulo, font=E.F_H2, fg=E.TEXTO, bg=E.BLANCO).pack(anchor="w",
                                                                                     pady=(0, 10))
        self.bind("<Escape>", lambda _e: self.destroy())

    def centrar(self, app):
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        self.focus_force()


class PestanaChat(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.actual = None            # clave de la conversación abierta
        self.datos = []               # [(clave, nombre, estado, en_linea)]
        self.no_leidos = {}           # clave -> cantidad de mensajes sin leer
        self.fotos = {}               # clave -> ruta de la foto del amigo
        self.mensajes = []            # mensajes de la conversación abierta
        self.filas = {}               # id de mensaje -> FilaMensaje
        self.respondiendo = None      # mensaje al que se responde
        self.editando = None          # mensaje que se está editando
        self.reproduciendo = None     # id del audio que suena

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

        # ---- barra para escribir (se empaca antes para que quede siempre abajo)
        self.zona_envio = tk.Frame(der, bg=E.BLANCO)
        self.zona_envio.pack(side="bottom", fill="x")
        tk.Frame(self.zona_envio, bg=E.BORDE, height=1).pack(fill="x")
        self.aviso = tk.Frame(self.zona_envio, bg=E.BOTON_SEC)   # "Respondiendo a…" / "Editando…"
        self.lbl_aviso = tk.Label(self.aviso, font=E.F_PEQ, fg=E.TEXTO, bg=E.BOTON_SEC, anchor="w")
        self.lbl_aviso.pack(side="left", fill="x", expand=True, padx=14, pady=6)
        cerrar = tk.Label(self.aviso, text="✕", font=E.F_NEG, fg=E.SUAVE, bg=E.BOTON_SEC,
                          cursor="hand2", padx=12)
        cerrar.pack(side="right")
        cerrar.bind("<Button-1>", lambda _e: self._cancelar_modo())

        envio = tk.Frame(self.zona_envio, bg=E.BLANCO)
        envio.pack(fill="x", padx=14, pady=12)
        self.btn_mas = self._icono(envio, "＋", self._menu_mas, fuente=(E.FAMILIA, 16, "bold"))
        self.btn_mas.pack(side="left", padx=(0, 2))
        self._icono(envio, EM.foto_emoji("📎", 20), self._subir_archivo).pack(side="left")
        self._icono(envio, EM.foto_emoji("🎤", 20), self._grabar).pack(side="left", padx=(0, 8))
        Boton(envio, "Enviar", self._enviar, "primario", padx=22, pady=9,
              fondo=E.BLANCO).pack(side="right", padx=(8, 0))
        self.btn_emoji = self._icono(envio, EM.foto_emoji("🙂", 22), self._abrir_emojis)
        self.btn_emoji.pack(side="right")
        self.btn_sticker = self._icono(envio, EM.foto_emoji("🐱", 22), self._abrir_stickers)
        self.btn_sticker.pack(side="right")
        self.btn_gif = self._icono(envio, "GIF", self._abrir_gifs, fuente=(E.FAMILIA, 9, "bold"))
        self.btn_gif.pack(side="right")
        self.campo = Campo(envio, placeholder="Escribe un mensaje…", fondo=E.BLANCO)
        self.campo.pack(side="left", fill="x", expand=True)
        self.campo.al_presionar_enter(self._enviar)
        self.campo.entrada.bind("<Escape>", lambda _e: self._cancelar_modo())
        self.campo.entrada.bind("<Up>", lambda _e: self._editar_ultimo())

        self.marco = MarcoScroll(der, fondo=E.FONDO_CHAT)
        self.marco.pack(fill="both", expand=True)

    def _icono(self, padre, contenido, comando, fuente=None):
        """Botón de ícono redondo (texto o imagen) con hover."""
        kw = {"image": contenido} if not isinstance(contenido, str) else {
            "text": contenido, "font": fuente or E.F_NEG}
        lbl = tk.Label(padre, bg=E.BLANCO, fg=E.SUAVE, cursor="hand2", padx=7, pady=3, **kw)
        lbl.bind("<Button-1>", lambda _e: comando())
        lbl.bind("<Enter>", lambda _e: lbl.config(bg=E.BOTON_SEC, fg=E.TEXTO))
        lbl.bind("<Leave>", lambda _e: lbl.config(bg=E.BLANCO, fg=E.SUAVE))
        return lbl

    # --------------------------------------------------------- conversaciones
    def refrescar(self):
        resp = self.app.cliente.listar_amigos()
        if not respuesta_ok(resp, "No se pudo cargar la lista de conversaciones."):
            return
        self.datos = [(SALA, "Sala general", "Todos los usuarios", None)]
        for a in resp.get("amigos", []):
            self.fotos[a["usuario"]] = self.app.ruta_foto(a)
            self.datos.append((a["usuario"], a.get("apodo") or a["nombre"],
                               "En línea" if a.get("en_linea") else "Desconectado",
                               bool(a.get("en_linea"))))
        self._pintar_lista()
        if self.actual is None:
            self._abrir_clave(SALA)

    def _pintar_lista(self):
        self.lista.limpiar()
        for clave, nombre, estado, en_linea in self.datos:
            FilaConversacion(self.lista.interior, clave, nombre, estado, en_linea,
                             self.no_leidos.get(clave, 0), clave == self.actual,
                             lambda c=clave: self._abrir_clave(c),
                             self.fotos.get(clave)).pack(fill="x")

    def abrir(self, usuario):
        """Usada por la pestaña Amigos para abrir un chat privado."""
        self.refrescar()
        self._abrir_clave(usuario)

    def _abrir_clave(self, clave):
        self.actual = clave
        self.no_leidos.pop(clave, None)
        self._cancelar_modo()
        self._pintar_lista()
        for c, nombre, estado, _en in self.datos:
            if c == clave:
                self.lbl_titulo.config(text=nombre)
                self.lbl_estado.config(text=estado)
                self.av_cab.cambiar("#" if c == SALA else nombre, c, self.fotos.get(c), 38)
        resp = self.app.cliente.obtener_chat(clave)
        if not respuesta_ok(resp, "No se pudo cargar el historial."):
            return
        self.mensajes = resp.get("mensajes", [])
        self._pintar_mensajes()

    # ---------------------------------------------------------------- mensajes
    def _pintar_mensajes(self):
        self.marco.limpiar()
        self.filas = {}
        if not self.mensajes:
            vacio(self.marco.interior, "Aún no hay mensajes. ¡Escribe el primero!",
                  E.FONDO_CHAT).pack(pady=30)
        for m in self.mensajes:
            self._agregar_fila(m)
        self._bajar()

    def _agregar_fila(self, m, despues_de=None):
        fila = FilaMensaje(self.marco.interior, self, m)
        if despues_de is not None:
            fila.pack(fill="x", after=despues_de)
        else:
            fila.pack(fill="x")
        self.filas[m.get("id")] = fila
        return fila

    def _bajar(self):
        self.update_idletasks()
        self.marco.canvas.yview_moveto(1.0)

    def _agregar(self, m):
        if not self.mensajes:
            self.marco.limpiar()
        self.mensajes.append(m)
        self._agregar_fila(m)
        self.after(20, self._bajar)

    def reemplazar(self, m):
        """Pinta de nuevo un mensaje que cambió (editado, reacción, voto, eliminado)."""
        for i, viejo in enumerate(self.mensajes):
            if viejo.get("id") == m.get("id"):
                self.mensajes[i] = m
                anterior = self.filas.get(m["id"])
                if anterior is not None and anterior.winfo_exists():
                    self._agregar_fila(m, despues_de=anterior)
                    anterior.destroy()
                return

    def _clave_de(self, m):
        if m.get("receptor") == SALA:
            return SALA
        yo = self.app.perfil["usuario"]
        return m.get("receptor") if m.get("emisor") == yo else m.get("emisor")

    def recibir(self, ev):
        """Mensaje de chat en vivo enviado por el servidor."""
        m = ev.get("mensaje") or ev
        if m.get("emisor") == self.app.perfil["usuario"]:
            return
        clave = self._clave_de(m)
        if clave == self.actual:
            self._agregar(m)
        else:
            self.no_leidos[clave] = self.no_leidos.get(clave, 0) + 1
            self._pintar_lista()

    def actualizar(self, ev):
        m = ev.get("mensaje") or ev
        if self._clave_de(m) == self.actual:
            self.reemplazar(m)

    # ----------------------------------------------------------------- enviar
    def _sin_conversacion(self):
        if self.actual is None:
            alerta_aviso("Elige una conversación primero.")
            return True
        return False

    def _enviar_tipo(self, tipo, texto="", ruta=None, encuesta=None):
        """Envía cualquier tipo de mensaje y lo agrega a la conversación."""
        if self._sin_conversacion():
            return False
        responde = self.respondiendo.get("id") if self.respondiendo else None
        resp = self.app.cliente.enviar_chat(self.actual, texto, tipo, ruta, responde, encuesta)
        if not respuesta_ok(resp, "No se pudo enviar el mensaje."):
            return False
        self._cancelar_modo()
        self._agregar(resp["mensaje"])
        return True

    def _enviar(self):
        texto = self.campo.get().strip()
        if self._sin_conversacion():
            return
        if not texto:
            alerta_aviso("Escribe un mensaje antes de enviar.")
            return
        if self.editando:
            resp = self.app.cliente.actualizar_mensaje(self.actual, self.editando["id"],
                                                       "editar", texto)
            if respuesta_ok(resp, "No se pudo editar el mensaje."):
                self.reemplazar(resp["mensaje"])
                self._cancelar_modo()
            return
        if self._enviar_tipo("texto", texto):
            self.campo.set("")

    def accion(self, m, accion, valor=None):
        """Reaccionar, votar o eliminar un mensaje (lo usan las filas)."""
        resp = self.app.cliente.actualizar_mensaje(self.actual, m["id"], accion, valor)
        if respuesta_ok(resp):
            self.reemplazar(resp["mensaje"])

    # -------------------------------------------- responder / editar (modos)
    def responder(self, m):
        self.editando = None
        self.respondiendo = m
        quien = "ti mismo" if m["emisor"] == self.app.perfil["usuario"] else "@" + m["emisor"]
        self._mostrar_aviso(f"↩  Respondiendo a {quien}: {resumen(m)[:60]}")
        self.campo.focus()

    def editar(self, m):
        self.respondiendo = None
        self.editando = m
        self._mostrar_aviso("✏  Editando mensaje  ·  Esc para cancelar  ·  Enter para guardar")
        self.campo.set(m["texto"])
        self.campo.focus()
        self.campo.entrada.icursor("end")

    def _editar_ultimo(self):
        """Flecha arriba con el campo vacío: editar tu último mensaje (como en Discord)."""
        if self.campo.get():
            return
        yo = self.app.perfil["usuario"]
        for m in reversed(self.mensajes):
            if m["emisor"] == yo and m.get("tipo", "texto") == "texto":
                self.editar(m)
                return

    def _mostrar_aviso(self, texto):
        self.lbl_aviso.config(text=texto)
        self.aviso.pack(fill="x", before=self.zona_envio.winfo_children()[-1])

    def _cancelar_modo(self):
        if self.editando:
            self.campo.set("")
        self.editando = self.respondiendo = None
        self.aviso.pack_forget()

    # ------------------------------------------------------ emojis, GIF, sticker
    def _abrir_emojis(self):
        SelectorEmoji(self.app, self.btn_emoji, self.campo.insertar)

    def _abrir_stickers(self):
        if not self._sin_conversacion():
            SelectorSticker(self.app, self.btn_sticker, lambda r: self._enviar_tipo("sticker", "", r))

    def _abrir_gifs(self):
        if self._sin_conversacion():
            return

        def elegido(ruta):
            guardar_prefs(self.app.prefs)
            self._enviar_tipo("imagen", "", ruta)
        SelectorGif(self.app, self.btn_gif, elegido, self.app.prefs)

    # ------------------------------------------------------------- menú "+"
    def _menu_mas(self):
        menu = tk.Menu(self, tearoff=0, bg=E.BLANCO, fg=E.TEXTO, activebackground=E.CLARO,
                       activeforeground=E.TEXTO, font=E.F_NORMAL, bd=0)
        menu.add_command(label="  📎  Subir un archivo", command=self._subir_archivo)
        menu.add_command(label="  🖼  Enviar imagen", command=self._subir_imagen)
        menu.add_command(label="  📊  Crear encuesta", command=self._crear_encuesta)
        menu.add_command(label="  ⏰  Programar mensaje", command=self._programar)
        menu.add_command(label="  🎤  Grabar mensaje de voz", command=self._grabar)
        x = self.btn_mas.winfo_rootx()
        y = self.btn_mas.winfo_rooty() - 5 * 30
        menu.tk_popup(x, y)

    def _subir_archivo(self):
        if self._sin_conversacion():
            return
        ruta = elegir_archivo()
        if ruta:
            if ruta.lower().endswith(".wav"):
                self._enviar_tipo("audio", "", ruta)
            elif ruta.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                self._enviar_tipo("imagen", "", ruta)
            else:
                self._enviar_tipo("archivo", "", ruta)

    def _subir_imagen(self):
        if not self._sin_conversacion():
            ruta = elegir_imagen()
            if ruta:
                self._enviar_tipo("imagen", self.campo.get().strip(), ruta)
                self.campo.set("")

    def _crear_encuesta(self):
        if self._sin_conversacion():
            return
        d = Dialogo(self.app, "Crear encuesta")
        pregunta = Campo(d.cuerpo, "Pregunta", placeholder="¿Qué quieres preguntar?", fondo=E.BLANCO)
        pregunta.pack(fill="x", pady=(0, 10))
        opciones = [Campo(d.cuerpo, f"Opción {i + 1}" + (" (opcional)" if i > 1 else ""),
                          fondo=E.BLANCO) for i in range(4)]
        for o in opciones:
            o.pack(fill="x", pady=3)

        def crear():
            textos = [o.get().strip() for o in opciones if o.get().strip()]
            if not pregunta.get().strip() or len(textos) < 2:
                alerta_aviso("Escribe la pregunta y al menos dos opciones.", parent=d)
                return
            if self._enviar_tipo("encuesta", "", encuesta={"pregunta": pregunta.get().strip(),
                                                          "opciones": textos}):
                d.destroy()
        Boton(d.cuerpo, "Publicar encuesta", crear, "primario", fondo=E.BLANCO).pack(anchor="e",
                                                                                   pady=(14, 0))
        d.centrar(self.app)
        pregunta.focus()

    def _programar(self):
        if self._sin_conversacion():
            return
        d = Dialogo(self.app, "Programar mensaje")
        texto = Campo(d.cuerpo, "Mensaje", valor=self.campo.get(), fondo=E.BLANCO)
        texto.pack(fill="x", pady=(0, 10))
        minutos = Campo(d.cuerpo, "Enviar dentro de (minutos, 1 a 720)", valor="5", fondo=E.BLANCO)
        minutos.pack(fill="x")
        tk.Label(d.cuerpo, text="La app debe seguir abierta hasta esa hora.", font=E.F_PEQ,
                 fg=E.SUAVE, bg=E.BLANCO).pack(anchor="w", pady=(6, 0))

        def programar():
            m = minutos.get().strip()
            if not texto.get().strip() or not m.isdigit() or not 1 <= int(m) <= 720:
                alerta_aviso("Escribe el mensaje y un número de minutos entre 1 y 720.", parent=d)
                return
            destino, contenido = self.actual, texto.get().strip()
            # ponytail: se programa en este cliente; si se cierra la app, no se envía.
            # Para que llegue igual habría que guardarlo en el servidor con su hora.
            self.app.after(int(m) * 60000, lambda: self._enviar_programado(destino, contenido))
            d.destroy()
            self.campo.set("")
            E.alerta_info(f"Mensaje programado para dentro de {m} min")
        Boton(d.cuerpo, "Programar", programar, "primario", fondo=E.BLANCO).pack(anchor="e",
                                                                               pady=(14, 0))
        d.centrar(self.app)

    def _enviar_programado(self, destino, texto):
        resp = self.app.cliente.enviar_chat(destino, texto)
        if resp.get("ok"):
            E.alerta_info("Se envió tu mensaje programado")
            if destino == self.actual and self.winfo_exists():
                self._agregar(resp["mensaje"])

    def _grabar(self):
        if self._sin_conversacion():
            return
        grabadora = Grabadora()
        try:
            grabadora.iniciar()
        except OSError as exc:
            alerta_aviso(f"No se pudo usar el micrófono: {exc}")
            return
        d = Dialogo(self.app, "Mensaje de voz")
        lbl = tk.Label(d.cuerpo, text="●  Grabando  0:00", font=E.F_H3, fg=E.ROJO, bg=E.BLANCO)
        lbl.pack(anchor="w")
        tk.Label(d.cuerpo, text=f"Máximo {MAX_SEGUNDOS_VOZ} segundos.", font=E.F_PEQ, fg=E.SUAVE,
                 bg=E.BLANCO).pack(anchor="w", pady=(2, 12))
        botones = tk.Frame(d.cuerpo, bg=E.BLANCO)
        botones.pack(fill="x")
        estado = {"seg": 0, "activo": True}

        def terminar(enviar):
            if not estado["activo"]:
                return
            estado["activo"] = False
            if enviar:
                ruta = os.path.join(tempfile.gettempdir(), f"voz_{os.getpid()}.wav")
                try:
                    grabadora.detener(ruta)
                except OSError as exc:
                    alerta_aviso(f"No se pudo guardar la grabación: {exc}", parent=d)
                    d.destroy()
                    return
                d.destroy()
                self._enviar_tipo("audio", "", ruta)
            else:
                grabadora.cancelar()
                d.destroy()

        def tic():
            if not estado["activo"] or not d.winfo_exists():
                return
            estado["seg"] += 1
            lbl.config(text=f"●  Grabando  {estado['seg'] // 60}:{estado['seg'] % 60:02d}",
                       fg=E.ROJO if estado["seg"] % 2 else E.SUAVE)
            if estado["seg"] >= MAX_SEGUNDOS_VOZ:
                terminar(True)
            else:
                d.after(1000, tic)
        Boton(botones, "Cancelar", lambda: terminar(False), "secundario",
              fondo=E.BLANCO).pack(side="left")
        Boton(botones, "■  Detener y enviar", lambda: terminar(True), "primario",
              fondo=E.BLANCO).pack(side="right")
        d.protocol("WM_DELETE_WINDOW", lambda: terminar(False))
        d.bind("<Escape>", lambda _e: terminar(False))
        d.after(1000, tic)
        d.centrar(self.app)

    # ---------------------------------------------------------------- audio
    def alternar_audio(self, m, boton):
        if self.reproduciendo == m["id"]:
            detener_sonido()
            self.reproduciendo = None
            boton.config(text="▶")
            return
        ruta = self.app.cliente.ruta_imagen(m["adjunto"])
        if not ruta:
            alerta_aviso("No se pudo descargar el audio.")
            return
        reproducir(ruta)
        self.reproduciendo = m["id"]
        boton.config(text="■")

        def fin():
            if self.reproduciendo == m["id"]:
                self.reproduciendo = None
                if boton.winfo_exists():
                    boton.config(text="▶")
        boton.after(int(duracion(ruta) * 1000) + 300, fin)


def resumen(m):
    """Texto corto para respuestas, avisos y notificaciones."""
    tipo = m.get("tipo", "texto")
    return {"imagen": "🖼 Imagen", "sticker": "Sticker", "archivo": "📎 " + m.get("nombre_archivo", ""),
            "audio": "🎤 Mensaje de voz", "encuesta": "📊 Encuesta",
            "eliminado": "Mensaje eliminado"}.get(tipo, m.get("texto", ""))


def _tamano(n):
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1048576:.1f} MB"


def _hora(fecha):
    hora = fecha[11:16] if len(fecha or "") >= 16 else (fecha or "")
    hoy = datetime.now().strftime("%Y-%m-%d")
    return hora if (fecha or "").startswith(hoy) else f"{E.tiempo_relativo(fecha)} {hora}"


class FilaMensaje(tk.Frame):
    """Un mensaje con su contenido, respuesta, reacciones y la barra de acciones
    que aparece al pasar el mouse (como en Discord)."""

    def __init__(self, padre, chat, m):
        super().__init__(padre, bg=E.FONDO_CHAT)
        self.chat, self.m = chat, m
        app = chat.app
        self.yo = m["emisor"] == app.perfil["usuario"]
        lado = "e" if self.yo else "w"
        fila = tk.Frame(self, bg=E.FONDO_CHAT)
        fila.pack(anchor=lado, padx=18, pady=(6, 2))
        if not self.yo:
            autor = app.perfil_de(m["emisor"]) or {"nombre": m["emisor"]}
            av = Avatar(fila, autor.get("nombre", m["emisor"]), m["emisor"], app.ruta_foto(autor),
                        lado=34, fondo=E.FONDO_CHAT)
            av.pack(side="left", anchor="n", padx=(0, 10))
            av.config(cursor="hand2")
            av.bind("<Button-1>", lambda _e: app.ver_perfil(m["emisor"]))
        col = tk.Frame(fila, bg=E.FONDO_CHAT)
        col.pack(side="left")

        meta = ("Tú" if self.yo else "@" + m["emisor"]) + "  ·  " + _hora(m.get("fecha", ""))
        if m.get("editado"):
            meta += "  ·  (editado)"
        tk.Label(col, text=meta, font=(E.FAMILIA, 8), fg=E.SUAVE, bg=E.FONDO_CHAT).pack(anchor=lado)

        if m.get("responde_a"):
            r = m["responde_a"]
            cita = tk.Frame(col, bg=E.FONDO_CHAT)
            cita.pack(anchor=lado, pady=(2, 2))
            tk.Frame(cita, bg=E.ACENTO, width=3).pack(side="left", fill="y")
            texto_cita = f"@{r['emisor']}: {resumen(r)[:70] or '…'}"
            tk.Label(cita, image=EM.burbuja(texto_cita, None, E.SUAVE, 420, 11, relleno=(6, 1)),
                     bg=E.FONDO_CHAT).pack(side="left")

        self._contenido(col, lado)
        self._reacciones(col, lado)
        self.barra = None
        if m.get("tipo") != "eliminado":
            for w in (self, fila, col):
                w.bind("<Enter>", self._mostrar_barra, add="+")
            self.bind("<Leave>", self._salir, add="+")

    # ---- contenido según el tipo
    def _contenido(self, col, lado):
        m, app = self.m, self.chat.app
        tipo = m.get("tipo", "texto")
        fondo = E.ACENTO if self.yo else E.BURBUJA
        color = "#ffffff" if self.yo else E.TEXTO
        if tipo == "texto":
            img = (EM.emojis_grandes(m["texto"]) if EM.solo_emojis(m["texto"])
                   else EM.burbuja(m["texto"], fondo, color))
            tk.Label(col, image=img, bg=E.FONDO_CHAT, bd=0).pack(anchor=lado, pady=(2, 0))
        elif tipo == "eliminado":
            tk.Label(col, text="Mensaje eliminado", font=(E.FAMILIA, 10, "italic"), fg=E.SUAVE,
                     bg=E.BOTON_SEC, padx=12, pady=6).pack(anchor=lado, pady=(2, 0))
        elif tipo in ("imagen", "sticker"):
            ruta = app.cliente.ruta_imagen(m.get("adjunto"))
            caja = (150, 150) if tipo == "sticker" else (280, 220)
            cuadros = cuadros_imagen(ruta, caja)
            lbl = tk.Label(col, bg=E.FONDO_CHAT, bd=0, cursor="hand2")
            if cuadros:
                animar(lbl, cuadros)
            else:
                foto = miniatura(ruta, caja, transparente=True)
                lbl.config(image=foto) if foto else lbl.config(
                    text="[imagen no disponible]", font=E.F_PEQ, fg=E.SUAVE)
            lbl.pack(anchor=lado, pady=(2, 0))
            if ruta:
                lbl.bind("<Button-1>", lambda _e: abrir_archivo(ruta))
            if m.get("texto"):
                tk.Label(col, image=EM.burbuja(m["texto"], fondo, color), bg=E.FONDO_CHAT,
                         bd=0).pack(anchor=lado, pady=(4, 0))
        elif tipo == "archivo":
            self._tarjeta_archivo(col, lado)
        elif tipo == "audio":
            self._tarjeta_audio(col, lado)
        elif tipo == "encuesta":
            self._tarjeta_encuesta(col, lado)

    def _tarjeta(self, col, lado):
        t = tk.Frame(col, bg=E.BURBUJA, highlightthickness=1, highlightbackground=E.BORDE)
        t.pack(anchor=lado, pady=(2, 0))
        return t

    def _tarjeta_archivo(self, col, lado):
        tarjeta_archivo(col, self.chat.app, self.m.get("nombre_archivo"), self.m["adjunto"],
                        E.BURBUJA).pack(anchor=lado, pady=(2, 0))

    def _tarjeta_audio(self, col, lado):
        m = self.m
        t = self._tarjeta(col, lado)
        boton = tk.Label(t, text="■" if self.chat.reproduciendo == m["id"] else "▶",
                         font=(E.FAMILIA, 14, "bold"), fg="#ffffff", bg=E.ACENTO, width=3,
                         cursor="hand2")
        boton.pack(side="left", padx=10, pady=10)
        boton.bind("<Button-1>", lambda _e: self.chat.alternar_audio(m, boton))
        datos = tk.Frame(t, bg=E.BURBUJA)
        datos.pack(side="left", padx=(0, 16))
        tk.Label(datos, text="Mensaje de voz", font=E.F_NEG, fg=E.TEXTO, bg=E.BURBUJA).pack(anchor="w")
        onda = tk.Canvas(datos, width=150, height=18, bg=E.BURBUJA, highlightthickness=0)
        onda.pack(anchor="w")
        alturas = [3, 7, 12, 6, 15, 9, 4, 11, 16, 8, 5, 13, 7, 10, 4, 12, 6, 9, 14, 5]
        for i, h in enumerate(alturas):     # ondita decorativa
            onda.create_rectangle(i * 7.5, 9 - h / 2, i * 7.5 + 4, 9 + h / 2, fill=E.GRIS_PH,
                                  outline="")

    def _tarjeta_encuesta(self, col, lado):
        m, yo = self.m, self.chat.app.perfil["usuario"]
        enc = m.get("encuesta") or {"pregunta": "", "opciones": []}
        t = self._tarjeta(col, lado)
        cuerpo = tk.Frame(t, bg=E.BURBUJA)
        cuerpo.pack(padx=14, pady=12)
        tk.Label(cuerpo, image=EM.foto_emoji("📊", 18), text="  " + enc["pregunta"], compound="left",
                 font=E.F_H3, fg=E.TEXTO, bg=E.BURBUJA, wraplength=320,
                 justify="left").pack(anchor="w", pady=(0, 8))
        total = sum(len(o["votos"]) for o in enc["opciones"])
        for i, o in enumerate(enc["opciones"]):
            mio = yo in o["votos"]
            pct = len(o["votos"]) / total if total else 0
            opcion = tk.Canvas(cuerpo, width=300, height=30, bg=E.BURBUJA, highlightthickness=0,
                               cursor="hand2")
            opcion.pack(anchor="w", pady=2)
            opcion.create_rectangle(0, 0, 299, 29, outline=E.ACENTO if mio else E.BORDE,
                                    fill=E.BOTON_SEC)
            if pct:
                opcion.create_rectangle(1, 1, max(2, 298 * pct), 28, outline="",
                                        fill=E.mezclar(E.BOTON_SEC, E.ACENTO, 0.45))
            opcion.create_image(8, 15, anchor="w", image=EM.burbuja(
                ("✓ " if mio else "") + o["texto"], None, E.TEXTO, 220, 12, relleno=(0, 0)))
            opcion.create_text(290, 15, text=f"{round(pct * 100)}%  ({len(o['votos'])})",
                               anchor="e", font=E.F_PEQ, fill=E.SUAVE)
            opcion.bind("<Button-1>", lambda _e, i=i: self.chat.accion(m, "votar", i))
        tk.Label(cuerpo, text=f"{total} voto{'s' if total != 1 else ''}  ·  toca una opción para votar",
                 font=E.F_PEQ, fg=E.SUAVE, bg=E.BURBUJA).pack(anchor="w", pady=(6, 0))

    def _reacciones(self, col, lado):
        reacciones = self.m.get("reacciones") or {}
        if not reacciones:
            return
        yo = self.chat.app.perfil["usuario"]
        fila = tk.Frame(col, bg=E.FONDO_CHAT)
        fila.pack(anchor=lado, pady=(4, 0))
        for emoji, usuarios in reacciones.items():
            mio = yo in usuarios
            chip = tk.Label(fila, image=EM.foto_emoji(emoji, 16), text=f" {len(usuarios)}",
                            compound="left", font=E.F_PEQ_NEG, fg=E.TEXTO, padx=6, pady=1,
                            bg=E.CLARO if mio else E.BOTON_SEC, cursor="hand2",
                            highlightthickness=1,
                            highlightbackground=E.ACENTO if mio else E.BOTON_SEC)
            chip.pack(side="left", padx=(0, 4))
            chip.bind("<Button-1>", lambda _e, e=emoji: self.chat.accion(self.m, "reaccionar", e))

    # ---- barra de acciones al pasar el mouse
    def _mostrar_barra(self, _e=None):
        if self.barra is not None:
            return
        m = self.m
        self.barra = barra = tk.Frame(self, bg=E.BLANCO, highlightthickness=1,
                                      highlightbackground=E.BORDE)

        def boton(contenido, comando, ayuda):
            kw = ({"image": contenido} if not isinstance(contenido, str)
                  else {"text": contenido, "font": (E.FAMILIA, 12)})
            b = tk.Label(barra, bg=E.BLANCO, fg=E.SUAVE, cursor="hand2", padx=6, pady=2, **kw)
            b.pack(side="left")
            b.bind("<Button-1>", lambda _e: comando())
            b.bind("<Enter>", lambda _e: b.config(bg=E.BOTON_SEC, fg=E.TEXTO))
            b.bind("<Leave>", lambda _e: b.config(bg=E.BLANCO, fg=E.SUAVE))
            return b

        for emoji in EM.REACCIONES_RAPIDAS:
            boton(EM.foto_emoji(emoji, 20), lambda e=emoji: self.chat.accion(m, "reaccionar", e),
                  "Reaccionar")
        tk.Frame(barra, bg=E.BORDE, width=1).pack(side="left", fill="y", padx=2, pady=4)
        mas = boton(EM.foto_emoji("😀", 18), lambda: None, "Más reacciones")
        mas.bind("<Button-1>", lambda _e: SelectorEmoji(
            self.chat.app, mas, lambda e: self.chat.accion(m, "reaccionar", e)))
        if self.yo and m.get("tipo", "texto") == "texto":
            boton("✏", lambda: self.chat.editar(m), "Editar")
        boton("↩", lambda: self.chat.responder(m), "Responder")
        mas_op = boton("⋯", lambda: None, "Más")
        mas_op.bind("<Button-1>", lambda e: self._menu(e))
        barra.place(relx=0 if self.yo else 1, x=60 if self.yo else -24, y=0,
                    anchor="nw" if self.yo else "ne")
        barra.bind("<Leave>", self._salir, add="+")

    def _menu(self, e):
        m = self.m
        menu = tk.Menu(self, tearoff=0, bg=E.BLANCO, fg=E.TEXTO, activebackground=E.CLARO,
                       activeforeground=E.TEXTO, font=E.F_NORMAL)
        if m.get("texto"):
            menu.add_command(label="Copiar texto", command=lambda: (
                self.clipboard_clear(), self.clipboard_append(m["texto"])))
        menu.add_command(label="Responder", command=lambda: self.chat.responder(m))
        if self.yo:
            if m.get("tipo", "texto") == "texto":
                menu.add_command(label="Editar", command=lambda: self.chat.editar(m))
            menu.add_separator()
            menu.add_command(label="Eliminar mensaje", foreground=E.ROJO,
                             command=lambda: confirmar("¿Eliminar este mensaje para todos?")
                             and self.chat.accion(m, "eliminar"))
        menu.tk_popup(e.x_root, e.y_root)

    def _salir(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):
            w = None
        while w is not None and w is not self:
            w = w.master
        if w is None and self.barra is not None:
            self.barra.destroy()
            self.barra = None
