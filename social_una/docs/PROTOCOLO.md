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
| `sugerencias` | usuario | lista de usuarios sugeridos | Sugerencias de amigos de amigos |

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