# Contrato entre la interfaz (Brayan) y `cliente.py` (Daniel)

La GUI solo habla con un objeto `Cliente` (clase `Cliente` en `cliente.py`, sin argumentos en el
constructor). `python main.py` lo importa con `from cliente import Cliente`; si no existe, usa
`gui/cliente_demo.py`, que tiene los mismos métodos y sirve de ejemplo.

Todos los métodos devuelven un diccionario `{"ok": True, ...datos}` o `{"ok": False, "error": "texto"}`.
La GUI muestra el `error` en una alerta.

| Método | Devuelve (además de `ok`) |
|---|---|
| `conectar(ip, puerto)` | — |
| `registrar(id, nombre, usuario, clave)` | — |
| `login(usuario, clave)` | `usuario`: `{id, usuario, nombre, bio, foto, link}` |
| `logout()` | — |
| `ver_perfil(usuario)` | `usuario`: igual que arriba |
| `editar_perfil(bio, ruta_foto_o_None, link)` | `usuario` |
| `buscar_usuarios(texto)` | `usuarios`: `[{usuario, nombre, amigo, pendiente}]` |
| `enviar_solicitud(usuario)` | — |
| `responder_solicitud(usuario, acepta)` | — (`acepta` es True/False) |
| `listar_amigos()` | `amigos`: `[{usuario, nombre, en_linea}]`, `solicitudes`: `[{usuario, nombre}]` |
| `sugerencias()` | `sugerencias`: `[{usuario, nombre, en_comun}]` |
| `publicar(texto, ruta_imagen_o_None, link)` | — |
| `obtener_muro()` | `publicaciones`: `[{id, autor, texto, imagen, link, fecha, likes}]`, de la más reciente a la más antigua |
| `dar_like(id_publicacion)` | — |
| `enviar_chat(receptor, texto)` | `mensaje`: `{emisor, receptor, texto, fecha}` (`receptor` = `"#general"` para la sala) |
| `obtener_chat(con)` | `mensajes`: `[{emisor, receptor, texto, fecha}]` (`con` = usuario o `"#general"`) |
| `ruta_imagen(nombre)` | ruta local del archivo (carpeta temporal) o `None` |

Notas:
- `fecha` con formato `"AAAA-MM-DD HH:MM:SS"`; `likes` es la lista de usuarios que dieron like.
- La imagen se limita a 2 MB; la GUI ya lo valida, pero `cliente.py` debe validarlo también.
- `ruta_imagen(nombre)` descarga la imagen si hace falta y devuelve dónde quedó guardada.

## Eventos del servidor (sin que el usuario los pida)

`Cliente` debe tener un atributo `cola` (`queue.Queue`). El hilo que escucha al servidor pone ahí
diccionarios y la GUI los revisa cada 200 ms con `after()`:

- `{"tipo": "chat", "emisor", "receptor", "texto", "fecha"}` — mensaje nuevo (el servidor no debe reenviárselo a quien lo envió).
- `{"tipo": "en_linea", "usuario", "en_linea": True/False}` — un amigo se conectó o desconectó.
- `{"tipo": "solicitud", "usuario"}` — llegó una solicitud de amistad.
- `{"tipo": "desconectado", "mensaje"}` — se perdió la conexión; la GUI vuelve a la pantalla de conexión.
