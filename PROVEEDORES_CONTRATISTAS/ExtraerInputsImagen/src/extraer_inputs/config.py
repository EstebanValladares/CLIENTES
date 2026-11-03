"""Configuracion central. Los valores se pueden sobrescribir con variables de entorno EXTRAER_*."""

from __future__ import annotations

import os
from pathlib import Path

#: Raiz del proyecto: .../src/extraer_inputs/config.py -> parents[2] == ExtraerInputsImagen/
RAIZ_PROYECTO: Path = Path(__file__).resolve().parents[2]


def _env(nombre: str, defecto: str) -> str:
    return os.environ.get(f"EXTRAER_{nombre}", defecto)


# --- Ollama (modelo de vision local) ---------------------------------------
OLLAMA_URL: str = _env("OLLAMA_URL", "http://localhost:11434")
MODELO_VISION: str = _env("MODELO", "qwen2.5vl:7b")
#: En CPU el modelo 7b tarda 1-3 min por imagen.
TIMEOUT_OLLAMA_SEG: float = float(_env("TIMEOUT_OLLAMA", "900"))

# --- OCR -------------------------------------------------------------------
#: "paddle" (principal) o "easyocr" (alternativa). Si paddle no esta disponible se usa easyocr.
MOTOR_OCR: str = _env("OCR", "paddle").lower()
IDIOMA_OCR: str = "es"

# --- Preprocesado ----------------------------------------------------------
EXTENSIONES: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})
ANCHO_MINIMO: int = 1500  # por debajo se escala x2 (LANCZOS)
CARPETA_TEMPORAL: Path = Path(_env("TEMP", str(RAIZ_PROYECTO / "temp")))

# --- Validacion ------------------------------------------------------------
UMBRAL_SIMILITUD: float = 0.9   # >= usa el texto del OCR como valor final
UMBRAL_ETIQUETA: float = 0.8    # para ubicar la etiqueta en el OCR al recuperar valores null
#: Campos criticos (etiqueta normalizada -> sinonimos). No pueden tener errores.
CAMPOS_CRITICOS: dict[str, tuple[str, ...]] = {
    "PROVEEDOR": ("PROVEEDOR", "CLAVE PROVEEDOR", "NO PROVEEDOR", "NUMERO PROVEEDOR"),
    "NOMBRE": ("NOMBRE", "RAZON SOCIAL", "NOMBRE O RAZON SOCIAL"),
    "DIRECCION": ("DIRECCION", "DOMICILIO", "CALLE"),
    "CODIGO POSTAL": ("CODIGO POSTAL", "C.P.", "CP", "C P"),
    "RFC": ("RFC", "R.F.C."),
}

# --- Salida y logs ---------------------------------------------------------
NOMBRE_CARPETA_SALIDA: str = "resultados_extraccion"  # se crea junto a las imagenes
NOMBRE_CONSOLIDADO: str = "consolidado.csv"
CARPETA_LOGS: Path = RAIZ_PROYECTO / "logs"
ARCHIVO_LOG: str = "extraer_inputs.log"
NIVEL_LOG: str = _env("NIVEL_LOG", "INFO")
