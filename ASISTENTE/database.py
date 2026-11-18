"""
Persistencia y Base de Datos del Asistente Centinela.
Almacena configuración de usuario, nombre personalizado del asistente y memoria histórica.
"""

import os
import sqlite3
import datetime
from typing import Dict, Any, Optional
from ASISTENTE.config import DB_ASISTENTE_PATH, DATA_DIR, NOMBRE_DEFAULT


def get_asistente_db() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_ASISTENTE_PATH)
    conn.row_factory = sqlite3.Row
    _crear_tablas_si_no_existen(conn)
    return conn


def _crear_tablas_si_no_existen(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS asistente_config (
            usuario_id TEXT PRIMARY KEY,
            nombre_asistente TEXT NOT NULL,
            primer_inicio_completado INTEGER DEFAULT 0,
            sonido_activo INTEGER DEFAULT 1,
            fecha_registro TEXT,
            fecha_modificacion TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS asistente_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id TEXT,
            tipo TEXT,
            titulo TEXT,
            mensaje TEXT,
            fecha TEXT,
            leido INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def obtener_config_usuario(usuario_id: str) -> Dict[str, Any]:
    uid = str(usuario_id or "default").strip()
    conn = get_asistente_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM asistente_config WHERE usuario_id = ?", (uid,))
    row = cur.fetchone()

    if not row:
        # Si no existe, revisar si existe un perfil default
        cur.execute("SELECT * FROM asistente_config WHERE usuario_id = 'default'")
        row = cur.fetchone()

    conn.close()

    if row:
        return {
            "usuario_id": row["usuario_id"],
            "nombre_asistente": row["nombre_asistente"] or NOMBRE_DEFAULT,
            "primer_inicio_completado": bool(row["primer_inicio_completado"]),
            "sonido_activo": bool(row["sonido_activo"])
        }

    return {
        "usuario_id": uid,
        "nombre_asistente": NOMBRE_DEFAULT,
        "primer_inicio_completado": False,
        "sonido_activo": True
    }


def guardar_nombre_asistente(usuario_id: str, nombre_asistente: str) -> Dict[str, Any]:
    uid = str(usuario_id or "default").strip()
    nombre_limpio = str(nombre_asistente or NOMBRE_DEFAULT).strip()[:30]
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_asistente_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO asistente_config (usuario_id, nombre_asistente, primer_inicio_completado, sonido_activo, fecha_registro, fecha_modificacion)
        VALUES (?, ?, 1, 1, ?, ?)
        ON CONFLICT(usuario_id) DO UPDATE SET
            nombre_asistente = excluded.nombre_asistente,
            primer_inicio_completado = 1,
            fecha_modificacion = excluded.fecha_modificacion
    """, (uid, nombre_limpio, ahora, ahora))

    # También actualizar el 'default' si es el usuario principal
    if uid != "default":
        cur.execute("""
            INSERT INTO asistente_config (usuario_id, nombre_asistente, primer_inicio_completado, sonido_activo, fecha_registro, fecha_modificacion)
            VALUES ('default', ?, 1, 1, ?, ?)
            ON CONFLICT(usuario_id) DO UPDATE SET
                nombre_asistente = excluded.nombre_asistente,
                primer_inicio_completado = 1,
                fecha_modificacion = excluded.fecha_modificacion
        """, (nombre_limpio, ahora, ahora))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "usuario_id": uid,
        "nombre_asistente": nombre_limpio,
        "primer_inicio_completado": True
    }


def guardar_en_historial(usuario_id: str, tipo: str, titulo: str, mensaje: str) -> None:
    try:
        conn = get_asistente_db()
        cur = conn.cursor()
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO asistente_historial (usuario_id, tipo, titulo, mensaje, fecha, leido)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (str(usuario_id or 'default'), tipo, titulo, mensaje, ahora))
        conn.commit()
        conn.close()
    except Exception:
        pass


def obtener_historial(usuario_id: str, limite: int = 15):
    try:
        conn = get_asistente_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, usuario_id, tipo, titulo, mensaje, fecha
            FROM asistente_historial
            WHERE usuario_id = ? OR usuario_id = 'default'
            ORDER BY id DESC
            LIMIT ?
        """, (str(usuario_id or 'default'), limite))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []
