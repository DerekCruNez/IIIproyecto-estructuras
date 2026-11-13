"""Imágenes con Pillow: miniaturas para publicaciones y avatares redondos."""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageTk

_cache = {}
_COLORES = ["#0f766e", "#b45309", "#be123c", "#6d28d9", "#0369a1", "#4d7c0f", "#c2410c", "#a21caf"]


def miniatura(ruta, caja=(520, 340)):
    """PhotoImage reducida para caber en `caja`, o None si no se puede abrir."""
    if not ruta or not os.path.isfile(ruta):
        return None
    clave = ("mini", ruta, caja, os.path.getmtime(ruta))
    if clave not in _cache:
        try:
            with Image.open(ruta) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img.thumbnail(caja)
                _cache[clave] = ImageTk.PhotoImage(img)
        except Exception:
            return None
    return _cache[clave]


def _fuente(tam):
    for nombre in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except Exception:
        return ImageFont.load_default()


def _iniciales(nombre):
    partes = [p for p in (nombre or "").replace("#", "# ").split() if p]
    if not partes:
        return "?"
    if partes[0] == "#":
        return "#"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[1][0]).upper()


def avatar(nombre, usuario, ruta=None, lado=40):
    """Avatar circular: la foto si existe; si no, las iniciales sobre un color fijo por usuario."""
    mtime = os.path.getmtime(ruta) if ruta and os.path.isfile(ruta) else 0
    clave = ("avatar", nombre, usuario, ruta, lado, mtime)
    if clave in _cache:
        return _cache[clave]
    grande = lado * 4  # se dibuja grande y se reduce: bordes suaves
    if mtime:
        try:
            with Image.open(ruta) as img:
                base = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (grande, grande))
        except Exception:
            base = None
    else:
        base = None
    if base is None:
        color = _COLORES[sum(ord(c) for c in (usuario or nombre or "?")) % len(_COLORES)]
        base = Image.new("RGB", (grande, grande), color)
        d = ImageDraw.Draw(base)
        d.text((grande / 2, grande / 2), _iniciales(nombre), fill="white",
               font=_fuente(int(grande * 0.4)), anchor="mm")
    mascara = Image.new("L", (grande, grande), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, grande - 1, grande - 1), fill=255)
    salida = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    salida.paste(base, (0, 0), mascara)
    _cache[clave] = ImageTk.PhotoImage(salida.resize((lado, lado), Image.LANCZOS))
    return _cache[clave]


# ------------------------------------------------------------------ marca
def _hex(color, alpha=255):
    color = color.lstrip("#")
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), alpha)


def logo(lado=64):
    """Logo de Social UNA: tres nodos conectados (un grafo de amistades) sobre un cuadro redondeado."""
    clave = ("logo", lado)
    if clave in _cache:
        return _cache[clave]
    g = lado * 4
    # fondo con degradado vertical verde azulado
    degradado = Image.new("RGBA", (g, g))
    d = ImageDraw.Draw(degradado)
    arriba, abajo = _hex("#14a39a"), _hex("#0a4f55")
    for y in range(g):
        t = y / (g - 1)
        d.line([(0, y), (g, y)], fill=tuple(int(arriba[i] + (abajo[i] - arriba[i]) * t) for i in range(3)) + (255,))
    mascara = Image.new("L", (g, g), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, g - 1, g - 1), radius=int(g * 0.26), fill=255)
    img = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    img.paste(degradado, (0, 0), mascara)

    d = ImageDraw.Draw(img)
    A, B, C = (0.29 * g, 0.30 * g), (0.72 * g, 0.28 * g), (0.52 * g, 0.74 * g)
    grosor = int(g * 0.045)
    for p, q in ((A, B), (A, C), (B, C)):
        d.line([p, q], fill=(255, 255, 255, 235), width=grosor)
    for (x, y), r, color in ((A, 0.095, "#ffffff"), (B, 0.095, "#ffffff"), (C, 0.125, "#f5a524")):
        r *= g
        d.ellipse((x - r, y - r, x + r, y + r), fill=_hex(color))
    _cache[clave] = ImageTk.PhotoImage(img.resize((lado, lado), Image.LANCZOS))
    return _cache[clave]


def constelacion(ancho=420, alto=1100):
    """Fondo decorativo del panel de marca: red de nodos conectados sobre verde azulado."""
    clave = ("constelacion", ancho, alto)
    if clave in _cache:
        return _cache[clave]
    base = Image.new("RGBA", (ancho, alto))
    d = ImageDraw.Draw(base)
    arriba, abajo = _hex("#0d3a40"), _hex("#071d21")
    for y in range(alto):
        t = y / (alto - 1)
        d.line([(0, y), (ancho, y)], fill=tuple(int(arriba[i] + (abajo[i] - arriba[i]) * t) for i in range(3)) + (255,))

    # resplandores suaves
    brillo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    bd = ImageDraw.Draw(brillo)
    bd.ellipse((-140, -120, 300, 320), fill=_hex("#14b8a6", 70))
    bd.ellipse((140, alto - 360, 560, alto + 60), fill=_hex("#f5a524", 38))
    base = Image.alpha_composite(base, brillo.filter(ImageFilter.GaussianBlur(70)))

    # red de nodos (semilla fija: siempre el mismo dibujo)
    azar = random.Random(11)
    puntos = [(azar.uniform(0, ancho), azar.uniform(0, alto)) for _ in range(46)]
    red = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    rd = ImageDraw.Draw(red)
    for i, (x1, y1) in enumerate(puntos):
        for x2, y2 in puntos[i + 1:]:
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            if dist < 150:
                rd.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, int(46 * (1 - dist / 150)) + 8), width=1)
    for n, (x, y) in enumerate(puntos):
        r = azar.choice((2, 3, 3, 4))
        color = _hex("#f5a524", 150) if n % 9 == 0 else (255, 255, 255, 70)
        rd.ellipse((x - r, y - r, x + r, y + r), fill=color)
    base = Image.alpha_composite(base, red)
    _cache[clave] = ImageTk.PhotoImage(base.convert("RGB"))
    return _cache[clave]
