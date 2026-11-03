"""Pruebas del preprocesado (no requieren Ollama ni OCR)."""

from pathlib import Path

import pytest
from PIL import Image

from extraer_inputs.preprocesado import listar_imagenes, preparar

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _fixtures_existen():
    if not (FIXTURES / "proveedor_nitido.png").exists():
        pytest.skip("Faltan fixtures: ejecute tests\\fixtures\\crear_fixtures.py")


def test_jpg_girado_queda_derecho(tmp_path):
    p = preparar(FIXTURES / "proveedor_girado.jpg", tmp_path)
    with Image.open(p.orientada) as img:
        assert img.width > img.height  # el formulario es horizontal


def test_jpg_comprimido_se_escala_para_ocr(tmp_path):
    p = preparar(FIXTURES / "proveedor_comprimido.jpg", tmp_path)
    assert p.escala == 2.0
    with Image.open(p.para_ocr) as ocr, Image.open(p.orientada) as orig:
        assert ocr.width == orig.width * 2


def test_png_sin_alfa_y_original_intacto(tmp_path):
    original = FIXTURES / "proveedor_nitido.png"
    antes = original.read_bytes()
    p = preparar(original, tmp_path)
    with Image.open(p.orientada) as img:
        assert img.mode == "RGB"
    assert original.read_bytes() == antes


def test_ignora_extensiones_no_soportadas(tmp_path):
    (tmp_path / "nota.txt").write_text("x")
    (tmp_path / "a.PNG").write_bytes((FIXTURES / "proveedor_nitido.png").read_bytes())
    assert [p.name for p in listar_imagenes([tmp_path])] == ["a.PNG"]


def test_imagen_corrupta_lanza_oserror(tmp_path):
    rota = tmp_path / "rota.jpg"
    rota.write_bytes(b"no es una imagen")
    with pytest.raises(OSError):
        preparar(rota, tmp_path / "tmp")
