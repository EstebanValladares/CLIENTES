"""
Punto de Entrada Principal (CLI y API) del Módulo CONTRATISTAS.

Comandos de uso rápido:
  - Ejecutar automatización en Aryve (del 223 al 229 por defecto):
      python CONTRATISTAS/main.py --desde 223 --hasta 229

  - Procesar un solo contratista:
      python CONTRATISTAS/main.py --id 229

  - Generar imágenes por lote para contratistas desde ID >= 222:
      python CONTRATISTAS/main.py --generate-images --desde 222

  - Reconstruir el catálogo oficial 'contratista_mapeado.json' desde el CSV:
      python CONTRATISTAS/main.py --build-catalog
"""

import sys
import os
import argparse
from typing import Optional, List, Dict, Any

# Agregar directorio actual al sys.path para importación modular
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config.settings import (
    BASE_DIR,
    OUTPUT_DIR,
    CATALOG_JSON_PATH,
    SOURCE_CSV_PATH,
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
)
from domain.catalog_service import (
    load_mapped_catalog,
    build_catalog_from_csv,
    get_contractor_by_id,
    get_contractors_range,
)
from domain.image_generator import generate_badge_for_contractor
from automation.contractor_bot import ContractorBot


def generar_imagenes_lote(desde_id: int = 222, hasta_id: Optional[int] = None) -> List[str]:
    """Genera las imágenes de gafetes {id}.png para todos los contratistas en el rango."""
    catalogo = load_mapped_catalog()
    if not catalogo and os.path.exists(SOURCE_CSV_PATH):
        print("[INFO] Generando contratista_mapeado.json desde CSV...")
        catalogo = build_catalog_from_csv()

    seleccionados = [c for c in catalogo if c.get("id") is not None and c["id"] >= desde_id]
    if hasta_id is not None:
        seleccionados = [c for c in seleccionados if c["id"] <= hasta_id]

    seleccionados.sort(key=lambda x: x["id"])

    print("=" * 80)
    print(f"GENERACIÓN DE GAFETES POR ID ({CANVAS_WIDTH}x{CANVAS_HEIGHT} px)")
    print(f"Total a generar: {len(seleccionados)} contratistas")
    print("=" * 80)

    rutas_generadas = []
    for c in seleccionados:
        cid = c["id"]
        nombre = c["nombre"]
        lineas = c.get("lineas_imagen")
        ruta = generate_badge_for_contractor(cid, nombre, custom_lines=lineas, output_dir=OUTPUT_DIR)
        print(f"  [OK] Gafete generado: {cid}.png -> {' / '.join(lineas if lineas else [nombre])}")
        rutas_generadas.append(ruta)

    print("=" * 80)
    return rutas_generadas


def ejecutar_automatizacion(
    desde_id: int = 223,
    hasta_id: int = 229,
    usuario: Optional[str] = None,
    password: Optional[str] = None,
    headless: bool = False,
    no_pause: bool = False
) -> List[Dict[str, Any]]:
    """Ejecuta el bot de Selenium para cargar fotos en Aryve."""
    bot = ContractorBot(
        usuario=usuario,
        password=password,
        headless=headless,
        images_dir=OUTPUT_DIR
    )
    return bot.run_batch(start_id=desde_id, end_id=hasta_id, pause_at_end=not no_pause)


def main():
    parser = argparse.ArgumentParser(
        description="Módulo Oficial de Contratistas - Dashboard EK10"
    )
    parser.add_argument("--desde", "-d", type=int, default=223, help="ID inicial a procesar")
    parser.add_argument("--hasta", "-h_id", type=int, default=229, help="ID final a procesar")
    parser.add_argument("--id", "-i", type=int, help="Procesar un ID específico")
    parser.add_argument("--user", "-u", help="Usuario para Aryve (por defecto EK10_USER)")
    parser.add_argument("--password", "-p", help="Contraseña para Aryve (por defecto EK10_PASS)")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin ventana visible de Chrome")
    parser.add_argument("--no-pause", action="store_true", help="Cerrar el navegador al finalizar")
    parser.add_argument("--generate-images", action="store_true", help="Generar imágenes de gafetes {id}.png")
    parser.add_argument("--build-catalog", action="store_true", help="Reconstruir contratista_mapeado.json desde CSV")

    args = parser.parse_args()

    # Opción 1: Reconstruir catálogo
    if args.build_catalog:
        print("[INFO] Reconstruyendo contratista_mapeado.json...")
        res = build_catalog_from_csv()
        print(f"[OK] Catálogo reconstruido con {len(res)} contratistas en {CATALOG_JSON_PATH}")
        return

    # Opción 2: Generar imágenes
    if args.generate_images:
        desde = args.id if args.id else args.desde
        hasta = args.id if args.id else (args.hasta if args.hasta != 229 or not args.id else None)
        generar_imagenes_lote(desde_id=desde, hasta_id=hasta)
        return

    # Opción 3 (Predeterminada): Ejecutar automatización de carga en Aryve
    desde = args.id if args.id else args.desde
    hasta = args.id if args.id else args.hasta

    ejecutar_automatizacion(
        desde_id=desde,
        hasta_id=hasta,
        usuario=args.user,
        password=args.password,
        headless=args.headless,
        no_pause=args.no_pause
    )


if __name__ == "__main__":
    main()

