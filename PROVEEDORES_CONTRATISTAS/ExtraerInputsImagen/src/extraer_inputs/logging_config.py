"""Configuracion centralizada del logging (misma convencion que los demas proyectos).

Regla del proyecto: prohibido ``print``. Todo mensaje pasa por un logger.
"""

from __future__ import annotations

import logging
from pathlib import Path

_PAQUETE_RAIZ = "extraer_inputs"

_FORMATO = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def configurar_logging(nivel: str, carpeta_logs: Path, nombre_archivo: str) -> None:
    """Handlers de archivo (se reinicia en cada corrida) y consola del logger del paquete."""
    carpeta_logs.mkdir(parents=True, exist_ok=True)
    raiz = logging.getLogger(_PAQUETE_RAIZ)
    raiz.setLevel(nivel)
    raiz.propagate = False
    raiz.handlers.clear()
    archivo = logging.FileHandler(carpeta_logs / nombre_archivo, mode="w", encoding="utf-8")
    archivo.setFormatter(_FORMATO)
    raiz.addHandler(archivo)
    consola = logging.StreamHandler()
    consola.setFormatter(_FORMATO)
    raiz.addHandler(consola)


def obtener_logger(nombre: str) -> logging.Logger:
    raiz = logging.getLogger(_PAQUETE_RAIZ)
    if not raiz.handlers:
        raiz.addHandler(logging.NullHandler())
    return logging.getLogger(nombre)
