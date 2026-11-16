"""Sonidos de notificación, preferencias locales y mensajes de voz.

Los tonos se generan con matemáticas (ondas seno con envolvente) la primera vez,
así no hay archivos de audio con licencia. También se puede elegir un .wav propio.
Reproducir y grabar usa lo que trae Windows (winsound y la API MCI de winmm),
sin instalar nada.
"""
import json
import math
import os
import struct
import sys
import threading
import wave
from array import array

CARPETA = os.path.join(os.path.expanduser("~"), ".social_una")
ARCHIVO_PREFS = os.path.join(CARPETA, "preferencias.json")
FRECUENCIA = 22050
MAX_SEGUNDOS_VOZ = 60          # con 16 kHz mono 16 bits: ~1.9 MB, bajo el límite de 2 MB
MAX_SONIDO_PROPIO = 1024 * 1024

ES_WINDOWS = sys.platform == "win32"
if ES_WINDOWS:
    import ctypes
    import winsound

# sounddevice es opcional: sin él se usan el micrófono y los altavoces predeterminados.
ERROR_AUDIO = ""     # por qué no se pudo cargar sounddevice (se muestra en Personalizar)
try:
    import sounddevice as sd
    HAY_SELECCION_AUDIO = True
except Exception as _exc:       # no instalado, o sin PortAudio
    sd = None
    HAY_SELECCION_AUDIO = False
    ERROR_AUDIO = f"{type(_exc).__name__}: {_exc}"


# ------------------------------------------------------------- preferencias
_PREFS_DEFECTO = {"sonido": True, "tono": "Campanita", "tono_propio": "", "giphy_key": "",
                  "audio_entrada": "", "audio_salida": ""}   # "" = predeterminado del sistema


def cargar_prefs():
    try:
        with open(ARCHIVO_PREFS, encoding="utf-8") as f:
            prefs = {**_PREFS_DEFECTO, **json.load(f)}
    except (OSError, ValueError):
        prefs = dict(_PREFS_DEFECTO)
    aplicar_audio(prefs)
    return prefs


def guardar_prefs(prefs):
    try:
        os.makedirs(CARPETA, exist_ok=True)
        with open(ARCHIVO_PREFS, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except OSError:
        pass   # sin preferencias guardadas la app sigue funcionando


# --------------------------------------------------------------- síntesis
def _nota(frec, dur, vol=0.5, ataque=0.005, caida=6.0, armonicos=(1.0, 0.3, 0.12)):
    """Muestras de una nota tipo campana: seno + armónicos con caída exponencial."""
    n = int(FRECUENCIA * dur)
    muestras = []
    for i in range(n):
        t = i / FRECUENCIA
        env = min(1.0, t / ataque) * math.exp(-caida * t)
        v = sum(a * math.sin(2 * math.pi * frec * (k + 1) * t) for k, a in enumerate(armonicos))
        muestras.append(vol * env * v / sum(armonicos))
    return muestras


def _barrido(f0, f1, dur, vol=0.5, caida=12.0):
    """Tono que cambia de frecuencia (para 'pop' y 'burbuja')."""
    n = int(FRECUENCIA * dur)
    fase, muestras = 0.0, []
    for i in range(n):
        t = i / FRECUENCIA
        frec = f0 + (f1 - f0) * (i / n)
        fase += 2 * math.pi * frec / FRECUENCIA
        muestras.append(vol * min(1.0, t / 0.003) * math.exp(-caida * t) * math.sin(fase))
    return muestras


def _mezclar_en(base, otra, desde):
    inicio = int(desde * FRECUENCIA)
    base.extend([0.0] * max(0, inicio + len(otra) - len(base)))
    for i, v in enumerate(otra):
        base[inicio + i] += v
    return base


TONOS = {
    "Campanita": lambda: _mezclar_en(_nota(1318.5, 0.6), _nota(1760, 0.7), 0.11),
    "Pop": lambda: _barrido(900, 260, 0.12, 0.6, 25),
    "Burbuja": lambda: _mezclar_en(_barrido(380, 1150, 0.16, 0.5, 14),
                                   _barrido(520, 1500, 0.12, 0.35, 18), 0.09),
    "Acorde": lambda: _mezclar_en(_mezclar_en(_nota(523.3, 0.8, 0.4, caida=4),
                                              _nota(659.3, 0.7, 0.4, caida=4), 0.07),
                                  _nota(784, 0.7, 0.4, caida=4), 0.14),
    "Gota": lambda: _barrido(1600, 700, 0.09, 0.55, 30),
}


def _escribir_wav(ruta, muestras):
    pico = max(1e-6, max(abs(v) for v in muestras))
    escala = 0.85 / pico if pico > 0.85 else 1.0
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes(b"".join(struct.pack("<h", int(v * escala * 32767)) for v in muestras))


def ruta_tono(nombre):
    """Ruta del .wav de un tono incluido (se genera la primera vez)."""
    os.makedirs(os.path.join(CARPETA, "tonos"), exist_ok=True)
    ruta = os.path.join(CARPETA, "tonos", f"{nombre.lower()}.wav")
    if not os.path.isfile(ruta):
        _escribir_wav(ruta, TONOS[nombre]())
    return ruta


# --------------------------------------------------- dispositivos de audio
_AUDIO = {"entrada": "", "salida": ""}      # nombres elegidos ("" = predeterminado)
_NO_LISTAR = ("asignador de sonido", "sound mapper", "controlador primario")


def aplicar_audio(prefs):
    """Toma de las preferencias el micrófono y los altavoces elegidos."""
    _AUDIO["entrada"] = prefs.get("audio_entrada") or ""
    _AUDIO["salida"] = prefs.get("audio_salida") or ""


def recargar_audio():
    """Vuelve a intentar cargar sounddevice (p. ej. justo después de instalarlo)."""
    global sd, HAY_SELECCION_AUDIO, ERROR_AUDIO
    import importlib
    try:
        importlib.invalidate_caches()
        sd = importlib.import_module("sounddevice")
        HAY_SELECCION_AUDIO, ERROR_AUDIO = True, ""
    except Exception as exc:
        HAY_SELECCION_AUDIO = False
        ERROR_AUDIO = f"{type(exc).__name__}: {exc}"
    return HAY_SELECCION_AUDIO


def dispositivos(tipo):
    """Lista de nombres de dispositivos. tipo: 'entrada' (micrófonos) o 'salida' (altavoces)."""
    if not HAY_SELECCION_AUDIO:
        return []
    campo = "max_input_channels" if tipo == "entrada" else "max_output_channels"

    def recoger(solo_api):
        nombres = []
        for d in sd.query_devices():
            nombre = d["name"].strip()
            if ((solo_api is None or d["hostapi"] == solo_api) and d[campo] > 0
                    and nombre not in nombres and not nombre.lower().startswith(_NO_LISTAR)):
                nombres.append(nombre)
        return nombres
    try:
        # primero solo la API principal (así no salen repetidos); si no hay nada, todas
        return recoger(sd.default.hostapi) or recoger(None)
    except Exception:
        return []


def _indice(tipo):
    """Índice del dispositivo elegido, o None para usar el predeterminado."""
    nombre = _AUDIO[tipo]
    if not nombre or not HAY_SELECCION_AUDIO:
        return None
    campo = "max_input_channels" if tipo == "entrada" else "max_output_channels"
    try:
        api = sd.default.hostapi
        for i, d in enumerate(sd.query_devices()):
            if d["hostapi"] == api and d[campo] > 0 and d["name"].strip() == nombre:
                return i
    except Exception:
        pass
    return None      # ya no está conectado: se usa el predeterminado


# ------------------------------------------------------------ reproducción
_parar_actual = threading.Event()
_DTYPE = {1: "uint8", 2: "int16", 3: "int24", 4: "int32"}


def _reproducir_elegido(ruta, indice):
    """Reproduce el .wav en el dispositivo elegido (en un hilo). False si no se puede."""
    global _parar_actual
    try:
        with wave.open(ruta) as w:
            canales, ancho, tasa = w.getnchannels(), w.getsampwidth(), w.getframerate()
            datos = w.readframes(w.getnframes())
        dtype = _DTYPE[ancho]
    except (wave.Error, EOFError, OSError, KeyError):
        return False
    _parar_actual.set()                   # corta lo que estuviera sonando
    parar = _parar_actual = threading.Event()

    def tarea():
        try:
            with sd.RawOutputStream(samplerate=tasa, channels=canales, dtype=dtype,
                                    device=indice) as flujo:
                trozo = max(1, tasa // 10) * canales * ancho
                for i in range(0, len(datos), trozo):
                    if parar.is_set():
                        return
                    flujo.write(datos[i:i + trozo])
        except Exception:
            if ES_WINDOWS and not parar.is_set():      # el dispositivo falló: se usa el normal
                winsound.PlaySound(ruta, winsound.SND_FILENAME | winsound.SND_ASYNC
                                   | winsound.SND_NODEFAULT)
    threading.Thread(target=tarea, daemon=True).start()
    return True


def reproducir(ruta):
    """Reproduce un .wav sin bloquear la interfaz (en los altavoces elegidos)."""
    if not (ruta and os.path.isfile(ruta)):
        return
    indice = _indice("salida")
    if indice is not None and _reproducir_elegido(ruta, indice):
        return
    if ES_WINDOWS:
        winsound.PlaySound(ruta, winsound.SND_FILENAME | winsound.SND_ASYNC
                           | winsound.SND_NODEFAULT)


def detener():
    _parar_actual.set()
    if ES_WINDOWS:
        winsound.PlaySound(None, 0)


def notificar(prefs, raiz=None):
    """Sonido de mensaje nuevo según las preferencias."""
    if not prefs.get("sonido"):
        return
    propio = prefs.get("tono_propio")
    if propio and os.path.isfile(propio):
        reproducir(propio)
    elif ES_WINDOWS:
        reproducir(ruta_tono(prefs.get("tono") if prefs.get("tono") in TONOS else "Campanita"))
    elif raiz is not None:
        raiz.bell()


def validar_tono_propio(ruta):
    if not ruta.lower().endswith(".wav"):
        return "El sonido debe ser un archivo .wav."
    if os.path.getsize(ruta) > MAX_SONIDO_PROPIO:
        return "El sonido debe pesar menos de 1 MB (unos segundos)."
    try:
        with wave.open(ruta) as w:
            if w.getnframes() / w.getframerate() > 5:
                return "El sonido debe durar 5 segundos o menos."
    except (wave.Error, EOFError):
        return "No se pudo leer ese .wav."
    return None


def duracion(ruta):
    """Duración de un .wav en segundos (0 si no se puede leer)."""
    try:
        with wave.open(ruta) as w:
            return w.getnframes() / w.getframerate()
    except (wave.Error, EOFError, OSError):
        return 0


# ----------------------------------------------------------- mensajes de voz
class Grabadora:
    """Graba el micrófono a un .wav. Con un micrófono elegido usa sounddevice; si no,
    la API MCI de Windows (sin instalar nada) con el micrófono predeterminado."""

    ALIAS = "socialuna_voz"
    TASA = 16000

    def __init__(self):
        self._flujo = None
        self._trozos = []
        self._tasa = self.TASA

    @staticmethod
    def _mci(orden):
        if not ES_WINDOWS:
            raise OSError("La grabación de voz solo está disponible en Windows.")
        buf = ctypes.create_unicode_buffer(256)
        error = ctypes.windll.winmm.mciSendStringW(orden, buf, 255, 0)
        if error:
            mensaje = ctypes.create_unicode_buffer(256)
            ctypes.windll.winmm.mciGetErrorStringW(error, mensaje, 255)
            raise OSError(mensaje.value or f"Error de audio {error}")
        return buf.value

    def iniciar(self):
        self.cancelar()
        indice = _indice("entrada")
        if indice is not None:
            self._iniciar_elegido(indice)
            return
        self._mci(f"open new type waveaudio alias {self.ALIAS}")
        try:
            self._mci(f"set {self.ALIAS} bitspersample 16 samplespersec 16000 channels 1")
        except OSError:
            pass   # algunos micrófonos no aceptan el formato: se usa el de fábrica
        self._mci(f"record {self.ALIAS}")

    def _iniciar_elegido(self, indice):
        self._trozos = []
        ultimo_error = None
        tasas = [self.TASA]
        try:
            tasas.append(int(sd.query_devices(indice)["default_samplerate"]))
        except Exception:
            pass
        for tasa in tasas:        # 16 kHz si el micrófono lo acepta; si no, su tasa propia
            try:
                flujo = sd.RawInputStream(
                    samplerate=tasa, channels=1, dtype="int16", device=indice,
                    callback=lambda datos, _n, _t, _s: self._trozos.append(bytes(datos)))
                flujo.start()
            except Exception as exc:
                ultimo_error = exc
                continue
            self._flujo, self._tasa = flujo, tasa
            return
        raise OSError(f"no se pudo abrir el micrófono elegido ({ultimo_error})")

    def detener(self, ruta):
        if self._flujo is None:
            self._mci(f"stop {self.ALIAS}")
            self._mci(f'save {self.ALIAS} "{ruta}"')
            self._mci(f"close {self.ALIAS}")
            return
        self._cerrar_flujo()
        datos = b"".join(self._trozos)
        if self._tasa != self.TASA:
            datos = _a_16k(datos, self._tasa)
        with wave.open(ruta, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.TASA)
            w.writeframes(datos)

    def _cerrar_flujo(self):
        flujo, self._flujo = self._flujo, None
        if flujo is not None:
            try:
                flujo.stop()
                flujo.close()
            except Exception:
                pass

    def cancelar(self):
        self._cerrar_flujo()
        try:
            self._mci(f"close {self.ALIAS}")
        except OSError:
            pass


def _a_16k(datos, tasa):
    """Baja un audio de 16 bits mono a 16 kHz (el tamaño se mantiene bajo el límite)."""
    muestras = array("h")
    muestras.frombytes(datos[:len(datos) // 2 * 2])
    paso = tasa / Grabadora.TASA
    n = int(len(muestras) / paso)
    return array("h", (muestras[int(i * paso)] for i in range(n))).tobytes()


if __name__ == "__main__":
    for nombre in TONOS:
        assert 0 < duracion(ruta_tono(nombre)) < 2, nombre
    assert cargar_prefs()["tono"] in TONOS or cargar_prefs()["tono"]
    print("sonidos OK:", ", ".join(TONOS))
