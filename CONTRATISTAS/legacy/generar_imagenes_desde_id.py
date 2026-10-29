"""
Compatibilidad Retroactiva: Generador de Imágenes por ID.
Delega a CONTRATISTAS.main.generar_imagenes_lote.
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from main import generar_imagenes_lote

def generar_imagenes_desde_id(min_id: int = 222, **kwargs):
    return generar_imagenes_lote(desde_id=min_id)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", "-d", type=int, default=222)
    args = parser.parse_args()
    generar_imagenes_lote(desde_id=args.desde)
