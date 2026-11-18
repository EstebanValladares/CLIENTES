"""
===============================================================================
MÓDULO ASISTENTE CENTINELA - DASHBOARD EK10
Avatar / Centinela Proactivo en Pantalla (OMFG Hello Toast)
Orquestador principal de monitores, persistencia y eventos.
===============================================================================
"""

import time
import datetime
from typing import Dict, Any, List, Optional

from ASISTENTE.config import (
    NOMBRE_DEFAULT,
    AVATAR_IMG,
    DURACION_GLOBO_SEGUNDOS,
    MAX_HISTORIAL_MEMORIA
)
from ASISTENTE.database import (
    obtener_config_usuario,
    guardar_nombre_asistente,
    guardar_en_historial,
    obtener_historial
)
from ASISTENTE.dialogos.banco_frases import (
    obtener_saludo_contextual,
    obtener_frase_clic,
    obtener_frase_bautizo
)
from ASISTENTE.monitores.chat_monitor import ChatMonitor
from ASISTENTE.monitores.escalatorias_monitor import EscalatoriasMonitor
from ASISTENTE.monitores.sistema_monitor import SistemaMonitor


class AsistenteService:
    # Memoria de eventos ya mostrados para no repetir spam
    _notificaciones_mostradas = set()
    _cola_mensajes_hablados = []

    @classmethod
    def obtener_estado_asistente(cls, usuario_id: Optional[str] = None, nombre_usuario: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna el estado actual del asistente, incluyendo cualquier notificación
        inmediata que deba "decir" en el globo de diálogo en la esquina.
        """
        config = obtener_config_usuario(usuario_id or "default")
        nombre_asistente = config.get("nombre_asistente") or NOMBRE_DEFAULT
        primer_inicio = config.get("primer_inicio_completado", False)

        nuevos_globos = []

        # 1. Monitoreo de Chat de Equipo / DMs
        mensajes_chat = ChatMonitor.obtener_nuevos_mensajes(usuario_id)
        for msg in mensajes_chat:
            globo = {
                "id": f"chat_{msg['id']}",
                "tipo": "chat",
                "emisor": msg["remitente_nombre"],
                "titulo": f"💬 Mensaje de {msg['remitente_nombre']}",
                "texto": f'"{msg["mensaje"]}"',
                "subtexto": f"Canal: {msg.get('canal_nombre') or 'General'}",
                "hora": msg["fecha"],
                "accion": "abrir_chat",
                "payload": {"usuario_id": msg["remitente_id"], "canal": msg.get("canal_clave")},
                "prioridad": "alta",
                "duracion_segundos": DURACION_GLOBO_SEGUNDOS
            }
            if globo["id"] not in cls._notificaciones_mostradas:
                cls._notificaciones_mostradas.add(globo["id"])
                nuevos_globos.append(globo)
                cls._cola_mensajes_hablados.insert(0, globo)
                guardar_en_historial(usuario_id or "default", globo["tipo"], globo["titulo"], globo["texto"])

        # 2. Monitoreo de Nuevas Escalatorias de Precios
        nuevas_esc = EscalatoriasMonitor.obtener_nuevas_escalatorias()
        for esc in nuevas_esc:
            globo = {
                "id": f"esc_{esc['id']}",
                "tipo": "escalatoria",
                "emisor": "Enkontrol SOC",
                "titulo": "📈 Escalatoria Autorizada",
                "texto": f"Nueva escalatoria '{esc['clave']}': {esc['nombre']}",
                "subtexto": f"{esc.get('numero_insumos', 0)} insumos con nuevo precio",
                "hora": esc.get("fecha_autorizacion") or datetime.datetime.now().strftime("%H:%M"),
                "accion": "abrir_escalatorias",
                "payload": {"escalatoria_id": esc["id"], "clave": esc["clave"]},
                "prioridad": "media",
                "duracion_segundos": DURACION_GLOBO_SEGUNDOS
            }
            if globo["id"] not in cls._notificaciones_mostradas:
                cls._notificaciones_mostradas.add(globo["id"])
                nuevos_globos.append(globo)
                cls._cola_mensajes_hablados.insert(0, globo)
                guardar_en_historial(usuario_id or "default", globo["tipo"], globo["titulo"], globo["texto"])

        # Limitar cola en memoria
        if len(cls._cola_mensajes_hablados) > MAX_HISTORIAL_MEMORIA:
            cls._cola_mensajes_hablados = cls._cola_mensajes_hablados[:MAX_HISTORIAL_MEMORIA]

        # Métricas
        total_dms = ChatMonitor.contar_dms_no_leidos(usuario_id)
        total_esc = EscalatoriasMonitor.contar_activas()

        return {
            "ok": True,
            "activo": True,
            "personaje": {
                "nombre": nombre_asistente,
                "avatar": AVATAR_IMG,
                "estado": "hablando" if nuevos_globos else "vigilando",
                "lema": f"¡OMFG HELLO! Cuidando tus pendientes en tiempo real."
            },
            "primer_inicio_completado": primer_inicio,
            "config": config,
            "nuevo_globo": nuevos_globos[0] if nuevos_globos else None,
            "nuevos_globos_pendientes": nuevos_globos,
            "historial_reciente": cls._cola_mensajes_hablados[:5],
            "metricas": {
                "dms_no_leidos": total_dms,
                "escalatorias_activas": total_esc
            }
        }

    @classmethod
    def bautizar_asistente(cls, usuario_id: str, nuevo_nombre: str) -> Dict[str, Any]:
        """
        Asigna el nombre personalizado que el usuario eligió y lo guarda permanentemente.
        """
        res = guardar_nombre_asistente(usuario_id, nuevo_nombre)
        nombre = res["nombre_asistente"]
        frase = obtener_frase_bautizo(nombre)

        globo = {
            "id": f"bautizo_{int(time.time()*1000)}",
            "tipo": "bautizo",
            "emisor": nombre,
            "titulo": f"🎉 ¡Hola! Ahora me llamo {nombre}",
            "texto": frase,
            "subtexto": "Nombre guardado con éxito",
            "hora": datetime.datetime.now().strftime("%H:%M"),
            "accion": "",
            "payload": {},
            "prioridad": "alta",
            "duracion_segundos": 10
        }
        cls._cola_mensajes_hablados.insert(0, globo)
        guardar_en_historial(usuario_id, globo["tipo"], globo["titulo"], globo["texto"])

        return {
            "ok": True,
            "nombre_asistente": nombre,
            "globo": globo
        }

    @classmethod
    def generar_saludo_inicial(cls, usuario_id: Optional[str] = None, nombre_usuario: Optional[str] = None) -> Dict[str, Any]:
        """Genera el saludo proactivo al iniciar sesión en el dashboard."""
        config = obtener_config_usuario(usuario_id or "default")
        nombre_asistente = config.get("nombre_asistente") or NOMBRE_DEFAULT
        dms = ChatMonitor.contar_dms_no_leidos(usuario_id)

        datos_saludo = obtener_saludo_contextual(
            nombre_usuario=nombre_usuario or "Colaborador",
            nombre_asistente=nombre_asistente,
            dms_pendientes=dms
        )

        return {
            "id": f"saludo_{int(time.time())}",
            "tipo": "saludo",
            "emisor": nombre_asistente,
            "titulo": datos_saludo["titulo"],
            "texto": datos_saludo["texto"],
            "subtexto": datos_saludo["subtexto"],
            "hora": datetime.datetime.now().strftime("%H:%M"),
            "accion": "abrir_chat" if dms > 0 else "",
            "payload": {},
            "prioridad": "normal",
            "duracion_segundos": 9
        }

    @classmethod
    def obtener_reaccion_clic(cls, usuario_id: Optional[str] = None) -> Dict[str, Any]:
        """Reacción divertida cuando el usuario hace clic sobre la tostada."""
        config = obtener_config_usuario(usuario_id or "default")
        nombre_asistente = config.get("nombre_asistente") or NOMBRE_DEFAULT
        frase = obtener_frase_clic(nombre_asistente)

        return {
            "id": f"clic_{int(time.time()*1000)}",
            "tipo": "interaccion",
            "emisor": nombre_asistente,
            "titulo": f"🍞 {nombre_asistente} Centinela",
            "texto": frase,
            "subtexto": "Haz clic en la campanita para ver el historial",
            "hora": datetime.datetime.now().strftime("%H:%M"),
            "accion": "",
            "payload": {},
            "prioridad": "normal",
            "duracion_segundos": 6
        }

    @classmethod
    def emitir_mensaje_manual(cls, titulo: str, mensaje: str, tipo: str = "info", accion: str = "") -> Dict[str, Any]:
        """Permite que cualquier parte del sistema haga que la tostada hable de inmediato."""
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
            "duracion_segundos": DURACION_GLOBO_SEGUNDOS
        }
        cls._cola_mensajes_hablados.insert(0, globo)
        return {"ok": True, "globo": globo}
