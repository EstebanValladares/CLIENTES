"""
Herramientas Ejecutables (Tools / Function Calling) del Asistente Centinela.
Permite al asistente realizar consultas, auditorías y diagnósticos en tiempo real sobre la base local.
"""

import sqlite3
import os
from typing import Dict, Any, List
from ASISTENTE.config import DB_MAPEO_PATH, DB_ESC_PATH
from ASISTENTE.cerebro.grafo_conocimiento import GrafoConocimiento
from ASISTENTE.cerebro.aprendizaje import ModuloAprendizaje


def tool_consultar_obra(cc: str) -> Dict[str, Any]:
    """Diagnostica la salud de una obra, sus lotes y su sincronización entre EK9 y EK10."""
    return GrafoConocimiento.diagnosticar_obra(cc)


def tool_buscar_lotes(cc: str, manzana: str = "", limite: int = 10) -> Dict[str, Any]:
    """Busca lotes específicos de un Centro de Costo (Obra) para ver sus claves EK9 y EK10."""
    if not os.path.exists(DB_MAPEO_PATH):
        return {"ok": False, "error": "Base de datos de lotes no disponible"}

    try:
        conn = sqlite3.connect(DB_MAPEO_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = "SELECT cc, manzana, lote, no_int, id_lote_ek, id_ek10, clave_ek9, clave_ek10 FROM lotes_mapeo WHERE cc = ?"
        params = [cc.strip().upper()]

        if manzana:
            query += " AND manzana = ?"
            params.append(str(manzana).strip())

        query += " ORDER BY CAST(manzana AS INTEGER), CAST(lote AS INTEGER) LIMIT ?"
        params.append(limite)

        rows = [dict(r) for r in cur.execute(query, params).fetchall()]
        conn.close()

        return {
            "ok": True,
            "obra": cc,
            "total_encontrados": len(rows),
            "lotes": rows
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_consultar_escalatorias() -> Dict[str, Any]:
    """Consulta las últimas escalatorias de precios autorizadas en Enkontrol SOC."""
    if not os.path.exists(DB_ESC_PATH):
        return {"ok": False, "error": "Base de datos de escalatorias no disponible"}

    try:
        conn = sqlite3.connect(DB_ESC_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = [dict(r) for r in cur.execute("""
            SELECT id, clave, nombre, estatus_desc, fecha_autorizacion, numero_insumos
            FROM escalatorias
            ORDER BY id DESC
            LIMIT 5
        """).fetchall()]
        conn.close()

        return {"ok": True, "escalatorias_recientes": rows}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_buscar_conocimiento(consulta: str) -> Dict[str, Any]:
    """Busca en los documentos, manuales y notas aprendidas por el asistente."""
    resultados = ModuloAprendizaje.buscar_en_conocimiento(consulta, limite=5)
    return {"ok": True, "consulta": consulta, "documentos": resultados}


CATALOGO_HERRAMIENTAS = {
    "consultar_obra": tool_consultar_obra,
    "buscar_lotes": tool_buscar_lotes,
    "consultar_escalatorias": tool_consultar_escalatorias,
    "buscar_conocimiento": tool_buscar_conocimiento
}
