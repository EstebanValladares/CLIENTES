"""
Logger especializado para incidencias y fallas de KHIARA.
Registra únicamente errores, excepciones, timeouts o datos no localizados
para auditoría y mejora continua, sin interrumpir la experiencia de usuario.
"""
import os
import datetime
from pathlib import Path

DIR_BASE = Path(__file__).resolve().parent.parent.parent
DIR_LOGS = DIR_BASE / "data" / "logs"
DIR_LOGS.mkdir(parents=True, exist_ok=True)
ARCHIVO_LOG = DIR_LOGS / "fallas_khiara.log"


def registrar_falla(consulta: str, origen: str, detalle: str):
    """Guarda un registro detallado de la falla o error en fallas_khiara.log."""
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{now}] [{origen}] Consulta: \"{consulta.strip()}\" | Detalle: {str(detalle).strip()}\n"
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception:
        pass


def obtener_ultimas_fallas(limite: int = 20) -> list:
    """Devuelve las últimas fallas registradas para inspección."""
    if not ARCHIVO_LOG.exists():
        return []
    try:
        with open(ARCHIVO_LOG, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        return [l.strip() for l in lineas[-limite:]]
    except Exception:
        return []
