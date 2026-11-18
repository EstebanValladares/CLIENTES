"""
Rutas Proxy del Microservicio KHIARA en DASHBOARD_EK10.
Comunica el Frontend del Dashboard con el Agente Autónomo KHIARA (http://localhost:8001).
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/khiara", tags=["KHIARA"])

KHIARA_BASE_URL = "http://127.0.0.1:8001"


class ChatPayload(BaseModel):
    mensaje: str
    usuario: Optional[str] = "Esteban"


@router.get("/status")
def proxy_status() -> Dict[str, Any]:
    """Verifica si el microservicio de KHIARA está encendido en el puerto 8001."""
    url = f"{KHIARA_BASE_URL}/api/khiara/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Dashboard-EK10"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return {"online": True, **data}
    except Exception:
        pass
    return {
        "online": False,
        "nombre": "KHIARA",
        "estado": "desconectado",
        "mensaje": "KHIARA está apagada. Ejecuta 'python run.py --server' en la carpeta KHIARA para activarla."
    }


@router.post("/chat")
def proxy_chat(payload: ChatPayload) -> Dict[str, Any]:
    """Envía un mensaje al agente KHIARA y retorna su respuesta."""
    url = f"{KHIARA_BASE_URL}/api/khiara/chat"
    try:
        req_data = json.dumps(payload.dict()).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "Dashboard-EK10"}
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        return {
            "ok": False,
            "error": "KHIARA_OFFLINE",
            "respuesta": "KHIARA no está corriendo. Inicia el microservicio con: `python run.py --server` en su repositorio."
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "respuesta": f"Error comunicando con KHIARA: {str(e)}"
        }


@router.get("/notificaciones")
def proxy_notificaciones() -> Dict[str, Any]:
    """Obtiene las alertas y notificaciones pendientes de KHIARA."""
    url = f"{KHIARA_BASE_URL}/api/khiara/notificaciones"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Dashboard-EK10"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
    return {"ok": True, "total": 0, "notificaciones": []}


@router.delete("/notificaciones")
def proxy_limpiar_notificaciones() -> Dict[str, Any]:
    """Limpia la bandeja de alertas en KHIARA."""
    url = f"{KHIARA_BASE_URL}/api/khiara/notificaciones"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Dashboard-EK10"}, method="DELETE")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
    return {"ok": True, "mensaje": "Limpiado"}
