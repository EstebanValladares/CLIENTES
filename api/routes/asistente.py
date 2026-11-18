"""
API Route: Asistente Centinela de Esquina (OMFG Hello Toast)
Permite monitorear notificaciones proactivas, chat, escalatorias y disparar globos de diálogo.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any
from ASISTENTE.asistente_service import AsistenteService

router = APIRouter(prefix="/api/asistente", tags=["Asistente"])


@router.get("/estado")
def obtener_estado(usuario_id: Optional[int] = Query(None), nombre: Optional[str] = Query(None)):
    """Retorna el estado del asistente y cualquier globo de diálogo pendiente para hablar."""
    return AsistenteService.obtener_estado_asistente(usuario_id=usuario_id, nombre_usuario=nombre)


@router.get("/saludo")
def obtener_saludo(nombre: Optional[str] = Query("Esteban")):
    """Genera un saludo proactivo en cuanto el usuario entra al Dashboard."""
    return AsistenteService.generar_saludo_inicial(nombre=nombre)


@router.post("/hablar")
def emitir_habla(payload: Dict[str, Any] = Body(...)):
    """Dispara un globo de diálogo manual en pantalla."""
    titulo = payload.get("titulo", "Aviso del Asistente")
    mensaje = payload.get("mensaje", "")
    tipo = payload.get("tipo", "info")
    accion = payload.get("accion", "")
    return AsistenteService.emitir_mensaje_manual(titulo=titulo, mensaje=mensaje, tipo=tipo, accion=accion)
