"""
Compatibilidad Retroactiva: Conversión de CSV a contratista_mapeado.json.
Delega a CONTRATISTAS.domain.catalog_service.build_catalog_from_csv.
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from domain.catalog_service import build_catalog_from_csv

def procesar_csv_contratistas(csv_path: str = None, output_dir: str = None):
    return build_catalog_from_csv(csv_path=csv_path)

if __name__ == "__main__":
    build_catalog_from_csv()
