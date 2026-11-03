"""Modo para otros programas (ej. el portal de AltaProveedores): procesa UNA imagen y escribe en
stdout una sola linea JSON. El log va solo al archivo para no ensuciar stdout.

Uso:  python -m extraer_inputs.json_cli <imagen> [--campos "Etiqueta 1|Etiqueta 2|..."]
      --campos: formulario conocido; solo se piden esas etiquetas (respuesta corta, mucho mas rapido).
Salida: {"campos": [{etiqueta, valor, tipo, valor_modelo, valor_ocr, similitud, revisar, critico, motivo}],
         "tablas": [...], "motor_ocr": "PaddleOCR", "segundos": 123.4}
     o: {"error": "mensaje"}
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

from extraer_inputs import config
from extraer_inputs.logging_config import configurar_logging


def _responder(datos: dict) -> None:
    sys.stdout.write(json.dumps(datos, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    configurar_logging(config.NIVEL_LOG, config.CARPETA_LOGS, "extraer_inputs_json.log")
    raiz = logging.getLogger("extraer_inputs")
    raiz.handlers = [h for h in raiz.handlers if isinstance(h, logging.FileHandler)]  # sin consola
    etiquetas = None
    if "--campos" in argv and argv.index("--campos") + 1 < len(argv):
        i = argv.index("--campos")
        etiquetas = [e.strip() for e in argv[i + 1].split("|") if e.strip()]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 1:
        _responder({"error": "Uso: python -m extraer_inputs.json_cli <imagen> [--campos \"A|B|...\"]"})
        return 3
    imagen = Path(argv[0])
    if not imagen.is_file() or imagen.suffix.lower() not in config.EXTENSIONES:
        _responder({"error": f"No es una imagen .png/.jpg/.jpeg: {imagen.name}"})
        return 3

    from extraer_inputs import vision
    from extraer_inputs.main import procesar_imagen
    from extraer_inputs.ocr import MotorOCR

    problema = vision.verificar_ollama()
    if problema:
        _responder({"error": problema})
        return 2
    inicio = time.time()
    try:
        motor = MotorOCR()
        campos, tablas, _ = procesar_imagen(imagen, motor, config.RAIZ_PROYECTO / "resultados_json", etiquetas)
    except OSError as e:
        _responder({"error": f"Imagen corrupta o ilegible: {e}"})
        return 1
    except vision.ErrorOllama as e:
        _responder({"error": str(e)})
        return 1
    except Exception as e:  # cualquier otro fallo se reporta como JSON
        logging.getLogger("extraer_inputs.json_cli").exception("Error procesando %s", imagen)
        _responder({"error": f"Error inesperado: {e}"})
        return 1
    _responder({"campos": [c.como_dict() for c in campos], "tablas": tablas,
                "motor_ocr": motor.nombre, "segundos": round(time.time() - inicio, 1)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
