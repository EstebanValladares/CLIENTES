"""
Servidor API REST y WebSockets de KHIARA (FastAPI + Uvicorn).
Permite conectar KHIARA con Dashboards, interfaces web, clientes móviles y bots.
"""

import os
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from khiara.core.config import DEFAULT_MODEL, tiene_api_key
from khiara.core.agente import crear_agente_khiara
from khiara.herramientas.explorador import red_global
from khiara.grafo.indexador import IndexadorProyecto

app = FastAPI(
    title="KHIARA Autonomous Agent API",
    description="Microservicio de Inteligencia, Grafos de Conocimiento y Notificaciones",
    version="1.0.0"
)

# CORS habilitado para conectarse con cualquier dashboard local o en red
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cola de notificaciones en memoria (alertas importantes de correos, whatsapp, proyectos)
_notificaciones_activas: List[Dict[str, Any]] = []

# Instancia del agente KHIARA
try:
    _agente_khiara = crear_agente_khiara()
except Exception as e:
    _agente_khiara = None
    print(f"[KHIARA] Advertencia: Agente inicializado en modo fallback: {e}")


class MensajeChat(BaseModel):
    mensaje: str
    usuario: Optional[str] = "Esteban"


class NuevaNotificacion(BaseModel):
    origen: str  # ej. "GMAIL", "WHATSAPP", "DASHBOARD", "SISTEMA"
    titulo: str
    resumen: str
    nivel: Optional[str] = "info"  # "info", "alerta", "urgente"
    datos: Optional[Dict[str, Any]] = None


class AprenderProyecto(BaseModel):
    ruta: str


@app.get("/api/khiara/status")
def obtener_estado() -> Dict[str, Any]:
    """Retorna el estado de salud y telemetría de KHIARA."""
    metricas = red_global.metricas()
    return {
        "ok": True,
        "nombre": "KHIARA",
        "version": "1.0.0",
        "estado": "activo",
        "modelo": DEFAULT_MODEL,
        "api_key_activa": tiene_api_key(),
        "total_nodos_grafo": metricas.get("total_nodos", 0),
        "total_relaciones_grafo": metricas.get("total_relaciones", 0),
        "notificaciones_pendientes": len(_notificaciones_activas),
        "timestamp": int(time.time())
    }


@app.post("/api/khiara/chat")
def procesar_chat(payload: MensajeChat) -> Dict[str, Any]:
    """Procesa una consulta al agente KHIARA y retorna la respuesta razonada."""
    global _agente_khiara
    if not _agente_khiara:
        try:
            _agente_khiara = crear_agente_khiara()
        except Exception as e:
            return {
                "ok": False,
                "error": f"No se pudo inicializar KHIARA: {str(e)}",
                "respuesta": "No tengo configurada mi clave de API o hubo un error al iniciar mi modelo."
            }

    try:
        resultado = _agente_khiara.run(payload.mensaje)
        texto = resultado.content if hasattr(resultado, "content") else str(resultado)
        return {
            "ok": True,
            "respuesta": texto,
            "usuario": payload.usuario,
            "timestamp": int(time.time())
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "respuesta": f"Tuve un inconveniente al procesar la respuesta: {str(e)}"
        }


@app.get("/api/khiara/notificaciones")
def obtener_notificaciones() -> Dict[str, Any]:
    """Obtiene las notificaciones pendientes generadas por KHIARA o conectores."""
    return {
        "ok": True,
        "total": len(_notificaciones_activas),
        "notificaciones": _notificaciones_activas
    }


@app.post("/api/khiara/notificaciones")
def registrar_notificacion(payload: NuevaNotificacion) -> Dict[str, Any]:
    """Permite registrar una notificación (desde Gmail, WhatsApp, Watchers)."""
    notif = {
        "id": f"notif_{int(time.time()*1000)}",
        "origen": payload.origen,
        "titulo": payload.titulo,
        "resumen": payload.resumen,
        "nivel": payload.nivel,
        "datos": payload.datos or {},
        "fecha": time.strftime("%H:%M"),
        "timestamp": int(time.time())
    }
    _notificaciones_activas.insert(0, notif)
    # Mantener máximo 50 notificaciones recientes
    if len(_notificaciones_activas) > 50:
        _notificaciones_activas.pop()
    return {"ok": True, "notificacion": notif}


@app.delete("/api/khiara/notificaciones")
def limpiar_notificaciones() -> Dict[str, Any]:
    """Limpia la bandeja de notificaciones."""
    _notificaciones_activas.clear()
    return {"ok": True, "mensaje": "Notificaciones limpiadas"}


@app.post("/api/khiara/aprender")
def aprender_ruta(payload: AprenderProyecto) -> Dict[str, Any]:
    """Indexa un proyecto en el grafo de KHIARA vía API."""
    indexador = IndexadorProyecto(red_global)
    res = indexador.aprender_proyecto(payload.ruta)
    return res
