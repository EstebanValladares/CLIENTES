"""
Monitor de Chat de Equipo y Mensajes Directos (DMs).
Detecta en tiempo real si algún compañero le escribió al usuario.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional
from ASISTENTE.config import DB_CHAT_PATH


class ChatMonitor:
    _ultimo_id_visto = 0

    @classmethod
    def obtener_nuevos_mensajes(cls, usuario_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(DB_CHAT_PATH):
            return []
        try:
            conn = sqlite3.connect(DB_CHAT_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if cls._ultimo_id_visto == 0:
                max_id = cur.execute("SELECT COALESCE(MAX(id), 0) FROM chat_mensajes").fetchone()[0]
                cls._ultimo_id_visto = max(0, max_id - 1)

            cur.execute("""
                SELECT id, remitente_id, remitente_nombre, canal_clave, canal_nombre, mensaje, fecha, leido
                FROM chat_mensajes
                WHERE id > ?
                ORDER BY id ASC
                LIMIT 5
            """, (cls._ultimo_id_visto,))
            rows = cur.fetchall()

            mensajes = []
            for r in rows:
                if r["id"] > cls._ultimo_id_visto:
                    cls._ultimo_id_visto = r["id"]
                # No alertar sobre mensajes enviados por uno mismo
                if usuario_id and str(r["remitente_id"]).strip() == str(usuario_id).strip():
                    continue
                mensajes.append(dict(r))

            conn.close()
            return mensajes
        except Exception:
            return []

    @classmethod
    def contar_dms_no_leidos(cls, usuario_id: Optional[str] = None) -> int:
        if not os.path.exists(DB_CHAT_PATH):
            return 0
        try:
            conn = sqlite3.connect(DB_CHAT_PATH)
            cur = conn.cursor()
            cnt = cur.execute("SELECT COUNT(*) FROM chat_mensajes WHERE leido = 0").fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return 0
