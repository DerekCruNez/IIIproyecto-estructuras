"""Generador de datos de prueba para Social UNA.

Crea usuarios, publicaciones y amistades de ejemplo usando Almacen.
Es idempotente: ejecutarlo varias veces no duplica usuarios, publicaciones
ni amistades existentes.
"""

from almacen import Almacen

USUARIOS_PRUEBA = [
    {"id": "u101", "nombre": "Angel Rodriguez", "usuario": "angel123",
     "clave": "clave123", "bio": "Estudiante de ingeniería de sistemas",
     "link": "https://ejemplo.com/angel"},
    {"id": "u102", "nombre": "Maria Garcia", "usuario": "maria456",
     "clave": "clave456", "bio": "Desarrolladora web apasionada por el software libre",
     "link": "https://ejemplo.com/maria"},
    {"id": "u103", "nombre": "Juan Perez", "usuario": "juan789",
     "clave": "clave789", "bio": "Diseñador UX/UI y entusiasta de la tecnología",
     "link": ""},
    {"id": "u104", "nombre": "Lucia Fernandez", "usuario": "lucia001",
     "clave": "clave001", "bio": "Estudiante de ciencia de datos y analítica",
     "link": "https://ejemplo.com/lucia"},
]

PUBLICACIONES_PRUEBA = [
    {"autor": "angel123", "texto": "¡Hola a todos! Este es mi primer post en Social UNA.",
     "imagen": "", "link": "", "extra": ""},
    {"autor": "angel123", "texto": "Conociendo Python y estructuras de datos. ¡Muy interesante!",
     "imagen": "", "link": "https://python.org", "extra": ""},
    {"autor": "maria456", "texto": "Hoy termine mi proyecto web. Muy contenta con el resultado final.",
     "imagen": "", "link": "", "extra": ""},
    {"autor": "juan789", "texto": "Nuevo curso de diseno UX disponible. Recomendado 100%.",
     "imagen": "", "link": "https://cursos.diseno.com", "extra": ""},
    {"autor": "lucia001", "texto": "Analizando grandes volúmenes de datos con Pandas y Python.",
     "imagen": "", "link": "", "extra": ""},
]

AMISTADES_PRUEBA = [
    ("angel123", "maria456"),
    ("angel123", "juan789"),
    ("maria456", "lucia001"),
]

CHATS_PRUEBA = [
    ("angel123", "maria456", "Hola Maria, ¿cómo estás?"),
    ("maria456", "angel123", "Hola Angel, bien y tú?"),
    ("angel123", "juan789", "Oye Juan, ¿viste el curso de UX?"),
]


def _usuario_existe(almacen: Almacen, nombre_usuario: str) -> bool:
    ok, _ = almacen.obtener_perfil(nombre_usuario)
    return ok


def _ya_son_amigos(almacen: Almacen, a: str, b: str) -> bool:
    ok, amigos = almacen.listar_amigos(a)
    return ok and b in amigos


def _existen_publicaciones(almacen: Almacen) -> bool:
    for u in almacen.usuarios:
        ok, muro = almacen.obtener_muro(u.usuario)
        if ok and len(muro) > 0:
            return True
    return False


def main() -> None:
    """Genera datos de prueba en el almacenamiento de forma idempotente."""
    almacen = Almacen()
    almacen.cargar_todo()

    usuarios_creados = 0
    usuarios_existentes = 0

    for datos in USUARIOS_PRUEBA:
        if _usuario_existe(almacen, datos["usuario"]):
            usuarios_existentes += 1
            continue
        ok, resultado = almacen.registrar_usuario(
            datos["id"], datos["nombre"], datos["usuario"], datos["clave"]
        )
        if ok:
            almacen.editar_perfil(datos["usuario"], datos["bio"], "", datos["link"])
            usuarios_creados += 1
            print(f"Usuario creado: {datos['usuario']}")
        else:
            print(f"Error creando {datos['usuario']}: {resultado}")

    if usuarios_existentes > 0:
        print(f"Se detectaron {usuarios_existentes} usuarios de prueba ya existentes.")

    amistades_creadas = 0
    for origen, destino in AMISTADES_PRUEBA:
        if _ya_son_amigos(almacen, origen, destino):
            continue
        if not _usuario_existe(almacen, origen) or not _usuario_existe(almacen, destino):
            print(f"Saltando amistad {origen}->{destino}: usuario no existe")
            continue
        ok, msg = almacen.enviar_solicitud(origen, destino)
        if ok:
            ok2, msg2 = almacen.responder_solicitud(destino, origen, True)
            if ok2:
                amistades_creadas += 1
                print(f"Amistad creada: {origen} <-> {destino}")
            else:
                print(f"Error aceptando amistad {origen}->{destino}: {msg2}")
        else:
            print(f"Error enviando solicitud {origen}->{destino}: {msg}")

    publicaciones_creadas = 0
    if _existen_publicaciones(almacen):
        print("Ya existen publicaciones en el almacenamiento. Se omiten las nuevas.")
    else:
        for datos in PUBLICACIONES_PRUEBA:
            if not _usuario_existe(almacen, datos["autor"]):
                print(f"Saltando publicación: autor {datos['autor']} no existe")
                continue
            ok, resultado = almacen.crear_publicacion(
                datos["autor"], datos["texto"], datos["imagen"],
                datos["link"], datos["extra"]
            )
            if ok:
                publicaciones_creadas += 1
                print(f"Publicación creada por {datos['autor']}: {datos['texto'][:40]}...")
            else:
                print(f"Error creando publicación de {datos['autor']}: {resultado}")

    chats_creados = 0
    for emisor, receptor, texto in CHATS_PRUEBA:
        if not _usuario_existe(almacen, emisor) or not _usuario_existe(almacen, receptor):
            continue
        ok, _ = almacen.guardar_chat(emisor, receptor, texto)
        if ok:
            chats_creados += 1

    almacen.guardar_todo()

    print("\n--- Resumen de generación de datos ---")
    print(f"Usuarios creados: {usuarios_creados}")
    print(f"Usuarios ya existentes: {usuarios_existentes}")
    print(f"Amistades creadas: {amistades_creadas}")
    print(f"Publicaciones creadas: {publicaciones_creadas}")
    print(f"Mensajes de chat guardados: {chats_creados}")

    total_usuarios = len(almacen.usuarios)
    print(f"Total de usuarios en almacenamiento: {total_usuarios}")
    assert total_usuarios >= 3, "Se esperaban al menos 3 usuarios"

    ok, muro = almacen.obtener_muro("angel123")
    if ok and len(muro) > 0:
        print("Verificación OK: existen publicaciones en el muro.")
    else:
        print("Advertencia: no se encontraron publicaciones.")

    ok, amigos_angel = almacen.listar_amigos("angel123")
    if ok and "maria456" in amigos_angel and "juan789" in amigos_angel:
        print("Verificación OK: amistades bidireccionales funcionando.")
    else:
        print("Advertencia: revisar amistades bidireccionales.")

    ok, sugerencias = almacen.sugerir_amigos("angel123")
    if ok:
        print(f"Sugerencias para angel123: {[s['usuario'] for s in sugerencias]}")

    almacen2 = Almacen()
    almacen2.cargar_todo()
    print(f"Usuarios tras recargar: {len(almacen2.usuarios)}")
    assert len(almacen2.usuarios) == total_usuarios, "Los usuarios no persisten correctamente"
    print("Verificación OK: los datos persisten entre instancias.")

    print("\nGeneración de datos completada exitosamente.")


if __name__ == "__main__":
    main()