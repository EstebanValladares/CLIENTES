"""Carga de configuración del núcleo.

Prioridad: variables de entorno > NUCLEO/config.json > valores por defecto.
config.json NO se versiona (contiene tokens). Usa config.ejemplo.json como plantilla.
"""
import json
import os

NUCLEO_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(NUCLEO_DIR)
RUTA_CONFIG = os.path.join(NUCLEO_DIR, "config.json")
RUTA_ENV_RAIZ = os.path.join(RAIZ, ".env")


def cargar_env(ruta_env=None):
    """Carga variables clave=valor desde el archivo .env en os.environ sin requerir librerías externas."""
    rutas = [ruta_env] if ruta_env else [RUTA_ENV_RAIZ, os.path.join(os.getcwd(), ".env")]
    for ruta in rutas:
        if ruta and os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if not linea or linea.startswith("#") or "=" not in linea:
                            continue
                        clave, valor = linea.split("=", 1)
                        clave = clave.strip()
                        valor = valor.strip().strip('"').strip("'")
                        if clave:
                            os.environ[clave] = valor
            except Exception as e:
                print(f"[NUCLEO] Aviso al leer {ruta}: {e}")


def obtener_credenciales_aryve():
    """
    Devuelve (usuario, password) leídos desde .env o variables de entorno.
    Prioriza credenciales oficiales EK10 (EK10_USER, EK10_PASS) con fallback a EK9.
    """
    cargar_env()
    usuario = os.environ.get("EK10_USER", "").strip() or os.environ.get("EK9_USER", "").strip()
    password = os.environ.get("EK10_PASS", "").strip() or os.environ.get("EK9_PASS", "").strip()
    if not usuario or not password:
        raise RuntimeError(
            "No se encontraron las credenciales EK10_USER / EK10_PASS o EK9_USER / EK9_PASS. "
            "Verifica que exista el archivo '.env' en la raíz del proyecto."
        )
    return usuario, password


DEFECTO = {
    "popup_windows": True,            # ventana emergente en FALLO / FALLO_SILENCIOSO
    "notificar_advertencias": True,   # enviar también las ADVERTENCIA (Telegram/bitácora)
    "telegram_token": "",
    "telegram_chat_id": "",
    "gemini_api_key": "",
    "modelo_vision": "gemini-3.8-flash",
    "dias_retencion_capturas": 30,
    "url_portal": "",
}

_cache = None


def cargar(forzar=False):
    global _cache
    if _cache is not None and not forzar:
        return _cache

    cargar_env()
    cfg = dict(DEFECTO)
    if os.path.exists(RUTA_CONFIG):
        try:
            with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[NUCLEO] No se pudo leer config.json: {e}")

    env_map = {
        "VELAS_TELEGRAM_TOKEN": "telegram_token",
        "VELAS_TELEGRAM_CHAT_ID": "telegram_chat_id",
        "GEMINI_API_KEY": "gemini_api_key",
    }
    for env, clave in env_map.items():
        if os.environ.get(env):
            cfg[clave] = os.environ[env]
    if os.environ.get("VELAS_SIN_POPUP"):
        cfg["popup_windows"] = False

    _cache = cfg
    return cfg
