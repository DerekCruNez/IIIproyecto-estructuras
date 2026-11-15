"""Pestaña Amigos: lista con estado en línea y solicitudes pendientes."""
import tkinter as tk

from gui import estilo as E
from gui.estilo import MarcoScroll, alerta_aviso, alerta_info, confirmar, respuesta_ok
from gui.widgets import Boton, Campo, Tarjeta, FilaUsuario, vacio


def _panel(padre, titulo):
    """Tarjeta con encabezado y una lista desplazable. Devuelve (tarjeta, encabezado, marco)."""
    tarjeta = Tarjeta(padre)
    cab = tk.Frame(tarjeta, bg=E.BLANCO)
    cab.pack(fill="x", padx=18, pady=(16, 10))
    lbl = tk.Label(cab, text=titulo, font=E.F_H3, fg=E.TEXTO, bg=E.BLANCO)
    lbl.pack(side="left")
    tk.Frame(tarjeta, bg=E.BORDE, height=1).pack(fill="x")
    marco = MarcoScroll(tarjeta, fondo=E.BLANCO)
    marco.pack(fill="both", expand=True)
    return tarjeta, lbl, marco


class PestanaAmigos(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.columnconfigure(0, weight=3, uniform="c")
        self.columnconfigure(1, weight=2, uniform="c")
        self.rowconfigure(0, weight=1)

        t1, self.lbl_amigos, self.marco_amigos = _panel(self, "Mis amigos")
        t1.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        t2, self.lbl_sol, self.marco_sol = _panel(self, "Solicitudes de amistad")
        t2.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    def refrescar(self):
        resp = self.app.cliente.listar_amigos()
        if not respuesta_ok(resp, "No se pudo cargar la lista de amigos."):
            return
        amigos, solicitudes = resp.get("amigos", []), resp.get("solicitudes", [])

        self.lbl_amigos.config(text=f"Mis amigos  ·  {len(amigos)}")
        self.marco_amigos.limpiar()
        if not amigos:
            vacio(self.marco_amigos.interior, "Aún no tienes amigos.\nBusca personas para empezar.",
                  E.BLANCO).pack(pady=(30, 12))
            Boton(self.marco_amigos.interior, "Buscar personas",
                  lambda: self.app.vista.ir("Buscar"), "primario", fondo=E.BLANCO).pack()
        for a in amigos:
            u = a["usuario"]
            estado = "En línea" if a.get("en_linea") else "Desconectado"
            apodo = a.get("apodo")
            FilaUsuario(self.marco_amigos.interior, u, apodo or a["nombre"],
                        f"{estado}  ·  {a['nombre']}" if apodo else estado,
                        en_linea=bool(a.get("en_linea")),
                        ruta_foto=self.app.ruta_foto(a),
                        al_click=lambda u=u: self.app.ver_perfil(u),
                        acciones=[("Chat", lambda u=u: self.app.vista.abrir_chat(u), "primario"),
                                  ("⋯", lambda a=a: self._menu(a), "fantasma")]
                        ).pack(fill="x")

        self.lbl_sol.config(text=f"Solicitudes de amistad  ·  {len(solicitudes)}")
        self.marco_sol.limpiar()
        if not solicitudes:
            vacio(self.marco_sol.interior, "No tienes solicitudes pendientes.", E.BLANCO).pack(pady=30)
        for s in solicitudes:
            FilaUsuario(self.marco_sol.interior, s["usuario"], s["nombre"],
                        ruta_foto=self.app.ruta_foto(s),
                        al_click=lambda u=s["usuario"]: self.app.ver_perfil(u),
                        acciones=[("Aceptar", lambda u=s["usuario"]: self._responder(u, True), "primario"),
                                  ("Rechazar", lambda u=s["usuario"]: self._responder(u, False),
                                   "secundario")]).pack(fill="x")

    def _responder(self, usuario, acepta):
        if respuesta_ok(self.app.cliente.responder_solicitud(usuario, acepta)):
            alerta_info(f"Ahora tú y @{usuario} son amigos" if acepta else "Solicitud rechazada")
            self.refrescar()

    def _menu(self, amigo):
        """Menú de los 3 puntos: apodo y eliminar amigo."""
        u = amigo["usuario"]
        menu = tk.Menu(self, tearoff=0, bg=E.BLANCO, fg=E.TEXTO, activebackground=E.CLARO,
                       activeforeground=E.TEXTO, font=E.F_NORMAL)
        menu.add_command(label="Cambiar apodo", command=lambda: self._apodo(amigo))
        if amigo.get("apodo"):
            menu.add_command(label="Quitar apodo", command=lambda: self._guardar_apodo(u, ""))
        menu.add_command(label="Ver perfil", command=lambda: self.app.ver_perfil(u))
        if amigo.get("en_linea"):
            menu.add_command(label="Retar a 3 en raya ⭕",
                             command=lambda: self.app.vista.pestanas["Juegos"].retar(u))
        menu.add_separator()
        menu.add_command(label="Eliminar amigo", foreground=E.ROJO, command=lambda: self._eliminar(u))
        x, y = self.winfo_pointerxy()
        menu.tk_popup(x, y)

    def _apodo(self, amigo):
        from gui.chat import Dialogo
        d = Dialogo(self.app, "Cambiar apodo")
        tk.Label(d.cuerpo, text=f"Solo tú verás este apodo para @{amigo['usuario']} "
                                f"({amigo['nombre']}).", font=E.F_PEQ, fg=E.SUAVE,
                 bg=E.BLANCO).pack(anchor="w", pady=(0, 8))
        campo = Campo(d.cuerpo, "Apodo (máx. 32 caracteres)", valor=amigo.get("apodo", ""),
                      fondo=E.BLANCO)
        campo.pack(fill="x")

        def guardar():
            apodo = campo.get().strip()
            if len(apodo) > 32:
                alerta_aviso("El apodo puede tener como máximo 32 caracteres.", parent=d)
                return
            d.destroy()
            self._guardar_apodo(amigo["usuario"], apodo)
        campo.al_presionar_enter(guardar)
        Boton(d.cuerpo, "Guardar", guardar, "primario", fondo=E.BLANCO).pack(anchor="e", pady=(14, 0))
        d.centrar(self.app)
        campo.focus()

    def _guardar_apodo(self, usuario, apodo):
        if respuesta_ok(self.app.cliente.poner_apodo(usuario, apodo), "No se pudo guardar el apodo."):
            alerta_info("Apodo guardado" if apodo else "Apodo quitado")
            self.refrescar()

    def _eliminar(self, usuario):
        if confirmar(f"¿Eliminar a @{usuario} de tus amigos?"):
            if respuesta_ok(self.app.cliente.eliminar_amigo(usuario)):
                alerta_info(f"@{usuario} ya no está en tus amigos")
                self.refrescar()
