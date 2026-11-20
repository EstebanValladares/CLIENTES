from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any, List
from core.permisos_service import PermisosService

router = APIRouter(prefix="/api/operaciones", tags=["Permisos Proyectos"])

# --- PERMISOS PROYECTOS ---
@router.get("/permisos")
def obtener_permisos():
    return PermisosService.obtener_datos()

@router.post("/permisos")
def guardar_permisos(payload: Dict[str, Any] = Body(...)):
    usrs = payload.get("usuarios_protegidos", [])
    obras = payload.get("obras", [])
    ok = PermisosService.guardar_datos(usrs, obras)
    if not ok:
        raise HTTPException(status_code=500, detail="Error guardando permisos")
    return {"ok": True, "mensaje": "Datos actualizados"}

@router.get("/permisos/historial")
def historial_permisos():
    return {"log": PermisosService.obtener_log_historial()}

# --- DESASIGNACIÓN DE USUARIOS POR PROYECTO ---
@router.get("/desasignacion")
def obtener_desasignacion():
    return PermisosService.obtener_desasignacion()

@router.post("/desasignacion")
def guardar_desasignacion(payload: Dict[str, Any] = Body(...)):
    ok = PermisosService.guardar_desasignacion(payload)
    if not ok:
        raise HTTPException(status_code=500, detail="Error guardando datos de desasignación")
    return {"ok": True, "mensaje": "Datos de desasignación actualizados"}

@router.get("/desasignacion/config")
def obtener_config_desasignacion():
    return PermisosService.obtener_config_desasignacion()

@router.post("/desasignacion/config")
def guardar_config_desasignacion(payload: Dict[str, Any] = Body(...)):
    ok = PermisosService.guardar_config_desasignacion(payload)
    if not ok:
        raise HTTPException(status_code=500, detail="Error guardando configuración de desasignación")
    return {"ok": True, "mensaje": "Configuración de desasignación actualizada"}
