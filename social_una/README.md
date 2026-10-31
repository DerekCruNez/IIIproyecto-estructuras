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
- Sugerencias de amigos de amigos

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

### Cliente

Desde la carpeta `social_una/`:

```bash
python main.py
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
├── gui/
│   ├── __init__.py
│   ├── estilo.py
│   ├── ventana_conexion.py
│   ├── ventana_login.py
│   ├── ventana_registro.py
│   ├── ventana_principal.py
│   ├── pestana_muro.py
│   ├── pestana_amigos.py
│   ├── pestana_buscar.py
│   ├── pestana_chat.py
│   └── pestana_perfil.py
├── datos/
│   ├── .gitkeep
│   └── imagenes/.gitkeep
└── docs/
    ├── PROTOCOLO.md
    ├── CONTRATO_FUNCIONES.md
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