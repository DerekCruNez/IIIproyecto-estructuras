"""Prueba de cliente.py contra el servidor real (python -m unittest tests.test_cliente)."""

import os
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path

from almacen import Almacen
from cliente import Cliente, SALA
from servidor import Servidor

PNG = b"\x89PNG" + b"0" * 100


class PruebaCliente(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.servidor = Servidor(Almacen(str(Path(self.dir.name) / "datos")))
        threading.Thread(target=self.servidor.iniciar, args=("127.0.0.1", 0),
                         daemon=True).start()
        while self.servidor.puerto is None:
            time.sleep(0.01)

    def tearDown(self):
        self.servidor.detener()
        self.dir.cleanup()

    def nuevo(self, usuario, id_):
        c = Cliente()
        self.assertTrue(c.conectar("127.0.0.1", self.servidor.puerto)["ok"])
        self.assertTrue(c.registrar(id_, usuario.title(), usuario, "1234")["ok"])
        self.assertTrue(c.login(usuario, "1234")["ok"])
        return c

    @staticmethod
    def evento(cliente, tipo):
        """Siguiente evento de ese tipo (salta los demás)."""
        limite = time.monotonic() + 3
        while time.monotonic() < limite:
            try:
                ev = cliente.cola.get(timeout=0.2)
            except queue.Empty:
                continue
            if ev["tipo"] == tipo:
                return ev
        raise AssertionError(f"No llegó el evento {tipo}")

    def archivo(self, nombre, contenido):
        ruta = Path(self.dir.name) / nombre
        ruta.write_bytes(contenido)
        return str(ruta)

    def test_flujo_completo(self):
        self.assertFalse(Cliente().conectar("127.0.0.1", 1)["ok"])
        ana, luis, cami = self.nuevo("ana", "1"), self.nuevo("luis", "2"), self.nuevo("cami", "3")
        self.assertFalse(Cliente().registrar("1", "X", "otro", "1")["ok"])  # sin conexión
        self.assertIn("ID", ana.registrar("1", "Otro", "otro", "1")["error"])  # ID repetido

        # solicitudes, búsqueda con banderas y solicitud cruzada
        self.assertTrue(ana.enviar_solicitud("luis")["ok"])
        self.assertTrue(ana.buscar_usuarios("lu")["usuarios"][0]["pendiente"])
        self.assertEqual(self.evento(luis, "solicitud")["usuario"], "ana")
        self.assertEqual(luis.listar_amigos()["solicitudes"][0]["nombre"], "Ana")
        self.assertTrue(luis.enviar_solicitud("ana")["ok"])  # se aceptan solas
        amigos = ana.listar_amigos()["amigos"]
        self.assertEqual((amigos[0]["usuario"], amigos[0]["en_linea"]), ("luis", True))
        self.assertTrue(ana.buscar_usuarios("lu")["usuarios"][0]["amigo"])
        self.assertTrue(luis.enviar_solicitud("cami")["ok"])
        self.assertTrue(cami.responder_solicitud("luis", True)["ok"])
        self.assertEqual(ana.sugerencias()["sugerencias"][0]["en_comun"], 1)

        # publicaciones con imagen, solo link, reacciones y likes
        img = self.archivo("foto.png", PNG)
        self.assertTrue(ana.publicar("hola", img, "https://una.ac.cr")["ok"])
        self.assertEqual(self.evento(luis, "publicacion")["autor"], "ana")
        self.assertTrue(luis.publicar("", None, "https://python.org")["ok"])
        self.assertIn("Formato", ana.publicar("x", self.archivo("a.txt", b"hola"), "")["error"])
        self.assertIn("2 MB", ana.publicar(
            "x", self.archivo("g.jpg", b"\xff\xd8" + b"0" * 2 * 1024 * 1024), "")["error"])
        muro = luis.obtener_muro()["publicaciones"]
        self.assertEqual([p["autor"] for p in muro], ["luis", "ana"])
        self.assertRegex(muro[0]["fecha"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
        self.assertTrue(luis.dar_like(muro[1]["id"])["ok"])
        self.assertTrue(luis.reaccionar(muro[1]["id"], "🔥")["ok"])
        self.assertFalse(luis.reaccionar(muro[1]["id"], "💩")["ok"])
        p = ana.obtener_muro()["publicaciones"][1]
        self.assertEqual((p["likes"], p["reacciones"]), (["luis"], {"🔥": ["luis"]}))

        # la imagen se descarga del servidor si no está en la caché
        local = luis.ruta_imagen(muro[1]["imagen"])
        os.remove(local)
        self.assertEqual(Path(luis.ruta_imagen(muro[1]["imagen"])).read_bytes(), PNG)
        self.assertIsNone(luis.ruta_imagen("../../servidor.py"))

        # chat privado y sala general
        self.assertTrue(ana.enviar_chat("luis", "hola luis")["ok"])
        self.assertEqual(self.evento(luis, "chat")["texto"], "hola luis")
        self.assertEqual(luis.obtener_chat("ana")["mensajes"][0]["texto"], "hola luis")
        self.assertTrue(cami.enviar_chat(SALA, "hola a todos")["ok"])
        self.assertEqual(self.evento(ana, "chat")["receptor"], SALA)
        self.assertEqual(ana.obtener_chat(SALA)["mensajes"][0]["emisor"], "cami")

        # muro: archivo adjunto, editar y eliminar (solo el autor), apodos
        self.assertTrue(ana.publicar("con archivo", None, "",
                                     self.archivo("apuntes.txt", b"hola"))["ok"])
        mia = ana.obtener_muro()["publicaciones"][0]
        self.assertEqual(mia["nombre_archivo"], "apuntes.txt")
        self.assertFalse(luis.editar_publicacion(mia["id"], "hackeado")["ok"])
        self.assertTrue(ana.editar_publicacion(mia["id"], "corregido 😎")["ok"])
        mia = ana.obtener_muro()["publicaciones"][0]
        self.assertEqual((mia["texto"], mia["editado"]), ("corregido 😎", True))
        self.assertFalse(luis.eliminar_publicacion(mia["id"])["ok"])
        self.assertTrue(ana.eliminar_publicacion(mia["id"])["ok"])
        self.assertNotIn(mia["id"], [p["id"] for p in ana.obtener_muro()["publicaciones"]])
        self.assertTrue(ana.poner_apodo("luis", "Lucho")["ok"])
        self.assertEqual(ana.listar_amigos()["amigos"][0]["apodo"], "Lucho")
        self.assertFalse(ana.poner_apodo("cami", "x")["ok"])   # no es su amiga

        # juegos: puntajes (mejor marca), límites, leaderboard y 3 en raya por turnos
        self.assertEqual(ana.enviar_puntaje("serpiente", 120)["mejor"], 120)
        self.assertEqual(ana.enviar_puntaje("serpiente", 50)["mejor"], 120)
        self.assertFalse(ana.enviar_puntaje("serpiente", 999999)["ok"])
        self.assertFalse(ana.enviar_puntaje("tres_en_raya", 3)["ok"])   # solo lo da el servidor
        luis.enviar_puntaje("serpiente", 300)
        tabla = ana.leaderboard("serpiente")["tabla"]
        self.assertEqual([f["usuario"] for f in tabla], ["luis", "ana"])
        self.assertTrue(ana.invitar_juego("luis")["ok"])
        self.assertEqual(self.evento(luis, "invitacion_juego")["usuario"], "ana")
        p = luis.responder_juego("ana", True)["partida"]
        self.assertEqual(self.evento(ana, "partida")["partida"]["id"], p["id"])
        self.assertFalse(luis.jugada(p["id"], 0)["ok"])          # no es su turno (empieza X)
        for jugador, casilla in ((ana, 0), (luis, 3), (ana, 1), (luis, 4)):
            self.assertTrue(jugador.jugada(p["id"], casilla)["ok"])
        self.assertFalse(ana.jugada(p["id"], 4)["ok"])            # ocupada
        fin = ana.jugada(p["id"], 2)["partida"]
        self.assertEqual((fin["ganador"], fin["linea"]), ("ana", [0, 1, 2]))
        self.assertEqual(ana.leaderboard("tres_en_raya")["tabla"][0]["puntos"], 3)
        ana.invitar_juego("luis"); self.evento(luis, "invitacion_juego")
        p2 = luis.responder_juego("ana", True)["partida"]
        self.assertTrue(ana.abandonar_juego(p2["id"])["ok"])
        self.assertEqual(self.evento(luis, "partida")["partida"]["ganador"], "luis")

        # chat avanzado: respuesta, edición, reacción, archivos, audio, sticker, encuesta
        base = ana.obtener_chat("luis")["mensajes"][0]
        r = luis.enviar_chat("ana", "te respondo", responde_a=base["id"])
        self.assertEqual(r["mensaje"]["responde_a"]["texto"], "hola luis")
        self.assertFalse(ana.actualizar_mensaje("luis", r["mensaje"]["id"], "editar", "x")["ok"])
        self.assertTrue(luis.actualizar_mensaje("ana", r["mensaje"]["id"], "editar", "editado")["ok"])
        ev = self.evento(ana, "mensaje_actualizado")["mensaje"]
        self.assertEqual((ev["texto"], ev["editado"]), ("editado", True))
        self.assertTrue(ana.actualizar_mensaje("luis", r["mensaje"]["id"], "reaccionar", "❤️")["ok"])
        self.assertFalse(ana.enviar_chat("luis", "", "archivo", self.archivo("v.exe", b"MZ"))["ok"])
        pdf = ana.enviar_chat("luis", "", "archivo", self.archivo("tarea.pdf", b"%PDF-1.4"))
        self.assertEqual(pdf["mensaje"]["nombre_archivo"], "tarea.pdf")
        self.assertTrue(ana.enviar_chat("luis", "", "audio", self.archivo("voz.wav", b"RIFF0000"))["ok"])
        self.assertTrue(ana.enviar_chat("luis", "", "sticker", img)["ok"])
        enc = ana.enviar_chat("luis", "", "encuesta",
                              encuesta={"pregunta": "¿Pizza?", "opciones": ["Sí", "No"]})
        self.assertFalse(ana.enviar_chat("luis", "", "encuesta",
                                         encuesta={"pregunta": "x", "opciones": ["solo una"]})["ok"])
        self.assertTrue(luis.actualizar_mensaje("ana", enc["mensaje"]["id"], "votar", 1)["ok"])
        votos = ana.obtener_chat("luis")["mensajes"][-1]["encuesta"]["opciones"][1]["votos"]
        self.assertEqual(votos, ["luis"])
        self.assertTrue(luis.actualizar_mensaje("ana", r["mensaje"]["id"], "eliminar")["ok"])
        self.assertEqual(ana.obtener_chat("luis")["mensajes"][1]["tipo"], "eliminado")

        # perfil: foto GIF, banner, color y tema; una edición no borra lo demás
        gif = self.archivo("a.gif", b"GIF89a" + b"0" * 50)
        self.assertTrue(ana.editar_perfil("bio", gif, "", ruta_banner=img,
                                          color_perfil="#7c3aed")["ok"])
        perfil = luis.ver_perfil("ana")["usuario"]
        self.assertTrue(perfil["foto"].endswith(".gif"))
        self.assertEqual(perfil["color_perfil"], "#7c3aed")
        self.assertTrue(ana.editar_perfil("otra", None, "")["ok"])
        self.assertEqual(luis.ver_perfil("ana")["usuario"]["foto"], perfil["foto"])
        self.assertFalse(ana.editar_perfil("x" * 191, None, "")["ok"])
        self.assertFalse(ana.editar_perfil("b", None, "", color_perfil="rojo")["ok"])
        self.assertTrue(ana.guardar_apariencia("oscuro", "atardecer")["ok"])
        self.assertEqual(luis.ver_perfil("ana")["usuario"]["tema"], "oscuro")

        # presencia y eliminar amigo
        luis.logout()
        self.assertFalse(self.evento(ana, "en_linea")["en_linea"])
        self.assertTrue(ana.eliminar_amigo("luis")["ok"])
        self.assertEqual(ana.listar_amigos()["amigos"], [])

        # caída del servidor -> evento desconectado, sin colgar la GUI
        self.servidor.detener()
        self.evento(ana, "desconectado")
        self.assertFalse(ana.obtener_muro()["ok"])


if __name__ == "__main__":
    unittest.main()
