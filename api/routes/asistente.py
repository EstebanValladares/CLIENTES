"""
API Route: Asistente Centinela de Esquina (OMFG Hello Toast)
Permite monitorear notificaciones proactivas, chat, escalatorias y disparar globos de diálogo.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any
from ASISTENTE.asistente_service import AsistenteService

router = APIRouter(prefix="/api/asistente", tags=["Asistente"])


@router.get("/estado")
def obtener_estado(usuario_id: Optional[str] = Query(None), nombre: Optional[str] = Query(None)):
    """Retorna el estado del asistente y cualquier globo de diálogo pendiente para hablar."""
    return AsistenteService.obtener_estado_asistente(usuario_id=usuario_id, nombre_usuario=nombre)


@router.get("/saludo")
def obtener_saludo(usuario_id: Optional[str] = Query(None), nombre: Optional[str] = Query("Esteban")):
    """Genera un saludo proactivo en cuanto el usuario entra al Dashboard."""
    return AsistenteService.generar_saludo_inicial(usuario_id=usuario_id, nombre_usuario=nombre)


@router.get("/reaccion-clic")
def reaccionar_clic(usuario_id: Optional[str] = Query(None)):
    """Devuelve una frase divertida al hacer clic sobre el avatar de la tostada."""
    return AsistenteService.obtener_reaccion_clic(usuario_id=usuario_id)


@router.post("/configurar-nombre")
def configurar_nombre(payload: Dict[str, Any] = Body(...)):
    """Guarda el nombre personalizado que el usuario le asignó al asistente (bautizo inicial o edición)."""
    usuario_id = str(payload.get("usuario_id") or "default")
    nombre_asistente = str(payload.get("nombre_asistente") or "").strip()
    if not nombre_asistente:
        raise HTTPException(status_code=400, detail="El nombre del asistente no puede estar vacío")
    return AsistenteService.bautizar_asistente(usuario_id=usuario_id, nuevo_nombre=nombre_asistente)


@router.post("/hablar")
def emitir_habla(payload: Dict[str, Any] = Body(...)):
    """Dispara un globo de diálogo manual en pantalla."""
    titulo = payload.get("titulo", "Aviso del Asistente")
    mensaje = payload.get("mensaje", "")
    tipo = payload.get("tipo", "info")
    accion = payload.get("accion", "")
    return AsistenteService.emitir_mensaje_manual(titulo=titulo, mensaje=mensaje, tipo=tipo, accion=accion)
