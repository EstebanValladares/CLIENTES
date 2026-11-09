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
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mapeo_lotes.db")

_hilo_daemon_mapeo = None
_detener_daemon_mapeo = False


class MapeoService:
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
        y búsqueda libre.
        """
        try:
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

            # 5. Filtro por Id Lote EK
            if id_lote_ek and id_lote_ek.strip():
                clauses.append("CAST(id_lote_ek AS TEXT) LIKE ?")
                params.append(f"%{id_lote_ek.strip()}%")

            # 6. Búsqueda libre general (Cualquier texto)
            if busqueda and busqueda.strip():
                q = f"%{busqueda.strip()}%"
                clauses.append("""
                    (
                        cc LIKE ? OR 
                        CAST(id_lote_ek AS TEXT) LIKE ? OR 
                        lote LIKE ? OR 
                        manzana LIKE ? OR 
                        no_int LIKE ? OR 
                        calle LIKE ? OR 
                        fraccionamiento LIKE ? OR 
                        modelo_vivienda LIKE ?
                    )
                """)
                params.extend([q, q, q, q, q, q, q, q])

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
                    estatus
                FROM lotes_mapeo
                {where_sql}
                ORDER BY (CASE WHEN cc IS NULL OR TRIM(cc) = '' THEN 1 ELSE 0 END) ASC, cc ASC, manzana ASC, lote ASC
                LIMIT ? OFFSET ?
            """
            cur.execute(query_sql, params + [min(limite, 500), max(offset, 0)])
            rows = cur.fetchall()

            resultado = [
                {
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
                    "estatus": r["estatus"]
                }
                for r in rows
            ]

            conn.close()
            return {
                "ok": True,
                "total": total_filtrados,
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
                estatus TEXT
            )
            """)
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_cc ON lotes_mapeo(cc)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_ek ON lotes_mapeo(id_lote_ek)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_mza_lote ON lotes_mapeo(cc, manzana, lote)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_noint ON lotes_mapeo(cc, no_int)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_calle ON lotes_mapeo(calle)")
            cur_local.execute("CREATE INDEX IF NOT EXISTS idx_mapeo_fracc ON lotes_mapeo(fraccionamiento)")

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
                    str(r[12] or '').strip()
                )
                for r in rows
            ]
            cur_local.executemany("""
            INSERT INTO lotes_mapeo (
                cc, id_lote_ek, id_lote, no_int, lote, manzana, calle, cve_fracc, fraccionamiento, modelo_vivienda, mts_terreno, mts_exced, estatus
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
