"""Emojis a color, burbujas de chat y stickers dibujados con Pillow.

Tkinter dibuja los emojis con la fuente del sistema en blanco y negro. Pillow sí
puede usar los colores de la fuente "Segoe UI Emoji" (embedded_color=True), así
que los emojis y los mensajes que los contienen se muestran como imágenes.
"""
import os
import re

from PIL import Image, ImageDraw, ImageFont, ImageTk


CARPETA_LOCAL = os.path.join(os.path.expanduser("~"), ".social_una")
CARPETA_STICKERS = os.path.join(CARPETA_LOCAL, "stickers")

# Un emoji "completo": banderas, o un símbolo con variación, tono de piel y uniones (ZWJ).
_EMOJI = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2}"
    "|[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿←-⇿〰〽©®]"
    "️?[\U0001F3FB-\U0001F3FF]?"
    "(?:‍[\U0001F000-\U0001FAFF☀-➿]️?[\U0001F3FB-\U0001F3FF]?)*)")

CATEGORIAS = {
    "😀": ("Caras", "😀😃😄😁😆😅😂🤣😊😇🙂😉😍🥰😘😋😛😜🤪😎🤩🥳😏😒😞😔😟🙁😣😖😫😩🥺😢😭"
                   "😤😠😡🤯😳🥵🥶😱😨😰🤗🤔🤭🤫😶😐😑😬🙄😯😮😲🥱😴🤤😵🤐🥴🤢🤮🤧😷🤠🤑😈💀👻👽🤖💩🗿"),
    "👍": ("Gestos", "👍👎👌✌️🤞🤟🤘🤙👈👉👆👇☝️✋🤚🖐️🖖👋🤝👏🙌👐🤲🙏✍️💪🧠👀👅👄"),
    "❤️": ("Corazones", "❤️🧡💛💚💙💜🖤🤍🤎💔❣️💕💞💓💗💖💘💝💯💢💥💫💦💨🔥✨⭐🌟⚡🎉🎊"),
    "🐶": ("Animales", "🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐸🐵🐔🐧🐦🐤🦆🦅🦉🐺🐴🦄🐝🐛🦋🐌🐞🐢🐍🦖🐙🦀🐬🐳🦈"),
    "🍕": ("Comida", "🍎🍐🍊🍋🍌🍉🍇🍓🍒🍑🥭🍍🥥🥝🍅🥑🌽🥕🍞🧀🍳🥓🍔🍟🍕🌭🌮🌯🍜🍣🍩🍪🎂🍰🍫🍿☕🍺🥤"),
    "⚽": ("Cosas", "⚽🏀🏈⚾🎾🏐🎮🎧🎵🎶🎸🎹🎤🎬📷💻📱⌚💡📚✏️📝📌📎🔒🔑🎁🏆🥇🚀✈️🚗🏠🌈☀️🌙⛄🌊"),
}
REACCIONES_RAPIDAS = ("😭", "❤️", "🗿")   # las de la barra al pasar el mouse
STICKERS_BASE = "😂🥺😎🤯😡🥳😴🤔👍👏🙏💀🔥❤️🎉🗿🐶🐱🍕☕"

_cache = {}


def separar(texto):
    """Lista de emojis que hay en el texto."""
    return _EMOJI.findall(texto)


def _fuente_emoji(tam):
    clave = ("fe", tam)
    if clave not in _cache:
        try:
            _cache[clave] = ImageFont.truetype("seguiemj.ttf", tam)
        except OSError:
            _cache[clave] = None
    return _cache[clave]


def _fuente_texto(tam, negrita=False):
    clave = ("ft", tam, negrita)
    if clave not in _cache:
        nombres = ("segoeuib.ttf", "arialbd.ttf") if negrita else ("segoeui.ttf", "arial.ttf")
        for nombre in nombres + ("DejaVuSans.ttf",):
            try:
                _cache[clave] = ImageFont.truetype(nombre, tam)
                break
            except OSError:
                continue
        else:
            _cache[clave] = ImageFont.load_default()
    return _cache[clave]


def imagen_emoji(emoji, tam=64):
    """Emoji a color como imagen RGBA cuadrada de `tam` px (Pillow)."""
    clave = ("pil", emoji, tam)
    if clave in _cache:
        return _cache[clave]
    grande = 109 if tam > 40 else 72      # se dibuja a un tamaño nativo de la fuente
    lienzo = Image.new("RGBA", (int(grande * 1.6), int(grande * 1.6)), (0, 0, 0, 0))
    fuente = _fuente_emoji(grande)
    d = ImageDraw.Draw(lienzo)
    if fuente is not None:
        # sin el motor de texto "raqm", el selector de variación (FE0F) se mide como
        # un carácter ancho y descuadra el dibujo; el emoji se ve igual sin él
        d.text((lienzo.width // 2, lienzo.height // 2), emoji.replace("️", ""),
               font=fuente, embedded_color=True, anchor="mm")
    caja = lienzo.getbbox()
    if caja:
        lienzo = lienzo.crop(caja)
    lado = max(lienzo.size) if caja else grande
    cuadro = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    cuadro.paste(lienzo, ((lado - lienzo.width) // 2, (lado - lienzo.height) // 2))
    _cache[clave] = cuadro.resize((tam, tam), Image.LANCZOS)
    return _cache[clave]


def foto_emoji(emoji, tam=24):
    """Emoji a color como PhotoImage para Tkinter."""
    clave = ("tk", emoji, tam)
    if clave not in _cache:
        _cache[clave] = ImageTk.PhotoImage(imagen_emoji(emoji, tam))
    return _cache[clave]


def _partes(texto):
    """Divide en [(es_emoji, trozo)] respetando el orden."""
    partes, pos = [], 0
    for m in _EMOJI.finditer(texto):
        if m.start() > pos:
            partes.append((False, texto[pos:m.start()]))
        partes.append((True, m.group()))
        pos = m.end()
    if pos < len(texto):
        partes.append((False, texto[pos:]))
    return partes


def solo_emojis(texto):
    """True si el mensaje es de 1 a 3 emojis sin texto (se muestran grandes)."""
    sin_espacios = texto.replace(" ", "")
    emojis = separar(sin_espacios)
    return 0 < len(emojis) <= 3 and "".join(emojis) == sin_espacios


def burbuja(texto, fondo, color, ancho_max=380, tam=14, radio=14, relleno=(14, 9)):
    """Mensaje como imagen: texto con emojis a color, ajuste de línea y fondo redondeado.

    fondo=None dibuja sin burbuja (para mensajes de solo emojis).
    """
    clave = ("burbuja", texto, fondo, color, ancho_max, tam)
    if clave in _cache:
        return _cache[clave]
    f = _fuente_texto(tam)
    alto_linea = int(tam * 1.45)
    tam_emoji = int(tam * 1.3)
    ancho_util = ancho_max - 2 * relleno[0]

    def ancho(es_emoji, trozo):
        return tam_emoji + 2 if es_emoji else f.getlength(trozo)

    # 1) cortar en "palabras" (con su espacio) y ubicar cada trozo en líneas
    lineas = [[]]
    x = 0
    for linea_texto in texto.split("\n"):
        if lineas[-1]:
            lineas.append([])
            x = 0
        for palabra in re.findall(r"\S+\s*|\s+", linea_texto):
            trozos = _partes(palabra)
            w = sum(ancho(e, t) for e, t in trozos)
            if x + w > ancho_util and x > 0:
                lineas.append([])
                x = 0
            for e, t in trozos:
                if not e:      # palabra más larga que la línea: se corta por letras
                    while f.getlength(t) > ancho_util - x and len(t) > 1:
                        corte = len(t)
                        while corte > 1 and f.getlength(t[:corte]) > ancho_util - x:
                            corte -= 1
                        lineas[-1].append((False, t[:corte]))
                        lineas.append([])
                        x, t = 0, t[corte:]
                lineas[-1].append((e, t))
                x += ancho(e, t)
    anchos = [sum(ancho(e, t) for e, t in ln) for ln in lineas]
    w = int(max(anchos or [0])) + 2 * relleno[0]
    h = alto_linea * len(lineas) + 2 * relleno[1]

    # 2) dibujar
    escala = 2   # se dibuja al doble y se reduce: bordes suaves
    img = Image.new("RGBA", (w * escala, h * escala), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if fondo:
        d.rounded_rectangle((0, 0, w * escala - 1, h * escala - 1), radius=radio * escala, fill=fondo)
    f2 = _fuente_texto(tam * escala)
    y = relleno[1] * escala
    for ln in lineas:
        x = relleno[0] * escala
        for e, t in ln:
            if e:
                em = imagen_emoji(t, tam_emoji * escala)
                img.alpha_composite(em, (int(x), int(y + (alto_linea * escala - em.height) / 2)))
                x += (tam_emoji + 2) * escala
            else:
                d.text((x, y + alto_linea * escala / 2), t, font=f2, fill=color, anchor="lm")
                x += f.getlength(t) * escala
        y += alto_linea * escala
    _cache[clave] = ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS))
    return _cache[clave]


def emojis_grandes(texto, tam=44):
    """Mensaje de solo emojis: emojis grandes sin burbuja."""
    clave = ("grandes", texto, tam)
    if clave not in _cache:
        lista = separar(texto)
        img = Image.new("RGBA", (len(lista) * (tam + 6), tam + 4), (0, 0, 0, 0))
        for i, e in enumerate(lista):
            img.alpha_composite(imagen_emoji(e, tam), (i * (tam + 6), 2))
        _cache[clave] = ImageTk.PhotoImage(img)
    return _cache[clave]


def latido(etiqueta, emoji, tamanos=(22, 28, 24, 20)):
    """Animación: el emoji de una etiqueta crece y vuelve a su tamaño."""
    def paso(i):
        if i < len(tamanos) and etiqueta.winfo_exists():
            etiqueta.config(image=foto_emoji(emoji, tamanos[i]))
            etiqueta.after(45, lambda: paso(i + 1))
    paso(0)


# ------------------------------------------------------------------ stickers
def sticker_de_emoji(emoji):
    """Ruta a un PNG de sticker hecho con un emoji (se crea una sola vez)."""
    os.makedirs(CARPETA_STICKERS, exist_ok=True)
    nombre = "emoji2_" + "_".join(f"{ord(c):x}" for c in emoji) + ".png"
    ruta = os.path.join(CARPETA_STICKERS, "base", nombre)
    if not os.path.isfile(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        imagen_emoji(emoji, 150).save(ruta)
    return ruta


def crear_sticker(ruta_imagen):
    """Convierte una imagen en sticker (recorte con esquinas redondas) y la guarda en
    la carpeta de stickers propios. Devuelve la ruta del PNG."""
    from PIL import ImageOps
    import uuid
    with Image.open(ruta_imagen) as original:
        img = ImageOps.exif_transpose(original).convert("RGBA")
    img.thumbnail((170, 170))
    if img.getchannel("A").getextrema()[0] == 255:   # sin transparencia: esquinas redondas
        mascara = Image.new("L", img.size, 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, img.width - 1, img.height - 1),
                                                  radius=28, fill=255)
        img.putalpha(mascara)
    os.makedirs(CARPETA_STICKERS, exist_ok=True)
    ruta = os.path.join(CARPETA_STICKERS, f"propio_{uuid.uuid4().hex[:10]}.png")
    img.save(ruta)
    return ruta


def stickers_propios():
    if not os.path.isdir(CARPETA_STICKERS):
        return []
    return sorted((os.path.join(CARPETA_STICKERS, n) for n in os.listdir(CARPETA_STICKERS)
                   if n.endswith(".png")), key=os.path.getmtime, reverse=True)


if __name__ == "__main__":
    assert separar("hola 😂 y ❤️ 👍🏽") == ["😂", "❤️", "👍🏽"]
    assert solo_emojis("😂😂") and not solo_emojis("hola 😂") and not solo_emojis("😂" * 4)
    assert [p[0] for p in _partes("a😂b")] == [False, True, False]
    assert imagen_emoji("🔥", 32).getbbox() is not None, "la fuente de emojis no dibujó nada"
    caja = imagen_emoji("❤️", 64).getbbox()
    assert caja[0] < 8 and caja[2] > 56, f"corazón recortado: {caja}"
    print("emojis OK")
