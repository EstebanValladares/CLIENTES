"""
Motor de Grafos de Conocimiento (Knowledge Graph) para el Asistente Centinela.
Construye relaciones semánticas entre Obras, Lotes, Centros de Costo, Escalatorias y Documentos.
100% nativo, rápido y persistido en SQLite.
"""

import os
import sqlite3
import json
import datetime
from typing import Dict, Any, List, Optional
from ASISTENTE.cerebro.config_cerebro import DB_GRAFO_PATH, DATA_DIR
from ASISTENTE.config import DB_MAPEO_PATH, DB_ESC_PATH


class GrafoConocimiento:
    _conn = None

    @classmethod
    def get_db(cls) -> sqlite3.Connection:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_GRAFO_PATH, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS nodos (
                id TEXT PRIMARY KEY,
                tipo TEXT NOT NULL,
                etiqueta TEXT NOT NULL,
                propiedades TEXT,
                fecha_creacion TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS aristas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origen_id TEXT NOT NULL,
                destino_id TEXT NOT NULL,
                relacion TEXT NOT NULL,
                peso REAL DEFAULT 1.0,
                metadata TEXT,
                fecha_creacion TEXT,
                UNIQUE(origen_id, destino_id, relacion)
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_nodos_tipo ON nodos(tipo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aristas_origen ON aristas(origen_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aristas_destino ON aristas(destino_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aristas_rel ON aristas(relacion)")

        conn.commit()
        return conn

    @classmethod
    def agregar_nodo(cls, nodo_id: str, tipo: str, etiqueta: str, propiedades: Optional[Dict[str, Any]] = None) -> None:
        conn = cls.get_db()
        cur = conn.cursor()
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        props_str = json.dumps(propiedades or {}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO nodos (id, tipo, etiqueta, propiedades, fecha_creacion)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                etiqueta = excluded.etiqueta,
                propiedades = excluded.propiedades
        """, (str(nodo_id), str(tipo).upper(), str(etiqueta), props_str, ahora))
        conn.commit()
        conn.close()

    @classmethod
    def conectar(cls, origen_id: str, destino_id: str, relacion: str, peso: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> None:
        conn = cls.get_db()
        cur = conn.cursor()
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO aristas (origen_id, destino_id, relacion, peso, metadata, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(origen_id, destino_id, relacion) DO UPDATE SET
                peso = excluded.peso,
                metadata = excluded.metadata
        """, (str(origen_id), str(destino_id), str(relacion).upper(), peso, meta_str, ahora))
        conn.commit()
        conn.close()

    @classmethod
    def obtener_vecinos(cls, nodo_id: str, relacion: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = cls.get_db()
        cur = conn.cursor()
        if relacion:
            cur.execute("""
                SELECT n.id, n.tipo, n.etiqueta, n.propiedades, a.relacion, a.peso
                FROM aristas a
                JOIN nodos n ON n.id = a.destino_id
                WHERE a.origen_id = ? AND a.relacion = ?
            """, (str(nodo_id), str(relacion).upper()))
        else:
            cur.execute("""
                SELECT n.id, n.tipo, n.etiqueta, n.propiedades, a.relacion, a.peso
                FROM aristas a
                JOIN nodos n ON n.id = a.destino_id
                WHERE a.origen_id = ?
            """, (str(nodo_id),))

        rows = cur.fetchall()
        vecinos = []
        for r in rows:
            vecinos.append({
                "id": r["id"],
                "tipo": r["tipo"],
                "etiqueta": r["etiqueta"],
                "relacion": r["relacion"],
                "peso": r["peso"],
                "propiedades": json.loads(r["propiedades"] or "{}")
            })
        conn.close()
        return vecinos

    @classmethod
    def construir_grafo_desde_sistema(cls, max_obras: int = 50) -> Dict[str, Any]:
        """Indexa automáticamente las obras y lotes de mapeo_lotes.db en el grafo."""
        if not os.path.exists(DB_MAPEO_PATH):
            return {"ok": False, "error": "mapeo_lotes.db no existe"}

        # Cargar cache de mapeo si está disponible
        from core.mapeo_service import MapeoService
        MapeoService._init_cache_si_hace_falta() if hasattr(MapeoService, '_init_cache_si_hace_falta') else None

        conn_map = sqlite3.connect(DB_MAPEO_PATH)
        conn_map.row_factory = sqlite3.Row
        cur_map = conn_map.cursor()

        # 1. Obtener centros de costo / obras
        obras = cur_map.execute("""
            SELECT cc, COUNT(*) as total_lotes
            FROM lotes_mapeo
            GROUP BY cc
            ORDER BY total_lotes DESC
            LIMIT ?
        """, (max_obras,)).fetchall()

        total_nodos_nuevos = 0
        total_aristas_nuevas = 0

        for ob in obras:
            cc = str(ob["cc"]).strip().upper()
            if not cc:
                continue

            nodo_obra_id = f"OBRA_{cc}"
            cls.agregar_nodo(nodo_obra_id, "OBRA", f"Obra {cc}", {
                "cc": cc,
                "total_lotes": ob["total_lotes"]
            })
            total_nodos_nuevos += 1

            # Traer muestra de lotes de esta obra
            lotes = cur_map.execute("""
                SELECT id_lote_ek, manzana, lote, no_int, clave_lote, fraccionamiento, modelo_vivienda
                FROM lotes_mapeo
                WHERE cc = ?
                LIMIT 15
            """, (cc,)).fetchall()

            for lt in lotes:
                id_ek = str(lt["id_lote_ek"] or "").strip()
                lote_id = f"LOTE_{cc}_{lt['manzana']}_{lt['lote']}"
                cls.agregar_nodo(lote_id, "LOTE", f"Mza {lt['manzana']} Lote {lt['lote']}", {
                    "cc": cc,
                    "id_lote_ek": id_ek,
                    "manzana": lt["manzana"],
                    "lote": lt["lote"],
                    "no_int": lt["no_int"],
                    "clave_lote": lt["clave_lote"],
                    "fraccionamiento": lt["fraccionamiento"],
                    "modelo": lt["modelo_vivienda"]
                })
                cls.conectar(nodo_obra_id, lote_id, "CONTIENE_LOTE")
                total_aristas_nuevas += 1

        conn_map.close()

        # 2. Indexar Escalatorias en el grafo
        if os.path.exists(DB_ESC_PATH):
            try:
                conn_esc = sqlite3.connect(DB_ESC_PATH)
                conn_esc.row_factory = sqlite3.Row
                cur_esc = conn_esc.cursor()
                escs = cur_esc.execute("SELECT id, clave, nombre, estatus_desc, numero_insumos FROM escalatorias LIMIT 30").fetchall()
                for es in escs:
                    esc_id = f"ESC_{es['clave']}"
                    cls.agregar_nodo(esc_id, "ESCALATORIA", f"Escalatoria {es['clave']}", {
                        "nombre": es["nombre"],
                        "estatus": es["estatus_desc"],
                        "insumos": es["numero_insumos"]
                    })
                    total_nodos_nuevos += 1
                conn_esc.close()
            except Exception:
                pass

        return {
            "ok": True,
            "obras_procesadas": len(obras),
            "resumen": cls.obtener_estadisticas_grafo()
        }

    @classmethod
    def obtener_estadisticas_grafo(cls) -> Dict[str, Any]:
        conn = cls.get_db()
        cur = conn.cursor()
        total_nodos = cur.execute("SELECT COUNT(*) FROM nodos").fetchone()[0]
        total_aristas = cur.execute("SELECT COUNT(*) FROM aristas").fetchone()[0]

        tipos = cur.execute("SELECT tipo, COUNT(*) as c FROM nodos GROUP BY tipo").fetchall()
        tipos_dict = {t["tipo"]: t["c"] for t in tipos}

        conn.close()
        return {
            "total_nodos": total_nodos,
            "total_aristas": total_aristas,
            "distribucion_tipos": tipos_dict
        }

    @classmethod
    def diagnosticar_obra(cls, cc: str) -> Dict[str, Any]:
        """Diagnostica la salud de una obra consultando MapeoService y el Grafo."""
        cc_clean = cc.strip().upper()
        from core.mapeo_service import MapeoService

        res_consulta = MapeoService.consultar_lotes(cc=cc_clean, limite=100)
        lotes = res_consulta.get("lotes", [])
        total_obra = res_consulta.get("total", len(lotes))

        if not lotes and total_obra == 0:
            return {"ok": False, "mensaje": f"La obra '{cc_clean}' no tiene lotes registrados"}

        # Contar cuántos tienen coincidencia exacta con EK10 (verdes) y cuántos tienen clave EK10
        con_coincidencia_id = sum(1 for lt in lotes if lt.get("coincide_id"))
        con_ek10 = sum(1 for lt in lotes if lt.get("id_ek10") or lt.get("clave_ek10"))
        muestra = len(lotes)

        pct_coincidencia = round((con_coincidencia_id / max(1, muestra)) * 100, 1)

        return {
            "ok": True,
            "obra": cc_clean,
            "total_lotes_obra": total_obra,
            "muestra_analizada": muestra,
            "lotes_con_id_enk_coincidente": con_coincidencia_id,
            "lotes_con_suite_ek10": con_ek10,
            "lotes_pendientes_homologar": muestra - con_ek10,
            "salud_homologacion": f"{pct_coincidencia}%",
            "primeros_lotes": [
                {
                    "mza": lt.get("manzana"),
                    "lote": lt.get("lote"),
                    "id_lote_ek": lt.get("id_lote_ek"),
                    "id_enk": lt.get("id_enk"),
                    "clave_ek10": lt.get("clave_ek10"),
                    "coincide": lt.get("coincide_id")
                }
                for lt in lotes[:5]
            ]
        }
