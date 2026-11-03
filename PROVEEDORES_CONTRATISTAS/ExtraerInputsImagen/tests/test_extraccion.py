"""Prueba de punta a punta con Ollama + OCR sobre las 3 imagenes de ejemplo.

Compara los campos criticos con el JSON esperado: cada uno debe coincidir exactamente o quedar
marcado revisar=true. En la imagen nitida deben coincidir todos. Si Ollama no corre, se salta.
"""

import json
from pathlib import Path

import pytest

from extraer_inputs import preprocesado, validacion, vision

FIXTURES = Path(__file__).parent / "fixtures"
IMAGENES = ["proveedor_nitido.png", "proveedor_comprimido.jpg", "proveedor_girado.jpg"]


@pytest.fixture(scope="module")
def motor():
    problema = vision.verificar_ollama()
    if problema:
        pytest.skip("Ollama no disponible, se salta la prueba de extraccion:\n" + problema)
    if not (FIXTURES / IMAGENES[0]).exists():
        pytest.skip("Faltan fixtures: ejecute tests\\fixtures\\crear_fixtures.py")
    from extraer_inputs.ocr import MotorOCR
    return MotorOCR()


@pytest.mark.parametrize("nombre", IMAGENES)
def test_campos_criticos(motor, nombre, tmp_path):
    esperado = json.loads((FIXTURES / f"{Path(nombre).stem}.esperado.json").read_text(encoding="utf-8"))
    p = preprocesado.preparar(FIXTURES / nombre, tmp_path)
    estructura = vision.extraer_estructura(p.orientada)
    campos = validacion.validar(estructura["campos"], motor.leer(p.para_ocr))
    criticos = {c.critico: c for c in campos if c.critico}
    for campo, valor in esperado["criticos"].items():
        c = criticos[campo]
        assert c.valor == valor or c.revisar, f"{nombre} {campo}: '{c.valor}' != '{valor}' sin marcar revisar"
        if nombre == "proveedor_nitido.png":
            assert c.valor == valor, f"{campo}: '{c.valor}' != '{valor}' en la imagen nitida"
