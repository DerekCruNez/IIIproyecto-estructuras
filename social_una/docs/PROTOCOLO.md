# Protocolo de Comunicación - Social UNA

## Formato de mensaje

Cada mensaje se envía como: **4 bytes big-endian con el largo del payload +
JSON codificado en UTF-8**.

Límite de mensaje: 3 MB.  
Límite de imagen: 2 MB (`MAX_IMAGEN_BYTES`).

## Estructuras

### Petición (cliente → servidor)

```json
{
  "accion": "nombre_de_la_accion",
  "datos": { ... }
}
```

### Respuesta (servidor → cliente)

```json
{
  "ok": true,
  "datos": { ... },
  "error": ""
}
```

Si `ok` es falso, `datos` puede estar vacío y `error` contiene el motivo.

### Evento (servidor → cliente, sin petición previa)

```json
{
  "evento": "nombre_del_evento",
  "datos": { ... }
}
```

## Tabla de acciones

| Acción | Datos de entrada (datos) | Datos de salida (datos) | Descripción |
|--------|-------------------------|------------------------|-------------|
| `registrar` | nombre, usuario, clave | ok, mensaje | Registro de nuevo usuario |
| `login` | usuario, clave | ok, usuario, token/sesión | Inicio de sesión |
| `logout` | usuario | ok | Cierre de sesión |
| `buscar_usuarios` | texto | lista de usuarios | Buscar usuarios por nombre/usuario |
| `ver_perfil` | usuario | perfil del usuario | Obtener datos de perfil |
| `editar_perfil` | bio, foto, link | ok | Editar perfil propio |
| `enviar_solicitud` | origen, destino | ok | Enviar solicitud de amistad |
| `responder_solicitud` | destino, origen, aceptar | ok | Aceptar/rechazar solicitud |
| `listar_solicitudes` | usuario | lista de solicitudes | Listar solicitudes pendientes |
| `listar_amigos` | usuario | lista de amigos | Listar amigos de un usuario |
| `publicar` | autor, texto, imagen, link, extra | ok, id_publicacion | Crear publicación |
| `obtener_muro` | usuario | lista de publicaciones | Obtener muro cronológico |
| `dar_like` | id_publicacion, usuario | ok | Like/unlike a publicación |
| `enviar_chat` | emisor, receptor, texto | ok | Enviar mensaje de chat |
| `obtener_chat` | a, b | lista de mensajes | Obtener conversación |
| `sugerencias` | usuario | lista de usuarios sugeridos (con `en_comun`) | Sugerencias de amigos de amigos |
| `eliminar_amigo` | amigo | ok | Elimina la amistad en ambos sentidos |
| `reaccionar` | id_publicacion, emoji (😂 🔥 👏 😮 😢) | ok | Pone/quita una reacción rápida |
| `subir_imagen` | imagen (base64, PNG/JPG/GIF, ≤ 2 MB) | nombre | Sube foto de perfil o banner |
| `obtener_imagen` | nombre | nombre, imagen (base64) | Descarga una imagen o archivo guardado |
| `editar_publicacion` | id_publicacion, texto | publicacion | Solo el autor |
| `eliminar_publicacion` | id_publicacion | ok | Solo el autor |
| `poner_apodo` | amigo, apodo (≤ 32, vacío = quitar) | ok | Apodo que solo tú ves |
| `actualizar_mensaje` | con, id, accion (editar/eliminar/reaccionar/votar), valor | chat (mensaje) | Cambia un mensaje del chat |

Chat (nov 2026): `enviar_chat` acepta `tipo` (texto, imagen, sticker, archivo, audio,
encuesta), `adjunto` (base64 ≤ 2 MB), `nombre_archivo`, `responde_a` (id) y `encuesta`
(`{pregunta, opciones: [2 a 4 textos]}`). Responde con `chat` (el mensaje guardado).
No se aceptan ejecutables (.exe, .bat, .ps1, .js, ...). Solo el autor puede editar o
eliminar. Cada mensaje tiene `id`, `editado`, `reacciones` y `responde_a`.
Evento nuevo: `mensaje_actualizado` con el mensaje completo.

Muro: `publicar` acepta además `archivo` (base64 ≤ 2 MB) y `nombre_archivo`; las
publicaciones traen `archivo`, `nombre_archivo` y `editado`. `listar_amigos` trae `apodo`.

Cambios (nov 2026):
- `registrar` usa el `id` que envía el cliente (si viene vacío, genera uno). El ID y el usuario son únicos.
- `listar_amigos` / `listar_solicitudes` devuelven `[{usuario, nombre, foto, en_linea}]`.
- `buscar_usuarios`, con sesión iniciada, agrega `amigo` y `pendiente` a cada resultado.
- `editar_perfil` solo cambia los campos que llegan: bio (≤ 190), foto, link, banner, color_perfil (#RRGGBB), tema (claro/oscuro), paleta.
- `publicar`: el texto es opcional si hay imagen o link. Las publicaciones traen `reacciones` ({emoji: [usuarios]}).
- `enviar_chat` / `obtener_chat` aceptan `"#general"` (sala general, para todos los conectados).
- Si dos usuarios se envían solicitud mutuamente, quedan como amigos.
- El servidor escucha en `0.0.0.0` (acepta otras computadoras) y muestra su IP al arrancar.

## Ejemplos

### Petición de registro

```json
{
  "accion": "registrar",
  "datos": {
    "nombre": "Angel Rodriguez",
    "usuario": "angel123",
    "clave": "miclave123"
  }
}
```

### Respuesta de registro (éxito)

```json
{
  "ok": true,
  "datos": {
    "mensaje": "Usuario registrado exitosamente"
  },
  "error": ""
}
```

### Respuesta de registro (error)

```json
{
  "ok": false,
  "datos": {},
  "error": "El usuario ya existe"
}
```

### Evento de nueva solicitud de amistad

```json
{
  "evento": "nueva_solicitud",
  "datos": {
    "origen": "juan456",
    "destino": "angel123"
  }
}
```

### Otros eventos

- `en_linea`: `{"usuario", "en_linea": true/false}` — un amigo se conectó o desconectó.
- `nueva_publicacion`: `{"autor"}` — un amigo publicó.

### Evento de nuevo mensaje de chat

```json
{
  "evento": "nuevo_mensaje",
  "datos": {
    "emisor": "juan456",
    "receptor": "angel123",
    "texto": "Hola, ¿cómo estás?",
    "fecha": "2024-01-15T10:30:00"
  }
}
```

## Constantes

- `HOST_DEFECTO = "127.0.0.1"`
- `PUERTO_DEFECTO = 5000`
- `MAX_LONGITUD_MENSAJE = 3 * 1024 * 1024` (3 MB)
- `MAX_IMAGEN_BYTES = 2 * 1024 * 1024` (2 MB)

## Juegos (nov 2026)

| Acción | Datos | Respuesta |
|---|---|---|
| `enviar_puntaje` | juego (serpiente ≤ 4000, buscaminas ≤ 1000), puntos | mejor |
| `leaderboard` | juego | tabla [{usuario, nombre, foto, puntos}], jugando, duelos |
| `jugando` | juego ("" = ya no) | ok |
| `invitar_juego` | amigo (conectado) | ok |
| `responder_juego` | origen, aceptar | partida |
| `jugada` | id, casilla 0-8 | partida (el servidor valida turno y casilla) |
| `abandonar_juego` | id | ok (gana el rival) |

Eventos: `invitacion_juego` {origen, juego}, `juego_rechazado` {usuario}, `partida` {id, x, o,
tablero, turno, ganador, linea}. 3 en raya: ganar 3 puntos, empate 1 (los suma el servidor).
Puntajes en `datos/puntajes.json`. Medallas por puesto: rubí, diamante, esmeralda, platino, oro, bronce.
