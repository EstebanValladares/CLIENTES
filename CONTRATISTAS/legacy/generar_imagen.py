"""
Compatibilidad Retroactiva: Generador de Imágenes de Contratistas.
Delega al nuevo motor modular en CONTRATISTAS.domain.image_generator y text_processor.
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config.settings import (
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    OUTPUT_DIR,
)
from domain.text_processor import (
    process_contractor_name,
    normalize_text,
    strip_accents,
    remove_legal_suffixes,
    remove_system_prefixes,
    group_lines_smartly,
)
from domain.image_generator import (
    create_contractor_badge,
    generate_badge_for_contractor,
)


def select_relevant_name(name: str, force_mode: str = "auto"):
    """Función de compatibilidad con código anterior."""
    res = process_contractor_name(name)
    return {
        "original": res["nombre_original"],
        "cleaned": res["nombre_limpio"],
        "featured": res["nombre_destacado"],
        "lines": res["lineas"],
        "mode": res["tipo_entidad"].lower(),
        "is_company": res["tipo_entidad"] == "EMPRESA"
    }


def create_contractor_image(lines, output_path, width=CANVAS_WIDTH, height=CANVAS_HEIGHT):
    """Función de compatibilidad con código anterior."""
    return create_contractor_badge(lines, output_path, width=width, height=height)


def slugify_name(text: str) -> str:
    cleaned = strip_accents(text).upper()
    return "_".join(cleaned.split())


if __name__ == "__main__":
    from main import main
    main()
