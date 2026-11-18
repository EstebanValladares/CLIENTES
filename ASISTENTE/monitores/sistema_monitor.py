"""
Monitor de Estado del Sistema y Base de Datos.
Vigila la integridad y sincronización de bases de datos locales (Mapeo de Lotes, Chat, etc.).
"""

import os
import sqlite3
from typing import Dict, Any
from ASISTENTE.config import DB_MAPEO_PATH, DB_CHAT_PATH, DB_ESC_PATH


class SistemaMonitor:
    @classmethod
    def obtener_resumen_sistema(cls) -> Dict[str, Any]:
        """Devuelve estadísticas clave del dashboard para el asistente."""
        resumen = {
            "lotes_totales": 0,
            "obras_activas": 0,
            "chat_operativo": os.path.exists(DB_CHAT_PATH),
            "escalatorias_operativo": os.path.exists(DB_ESC_PATH),
            "mapeo_operativo": os.path.exists(DB_MAPEO_PATH)
        }

        if os.path.exists(DB_MAPEO_PATH):
            try:
                conn = sqlite3.connect(DB_MAPEO_PATH)
                cur = conn.cursor()
                row_lotes = cur.execute("SELECT COUNT(*) FROM lotes_mapeo").fetchone()
                if row_lotes:
                    resumen["lotes_totales"] = row_lotes[0]
                row_obras = cur.execute("SELECT COUNT(DISTINCT cc) FROM lotes_mapeo").fetchone()
                if row_obras:
                    resumen["obras_activas"] = row_obras[0]
                conn.close()
            except Exception:
                pass

        return resumen
