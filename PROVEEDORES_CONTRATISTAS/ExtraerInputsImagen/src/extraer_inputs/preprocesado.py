"""Paso 1: carga y preprocesado de las imagenes con Pillow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from extraer_inputs import config
from extraer_inputs.logging_config import obtener_logger

log = obtener_logger(__name__)


@dataclass(frozen=True)
class ImagenPreparada:
    origen: Path       # archivo original (no se modifica)
    orientada: Path    # original con la orientacion EXIF corregida, en RGB -> modelo de vision
    para_ocr: Path     # escalada si hace falta + nitidez/contraste -> OCR
    escala: float      # factor aplicado a para_ocr respecto a orientada


def listar_imagenes(rutas: list[Path]) -> list[Path]:
    """Imagenes .png/.jpg/.jpeg de las rutas (carpetas o archivos). El resto se ignora con aviso."""
    encontradas: list[Path] = []
    for ruta in rutas:
        candidatos = sorted(p for p in ruta.iterdir() if p.is_file()) if ruta.is_dir() else [ruta]
        for archivo in candidatos:
            if archivo.suffix.lower() in config.EXTENSIONES:
                encontradas.append(archivo)
            else:
                log.warning("Se ignora %s: solo se aceptan %s.", archivo.name, ", ".join(sorted(config.EXTENSIONES)))
    return encontradas


def preparar(origen: Path, carpeta_temporal: Path = config.CARPETA_TEMPORAL) -> ImagenPreparada:
    """Corrige orientacion EXIF, convierte a RGB, escala x2 si es angosta y mejora para el OCR.
    Lanza OSError si la imagen esta corrupta o no se puede leer."""
    carpeta_temporal.mkdir(parents=True, exist_ok=True)
    with Image.open(origen) as imagen:
        imagen.load()
        orientada = ImageOps.exif_transpose(imagen)  # los JPG de movil vienen girados
        orientada = orientada.convert("RGB")         # quita canal alfa (PNG) y paleta
    base = carpeta_temporal / f"{origen.stem}_{origen.suffix[1:].lower()}"  # a.png y a.jpg no chocan
    ruta_orientada = base.with_name(base.name + "_orientada.png")
    orientada.save(ruta_orientada)

    escala = 1.0
    para_ocr = orientada
    if para_ocr.width < config.ANCHO_MINIMO:
        escala = 2.0
        para_ocr = para_ocr.resize((para_ocr.width * 2, para_ocr.height * 2), Image.Resampling.LANCZOS)
    # Mejora ligera solo para el OCR (el modelo de vision recibe la orientada sin filtros)
    para_ocr = ImageEnhance.Contrast(para_ocr).enhance(1.3)
    para_ocr = para_ocr.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=2))
    ruta_ocr = base.with_name(base.name + "_ocr.png")
    para_ocr.save(ruta_ocr)
    log.info("%s: %dx%d px%s.", origen.name, orientada.width, orientada.height,
             " (escalada x2 para OCR)" if escala > 1 else "")
    return ImagenPreparada(origen, ruta_orientada, ruta_ocr, escala)
