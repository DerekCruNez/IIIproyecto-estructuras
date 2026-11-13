"""Pestaña Amigos: lista con estado en línea y solicitudes pendientes."""
import tkinter as tk

from gui import estilo as E
from gui.estilo import MarcoScroll, respuesta_ok
from gui.widgets import Boton, Tarjeta, FilaUsuario, vacio


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
            FilaUsuario(self.marco_amigos.interior, a["usuario"], a["nombre"],
                        "En línea" if a.get("en_linea") else "Desconectado",
                        en_linea=bool(a.get("en_linea")),
                        acciones=[("Chat", lambda u=a["usuario"]: self.app.vista.abrir_chat(u),
                                   "primario")]).pack(fill="x")

        self.lbl_sol.config(text=f"Solicitudes de amistad  ·  {len(solicitudes)}")
        self.marco_sol.limpiar()
        if not solicitudes:
            vacio(self.marco_sol.interior, "No tienes solicitudes pendientes.", E.BLANCO).pack(pady=30)
        for s in solicitudes:
            FilaUsuario(self.marco_sol.interior, s["usuario"], s["nombre"],
                        acciones=[("Aceptar", lambda u=s["usuario"]: self._responder(u, True), "primario"),
                                  ("Rechazar", lambda u=s["usuario"]: self._responder(u, False),
                                   "secundario")]).pack(fill="x")

    def _responder(self, usuario, acepta):
        if respuesta_ok(self.app.cliente.responder_solicitud(usuario, acepta)):
            self.refrescar()
