from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any, List
from core.permisos_service import PermisosService
from core.proveedores_service import ProveedoresService

router = APIRouter(prefix="/api/operaciones", tags=["Permisos y Proveedores"])

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

# --- PROVEEDORES ---
@router.post("/proveedores/calcular")
def calcular_proveedor(payload: Dict[str, Any] = Body(...)):
    nombre = payload.get("nombre", "")
    tipo = payload.get("tipo_persona", "MORAL")
    paterno = payload.get("paterno", "")
    return ProveedoresService.calcular_claves(nombre, tipo, paterno)

@router.get("/proveedores/cola")
def obtener_cola_proveedores():
    return ProveedoresService.obtener_cola()

@router.post("/proveedores/cola")
def agregar_a_cola_proveedor(payload: Dict[str, Any] = Body(...)):
    return ProveedoresService.agregar_a_cola(payload)

@router.delete("/proveedores/cola/{idx}")
def eliminar_de_cola_proveedor(idx: int):
    return ProveedoresService.eliminar_de_cola(idx)

@router.delete("/proveedores/cola")
def vaciar_cola_proveedor():
    return ProveedoresService.vaciar_cola()

@router.post("/proveedores/ejecutar")
def ejecutar_cola_proveedores():
    ok, msg = ProveedoresService.iniciar_procesamiento_cola()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}

@router.get("/proveedores/estado")
def estado_proveedores():
    return ProveedoresService.obtener_estado_ejecucion()

@router.get("/proveedores/registrados")
def proveedores_registrados():
    return ProveedoresService.obtener_registrados()

