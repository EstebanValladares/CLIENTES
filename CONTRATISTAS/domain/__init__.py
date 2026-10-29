"""Servicios de Dominio para Contratistas."""
from .text_processor import (
    process_contractor_name,
    normalize_text,
    strip_accents,
    remove_legal_suffixes,
    remove_system_prefixes,
    is_corporate_entity,
    extract_person_name,
    group_lines_smartly,
)
from .image_generator import (
    create_contractor_badge,
    generate_badge_for_contractor,
    find_system_font,
    calculate_optimal_font_size,
)
from .catalog_service import (
    load_mapped_catalog,
    get_contractor_by_id,
    get_contractors_range,
    build_catalog_from_csv,
)

__all__ = [
    "process_contractor_name",
    "normalize_text",
    "strip_accents",
    "remove_legal_suffixes",
    "remove_system_prefixes",
    "is_corporate_entity",
    "extract_person_name",
    "group_lines_smartly",
    "create_contractor_badge",
    "generate_badge_for_contractor",
    "find_system_font",
    "calculate_optimal_font_size",
    "load_mapped_catalog",
    "get_contractor_by_id",
    "get_contractors_range",
    "build_catalog_from_csv",
]

