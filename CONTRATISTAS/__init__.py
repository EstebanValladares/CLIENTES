"""
Paquete Oficial CONTRATISTAS - Dashboard EK10.
"""

from .config.settings import (
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    OUTPUT_DIR,
    CATALOG_JSON_PATH,
    SOURCE_CSV_PATH,
    resolver_credenciales,
)

from .domain.text_processor import (
    process_contractor_name,
    normalize_text,
    strip_accents,
    remove_legal_suffixes,
    remove_system_prefixes,
)

from .domain.image_generator import (
    create_contractor_badge,
    generate_badge_for_contractor,
)

from .domain.catalog_service import (
    load_mapped_catalog,
    get_contractor_by_id,
    get_contractors_range,
    build_catalog_from_csv,
)

from .automation.contractor_bot import ContractorBot
from .automation.driver_factory import build_chrome_driver

# Aliases de compatibilidad
select_relevant_name = process_contractor_name
create_contractor_image = create_contractor_badge

__all__ = [
    "CANVAS_WIDTH",
    "CANVAS_HEIGHT",
    "BACKGROUND_COLOR",
    "TEXT_COLOR",
    "OUTPUT_DIR",
    "CATALOG_JSON_PATH",
    "SOURCE_CSV_PATH",
    "resolver_credenciales",
    "process_contractor_name",
    "select_relevant_name",
    "normalize_text",
    "strip_accents",
    "remove_legal_suffixes",
    "remove_system_prefixes",
    "create_contractor_badge",
    "create_contractor_image",
    "generate_badge_for_contractor",
    "load_mapped_catalog",
    "get_contractor_by_id",
    "get_contractors_range",
    "build_catalog_from_csv",
    "ContractorBot",
    "build_chrome_driver",
]
