"""
Core Domain: Servicio de Mapeo de Lotes y Centros de Costos (Enkontrol / Aryve).
Permite consultas O(1) e instantáneas de:
- CC (Centro de Costos / Obra)
- MANZANA
- LOTE
- NÚMERO INTERIOR (No Int)
- ID LOTE EK (ej. 570345)
- Metadatos: Calle, Fraccionamiento, Modelo/Prototipo, Mts Terreno, Estatus.
- Cobertura completa: Comercial (sm_fraccionamiento_lote) + Obras (su_lotes).
"""

import os
import sqlite3
import time
import threading
import re
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mapeo_lotes.db")
DB_EK10_PATH = os.path.join(DATA_DIR, "ek10_homologacion_ubicaciones.sqlite")

_hilo_daemon_mapeo = None
_detener_daemon_mapeo = False

# ========================================================
# TABLAS DE HASH EN MEMORIA RAM (LOOKUP O(1) ULTRA-RÁPIDO)
# ========================================================
_cache_ek10_iniciado = False
_cache_ek10_lock = threading.Lock()
_cache_ek10_by_id_enk: Dict[str, Dict[str, Any]] = {}
_cache_ek10_by_clave: Dict[str, Dict[str, Any]] = {}
_cache_ek10_by_id_ek10: Dict[str, Dict[str, Any]] = {}
_cache_ek10_by_cc_mza_lote_int: Dict[tuple, Dict[str, Any]] = {}
_cache_ek10_by_cc_mza_lote: Dict[tuple, Dict[str, Any]] = {}

_regex_ek10_clave = re.compile(r'^(?:[A-Z0-9]+)-M([A-Z0-9]+)-L([A-Z0-9]+)-N([A-Z0-9]+)', re.IGNORECASE)

def _init_ek10_cache():
    global _cache_ek10_iniciado
    if _cache_ek10_iniciado:
        return
    with _cache_ek10_lock:
        if _cache_ek10_iniciado:
            return
        if not os.path.exists(DB_EK10_PATH):
            _cache_ek10_iniciado = True
            return
        try:
            conn_ek10 = sqlite3.connect(DB_EK10_PATH)
            conn_ek10.row_factory = sqlite3.Row
            cur = conn_ek10.cursor()
            cur.execute("""
                SELECT id_mapeo, compania_clave, compania_nombre, id_ek10, clave_ek10, nombre_ek10, id_enk, informacion_enk
                FROM homologacion_ubicaciones
            """)
            for r in cur.fetchall():
                id_enk_str = str(r["id_enk"] or "").strip()
                id_ek10_str = str(r["id_ek10"] or "").strip()
                clave_raw = str(r["clave_ek10"] or "").strip().upper()

                m = _regex_ek10_clave.search(clave_raw)
                if m:
                    mza_val = m.group(1).lstrip("0") or "0"
                    lote_val = m.group(2).lstrip("0") or "0"
                    noint_val = m.group(3).lstrip("0") or "0"
                else:
                    mza_val = ""
                    lote_val = ""
                    noint_val = ""

                item = {
                    "id_mapeo": r["id_mapeo"],
                    "cia_cve": r["compania_clave"] or "",
                    "cia_nom": r["compania_nombre"] or "",
                    "id_ek10": r["id_ek10"],
                    "clave_ek10": clave_raw,
                    "manzana": mza_val,
                    "lote": lote_val,
                    "no_int": noint_val,
                    "nombre_ek10": r["nombre_ek10"] or "",
                    "id_enk": id_enk_str,
                    "informacion_enk": r["informacion_enk"] or ""
                }
                if id_enk_str:
                    _cache_ek10_by_id_enk[id_enk_str] = item
                if id_ek10_str:
                    _cache_ek10_by_id_ek10[id_ek10_str] = item
                if clave_raw:
                    _cache_ek10_by_clave[clave_raw] = item
                    if clave_raw.startswith("C") and len(clave_raw) > 1:
                        _cache_ek10_by_clave[clave_raw[1:]] = item

                if m:
                    cc_raw = clave_raw.split("-")[0]
                    cc_clean = cc_raw[1:] if cc_raw.startswith("C") and len(cc_raw) > 1 else cc_raw
                    for cc_k in {cc_clean, cc_raw}:
                        k_int = (cc_k, mza_val, lote_val, noint_val)
                        k_lot = (cc_k, mza_val, lote_val)

                        if k_int not in _cache_ek10_by_cc_mza_lote_int or (id_enk_str and not _cache_ek10_by_cc_mza_lote_int[k_int].get("id_enk")):
                            _cache_ek10_by_cc_mza_lote_int[k_int] = item

                        if k_lot not in _cache_ek10_by_cc_mza_lote or (id_enk_str and not _cache_ek10_by_cc_mza_lote[k_lot].get("id_enk")):
                            _cache_ek10_by_cc_mza_lote[k_lot] = item

            conn_ek10.close()
        except Exception as e:
            print("Error cargando hash table de homologaciones EK10:", e)
        finally:
            _cache_ek10_iniciado = True


class MapeoService:
    @staticmethod
    def generar_clave_lote(cc: Any, manzana: Any, lote: Any, no_int: Any) -> str:
        """
        Genera la clave estándar única del lote con formato compuesto:
        [CC]-M[MZA]-L[LOTE]-N[INT]
        Ejemplo: CCOU-M010-L0114-N00114D1 o CKC9-M028-L0006-N000002D
        """
        cc_str = str(cc or "").strip().upper() or "000"
        mza_raw = str(manzana or "").strip()
        if mza_raw.upper().startswith("M"):
            mza_raw = mza_raw[1:].strip()
        if mza_raw.isdigit():
            mza_fmt = f"M{int(mza_raw):03d}"
        else:
            mza_fmt = f"M{mza_raw.zfill(3)}" if mza_raw else "M000"

        lote_raw = str(lote or "").strip()
        if lote_raw.upper().startswith("L"):
            lote_raw = lote_raw[1:].strip()
        if lote_raw.isdigit():
            lote_fmt = f"L{int(lote_raw):04d}"
        else:
            lote_fmt = f"L{lote_raw.zfill(4)}" if lote_raw else "L0000"

        int_raw = str(no_int or "").strip()
        if int_raw.upper().startswith("N"):
            int_raw = int_raw[1:].strip()
        if int_raw and int_raw not in ("0", "-", "000", "0000"):
            int_fmt = f"N{int_raw.zfill(7)}"
        else:
            int_fmt = "N0000000"

        return f"{cc_str}-{mza_fmt}-{lote_fmt}-{int_fmt}"

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        if not os.path.exists(DB_PATH):
            cls.sincronizar_desde_enkontrol()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def obtener_resumen(cls) -> Dict[str, Any]:
        """Retorna estadísticas generales y el catálogo único de CCs para filtros rápidos."""
        try:
            conn = cls._get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT cc) FROM lotes_mapeo")
            tot_lotes, tot_ccs = cur.fetchone()
            
            cur.execute("SELECT DISTINCT cc FROM lotes_mapeo WHERE cc != '' ORDER BY cc ASC")
            lista_ccs = [r[0] for r in cur.fetchall()]
            
            cur.execute("SELECT valor FROM meta WHERE clave = 'fecha_sincronizacion'")
            meta_fecha = cur.fetchone()
            fecha_sync = meta_fecha[0] if meta_fecha else "-"
            
            conn.close()
            return {
                "ok": True,
                "total_lotes": tot_lotes or 0,
                "total_ccs": tot_ccs or 0,
                "catalogo_ccs": lista_ccs,
                "fecha_sincronizacion": fecha_sync
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "total_lotes": 0,
                "total_ccs": 0,
                "catalogo_ccs": [],
                "fecha_sincronizacion": "-"
            }

    @classmethod
    def consultar_lotes(
        cls,
        cc: Optional[str] = None,
        manzana: Optional[str] = None,
        lote: Optional[str] = None,
        no_int: Optional[str] = None,
        id_lote_ek: Optional[str] = None,
        busqueda: Optional[str] = None,
        limite: int = 150,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Consulta rápida con soporte para filtros directos de CC, Manzana, Lote, No. Int, Id EK
        y búsqueda libre combinada EK9 + EK10.
        """
        try:
            _init_ek10_cache()
            conn = cls._get_connection()
            cur = conn.cursor()

            clauses = []
            params = []

            # 1. Filtro por CC
            if cc and cc.strip() and cc.strip().upper() != 'TODOS':
                clauses.append("cc = ?")
                params.append(cc.strip().upper())

            # 2. Filtro por Manzana
            if manzana and manzana.strip():
                clauses.append("manzana = ?")
                params.append(manzana.strip())

            # 3. Filtro por Lote
            if lote and lote.strip():
                clauses.append("lote = ?")
                params.append(lote.strip())

            # 4. Filtro por No. Interior
            if no_int and no_int.strip():
                clauses.append("no_int = ?")
                params.append(no_int.strip())

            # 5. Filtro por Id Lote EK o ID EK10 (Búsqueda Dual)
            if id_lote_ek and id_lote_ek.strip():
                val_id = id_lote_ek.strip()
                id_sub_clauses = ["CAST(id_lote_ek AS TEXT) LIKE ?"]
                id_sub_params = [f"%{val_id}%"]
                
                # Si coincide con un ID de EK10 en la tabla hash, mapear a su ID ENK o clave
                if val_id in _cache_ek10_by_id_ek10:
                    matched_item = _cache_ek10_by_id_ek10[val_id]
                    if matched_item.get("id_enk"):
                        id_sub_clauses.append("CAST(id_lote_ek AS TEXT) = ?")
                        id_sub_params.append(matched_item["id_enk"])
                    if matched_item.get("clave_ek10"):
                        id_sub_clauses.append("clave_lote LIKE ?")
                        id_sub_params.append(f"%{matched_item['clave_ek10']}%")
                        if matched_item['clave_ek10'].startswith("C"):
                            id_sub_params.append(f"%{matched_item['clave_ek10'][1:]}%")
                            id_sub_clauses.append("clave_lote LIKE ?")
                clauses.append(f"({' OR '.join(id_sub_clauses)})")
                params.extend(id_sub_params)

            # 6. Búsqueda libre general (Cualquier texto, Clave EK9 o Clave/Nombre EK10)
            if busqueda and busqueda.strip():
                q_raw = busqueda.strip()
                q = f"%{q_raw}%"
                sub_busqueda = [
                    "cc LIKE ?",
                    "clave_lote LIKE ?",
                    "CAST(id_lote_ek AS TEXT) LIKE ?",
                    "lote LIKE ?",
                    "manzana LIKE ?",
                    "no_int LIKE ?",
                    "calle LIKE ?",
                    "fraccionamiento LIKE ?",
                    "modelo_vivienda LIKE ?"
                ]
                busq_params = [q] * len(sub_busqueda)
                
                # Revisar si coincide con nombres o claves de EK10 en la tabla hash
                q_upper = q_raw.upper()
                ids_enk_match = []
                for cve, it in _cache_ek10_by_clave.items():
                    if q_upper in cve or q_upper in it.get("nombre_ek10", "").upper() or q_upper in it.get("informacion_enk", "").upper():
                        if it.get("id_enk"):
                            ids_enk_match.append(it["id_enk"])
                        if len(ids_enk_match) >= 100:
                            break
                if ids_enk_match:
                    placeholders = ",".join(["?"] * len(ids_enk_match))
                    sub_busqueda.append(f"CAST(id_lote_ek AS TEXT) IN ({placeholders})")
                    busq_params.extend(ids_enk_match)

                clauses.append(f"({' OR '.join(sub_busqueda)})")
                params.extend(busq_params)

            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

            # Conteo total filtrado
            cur.execute(f"SELECT COUNT(*) FROM lotes_mapeo {where_sql}", params)
            total_filtrados = cur.fetchone()[0]

            # Registros paginados
            query_sql = f"""
                SELECT 
                    cc, 
                    id_lote_ek, 
                    id_lote, 
                    no_int, 
                    lote, 
                    manzana, 
                    calle, 
                    cve_fracc, 
                    fraccionamiento, 
                    modelo_vivienda, 
                    mts_terreno, 
                    mts_exced, 
                    estatus,
                    clave_lote
                FROM lotes_mapeo
                {where_sql}
                ORDER BY (CASE WHEN cc IS NULL OR TRIM(cc) = '' THEN 1 ELSE 0 END) ASC, cc ASC, CAST(manzana AS INTEGER) ASC, manzana ASC, CAST(lote AS INTEGER) ASC, lote ASC
                LIMIT ? OFFSET ?
            """
            cur.execute(query_sql, params + [min(limite, 500), max(offset, 0)])
            rows = cur.fetchall()

            resultado = []
            total_homologados_pag = 0
            for r in rows:
                id_ek_str = str(r["id_lote_ek"] or "").strip()
                cve_lote = (
                    r["clave_lote"]
                    if "clave_lote" in r.keys() and r["clave_lote"]
                    else cls.generar_clave_lote(r["cc"], r["manzana"], r["lote"], r["no_int"])
                )
                cve_upper = (cve_lote or "").strip().upper()
                cc_clean = str(r["cc"] or "").strip().upper()
                mza_clean = str(r["manzana"] or "").strip().lstrip("0") or "0"
                lote_clean = str(r["lote"] or "").strip().lstrip("0") or "0"
                noint_clean = str(r["no_int"] or "").strip().lstrip("0") or "0"

                # Lookup O(1) instantáneo y jerárquico en hash table:
                # 1. Por ID ENK oficial (coincidencia de ID)
                # 2. Por Clave Consecutivo exacto (con o sin 'C')
                # 3. Por Ubicación (CC, Manzana, Lote, No. Int)
                # 4. Por Ubicación (CC, Manzana, Lote) para ver todas las claves
                ek10 = (
                    _cache_ek10_by_id_enk.get(id_ek_str) or
                    _cache_ek10_by_clave.get(cve_upper) or
                    _cache_ek10_by_clave.get(f"C{cve_upper}") or
                    _cache_ek10_by_cc_mza_lote_int.get((cc_clean, mza_clean, lote_clean, noint_clean)) or
                    _cache_ek10_by_cc_mza_lote.get((cc_clean, mza_clean, lote_clean))
                )
                
                homologado = bool(ek10)
                coincide_id = False
                if ek10 and ek10.get("id_enk"):
                    coincide_id = (str(ek10["id_enk"]).strip() == id_ek_str)

                if homologado:
                    total_homologados_pag += 1

                resultado.append({
                    "cc": r["cc"],
                    "id_lote_ek": r["id_lote_ek"],
                    "id_lote": r["id_lote"],
                    "lote_id_sun": r["id_lote"],
                    "no_int": r["no_int"],
                    "lote": r["lote"],
                    "manzana": r["manzana"],
                    "calle": r["calle"],
                    "cve_fracc": r["cve_fracc"],
                    "fraccionamiento": r["fraccionamiento"],
                    "modelo": r["modelo_vivienda"],
                    "mts_terreno": r["mts_terreno"],
                    "mts_exced": r["mts_exced"],
                    "estatus": r["estatus"],
                    "clave_lote": cve_lote,
                    # Campos Homologación EK10 O(1)
                    "ek10_id": ek10["id_ek10"] if ek10 else None,
                    "ek10_id_enk": ek10.get("id_enk", "") if ek10 else "",
                    "ek10_clave": ek10["clave_ek10"] if ek10 else "",
                    "ek10_manzana": ek10["manzana"] if ek10 else "",
                    "ek10_lote": ek10["lote"] if ek10 else "",
                    "ek10_no_int": ek10["no_int"] if ek10 else "",
                    "ek10_nombre": ek10["nombre_ek10"] if ek10 else "",
                    "ek10_info_enk": ek10["informacion_enk"] if ek10 else "",
                    "ek10_cia": ek10["cia_cve"] if ek10 else "",
                    "ek10_cia_nom": ek10["cia_nom"] if ek10 else "",
                    "ek10_homologado": homologado,
                    "ek10_coincide_id": coincide_id
                })

            conn.close()
            return {
                "ok": True,
                "total": total_filtrados,
                "total_homologados_pagina": total_homologados_pag,
                "limite": limite,
                "offset": offset,
                "registros": resultado
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "total": 0,
                "registros": []
            }

    @classmethod
    def sincronizar_desde_enkontrol(cls) -> Dict[str, Any]:
        """
        Extrae en vivo el universo completo de lotes desde el servidor Enkontrol (10.10.202.244).
        Combina la tabla de comercial/ventas (sm_fraccionamiento_lote) con la de obra física (su_lotes)
        para asegurar cobertura 100% total (116k+ lotes).
        """
        try:
            import pyodbc
            conn_ek = pyodbc.connect(
                "Driver={SQL Anywhere 11};"
                "EngineName=especial_v9;"
                "DatabaseName=EK_ADM01_11;"
                "CommLinks=tcpip(host=10.10.202.244:2544);"
                "UID=user_write;"
                "PWD=writaryb0904##;",
                timeout=12,
                readonly=True
            )
            cur_ek = conn_ek.cursor()
            query = """
            SELECT 
                l.obra                 AS cc,
                CAST(l.lote_id AS BIGINT) AS id_lote_ek,
                COALESCE(l.lote_id_sun, 0) AS id_lote,
                COALESCE(l.id_num_interior, '') AS no_int,
                COALESCE(l.id_num_lote, '') AS lote,
                COALESCE(l.id_num_mza, '') AS manzana,
                COALESCE(l.dir_casa, '') AS calle,
                COALESCE(f.id_cve_fracc, '') AS cve_fracc,
                COALESCE(f.nom_fracc, '') AS fraccionamiento,
                COALESCE(p.nom_tipocasa, '') AS modelo_vivienda,
                COALESCE(l.cant_superficie, 0) AS mts_terreno,
                COALESCE(l.cant_mts_excedente, 0) AS mts_exced,
                COALESCE(l.status_lote, '') AS estatus
            FROM DBA.sm_fraccionamiento_lote l
            LEFT JOIN DBA.sm_fraccionamiento f 
                ON l.id_cve_fracc = f.id_cve_fracc
            LEFT JOIN DBA.sm_prototipo p 
                ON l.id_num_tipocasa = p.id_num_tipocasa

            UNION ALL

            SELECT 
                su.obra AS cc,
                CAST(su.lote_id AS BIGINT) AS id_lote_ek,
                0 AS id_lote,
                COALESCE(su.interior, '') AS no_int,
                CAST(su.lote AS VARCHAR) AS lote,
                CAST(su.manzana AS VARCHAR) AS manzana,
                '' AS calle,
                '' AS cve_fracc,
                'OBRA / SUBCONTRATO' AS fraccionamiento,
                COALESCE(p.nom_tipocasa, '') AS modelo_vivienda,
                0.0 AS mts_terreno,
                0.0 AS mts_exced,
                'Obra' AS estatus
            FROM DBA.su_lotes su
            LEFT JOIN DBA.sm_fraccionamiento_lote sm ON su.lote_id = sm.lote_id
            LEFT JOIN DBA.sm_prototipo p ON su.id_num_tipocasa_smc = p.id_num_tipocasa
            WHERE sm.lote_id IS NULL

            ORDER BY 1 ASC, 6 ASC, 5 ASC
            """
            cur_ek.execute(query)
            rows = cur_ek.fetchall()
            conn_ek.close()

            os.makedirs(DATA_DIR, exist_ok=True)
            conn_local = sqlite3.connect(DB_PATH)
            cur_local = conn_local.cursor()

            cur_local.execute("DROP TABLE IF EXISTS lotes_mapeo")
            cur_local.execute("""
            CREATE TABLE lotes_mapeo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc TEXT NOT NULL,
                id_lote_ek INTEGER NOT NULL,
                id_lote INTEGER,
                no_int TEXT,
                lote TEXT,
                manzana TEXT,
                calle TEXT,
                cve_fracc TEXT,
                fraccionamiento TEXT,
                modelo_vivienda TEXT,
                mts_terreno REAL,
                mts_exced REAL,
                estatus TEXT,
                clave_lote TEXT
            )
            """)
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_cc ON lotes_mapeo(cc)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_ek ON lotes_mapeo(id_lote_ek)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_mza_lote ON lotes_mapeo(cc, manzana, lote)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_noint ON lotes_mapeo(cc, no_int)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_calle ON lotes_mapeo(calle)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_fracc ON lotes_mapeo(fraccionamiento)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_clave_lote ON lotes_mapeo(clave_lote)")

            insert_data = [
                (
                    str(r[0] or '').strip().upper(),
                    int(r[1] or 0),
                    int(r[2] or 0),
                    str(r[3] or '').strip(),
                    str(r[4] or '').strip(),
                    str(r[5] or '').strip(),
                    str(r[6] or '').strip(),
                    str(r[7] or '').strip(),
                    str(r[8] or '').strip(),
                    str(r[9] or '').strip(),
                    float(r[10] or 0),
                    float(r[11] or 0),
                    str(r[12] or '').strip(),
                    cls.generar_clave_lote(r[0], r[5], r[4], r[3])
                )
                for r in rows
            ]
            cur_local.executemany("""
            INSERT INTO lotes_mapeo (
                cc, id_lote_ek, id_lote, no_int, lote, manzana, calle, cve_fracc, fraccionamiento, modelo_vivienda, mts_terreno, mts_exced, estatus, clave_lote
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, insert_data)

            cur_local.execute("CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT)")
            cur_local.execute("INSERT OR REPLACE INTO meta VALUES ('total_lotes', ?)", (str(len(rows)),))
            fecha_now = time.strftime('%Y-%m-%d %H:%M:%S')
            cur_local.execute("INSERT OR REPLACE INTO meta VALUES ('fecha_sincronizacion', ?)", (fecha_now,))
            conn_local.commit()
            conn_local.close()

            print(f"[MAPEO SYNC] Base de lotes actualizada con éxito: {len(rows):,} registros.")
            return {
                "ok": True,
                "mensaje": f"Mapeo sincronizado exitosamente con {len(rows):,} lotes de Enkontrol.",
                "total_lotes": len(rows),
                "fecha": fecha_now
            }
        except Exception as e:
            err_msg = f"Error sincronizando con Enkontrol: {str(e)}"
            print(f"[MAPEO SYNC ERROR] {err_msg}")
            return {"ok": False, "error": err_msg}

    @classmethod
    def verificar_y_actualizar_si_hay_cambios(cls) -> bool:
        """
        Comprobación ligera (0.2s) para verificar si Enkontrol recibió nuevos lotes.
        Si la cantidad cambió respecto a la base local, dispara la sincronización automática.
        """
        try:
            import pyodbc
            conn_ek = pyodbc.connect(
                "Driver={SQL Anywhere 11};"
                "EngineName=especial_v9;"
                "DatabaseName=EK_ADM01_11;"
                "CommLinks=tcpip(host=10.10.202.244:2544);"
                "UID=user_write;"
                "PWD=writaryb0904##;",
                timeout=5,
                readonly=True
            )
            cur_ek = conn_ek.cursor()
            cur_ek.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM DBA.sm_fraccionamiento_lote) + 
                    (SELECT COUNT(*) FROM DBA.su_lotes su LEFT JOIN DBA.sm_fraccionamiento_lote sm ON su.lote_id = sm.lote_id WHERE sm.lote_id IS NULL)
            """)
            total_remoto = cur_ek.fetchone()[0]
            conn_ek.close()

            # Comparar con local
            if not os.path.exists(DB_PATH):
                cls.sincronizar_desde_enkontrol()
                return True

            conn_local = sqlite3.connect(DB_PATH)
            cur_loc = conn_local.cursor()
            cur_loc.execute("SELECT COUNT(*) FROM lotes_mapeo")
            total_local = cur_loc.fetchone()[0]
            conn_local.close()

            if total_remoto != total_local:
                print(f"[MAPEO AUTO-SYNC] Se detectaron nuevos lotes en Enkontrol (Remoto: {total_remoto:,} vs Local: {total_local:,}). Actualizando...")
                cls.sincronizar_desde_enkontrol()
                return True
            return False
        except Exception as e:
            # En caso de error de red o timeout, no interrumpir la ejecución
            return False

    @classmethod
    def iniciar_demonio_mapeo(cls, intervalo_minutos: int = 30):
        """Inicia un hilo daemon que revisa silenciosamente cada X minutos si hay nuevos lotes."""
        global _hilo_daemon_mapeo, _detener_daemon_mapeo
        if _hilo_daemon_mapeo is not None and _hilo_daemon_mapeo.is_alive():
            return

        def _bucle():
            print(f"[DAEMON MAPEO] Auto-actualizador de lotes iniciado (revisión cada {intervalo_minutos}m)...")
            while not _detener_daemon_mapeo:
                try:
                    time.sleep(intervalo_minutos * 60)
                    if _detener_daemon_mapeo:
                        break
                    cls.verificar_y_actualizar_si_hay_cambios()
                except Exception as ex:
                    print(f"[DAEMON MAPEO ERROR] {ex}")

        _detener_daemon_mapeo = False
        _hilo_daemon_mapeo = threading.Thread(
            target=_bucle,
            name="DemonioMapeoLotes",
            daemon=True
        )
        _hilo_daemon_mapeo.start()
