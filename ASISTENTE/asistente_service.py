"""
===============================================================================
MÓDULO ASISTENTE CENTINELA - DASHBOARD EK10
Avatar / Centinela Proactivo en Pantalla (OMFG Hello Toast)
Monitorea eventos en tiempo real: Chat, Correos, Escalatorias y Tareas.
===============================================================================
"""

import os
import sqlite3
import datetime
import time
import json
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_CHAT = os.path.join(DATA_DIR, "chat_equipo.db")
DB_ESC = os.path.join(DATA_DIR, "escalatorias.db")
DB_MAPEO = os.path.join(DATA_DIR, "mapeo_lotes.db")


class AsistenteService:
    # Memoria de eventos ya mostrados para no repetir spam
    _notificaciones_mostradas = set()
    _ultimo_mensaje_id_visto = 0
    _ultima_escalatoria_id_vista = 0
    _cola_mensajes_hablados = []
    _max_cola = 15

    @classmethod
    def obtener_estado_asistente(cls, usuario_id: Optional[int] = None, nombre_usuario: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna el estado actual del asistente, incluyendo cualquier notificación
        inmediata que deba "decir" en el globo de diálogo en la esquina.
        """
        nombre = nombre_usuario or "Colaborador"
        nuevos_globos = []

        # 1. Monitoreo de Chat de Equipo / Mensajes Directos (DMs)
        mensajes_chat = cls._revisar_mensajes_nuevos_chat(usuario_id)
        for msg in mensajes_chat:
            globo = {
                "id": f"chat_{msg['id']}",
                "tipo": "chat",
                "emisor": msg["remitente_nombre"],
                "titulo": f"💬 Mensaje de {msg['remitente_nombre']}",
                "texto": f'"{msg["mensaje"]}"',
                "subtexto": f"Canal: {msg['canal_nombre']}",
                "hora": msg["fecha"],
                "accion": "abrir_chat",
                "payload": {"usuario_id": msg["remitente_id"], "canal": msg["canal_clave"]},
                "prioridad": "alta",
                "duracion_segundos": 10
            }
            if globo["id"] not in cls._notificaciones_mostradas:
                cls._notificaciones_mostradas.add(globo["id"])
                nuevos_globos.append(globo)
                cls._cola_mensajes_hablados.insert(0, globo)

        # 2. Monitoreo de Nuevas Escalatorias de Precios
        nuevas_esc = cls._revisar_nuevas_escalatorias()
        for esc in nuevas_esc:
            globo = {
                "id": f"esc_{esc['id']}",
                "tipo": "escalatoria",
                "emisor": "Enkontrol SOC",
                "titulo": f"📈 Escalatoria Autorizada",
                "texto": f"Nueva escalatoria '{esc['clave']}': {esc['nombre']}",
                "subtexto": f"{esc['numero_insumos']} insumos con nuevo precio",
                "hora": esc["fecha_autorizacion"] or datetime.datetime.now().strftime("%H:%M"),
                "accion": "abrir_escalatorias",
                "payload": {"escalatoria_id": esc["id"], "clave": esc["clave"]},
                "prioridad": "media",
                "duracion_segundos": 10
            }
            if globo["id"] not in cls._notificaciones_mostradas:
                cls._notificaciones_mostradas.add(globo["id"])
                nuevos_globos.append(globo)
                cls._cola_mensajes_hablados.insert(0, globo)

        # Limitar historial
        if len(cls._cola_mensajes_hablados) > cls._max_cola:
            cls._cola_mensajes_hablados = cls._cola_mensajes_hablados[:cls._max_cola]

        # Resumen general para badges
        total_dms = cls._contar_dms_no_leidos(usuario_id)
        total_esc = cls._contar_total_escalatorias()

        return {
            "ok": True,
            "activo": True,
            "personaje": {
                "nombre": "Toastie",
                "avatar": "/static/img/toast.png",
                "estado": "hablando" if nuevos_globos else "vigilando",
                "lema": "¡OMFG HELLO! Cuidando tus pendientes en tiempo real."
            },
            "nuevo_globo": nuevos_globos[0] if nuevos_globos else None,
            "nuevos_globos_pendientes": nuevos_globos,
            "historial_reciente": cls._cola_mensajes_hablados[:5],
            "metricas": {
                "dms_no_leidos": total_dms,
                "escalatorias_activas": total_esc
            }
        }

    @classmethod
    def emitir_mensaje_manual(cls, titulo: str, mensaje: str, tipo: str = "info", accion: str = "") -> Dict[str, Any]:
        """Permite que el sistema o un bot haga que la tostada hable de inmediato."""
        globo_id = f"custom_{int(time.time()*1000)}"
        globo = {
            "id": globo_id,
            "tipo": tipo,
            "emisor": "Sistema",
            "titulo": titulo,
            "texto": mensaje,
            "subtexto": "",
            "hora": datetime.datetime.now().strftime("%H:%M"),
            "accion": accion,
            "payload": {},
            "prioridad": "alta",
            "duracion_segundos": 10
        }
        cls._cola_mensajes_hablados.insert(0, globo)
        return {"ok": True, "globo": globo}

    @classmethod
    def generar_saludo_inicial(cls, nombre: str = "Esteban") -> Dict[str, Any]:
        """Genera el saludo proactivo al iniciar sesión."""
        hora_actual = datetime.datetime.now().hour
        if hora_actual < 12:
            saludo = f"¡Buenos días, {nombre}!"
        elif hora_actual < 19:
            saludo = f"¡Buenas tardes, {nombre}!"
        else:
            saludo = f"¡Buenas noches, {nombre}!"

        dms = cls._contar_dms_no_leidos(None)
        if dms > 0:
            texto = f"{saludo} Tienes {dms} mensaje(s) nuevo(s) de tus compañeros esperándote. ¡Aquí estoy al pendiente de todo!"
        else:
            texto = f"{saludo} ¡OMFG HELLO! Todo tranquilo en el Dashboard. Te avisaré aquí mismo si entra un correo o mensaje."

        return {
            "id": f"saludo_{int(time.time())}",
            "tipo": "saludo",
            "emisor": "Toastie",
            "titulo": f"👋 {saludo}",
            "texto": texto,
            "subtexto": "Tu centinela personal de pantalla",
            "hora": datetime.datetime.now().strftime("%H:%M"),
            "accion": "",
            "payload": {},
            "prioridad": "normal",
            "duracion_segundos": 9
        }

    @classmethod
    def _revisar_mensajes_nuevos_chat(cls, usuario_id: Optional[int]) -> List[Dict[str, Any]]:
        """Revisa si hay mensajes recientes en chat_equipo.db."""
        if not os.path.exists(DB_CHAT):
            return []
        try:
            conn = sqlite3.connect(DB_CHAT)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Obtener el último ID registrado si es la primera vez
            if cls._ultimo_mensaje_id_visto == 0:
                max_id = cur.execute("SELECT COALESCE(MAX(id), 0) FROM chat_mensajes").fetchone()[0]
                cls._ultimo_mensaje_id_visto = max(0, max_id - 1)  # Permite ver el último reciente

            cur.execute("""
                SELECT id, remitente_id, remitente_nombre, canal_clave, canal_nombre, mensaje, fecha, leido
                FROM chat_mensajes
                WHERE id > ?
                ORDER BY id ASC
                LIMIT 5
            """, (cls._ultimo_mensaje_id_visto,))
            rows = cur.fetchall()

            mensajes = []
            for r in rows:
                if r["id"] > cls._ultimo_mensaje_id_visto:
                    cls._ultimo_mensaje_id_visto = r["id"]
                # Si el usuario_id está definido, no alertar mensajes que envió él mismo
                if usuario_id and r["remitente_id"] == usuario_id:
                    continue
                mensajes.append(dict(r))

            conn.close()
            return mensajes
        except Exception as e:
            return []

    @classmethod
    def _revisar_nuevas_escalatorias(cls) -> List[Dict[str, Any]]:
        """Revisa si hay nuevas escalatorias autorizadas."""
        if not os.path.exists(DB_ESC):
            return []
        try:
            conn = sqlite3.connect(DB_ESC)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if cls._ultima_escalatoria_id_vista == 0:
                max_id = cur.execute("SELECT COALESCE(MAX(id), 0) FROM escalatorias").fetchone()[0]
                cls._ultima_escalatoria_id_vista = max_id  # Empezar a monitorear desde el actual

            cur.execute("""
                SELECT id, clave, nombre, estatus_desc, fecha_autorizacion, numero_insumos
                FROM escalatorias
                WHERE id > ?
                ORDER BY id ASC
                LIMIT 3
            """, (cls._ultima_escalatoria_id_vista,))
            rows = cur.fetchall()
            for r in rows:
                if r["id"] > cls._ultima_escalatoria_id_vista:
                    cls._ultima_escalatoria_id_vista = r["id"]
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    @classmethod
    def _contar_dms_no_leidos(cls, usuario_id: Optional[int]) -> int:
        if not os.path.exists(DB_CHAT):
            return 0
        try:
            conn = sqlite3.connect(DB_CHAT)
            cur = conn.cursor()
            cnt = cur.execute("SELECT COUNT(*) FROM chat_mensajes WHERE leido = 0").fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return 0

    @classmethod
    def _contar_total_escalatorias(cls) -> int:
        if not os.path.exists(DB_ESC):
            return 0
        try:
            conn = sqlite3.connect(DB_ESC)
            cur = conn.cursor()
            cnt = cur.execute("SELECT COUNT(*) FROM escalatorias").fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return 0
