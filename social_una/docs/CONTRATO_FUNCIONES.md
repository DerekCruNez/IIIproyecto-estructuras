# Contrato de Funciones - Social UNA

## Flujo de llamadas

```
GUI (Brayan) → cliente.py (Daniel) → protocolo.py (compartido) →
servidor.py (Derek) → almacen.py (Angel) → modelos.py (Angel)
```

## Firmas de funciones

### protocolo.py (implementado completo)

```python
def enviar_mensaje(sock: socket.socket, mensaje: dict) -> None
def recibir_mensaje(sock: socket.socket) -> dict | None
def codificar_imagen(ruta: str) -> str
def guardar_imagen(base64_str: str, carpeta: str) -> str
```

Constantes: `HOST_DEFECTO`, `PUERTO_DEFECTO = 5000`, `MAX_IMAGEN_BYTES`.

### modelos.py (stubs con serialización implementada)

```python
class Usuario:
    def __init__(self, id, nombre, usuario, clave_hash, bio="", foto="", link="")
    def a_dict(self) -> dict
    @classmethod
    def desde_dict(cls, datos: dict) -> "Usuario"

class Publicacion:
    def __init__(self, id, autor, texto, imagen="", link="", fecha="",
                 likes=None, extra="")
    def a_dict(self) -> dict
    @classmethod
    def desde_dict(cls, datos: dict) -> "Publicacion"

class Mensaje:
    def __init__(self, emisor, receptor, texto, fecha="")
    def a_dict(self) -> dict
    @classmethod
    def desde_dict(cls, datos: dict) -> "Mensaje"

### almacen.py (clase Almacen, stubs)

```python
class Almacen:
    def __init__(self, carpeta_datos: str = "datos")
    def cargar_todo(self) -> None
    def guardar_todo(self) -> None
    @staticmethod
    def hash_clave(clave: str) -> str
    def registrar_usuario(self, id, nombre, usuario, clave) -> (bool, Any)
    def validar_login(self, usuario, clave) -> (bool, Any)
    def obtener_perfil(self, usuario) -> (bool, Any)
    def editar_perfil(self, usuario, bio, foto, link) -> (bool, Any)
    def buscar_usuarios(self, texto) -> (bool, Any)
    def enviar_solicitud(self, origen, destino) -> (bool, Any)
    def responder_solicitud(self, destino, origen, aceptar) -> (bool, Any)
    def listar_solicitudes(self, usuario) -> (bool, Any)
    def listar_amigos(self, usuario) -> (bool, Any)
    def eliminar_amigo(self, a, b) -> (bool, Any)
    def crear_publicacion(self, autor, texto, imagen, link, extra) -> (bool, Any)
    def obtener_muro(self, usuario) -> (bool, Any)
    def dar_like(self, id_publicacion, usuario) -> (bool, Any)
    def guardar_chat(self, emisor, receptor, texto) -> (bool, Any)
    def obtener_chat(self, a, b) -> (bool, Any)
    def sugerir_amigos(self, usuario) -> (bool, Any)
    def amigos_en_comun(self, a, b) -> (bool, Any)
```

Todos los métodos de `Almacen` retornan `(ok: bool, resultado_o_error)`.

Archivos JSON: `datos/usuarios.json`, `datos/amistades.json`,
`datos/solicitudes.json`, `datos/publicaciones.json`, `datos/chats.json`.

### servidor.py (Derek, stubs)

```python
class Servidor:
    def __init__(self, almacen: Almacen)
    def iniciar(self, host=HOST_DEFECTO, puerto=PUERTO_DEFECTO) -> None
    def aceptar_clientes(self) -> None
    def atender_cliente(self, sock, addr) -> None
    def despachar(self, peticion: dict, sesion: dict) -> dict
    def enviar_a_usuario(self, usuario: str, mensaje: dict) -> bool
    def cerrar_cliente(self, sock, usuario=None) -> None

    # Acciones (cada una es un stub):
    def accion_registrar(self, datos, sesion) -> dict
    def accion_login(self, datos, sesion) -> dict
    def accion_logout(self, datos, sesion) -> dict
    def accion_buscar_usuarios(self, datos, sesion) -> dict
    def accion_ver_perfil(self, datos, sesion) -> dict
    def accion_editar_perfil(self, datos, sesion) -> dict
    def accion_enviar_solicitud(self, datos, sesion) -> dict
    def accion_responder_solicitud(self, datos, sesion) -> dict
    def accion_listar_solicitudes(self, datos, sesion) -> dict
    def accion_listar_amigos(self, datos, sesion) -> dict
    def accion_publicar(self, datos, sesion) -> dict
    def accion_obtener_muro(self, datos, sesion) -> dict
    def accion_dar_like(self, datos, sesion) -> dict
    def accion_enviar_chat(self, datos, sesion) -> dict
    def accion_obtener_chat(self, datos, sesion) -> dict
    def accion_sugerencias(self, datos, sesion) -> dict
```

Atributo: `en_linea` (dict usuario → socket).

### cliente.py (Daniel, stubs)

```python
class ClienteSocial:
    def __init__(self)
    def conectar(self, host=HOST_DEFECTO, puerto=PUERTO_DEFECTO) -> bool
    def desconectar(self) -> None
    def enviar_peticion(self, accion: str, datos: dict) -> dict | None
    # cola_eventos: queue.Queue pública con eventos del servidor

    def registrar(self, nombre, usuario, clave) -> dict | None
    def login(self, usuario, clave) -> dict | None
    def logout(self) -> dict | None
    def buscar_usuarios(self, texto) -> dict | None
    def ver_perfil(self, usuario) -> dict | None
    def editar_perfil(self, bio, foto, link) -> dict | None
    def enviar_solicitud(self, origen, destino) -> dict | None
    def responder_solicitud(self, destino, origen, aceptar) -> dict | None
    def listar_amigos(self, usuario) -> dict | None
    def publicar(self, texto, ruta_imagen, link) -> dict | None
    def obtener_muro(self, usuario) -> dict | None
    def dar_like(self, id_publicacion, usuario) -> dict | None
    def enviar_chat(self, emisor, receptor, texto) -> dict | None
    def obtener_chat(self, a, b) -> dict | None
    def sugerencias(self, usuario) -> dict | None
```

### GUI (Brayan, stubs)

Cada ventana/pestaña recibe `cliente` y `root` en el constructor y tiene
`construir_widgets()`. Nunca tocan sockets; solo llaman a métodos de
`ClienteSocial`.

- `VentanaConexion(root, cliente)`
- `VentanaLogin(root, cliente)`
- `VentanaRegistro(root, cliente)`
- `VentanaPrincipal(root, cliente)` — Notebook con 5 pestañas +
  `revisar_eventos()` con `root.after(100, ...)`
- `PestanaMuro(notebook, cliente)`
- `PestanaAmigos(notebook, cliente)`
- `PestanaBuscar(notebook, cliente)`
- `PestanaChat(notebook, cliente)`
- `PestanaPerfil(notebook, cliente)`

### main.py (Brayan)

```python
def main() -> None
```

Crea el root, aplica estilo y abre la ventana de conexión.

### generar_datos.py (Angel, stub)

```python
def main() -> None
```

Crea al menos 3 usuarios de prueba con publicaciones y amistades usando `Almacen`.
```