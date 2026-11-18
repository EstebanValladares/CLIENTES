"""
Monitor de Escalatoria de Precios (SOC Enkontrol).
Detecta nuevas escalatorias autorizadas en segundo plano.
"""

import os
import sqlite3
from typing import List, Dict, Any
from ASISTENTE.config import DB_ESC_PATH


class EscalatoriasMonitor:
    _ultimo_id_visto = 0

    @classmethod
    def obtener_nuevas_escalatorias(cls) -> List[Dict[str, Any]]:
        if not os.path.exists(DB_ESC_PATH):
            return []
        try:
            conn = sqlite3.connect(DB_ESC_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if cls._ultimo_id_visto == 0:
                max_id = cur.execute("SELECT COALESCE(MAX(id), 0) FROM escalatorias").fetchone()[0]
                cls._ultimo_id_visto = max_id

            cur.execute("""
                SELECT id, clave, nombre, estatus_desc, fecha_autorizacion, numero_insumos
                FROM escalatorias
                WHERE id > ?
                ORDER BY id ASC
                LIMIT 3
            """, (cls._ultimo_id_visto,))
            rows = cur.fetchall()

            escalatorias = []
            for r in rows:
                if r["id"] > cls._ultimo_id_visto:
                    cls._ultimo_id_visto = r["id"]
                escalatorias.append(dict(r))

            conn.close()
            return escalatorias
        except Exception:
            return []

    @classmethod
    def contar_activas(cls) -> int:
        if not os.path.exists(DB_ESC_PATH):
            return 0
        try:
            conn = sqlite3.connect(DB_ESC_PATH)
            cur = conn.cursor()
            cnt = cur.execute("SELECT COUNT(*) FROM escalatorias").fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return 0
