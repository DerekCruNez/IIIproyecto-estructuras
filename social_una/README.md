# Social UNA

Red social pequeña con arquitectura cliente-servidor por sockets TCP. El servidor
es el único dueño de los datos (JSON en disco, estructuras en memoria). Los clientes
(GUI Tkinter) no guardan nada: solo envían peticiones.

## Funcionalidades

- Registro y login de usuarios
- Perfil (foto, bio, link)
- Buscador de usuarios
- Amistades con solicitudes
- Muro cronológico (propias + de amigos, de la más reciente a la más antigua)
  con texto/imagen/link
- Likes en publicaciones
- Chat en vivo
- Sugerencias de amigos de amigos; si no hay, otros usuarios que aún no son amigos

## Requisitos

- Python 3.10+
- Pillow (para manejo de imágenes)

## Instalación

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

### Servidor

Desde la carpeta `social_una/`:

```bash
python servidor.py
```

Al arrancar muestra la IP que deben escribir los demás. Escucha en todas las
interfaces (0.0.0.0); si otra computadora no conecta, abre el puerto 5000 en el
firewall de Windows. Para datos de prueba: `python generar_datos.py`.

### Cliente

Desde la carpeta `social_una/`:

```bash
python main.py          # se conecta a un servidor
python main.py --demo   # modo demostración, sin servidor
```

### Pruebas

```bash
python -m unittest tests.test_servidor tests.test_cliente
```

## Estructura de carpetas

```
social_una/
├── README.md
├── requirements.txt
├── .gitignore
├── servidor.py          # Derek - Servidor TCP
├── cliente.py           # Daniel - Cliente TCP
├── protocolo.py         # Compartido - Protocolo de mensajes (implementado completo)
├── modelos.py           # Angel - Modelos de datos
├── almacen.py           # Angel - Almacenamiento en memoria y disco
├── generar_datos.py     # Angel - Generador de datos de prueba
├── main.py              # Brayan - Punto de entrada del cliente
├── gui/                 # Brayan - interfaz (ver docs/README_GUI.md)
│   ├── app.py           # ventana raíz, navegación, tema y eventos
│   ├── vistas_acceso.py # conexión, login y registro
│   ├── principal.py     # menú lateral con contadores de novedades
│   ├── muro.py          # publicaciones, me gusta animado y reacciones
│   ├── chat.py          # chat estilo Discord: GIF, stickers, voz, archivos, encuestas
│   ├── juegos.py        # Serpiente, Buscaminas y 3 en raya con leaderboard y medallas
│   ├── emojis.py        # emojis a color (Pillow), burbujas y stickers
│   ├── selectores.py    # ventanitas de emojis, stickers y GIFs
│   ├── sonidos.py       # tonos de notificación, preferencias y grabación de voz
│   ├── amigos.py, buscar.py
│   ├── perfil.py        # perfil estilo Discord: banner, foto/GIF, bio
│   ├── apariencia.py    # modo claro/oscuro y paletas de color
│   ├── estilo.py        # temas, paletas, fuentes, toasts
│   ├── widgets.py, imagenes.py, textos.py
│   └── cliente_demo.py  # cliente falso para --demo
├── tests/               # pruebas de servidor y cliente
├── datos/
│   ├── .gitkeep
│   └── imagenes/.gitkeep
└── docs/
    ├── PROTOCOLO.md
    ├── CONTRATO_FUNCIONES.md
    ├── CONTRATO_CLIENTE.md
    └── REPARTO.md
```

## Reglas de Git

- Una rama por persona.
- Merge solo cuando la funcionalidad esté probada y funcione.
- Cada quien edita solo sus archivos asignados.

## Reparto de trabajo

- **Derek**: `servidor.py`
- **Daniel**: `cliente.py`
- **Angel**: `modelos.py`, `almacen.py`, `generar_datos.py`
- **Brayan**: `main.py` y `gui/`
- **Compartido**: `protocolo.py`