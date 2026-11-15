"""Pestaña Buscar: buscador de usuarios, agregar amigos y sugerencias."""
import tkinter as tk

from gui import estilo as E
from gui.estilo import MarcoScroll, alerta_aviso, alerta_info, respuesta_ok
from gui.widgets import Boton, Campo, Tarjeta, FilaUsuario, vacio


class PestanaBuscar(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=E.FONDO)
        self.app = app
        self.resultados = None      # None = todavía no se ha buscado
        self.sugerencias = []

        barra = Tarjeta(self)
        barra.pack(fill="x")
        fila = tk.Frame(barra, bg=E.BLANCO)
        fila.pack(fill="x", padx=18, pady=16)
        self.campo = Campo(fila, placeholder="Busca por nombre o usuario", fondo=E.BLANCO)
        self.campo.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.campo.al_presionar_enter(self._buscar)
        Boton(fila, "Buscar", self._buscar, "primario", padx=26, pady=9, fondo=E.BLANCO).pack(side="left")

        self.marco = MarcoScroll(self)
        self.marco.pack(fill="both", expand=True, pady=(16, 0))

    def refrescar(self):
        resp = self.app.cliente.sugerencias()
        self.sugerencias = resp.get("sugerencias", []) if resp and resp.get("ok") else []
        self._pintar()

    def _buscar(self):
        texto = self.campo.get().strip()
        if not texto:
            alerta_aviso("Escribe un nombre o usuario para buscar.")
            return
        resp = self.app.cliente.buscar_usuarios(texto)
        if not respuesta_ok(resp, "No se pudo buscar."):
            return
        self.resultados = resp.get("usuarios", [])
        self._pintar()

    def _seccion(self, titulo):
        t = Tarjeta(self.marco.interior)
        t.pack(fill="x", pady=(0, 14), padx=(0, 10))
        tk.Label(t, text=titulo, font=E.F_H3, fg=E.TEXTO, bg=E.BLANCO).pack(
            anchor="w", padx=18, pady=(16, 10))
        tk.Frame(t, bg=E.BORDE, height=1).pack(fill="x")
        return t

    def _pintar(self):
        self.marco.limpiar()
        if self.resultados is not None:
            t = self._seccion(f"Resultados  ·  {len(self.resultados)}")
            if not self.resultados:
                vacio(t, "No se encontraron usuarios con ese texto.").pack()
            for u in self.resultados:
                if u.get("amigo"):
                    kw = {"etiqueta": "Ya es tu amigo"}
                elif u.get("pendiente"):
                    kw = {"etiqueta": "Solicitud enviada"}
                else:
                    kw = {"acciones": [("Agregar amigo", lambda x=u["usuario"]: self._agregar(x),
                                        "primario")]}
                FilaUsuario(t, u["usuario"], u["nombre"], **kw).pack(fill="x")
        t = self._seccion("Sugerencias para ti")
        if not self.sugerencias:
            vacio(t, "Aún no hay sugerencias.\nAparecerán amigos de tus amigos.").pack()
        for s in self.sugerencias:
            n = s.get("en_comun", 0)
            FilaUsuario(t, s["usuario"], s["nombre"],
                        f"{n} amigo{'s' if n != 1 else ''} en común",
                        acciones=[("Agregar amigo", lambda x=s["usuario"]: self._agregar(x),
                                   "secundario")]).pack(fill="x")

    def _agregar(self, usuario):
        if respuesta_ok(self.app.cliente.enviar_solicitud(usuario)):
            alerta_info(f"Solicitud de amistad enviada a @{usuario}.")
            if self.resultados is not None and self.campo.get().strip():
                self._buscar()
            else:
                self.refrescar()
