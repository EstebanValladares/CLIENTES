"""
Ejecutor de Automatización para CONTRATISTAS en Aryve (EK10).
Mantiene 100% de retrocompatibilidad con los comandos y parámetros existentes.

Uso:
  python CONTRATISTAS/automatizacion_contratistas.py --desde 223 --hasta 229
  python CONTRATISTAS/automatizacion_contratistas.py --id 229
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from main import main, ejecutar_automatizacion
from automation.contractor_bot import ContractorBot
from config.settings import resolver_credenciales

if __name__ == "__main__":
    main()
