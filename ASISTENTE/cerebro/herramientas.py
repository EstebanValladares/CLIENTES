"""
Herramientas Ejecutables (Tools / Function Calling) del Asistente Centinela.
Permite al asistente realizar consultas, auditorías y diagnósticos en tiempo real sobre la base local.
"""

import sqlite3
import os
import json
import re
from typing import Dict, Any, List
from ASISTENTE.config import DB_MAPEO_PATH, DB_ESC_PATH, BASE_DIR
from ASISTENTE.cerebro.grafo_conocimiento import GrafoConocimiento
from ASISTENTE.cerebro.aprendizaje import ModuloAprendizaje

PATH_USUARIOS_JSON = os.path.join(BASE_DIR, "USUARIOS", "data", "Usuarios.json")
PATH_PUESTOS_JSON = os.path.join(BASE_DIR, "USUARIOS", "data", "puestos.json")
DB_EK10_PATH = os.path.join(BASE_DIR, "data", "ek10_homologacion_ubicaciones.sqlite")


def tool_metricas_totales() -> Dict[str, Any]:
    """Obtiene los números y métricas oficiales de todos los módulos del Dashboard."""
    metricas = {
        "usuarios_totales": 0,
        "usuarios_activos": 0,
        "puestos_totales": 0,
        "obras_totales": 0,
        "lotes_totales": 0,
        "lotes_ek10_totales": 0,
        "escalatorias_totales": 0,
        "areas_principales": {}
    }

    # 1. Usuarios y Áreas
    if os.path.exists(PATH_USUARIOS_JSON):
        try:
            with open(PATH_USUARIOS_JSON, "r", encoding="utf-8") as f:
                u_list = json.load(f)
                metricas["usuarios_totales"] = len(u_list)
                metricas["usuarios_activos"] = sum(1 for u in u_list if str(u.get("Estatus", "")).strip().lower() == "activo")
                
                # Conteo por área
                areas = {}
                for u in u_list:
                    a = u.get("AreaOrganizacion") or "General"
                    areas[a] = areas.get(a, 0) + 1
                metricas["areas_principales"] = dict(sorted(areas.items(), key=lambda x: x[1], reverse=True)[:6])
        except Exception:
            pass

    # 2. Puestos
    if os.path.exists(PATH_PUESTOS_JSON):
        try:
            with open(PATH_PUESTOS_JSON, "r", encoding="utf-8") as f:
                p_data = json.load(f)
                metricas["puestos_totales"] = p_data.get("total_posiciones", 230)
        except Exception:
            metricas["puestos_totales"] = 230

    # 3. Lotes y Obras
    if os.path.exists(DB_MAPEO_PATH):
        try:
            conn = sqlite3.connect(DB_MAPEO_PATH)
            cur = conn.cursor()
            metricas["lotes_totales"] = cur.execute("SELECT COUNT(*) FROM lotes_mapeo").fetchone()[0]
            metricas["obras_totales"] = cur.execute("SELECT COUNT(DISTINCT cc) FROM lotes_mapeo").fetchone()[0]
            conn.close()
        except Exception:
            pass

    # 4. Homologaciones EK10
    if os.path.exists(DB_EK10_PATH):
        try:
            conn = sqlite3.connect(DB_EK10_PATH)
            metricas["lotes_ek10_totales"] = conn.execute("SELECT COUNT(*) FROM homologacion_ubicaciones").fetchone()[0]
            conn.close()
        except Exception:
            pass

    # 5. Escalatorias
    if os.path.exists(DB_ESC_PATH):
        try:
            conn = sqlite3.connect(DB_ESC_PATH)
            metricas["escalatorias_totales"] = conn.execute("SELECT COUNT(*) FROM escalatorias").fetchone()[0]
            conn.close()
        except Exception:
            pass

    return metricas


def tool_buscar_usuarios_por_area(area_o_puesto: str, limite: int = 6) -> List[Dict[str, Any]]:
    """Busca colaboradores por área (ej. Sistemas, Ventas, Obra, Titulación) o puesto."""
    if not os.path.exists(PATH_USUARIOS_JSON):
        return []
    try:
        with open(PATH_USUARIOS_JSON, "r", encoding="utf-8") as f:
            usuarios = json.load(f)
        q = area_o_puesto.strip().lower()
        matches = []
        for u in usuarios:
            a = str(u.get("AreaOrganizacion", "")).lower()
            p = str(u.get("Posicion", "")).lower()
            if q in a or q in p:
                nom = f"{u.get('Nombre','')} {u.get('Apellidos','')}".strip()
                matches.append({
                    "nombre": nom,
                    "puesto": u.get("Posicion"),
                    "area": u.get("AreaOrganizacion"),
                    "email": u.get("Email") or u.get("Clave"),
                    "estatus": u.get("Estatus")
                })
        return matches[:limite]
    except Exception:
        return []


def tool_buscar_usuario(consulta: str, limite: int = 5) -> Dict[str, Any]:
    """Busca usuarios, colaboradores, puestos y correos en la base oficial de Grupo Velas."""
    if not os.path.exists(PATH_USUARIOS_JSON):
        return {"ok": False, "error": "Archivo Usuarios.json no encontrado", "total": 0, "usuarios": []}

    try:
        with open(PATH_USUARIOS_JSON, "r", encoding="utf-8") as f:
            usuarios = json.load(f)

        stop_words = {
            "sabes", "si", "tenemos", "un", "una", "usuario", "usuarios", "llamado", "llamada",
            "persona", "personas", "colaborador", "colaboradores", "compañero", "compañera",
            "quien", "quién", "es", "el", "la", "los", "las", "de", "en", "a", "por", "favor",
            "dime", "busca", "buscar", "contacto", "correo", "email", "trabaja", "cuantos",
            "cuántos", "hay", "guardados", "registrados", "activos"
        }

        tokens = [w for w in re.findall(r"\w+", consulta.lower()) if w not in stop_words and len(w) > 2]
        if not tokens:
            return {"ok": True, "total": 0, "usuarios": []}

        coincidencias = []
        for u in usuarios:
            nom_comp = f"{u.get('Nombre','')} {u.get('Apellidos','')}".strip()
            texto_completo = f"{nom_comp} {u.get('Email','')} {u.get('Clave','')} {u.get('Posicion','')} {u.get('AreaOrganizacion','')}".lower()

            if all(t in texto_completo for t in tokens):
                coincidencias.append({
                    "id": u.get("ID"),
                    "nombre_completo": nom_comp,
                    "puesto": u.get("Posicion") or "Sin puesto asignado",
                    "area": u.get("AreaOrganizacion") or "General",
                    "email": u.get("Email") or u.get("Clave"),
                    "telefono": u.get("Telefono") or "No registrado",
                    "estatus": u.get("Estatus") or "Activo"
                })

        return {
            "ok": True,
            "total": len(coincidencias),
            "usuarios": coincidencias[:limite]
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "total": 0, "usuarios": []}


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

        query = "SELECT cc, manzana, lote, no_int, id_lote_ek, clave_lote FROM lotes_mapeo WHERE cc = ?"
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
