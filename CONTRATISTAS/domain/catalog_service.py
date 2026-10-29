"""
Domain Service: Gestión y Consulta del Catálogo de Contratistas Mapeado.
Maneja la lectura y consultas indexadas de 'contratista_mapeado.json' y la ingesta desde CSV.
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from ..config.settings import (
        CATALOG_JSON_PATH,
        SOURCE_CSV_PATH,
        DATA_DIR,
        BASE_DIR,
    )
    from .text_processor import process_contractor_name
except (ImportError, ValueError):
    from config.settings import (
        CATALOG_JSON_PATH,
        SOURCE_CSV_PATH,
        DATA_DIR,
        BASE_DIR,
    )
    from domain.text_processor import process_contractor_name


def load_mapped_catalog(catalog_path: str = CATALOG_JSON_PATH) -> List[Dict[str, Any]]:
    """Carga la lista oficial de contratistas desde contratista_mapeado.json."""
    if not os.path.exists(catalog_path):
        # Fallback a directorio base si la ruta difiere
        alt_path = os.path.join(BASE_DIR, "contratista_mapeado.json")
        if os.path.exists(alt_path):
            catalog_path = alt_path
        else:
            return []

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "contratistas" in data:
        return data["contratistas"]
    return []


def get_contractor_by_id(contractor_id: int, catalog_path: str = CATALOG_JSON_PATH) -> Optional[Dict[str, Any]]:
    """Obtiene un contratista por su ID entero en O(N)."""
    catalogo = load_mapped_catalog(catalog_path)
    for c in catalogo:
        if c.get("id") == contractor_id:
            return c
    return None


def get_contractors_range(min_id: int, max_id: int, catalog_path: str = CATALOG_JSON_PATH) -> List[Dict[str, Any]]:
    """Obtiene los contratistas cuyo ID se encuentre en el rango [min_id, max_id]."""
    catalogo = load_mapped_catalog(catalog_path)
    return [c for c in catalogo if c.get("id") is not None and min_id <= c["id"] <= max_id]


def build_catalog_from_csv(
    csv_path: Optional[str] = None,
    output_json_path: str = CATALOG_JSON_PATH
) -> List[Dict[str, Any]]:
    """
    Parsea el CSV de origen 'Contratistas (2)(Contratistas).csv' y genera 'contratista_mapeado.json'.
    Garantiza que la salida sea una lista plana directamente consumible por APIs y bots.
    """
    if csv_path is None:
        candidatos = [
            SOURCE_CSV_PATH,
            os.path.join(BASE_DIR, "Contratistas (2)(Contratistas).csv"),
            os.path.join(DATA_DIR, "Contratistas (2)(Contratistas).csv"),
        ]
        for c in candidatos:
            if os.path.exists(c):
                csv_path = c
                break

    if not csv_path or not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el archivo CSV en ninguna de las rutas esperadas.")

    registros: List[Dict[str, Any]] = []

    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            id_raw = row.get("id_contratista") or row.get("id")
            if not id_raw or not id_raw.strip().isdigit():
                continue

            id_num = int(id_raw.strip())
            nombre_raw = (row.get("nombre") or "").strip()
            clave = (row.get("clave") or "").strip()
            rfc = (row.get("rfc") or "").strip()

            analisis = process_contractor_name(nombre_raw)

            registro = {
                "id": id_num,
                "clave": clave,
                "clave_ek9": (row.get("clave_ek9") or "").strip() or None,
                "rfc": rfc,
                "nombre": nombre_raw,
                "nombre_limpio": analisis["nombre_limpio"],
                "nombre_destacado": analisis["nombre_destacado"],
                "lineas_imagen": analisis["lineas"],
                "archivo_imagen": f"{id_num}.png",
                "tipo_entidad": analisis["tipo_entidad"],
                "es_prueba": "prueba" in nombre_raw.lower() or "test" in nombre_raw.lower(),
                "id_proveedor": int(row["id_proveedor"].strip()) if row.get("id_proveedor", "").strip().isdigit() else None,
                "proveedor": (row.get("proveedor") or "").strip() or None,
                "representante": (row.get("representante") or "").strip() or None,
                "direccion": (row.get("direccion") or "").strip() or None,
                "asentamiento": (row.get("asentamiento") or "").strip() or None,
                "domicilio": (row.get("domicilio") or "").strip() or None,
                "nss": (row.get("nss") or "").strip() or None,
                "estatus": (row.get("estatus") or "").strip() or "Activo",
                "activo": (row.get("activo") or "").strip().lower() in ("true", "1", "s"),
                "regimen": (row.get("regimen") or "").strip() or None,
                "vinculo_proveedor": (row.get("vinculo_proveedor") or "").strip().lower() in ("true", "1", "s"),
                "destajista": (row.get("destajista") or "").strip().lower() in ("true", "1", "s"),
                "objeto_social": (row.get("objeto_social") or "").strip() or None,
                "foto": (row.get("foto") or "").strip() or None,
                "version": (row.get("version") or "").strip() or None,
                "creado": (row.get("creado") or "").strip() or None,
                "creado_por": (row.get("creado_por") or "").strip() or None,
                "modificado": (row.get("modificado") or "").strip() or None,
                "modificado_por": (row.get("modificado_por") or "").strip() or None,
            }
            registros.append(registro)

    registros.sort(key=lambda x: x["id"])

    # Guardar archivo oficial
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    return registros
