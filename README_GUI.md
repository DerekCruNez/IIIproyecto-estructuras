# Interfaz gráfica de Social UNA (Brayan)

    pip install pillow
    python main.py          # usa cliente.py si existe; si no, modo demostración
    python main.py --demo   # fuerza el modo demostración (usuarios ana, luis, maria, pedro; clave 1234)

Ejecutar siempre `main.py` desde la carpeta raíz del proyecto (no los archivos de `gui/`).

Estructura: `main.py` + carpeta `gui/`:
- `app.py`: ventana raíz y navegación entre pantallas.
- `vistas_acceso.py`: conexión, login y registro (con botón Volver).
- `principal.py`: panel lateral, barra superior con botón **Volver** (historial de secciones).
- `muro.py`, `amigos.py`, `buscar.py`, `chat.py`, `perfil.py`: las secciones.
- `textos.py`: textos principales (lema, títulos, ventajas); edítalo para cambiar el lenguaje.
- `estilo.py`: paleta "Bosque y ámbar", fuentes y alertas (estilo único). `widgets.py`: botón, campo, tarjeta, avatar.
- `imagenes.py`: logo, fondo de la marca, miniaturas y avatares con Pillow. `cliente_demo.py`: cliente de prueba.

El contrato con `cliente.py` está en `CONTRATO_CLIENTE.md`.
