"""Punto de entrada: procesa una o varias carpetas/imagenes y genera los CSV.

Uso:
  python -m extraer_inputs.main <carpeta o imagen> [mas rutas...] [--salida CARPETA]
Codigos de salida: 0 = ok, 1 = alguna imagen con error, 2 = Ollama/modelo no disponible,
3 = sin imagenes validas o argumentos incorrectos.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from extraer_inputs import config
from extraer_inputs.logging_config import configurar_logging, obtener_logger

log = obtener_logger("extraer_inputs.main")


def procesar_imagen(imagen: Path, motor, carpeta_salida: Path,
                    etiquetas: list[str] | None = None) -> tuple[list, list[dict], int]:
    """Pipeline completo de una imagen -> (campos validados, tablas, lineas OCR). Escribe su CSV.
    `etiquetas`: solo esos campos (formulario conocido, mas rapido).
    Lanza OSError (imagen ilegible) o vision.ErrorOllama."""
    from extraer_inputs import preprocesado, salida, validacion, vision

    preparada = preprocesado.preparar(imagen)
    estructura = vision.extraer_estructura(preparada.orientada, etiquetas)
    lineas = motor.leer(preparada.para_ocr)
    campos = validacion.validar(estructura["campos"], lineas)
    salida.escribir_imagen(carpeta_salida, imagen.name, campos, estructura["tablas"])
    return campos, estructura["tablas"], len(lineas)


def procesar(rutas: list[Path], carpeta_salida: Path | None = None) -> int:
    from extraer_inputs import preprocesado, salida, vision
    from extraer_inputs.ocr import MotorOCR

    imagenes = preprocesado.listar_imagenes(rutas)
    if not imagenes:
        log.error("No se encontraron imagenes .png/.jpg/.jpeg en: %s", ", ".join(str(r) for r in rutas))
        return 3
    problema = vision.verificar_ollama()
    if problema:
        log.error("No se puede usar el modelo de vision:\n%s", problema)
        return 2
    if carpeta_salida is None:
        base = rutas[0] if rutas[0].is_dir() else rutas[0].parent
        carpeta_salida = base / config.NOMBRE_CARPETA_SALIDA
    log.info("Imagenes: %d | modelo: %s | salida: %s", len(imagenes), config.MODELO_VISION, carpeta_salida)
    motor = MotorOCR()

    por_imagen: dict[str, list] = {}
    errores: list[str] = []
    inicio = time.time()
    for n, imagen in enumerate(imagenes, 1):
        log.info("===== (%d/%d) %s =====", n, len(imagenes), imagen.name)
        t = time.time()
        try:
            campos, _, n_lineas = procesar_imagen(imagen, motor, carpeta_salida)
            por_imagen[imagen.name] = campos
            criticos = [c for c in campos if c.critico]
            log.info("%s: %d campos (%d criticos), %d a revisar, %d lineas OCR [%.0f s].", imagen.name,
                     len(campos), len(criticos), sum(c.revisar for c in campos), n_lineas, time.time() - t)
            for c in criticos:
                log.info("   %-14s %-40s %s", c.critico, c.valor[:40], "REVISAR: " + c.motivo if c.revisar else "ok")
        except OSError as e:
            errores.append(imagen.name)
            log.error("%s: imagen corrupta o ilegible (%s); se continua con la siguiente.", imagen.name, e)
        except vision.ErrorOllama as e:
            errores.append(imagen.name)
            log.error("%s; se continua con la siguiente.", e)
        except Exception as e:  # cualquier otro fallo no detiene el lote
            errores.append(imagen.name)
            log.exception("%s: error inesperado (%s); se continua con la siguiente.", imagen.name, e)

    if por_imagen:
        consolidado = salida.escribir_consolidado(carpeta_salida / config.NOMBRE_CONSOLIDADO, por_imagen)
        log.info("Consolidado: %s", consolidado)
    a_revisar = sum(c.revisar for campos in por_imagen.values() for c in campos)
    log.info("===== RESUMEN =====")
    log.info("Imagenes procesadas: %d | con error: %d | campos a revisar: %d | motor OCR: %s | %.1f min",
             len(por_imagen), len(errores), a_revisar, motor.nombre, (time.time() - inicio) / 60)
    for nombre in errores:
        log.info("   con error: %s", nombre)
    return 1 if errores else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extrae los datos de los inputs de capturas PNG/JPG (local).")
    parser.add_argument("rutas", nargs="*", type=Path, help="Carpeta(s) o imagen(es)")
    parser.add_argument("--salida", type=Path, help="Carpeta de salida (por defecto <carpeta>\\resultados_extraccion)")
    args = parser.parse_args(argv)
    configurar_logging(config.NIVEL_LOG, config.CARPETA_LOGS, config.ARCHIVO_LOG)
    rutas = [r for r in args.rutas if r.exists()]
    for r in args.rutas:
        if not r.exists():
            log.warning("No existe: %s", r)
    if not rutas:
        log.error("Indique una carpeta o imagen (o arrastrela sobre ejecutar.bat).")
        return 3
    return procesar(rutas, args.salida)


if __name__ == "__main__":
    sys.exit(main())
