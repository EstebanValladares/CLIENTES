"""
Domain Service: Generador Gráfico de Gafetes / Tarjetas de Identificación para Contratistas.
Dimensiones requeridas: 762 x 686 px (Fondo blanco, texto centrado en negro puro).
"""

import os
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

try:
    from ..config.settings import (
        CANVAS_WIDTH,
        CANVAS_HEIGHT,
        BACKGROUND_COLOR,
        TEXT_COLOR,
        OUTPUT_DIR,
    )
    from .text_processor import process_contractor_name
except (ImportError, ValueError):
    from config.settings import (
        CANVAS_WIDTH,
        CANVAS_HEIGHT,
        BACKGROUND_COLOR,
        TEXT_COLOR,
        OUTPUT_DIR,
    )
    from domain.text_processor import process_contractor_name


def find_system_font(font_size: int = 50) -> ImageFont.FreeTypeFont:
    """Busca y carga una tipografía Sans-Serif clara en el sistema operativo."""
    font_candidates = [
        # Windows
        r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold
        r"C:\Windows\Fonts\arial.ttf",     # Arial
        r"C:\Windows\Fonts\seguiui.ttf",   # Segoe UI
        r"C:\Windows\Fonts\segoeuib.ttf",  # Segoe UI Bold
        r"C:\Windows\Fonts\calibrib.ttf",  # Calibri Bold
        r"C:\Windows\Fonts\calibri.ttf",   # Calibri
        # Linux / Container
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue

    try:
        return ImageFont.load_default()
    except Exception:
        return None


def calculate_optimal_font_size(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    max_w: int,
    max_h: int,
    initial_size: int = 120,
    min_size: int = 24
) -> Tuple[int, ImageFont.FreeTypeFont]:
    """Calcula el tamaño de fuente óptimo para que todas las líneas quepan con holgura."""
    if not lines:
        font = find_system_font(initial_size)
        return initial_size, font

    font_size = initial_size
    while font_size >= min_size:
        font = find_system_font(font_size)
        fits = True
        total_text_h = 0
        line_spacing = int(font_size * 0.28)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]

            if line_w > max_w:
                fits = False
                break
            total_text_h += line_h

        total_text_h += line_spacing * (len(lines) - 1)
        if fits and total_text_h <= max_h:
            return font_size, font

        font_size -= 2

    return min_size, find_system_font(min_size)


def create_contractor_badge(
    lines: List[str],
    output_path: str,
    width: int = CANVAS_WIDTH,
    height: int = CANVAS_HEIGHT,
) -> str:
    """
    Crea una imagen de gafete con texto perfectamente centrado horizontal y verticalmente.
    Guarda en output_path y retorna la ruta del archivo generado.
    """
    img = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    margin_x = int(width * 0.08)
    margin_y = int(height * 0.10)
    avail_w = width - (2 * margin_x)
    avail_h = height - (2 * margin_y)

    _, font = calculate_optimal_font_size(draw, lines, avail_w, avail_h)

    # Medir dimensiones individuales de cada línea
    line_metrics = []
    line_spacing = 16
    total_h = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_metrics.append((line, w, h, bbox))
        total_h += h

    total_h += line_spacing * max(0, len(lines) - 1)

    # Centrado vertical
    start_y = (height - total_h) // 2
    cur_y = start_y

    for line, w, h, bbox in line_metrics:
        # Centrado horizontal
        cur_x = (width - w) // 2 - bbox[0]
        actual_y = cur_y - bbox[1]
        draw.text((cur_x, actual_y), line, fill=TEXT_COLOR, font=font)
        cur_y += h + line_spacing

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    return output_path


def generate_badge_for_contractor(
    contractor_id: int,
    contractor_name: str,
    custom_lines: Optional[List[str]] = None,
    output_dir: str = OUTPUT_DIR
) -> str:
    """Genera la imagen identificada como {contractor_id}.png a partir del nombre o líneas dadas."""
    if custom_lines and len(custom_lines) > 0:
        lines = custom_lines
    else:
        info = process_contractor_name(contractor_name)
        lines = info["lineas"]

    output_path = os.path.join(output_dir, f"{contractor_id}.png")
    return create_contractor_badge(lines, output_path)
