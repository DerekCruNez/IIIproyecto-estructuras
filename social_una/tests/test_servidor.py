"""Pruebas de integración independientes para el servidor TCP."""

import json
import socket
import struct
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from almacen import Almacen
from protocolo import enviar_mensaje, recibir_mensaje
from servidor import Servidor


class PruebasServidor(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        almacen = Almacen(str(Path(self.directorio.name) / "datos"))
        self.servidor = Servidor(almacen)
        self.hilo = threading.Thread(
            target=self.servidor.iniciar, args=("127.0.0.1", 0), daemon=True
        )
        self.hilo.start()
        limite = time.monotonic() + 3
        while self.servidor.puerto is None and time.monotonic() < limite:
            time.sleep(0.01)
        self.assertIsNotNone(self.servidor.puerto, "El servidor no inició")
        self.clientes = []

    def tearDown(self):
        for cliente in self.clientes:
            try:
                cliente.close()
            except OSError:
                pass
        self.servidor.detener()
        self.hilo.join(timeout=3)
        self.directorio.cleanup()

    def conectar(self):
        sock = socket.create_connection(("127.0.0.1", self.servidor.puerto), timeout=2)
        sock.settimeout(2)
        self.clientes.append(sock)
        return sock

    @staticmethod
    def pedir(sock, accion, datos=None):
        enviar_mensaje(sock, {"accion": accion, "datos": datos or {}, "id": "test-1"})
        respuesta = recibir_mensaje(sock)
        if respuesta is None:
            raise AssertionError("El servidor cerró la conexión antes de responder")
        return respuesta

    def registrar_e_iniciar(self, sock, usuario):
        self.assertTrue(self.pedir(sock, "registrar", {
            "nombre": usuario.title(), "usuario": usuario, "clave": "secreto"
        })["ok"])
        return self.pedir(sock, "login", {"usuario": usuario, "clave": "secreto"})

    def test_registro_login_sesion_unica_y_logout(self):
        a, b = self.conectar(), self.conectar()
        respuesta = self.registrar_e_iniciar(a, "ana")
        self.assertEqual(respuesta["id"], "test-1")
        self.assertNotIn("hash_password", respuesta["datos"]["usuario"])
        duplicado = self.pedir(a, "registrar", {
            "nombre": "Ana", "usuario": "ana", "clave": "secreto"
        })
        self.assertFalse(duplicado["ok"])
        self.assertFalse(self.pedir(b, "login", {
            "usuario": "ana", "clave": "incorrecta"
        })["ok"])
        self.assertFalse(self.pedir(b, "login", {
            "usuario": "ana", "clave": "secreto"
        })["ok"])
        self.assertFalse(self.pedir(b, "publicar", {"texto": "sin login"})["ok"])
        self.assertTrue(self.pedir(a, "logout")["ok"])
        self.assertTrue(self.pedir(b, "login", {
            "usuario": "ana", "clave": "secreto"
        })["ok"])

    def test_amistad_muro_like_chat_y_historial(self):
        ana, bob = self.conectar(), self.conectar()
        self.registrar_e_iniciar(ana, "ana")
        self.registrar_e_iniciar(bob, "bob")
        self.assertTrue(self.pedir(ana, "enviar_solicitud", {
            "origen": "bob", "destino": "bob"
        })["ok"])
        evento = recibir_mensaje(bob)
        self.assertEqual(evento["evento"], "nueva_solicitud")
        self.assertEqual(evento["datos"]["origen"], "ana")
        self.assertTrue(self.pedir(bob, "responder_solicitud", {
            "origen": "ana", "aceptar": True
        })["ok"])
        publicado = self.pedir(ana, "publicar", {
            "autor": "bob", "texto": "Hola", "link": "", "extra": ""
        })
        self.assertTrue(publicado["ok"])
        id_publicacion = publicado["datos"]["id_publicacion"]
        muro = self.pedir(bob, "obtener_muro", {"usuario": "ana"})
        self.assertEqual(muro["datos"]["publicaciones"][0]["autor"], "ana")
        self.assertTrue(self.pedir(bob, "dar_like", {
            "id_publicacion": id_publicacion, "usuario": "ana"
        })["ok"])
        quitar = self.pedir(bob, "dar_like", {"id_publicacion": id_publicacion})
        self.assertEqual(quitar["datos"]["mensaje"], "Like eliminado.")
        self.assertTrue(self.pedir(ana, "enviar_chat", {
            "emisor": "bob", "receptor": "bob", "texto": "Hola Bob"
        })["ok"])
        evento_chat = recibir_mensaje(bob)
        self.assertEqual(evento_chat["evento"], "nuevo_mensaje")
        historial = self.pedir(bob, "obtener_chat", {"a": "bob", "b": "ana"})
        self.assertEqual(historial["datos"]["mensajes"][0]["emisor"], "ana")
        bob.close()
        limite = time.monotonic() + 2
        while "bob" in self.servidor.en_linea and time.monotonic() < limite:
            time.sleep(0.01)
        sin_conexion = self.pedir(ana, "enviar_chat", {
            "receptor": "bob", "texto": "Te lo dejo para después"
        })
        self.assertTrue(sin_conexion["ok"])
        self.assertFalse(sin_conexion["datos"]["entregado"])
        bob_nuevo = self.conectar()
        self.assertTrue(self.pedir(bob_nuevo, "login", {
            "usuario": "bob", "clave": "secreto"
        })["ok"])
        historial = self.pedir(bob_nuevo, "obtener_chat", {"a": "bob", "b": "ana"})
        self.assertEqual(len(historial["datos"]["mensajes"]), 2)

    def test_perfiles_busqueda_solicitudes_amigos_y_sugerencias(self):
        ana, bob, cami = self.conectar(), self.conectar(), self.conectar()
        self.registrar_e_iniciar(ana, "ana")
        self.registrar_e_iniciar(bob, "bob")
        self.registrar_e_iniciar(cami, "cami")
        perfil = self.pedir(ana, "ver_perfil", {"usuario": "bob"})
        self.assertNotIn("hash_password", perfil["datos"]["perfil"])
        self.assertTrue(self.pedir(ana, "editar_perfil", {
            "bio": "Estudiante", "foto": "", "link": ""
        })["ok"])
        busqueda = self.pedir(ana, "buscar_usuarios", {"texto": "cam"})
        self.assertEqual(busqueda["datos"]["usuarios"][0]["usuario"], "cami")
        self.assertTrue(self.pedir(ana, "enviar_solicitud", {"destino": "bob"})["ok"])
        self.assertEqual(recibir_mensaje(bob)["datos"]["origen"], "ana")
        self.assertEqual(self.pedir(bob, "listar_solicitudes")["datos"]["solicitudes"], ["ana"])
        self.assertTrue(self.pedir(bob, "responder_solicitud", {
            "origen": "ana", "aceptar": False
        })["ok"])
        self.assertTrue(self.pedir(ana, "enviar_solicitud", {"destino": "bob"})["ok"])
        recibir_mensaje(bob)
        self.assertTrue(self.pedir(bob, "responder_solicitud", {
            "origen": "ana", "aceptar": True
        })["ok"])
        self.assertEqual(self.pedir(ana, "listar_amigos")["datos"]["amigos"], ["bob"])
        self.assertTrue(self.pedir(bob, "enviar_solicitud", {"destino": "cami"})["ok"])
        recibir_mensaje(cami)
        self.assertTrue(self.pedir(cami, "responder_solicitud", {
            "origen": "bob", "aceptar": True
        })["ok"])
        self.assertEqual(self.pedir(ana, "sugerencias")["datos"]["sugerencias"][0]["usuario"], "cami")
        self.assertTrue(self.pedir(ana, "eliminar_amigo", {"amigo": "bob"})["ok"])

    def test_clientes_independientes_desconexion_y_peticion_malformada(self):
        a, b, c = self.conectar(), self.conectar(), self.conectar()
        self.registrar_e_iniciar(a, "ana")
        self.registrar_e_iniciar(b, "bob")
        self.registrar_e_iniciar(c, "cami")
        a.close()
        respuesta = self.pedir(b, "buscar_usuarios", {"texto": ""})
        self.assertTrue(respuesta["ok"])
        enviar_mensaje(b, {"accion": "login", "datos": []})
        self.assertFalse(recibir_mensaje(b)["ok"])
        # Un payload JSON inválido produce error, pero el siguiente marco se atiende.
        payload = b"{no es json}"
        b.sendall(struct.pack(">I", len(payload)) + payload)
        error = recibir_mensaje(b)
        self.assertFalse(error["ok"])
        self.assertTrue(self.pedir(c, "accion_inexistente")["ok"] is False)
        self.assertTrue(self.pedir(b, "buscar_usuarios", {"texto": "ana"})["ok"])

    def test_operaciones_simultaneas_no_pierden_datos_ni_mezclan_respuestas(self):
        clientes = [self.conectar() for _ in range(4)]
        nombres = [f"usuario{i}" for i in range(len(clientes))]
        for cliente, nombre in zip(clientes, nombres):
            self.registrar_e_iniciar(cliente, nombre)

        barrera = threading.Barrier(len(clientes))
        operaciones_por_cliente = 12

        def publicar_en_lote(cliente, nombre):
            barrera.wait(timeout=3)
            ids = [f"{nombre}-{i}" for i in range(operaciones_por_cliente)]
            for indice, request_id in enumerate(ids):
                enviar_mensaje(cliente, {
                    "accion": "publicar",
                    "id": request_id,
                    "datos": {"texto": f"{nombre}-publicacion-{indice}"},
                })
            respuestas = [recibir_mensaje(cliente) for _ in ids]
            return ids, respuestas

        with ThreadPoolExecutor(max_workers=len(clientes)) as executor:
            resultados = list(executor.map(
                lambda args: publicar_en_lote(*args), zip(clientes, nombres)
            ))

        textos_esperados = set()
        for nombre, (ids_esperados, respuestas) in zip(nombres, resultados):
            self.assertEqual([r["id"] for r in respuestas], ids_esperados)
            for indice, respuesta in enumerate(respuestas):
                self.assertTrue(respuesta["ok"], respuesta)
                self.assertEqual(
                    respuesta["datos"]["publicacion"]["texto"],
                    f"{nombre}-publicacion-{indice}",
                )
                textos_esperados.add(respuesta["datos"]["publicacion"]["texto"])

        with self.servidor._lock_almacen:
            textos_guardados = {
                publicacion.texto for publicacion in self.servidor.almacen.publicaciones
            }
        self.assertEqual(len(textos_esperados), len(clientes) * operaciones_por_cliente)
        self.assertEqual(textos_guardados, textos_esperados)

    def test_detener_espera_operacion_activa_y_persiste_antes_de_salir(self):
        cliente = self.conectar()
        self.registrar_e_iniciar(cliente, "ana")
        operacion_iniciada = threading.Event()
        liberar_operacion = threading.Event()
        detener_finalizado = threading.Event()
        crear_publicacion_original = self.servidor.almacen.crear_publicacion

        def crear_publicacion_lenta(autor, texto, imagen, link, extra):
            operacion_iniciada.set()
            if not liberar_operacion.wait(timeout=5):
                raise TimeoutError("La prueba no liberó la operación a tiempo")
            return crear_publicacion_original(autor, texto, imagen, link, extra)

        self.servidor.almacen.crear_publicacion = crear_publicacion_lenta

        def enviar_publicacion():
            enviar_mensaje(cliente, {
                "accion": "publicar", "datos": {"texto": "Se guarda durante el cierre"}
            })
            try:
                recibir_mensaje(cliente)
            except OSError:
                pass

        hilo_peticion = threading.Thread(target=enviar_publicacion, daemon=True)
        hilo_peticion.start()
        self.assertTrue(operacion_iniciada.wait(timeout=3))

        def detener_servidor():
            self.servidor.detener()
            detener_finalizado.set()

        hilo_detener = threading.Thread(target=detener_servidor, daemon=True)
        hilo_detener.start()
        self.assertFalse(detener_finalizado.wait(timeout=0.1))
        segundo_detener_finalizado = threading.Event()
        hilo_segundo_detener = threading.Thread(
            target=lambda: (
                self.servidor.detener(), segundo_detener_finalizado.set()
            ),
            daemon=True,
        )
        hilo_segundo_detener.start()
        self.assertFalse(segundo_detener_finalizado.wait(timeout=0.1))
        liberar_operacion.set()
        hilo_detener.join(timeout=3)
        hilo_segundo_detener.join(timeout=3)
        hilo_peticion.join(timeout=3)

        self.assertTrue(detener_finalizado.is_set())
        self.assertTrue(segundo_detener_finalizado.is_set())
        self.assertFalse(hilo_detener.is_alive())
        self.assertFalse(hilo_segundo_detener.is_alive())
        self.assertFalse(hilo_peticion.is_alive())
        with self.servidor._lock_conexiones:
            self.assertFalse(self.servidor._hilos)
        recargado = Almacen(str(self.servidor.almacen.carpeta_datos))
        recargado.cargar_todo()
        self.assertEqual(len(recargado.publicaciones), 1)
        self.assertEqual(recargado.publicaciones[0].texto, "Se guarda durante el cierre")

    def test_interrupcion_del_bucle_aceptacion_aun_cierra_y_guarda(self):
        carpeta = Path(self.directorio.name) / "interrupcion"
        almacen = Almacen(str(carpeta))
        almacen.cargar_todo()
        self.assertTrue(almacen.registrar_usuario(
            "id-ana", "Ana", "ana", "secreto"
        )[0])
        servidor = Servidor(almacen)
        guardar_original = almacen.guardar_todo
        guardados = []

        def guardar_conteo():
            guardados.append(True)
            guardar_original()

        almacen.guardar_todo = guardar_conteo
        sockets_servidor = []
        sockets_cliente = []
        hilos_cliente = []

        def bucle_interrumpido():
            sock_servidor, sock_cliente = socket.socketpair()
            sockets_servidor.append(sock_servidor)
            sockets_cliente.append(sock_cliente)
            sesion = {
                "usuario": "ana",
                "socket": sock_servidor,
                "lock_envio": threading.Lock(),
                "addr": ("local", 0),
            }
            with servidor._lock_conexiones:
                servidor._conexiones[sock_servidor] = sesion
            with servidor.lock_en_linea:
                servidor.en_linea["ana"] = sock_servidor

            def esperar_cierre():
                try:
                    sock_servidor.recv(1)
                except OSError:
                    pass
                finally:
                    with servidor._lock_conexiones:
                        servidor._hilos.discard(threading.current_thread())

            hilo_cliente = threading.Thread(target=esperar_cierre, daemon=True)
            hilos_cliente.append(hilo_cliente)
            with servidor._lock_conexiones:
                servidor._hilos.add(hilo_cliente)
            hilo_cliente.start()
            raise KeyboardInterrupt

        servidor.aceptar_clientes = bucle_interrumpido
        with self.assertRaises(KeyboardInterrupt):
            servidor.iniciar("127.0.0.1", 0)

        self.assertFalse(servidor._ejecutando.is_set())
        socket_escucha = servidor.socket_servidor
        self.assertIsNotNone(socket_escucha)
        servidor.detener()

        self.assertIsNone(servidor.socket_servidor)
        self.assertEqual(socket_escucha.fileno(), -1)
        self.assertEqual(sockets_cliente[0].recv(1), b"")
        self.assertFalse(hilos_cliente[0].is_alive())
        self.assertFalse(servidor.en_linea)
        self.assertEqual(guardados, [True])
        almacen_recargado = Almacen(str(carpeta))
        almacen_recargado.cargar_todo()
        self.assertEqual(len(almacen_recargado.usuarios), 1)
        for sock in sockets_cliente + sockets_servidor:
            sock.close()

    def test_persistencia_al_reiniciar_almacen(self):
        cliente, amigo = self.conectar(), self.conectar()
        self.registrar_e_iniciar(cliente, "ana")
        self.registrar_e_iniciar(amigo, "bob")
        self.assertTrue(self.pedir(cliente, "publicar", {"texto": "Persistente"})["ok"])
        self.assertTrue(self.pedir(cliente, "enviar_solicitud", {"destino": "bob"})["ok"])
        recibir_mensaje(amigo)
        self.assertTrue(self.pedir(amigo, "responder_solicitud", {
            "origen": "ana", "aceptar": True
        })["ok"])
        self.assertTrue(self.pedir(cliente, "enviar_chat", {
            "receptor": "bob", "texto": "Chat persistente"
        })["ok"])
        recibir_mensaje(amigo)
        raiz = self.servidor.almacen.carpeta_datos
        self.servidor.detener()
        self.hilo.join(timeout=3)
        self.servidor = Servidor(Almacen(str(raiz)))
        self.hilo = threading.Thread(
            target=self.servidor.iniciar, args=("127.0.0.1", 0), daemon=True
        )
        self.hilo.start()
        limite = time.monotonic() + 3
        while self.servidor.puerto is None and time.monotonic() < limite:
            time.sleep(0.01)
        despues = self.conectar()
        self.assertTrue(self.pedir(despues, "login", {
            "usuario": "ana", "clave": "secreto"
        })["ok"])
        muro = self.pedir(despues, "obtener_muro")
        self.assertEqual(len(muro["datos"]["publicaciones"]), 1)
        self.assertEqual(len(self.pedir(despues, "obtener_chat", {
            "a": "ana", "b": "bob"
        })["datos"]["mensajes"]), 1)


if __name__ == "__main__":
    unittest.main()
