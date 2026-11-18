"""
Configuración centralizada de KHIARA.
Carga variables de entorno, rutas del sistema y parámetros de modelos.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar .env de KHIARA y .env del proyecto padre DASHBOARD_EK10
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(BASE_DIR.parent / ".env", override=False)

DATA_DIR = BASE_DIR / "data"
GRAFOS_DIR = DATA_DIR / "grafos"
MEMORIA_DIR = DATA_DIR / "memoria"
SANDBOX_DIR = DATA_DIR / "sandbox"
GRAFICAS_DIR = DATA_DIR / "graficas"

GRAFOS_DIR.mkdir(parents=True, exist_ok=True)
MEMORIA_DIR.mkdir(parents=True, exist_ok=True)
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
GRAFICAS_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-3.5-flash-lite")
GRAFO_DEFAULT_FILE = GRAFOS_DIR / "conocimiento_global.json"
MEMORIA_DB_FILE = MEMORIA_DIR / "khiara_memoria.db"

def tiene_api_key() -> bool:
    return bool(GEMINI_API_KEY)
