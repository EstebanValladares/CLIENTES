"""
Configuración centralizada del módulo PROVEEDORES.
Define rutas, URLs de Aryve, tiempos de espera reactivos, opciones de navegador
y carga segura de credenciales desde NUCLEO o variables de entorno.
"""
import os
import sys
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

# Garantizar salida UTF-8 segura en terminales Windows y subprocesos de iniciar_dashboard_v2
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# --- RUTAS DEL MÓDULO Y ECOSISTEMA ---
BASE_DIR: Path = Path(__file__).resolve().parent.parent
ECOSYSTEM_DIR: Path = BASE_DIR.parent

RUTA_DATOS_CSV: str = str(BASE_DIR / "datos.csv")
RUTA_REGISTRO_JSON: str = str(BASE_DIR / "registro_proveedores.json")
RUTA_LOG: str = str(BASE_DIR / "log_proveedores.txt")

# --- URLS DEL SISTEMA ARYVE ---
URL_BASE_ARYVE: str = os.getenv("ARYVE_BASE_URL", "")
URL_NUEVO_PROVEEDOR: str = f"{URL_BASE_ARYVE}#/scp/Proveedores/id?nuevo"

# --- TIMEOUTS Y POLLING REACTIVO (SEGUNDOS) ---
TIMEOUT_CORTO: float = 5.0
TIMEOUT_MEDIO: float = 10.0
TIMEOUT_LARGO: float = 15.0
TIMEOUT_LOGIN: float = 20.0
TIMEOUT_GUARDADO: float = 25.0
POLL_INTERVAL_RAPIDO: float = 0.1  # Sondeo reactivo cada 100ms (5x más rápido que el default de 500ms)

# Pausas breves de estabilización visual para controles React / Select2 en Aryve
PAUSA_MICRO: float = 0.15
PAUSA_ESTABILIZACION: float = 0.3
PAUSA_PANEL: float = 0.6
PAUSA_REMOTA_SELECT2: float = 0.8

# --- OPCIONES DE CHROME OPTIMIZADAS ---
CHROME_ARGUMENTS: list[str] = [
    "--start-maximized",
    "--ignore-certificate-errors",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-notifications",
    "--log-level=3",
]


def obtener_credenciales() -> Tuple[str, str]:
    """
    Obtiene las credenciales (usuario, password) de Aryve priorizando NUCLEO.config
    y usando variables de entorno (.env) como respaldo.
    """
    raiz_str = str(ECOSYSTEM_DIR)
    if raiz_str not in sys.path:
        sys.path.append(raiz_str)

    try:
        from NUCLEO.config import obtener_credenciales_aryve
        return obtener_credenciales_aryve()
    except Exception:
        load_dotenv(dotenv_path=ECOSYSTEM_DIR / ".env")
        load_dotenv(dotenv_path=BASE_DIR / ".env")
        user = os.getenv("EK9_USER", "").strip()
        password = os.getenv("EK9_PASS", "").strip()
        return user, password

