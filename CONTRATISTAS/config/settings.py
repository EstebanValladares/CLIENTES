"""
Módulo de Configuración y Constantes Globales para CONTRATISTAS.
Centraliza rutas del sistema, especificaciones de imagen, URLs de Aryve y resolución de credenciales.
"""

import os
from typing import Tuple, Optional

# Rutas del Sistema de Archivos
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CONFIG_DIR)
ROOT_DIR = os.path.dirname(BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CATALOG_JSON_PATH = os.path.join(BASE_DIR, "contratista_mapeado.json")
SOURCE_CSV_PATH = os.path.join(DATA_DIR, "Contratistas (2)(Contratistas).csv")

# Asegurar existencia de carpetas clave
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Especificaciones Gráficas de los Gafetes de Contratistas
CANVAS_WIDTH = 762
CANVAS_HEIGHT = 686
BACKGROUND_COLOR = (255, 255, 255)  # Fondo blanco puro
TEXT_COLOR = (0, 0, 0)              # Texto negro puro
MAX_LINES = 3

# Endpoints y Rutas de Aryve (EK10)
URL_LOGIN_ARYVE = ""
URL_CONTRATISTAS_BASE = "#/scco/Contratistas/"

# Argumentos de Selenium Chrome
CHROME_ARGUMENTS = [
    "--start-maximized",
    "--ignore-certificate-errors",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-notifications",
    "--log-level=3",
]


def resolver_credenciales(user_arg: Optional[str] = None, pass_arg: Optional[str] = None) -> Tuple[str, str]:
    """
    Obtiene las credenciales oficiales de acceso a Aryve.
    Prioridad: Argumentos directos > Variables de entorno (EK10_USER/PASS) > Archivos .env > Defaults.
    NOTA: La contraseña debe ser la cadena exacta sin decodificar (literal).
    """
    if user_arg and pass_arg:
        return user_arg, pass_arg

    usuario = os.getenv("EK10_USER") or os.getenv("EK9_USER")
    password = os.getenv("EK10_PASS") or os.getenv("EK9_PASS")

    if not usuario or not password:
        rutas_env = [
            os.path.join(ROOT_DIR, ".env"),
            os.path.join(BASE_DIR, ".env"),
            ".env"
        ]
        for r in rutas_env:
            if os.path.exists(r):
                try:
                    with open(r, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if line.startswith("EK10_USER=") and not usuario:
                                usuario = line.split("=", 1)[1].strip()
                            elif line.startswith("EK10_PASS=") and not password:
                                password = line.split("=", 1)[1].strip()
                            elif line.startswith("EK9_USER=") and not usuario:
                                usuario = line.split("=", 1)[1].strip()
                            elif line.startswith("EK9_PASS=") and not password:
                                password = line.split("=", 1)[1].strip()
                    if usuario and password:
                        break
                except Exception:
                    pass

    usuario = usuario or ""
    password = password or ""

    return usuario, password

