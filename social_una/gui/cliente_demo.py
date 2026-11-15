"""Cliente de demostración: imita a cliente.py (Daniel) sin red ni archivos.

Sirve para probar toda la interfaz antes de que el servidor y el cliente reales
estén listos. Tiene exactamente los mismos métodos que debe ofrecer cliente.Cliente
(ver CONTRATO_CLIENTE.md). Los datos viven solo en memoria.
"""
import os
import queue
import threading
from datetime import datetime

SALA = "#general"


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ok(**datos):
    return {"ok": True, **datos}


def _error(mensaje):
    return {"ok": False, "error": mensaje}


class ClienteDemo:
    def __init__(self):
        self.cola = queue.Queue()
        self.actual = None
        self._sig = 1
        self.usuarios = {
            "ana": {"id": "1", "nombre": "Ana Mora", "clave": "1234", "bio": "Estudiante de informática.",
                    "foto": "", "link": "https://una.ac.cr"},
            "luis": {"id": "2", "nombre": "Luis Vargas", "clave": "1234", "bio": "Me gusta la música.",
                     "foto": "", "link": ""},
            "maria": {"id": "3", "nombre": "María Rojas", "clave": "1234", "bio": "", "foto": "", "link": ""},
            "pedro": {"id": "4", "nombre": "Pedro Solís", "clave": "1234", "bio": "", "foto": "", "link": ""},
        }
        self.amigos = {"ana": {"luis"}, "luis": {"ana", "pedro"}, "maria": set(), "pedro": {"luis"}}
        self.solicitudes = {"ana": {"maria"}, "luis": set(), "maria": set(), "pedro": set()}
        self.en_linea = {"luis"}
        self.publicaciones = []
        self.chats = {}
        self._publicar_como("luis", "¡Hola a todos! Este es mi primer post en Social UNA.", None, "")
        self._publicar_como("ana", "Estudiando estructuras de datos 📚", None, "https://docs.python.org")
        self._publicar_como("pedro", "Alguien para el proyecto del martes?", None, "")
        self.chats[SALA] = [{"emisor": "luis", "receptor": SALA, "texto": "Bienvenidos a la sala general",
                             "fecha": _ahora()}]

    # ---------------------------------------------------------------- sesión
    def conectar(self, ip, puerto):
        return _ok()

    def registrar(self, id_, nombre, usuario, clave):
        if usuario in self.usuarios:
            return _error("Ese usuario ya existe.")
        self.usuarios[usuario] = {"id": id_, "nombre": nombre, "clave": clave, "bio": "", "foto": "", "link": ""}
        self.amigos[usuario] = set()
        self.solicitudes[usuario] = set()
        return _ok()

    def login(self, usuario, clave):
        u = self.usuarios.get(usuario)
        if not u or u["clave"] != clave:
            return _error("Usuario o contraseña incorrectos.")
        self.actual = usuario
        self.en_linea.add(usuario)
        return _ok(usuario=self._perfil(usuario))

    def logout(self):
        self.en_linea.discard(self.actual)
        self.actual = None
        return _ok()

    def _perfil(self, usuario):
        u = self.usuarios[usuario]
        return {"id": u["id"], "usuario": usuario, "nombre": u["nombre"], "bio": u["bio"],
                "foto": u["foto"], "link": u["link"]}

    # ----------------------------------------------------------------- perfil
    def ver_perfil(self, usuario):
        if usuario not in self.usuarios:
            return _error("Usuario no encontrado.")
        return _ok(usuario=self._perfil(usuario))

    def editar_perfil(self, bio, ruta_foto, link):
        u = self.usuarios[self.actual]
        u["bio"], u["link"] = bio, link
        if ruta_foto:
            u["foto"] = ruta_foto            # en la demo el "nombre" es la ruta completa
        return _ok(usuario=self._perfil(self.actual))

    def ruta_imagen(self, nombre):
        return nombre if nombre and os.path.isfile(nombre) else None

    # ---------------------------------------------------------------- usuarios
    def buscar_usuarios(self, texto):
        t = texto.lower()
        res = []
        for usuario, u in self.usuarios.items():
            if usuario == self.actual:
                continue
            if t in usuario.lower() or t in u["nombre"].lower():
                res.append({"usuario": usuario, "nombre": u["nombre"],
                            "amigo": usuario in self.amigos[self.actual],
                            "pendiente": self.actual in self.solicitudes[usuario]})
        return _ok(usuarios=res)

    def enviar_solicitud(self, usuario):
        if usuario in self.amigos[self.actual]:
            return _error("Ya son amigos.")
        if self.actual in self.solicitudes[usuario]:
            return _error("Ya enviaste una solicitud a ese usuario.")
        self.solicitudes[usuario].add(self.actual)
        return _ok()

    def responder_solicitud(self, usuario, acepta):
        self.solicitudes[self.actual].discard(usuario)
        if acepta:
            self.amigos[self.actual].add(usuario)
            self.amigos[usuario].add(self.actual)
        return _ok()

    def listar_amigos(self):
        return _ok(
            amigos=[{"usuario": a, "nombre": self.usuarios[a]["nombre"], "en_linea": a in self.en_linea}
                    for a in sorted(self.amigos[self.actual])],
            solicitudes=[{"usuario": s, "nombre": self.usuarios[s]["nombre"]}
                         for s in sorted(self.solicitudes[self.actual])])

    def sugerencias(self):
        mios = self.amigos[self.actual]
        cuenta = {}
        for amigo in mios:
            for otro in self.amigos[amigo]:
                if otro != self.actual and otro not in mios:
                    cuenta[otro] = cuenta.get(otro, 0) + 1
        return _ok(sugerencias=[{"usuario": u, "nombre": self.usuarios[u]["nombre"], "en_comun": n}
                                for u, n in sorted(cuenta.items(), key=lambda x: -x[1])])

    # ------------------------------------------------------------ publicaciones
    def _publicar_como(self, autor, texto, ruta_imagen, link):
        self.publicaciones.append({"id": self._sig, "autor": autor, "texto": texto,
                                   "imagen": ruta_imagen or "", "link": link, "fecha": _ahora(), "likes": []})
        self._sig += 1

    def publicar(self, texto, ruta_imagen, link):
        self._publicar_como(self.actual, texto, ruta_imagen, link)
        return _ok()

    def obtener_muro(self):
        visibles = self.amigos[self.actual] | {self.actual}
        pubs = [p for p in self.publicaciones if p["autor"] in visibles]
        return _ok(publicaciones=sorted(pubs, key=lambda p: (p["fecha"], p["id"]), reverse=True))

    def dar_like(self, id_publicacion):
        for p in self.publicaciones:
            if p["id"] == id_publicacion:
                if self.actual in p["likes"]:
                    p["likes"].remove(self.actual)
                else:
                    p["likes"].append(self.actual)
                return _ok()
        return _error("La publicación no existe.")

    # --------------------------------------------------------------------- chat
    @staticmethod
    def _clave(a, b):
        return "|".join(sorted((a, b)))

    def obtener_chat(self, con):
        clave = SALA if con == SALA else self._clave(self.actual, con)
        return _ok(mensajes=list(self.chats.get(clave, [])))

    def enviar_chat(self, receptor, texto):
        msg = {"emisor": self.actual, "receptor": receptor, "texto": texto, "fecha": _ahora()}
        clave = SALA if receptor == SALA else self._clave(self.actual, receptor)
        self.chats.setdefault(clave, []).append(msg)
        if receptor != SALA:
            # simula la respuesta en vivo de un amigo (llega por la cola, como con el servidor)
            respuesta = {"tipo": "chat", "emisor": receptor, "receptor": self.actual,
                         "texto": "¡Recibido! (respuesta automática de la demo)", "fecha": ""}

            def responder():
                respuesta["fecha"] = _ahora()
                self.chats.setdefault(clave, []).append(
                    {k: respuesta[k] for k in ("emisor", "receptor", "texto", "fecha")})
                self.cola.put(respuesta)
            t = threading.Timer(1.5, responder)
            t.daemon = True
            t.start()
        return _ok(mensaje=msg)
