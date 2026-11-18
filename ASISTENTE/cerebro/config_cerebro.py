"""
Configuración del Cerebro Cognitivo y Motor de Inteligencia Artificial del Asistente.
Soporta: Google Gemini API (google-genai SDK) y fallback nativo de Grafos locales.
"""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_GRAFO_PATH = os.path.join(DATA_DIR, "memoria_grafo.db")
CONOCIMIENTO_DIR = os.path.join(os.path.dirname(__file__), "conocimiento")
KEY_FILE = os.path.join(DATA_DIR, "gemini_key.txt")

# Modelo recomendado por Google para razonamiento rápido y eficiente
DEFAULT_MODEL = "gemini-2.5-flash"


def obtener_gemini_api_key() -> str:
    """Busca la API Key de Gemini en variable de entorno o archivo seguro local."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def guardar_gemini_api_key(key: str) -> bool:
    """Permite configurar la API Key de Gemini desde la interfaz o endpoint."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            f.write(str(key or "").strip())
        return True
    except Exception:
        return False
