"""
Rutas API para el Módulo de Contratistas en Dashboard Intelligence Solutions.
"""

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Dict, Any, List, Optional
from core.contratistas_service import ContratistasService

router = APIRouter(prefix="/api/contratistas", tags=["Contratistas"])


@router.get("/db")
def obtener_contratistas_db(forzar: bool = Query(False)):
    """Obtiene el listado desde DBA.SU_CONTRATISTAS comparado contra contratista_mapeado.json."""
    return ContratistasService.obtener_contratistas_dba(forzar_recarga=forzar)


@router.get("/cola")
def obtener_cola():
    """Obtiene los contratistas actualmente en la cola 'EN FILA'."""
    return ContratistasService.obtener_cola()


@router.post("/cola/toggle")
def toggle_cola(item: Dict[str, Any] = Body(...)):
    """Agrega o quita un contratista de la cola."""
    return ContratistasService.toggle_cola(item)


@router.post("/cola/sincronizar")
def sincronizar_cola(payload: Dict[str, Any] = Body(...)):
    """Sincroniza un conjunto de contratistas seleccionados en lote."""
    items = payload.get("items", [])
    return ContratistasService.sincronizar_cola_por_lote(items)


@router.delete("/cola/{numpro}")
def quitar_de_cola(numpro: str):
    """Elimina un contratista específico de la fila."""
    return ContratistasService.quitar_de_cola(numpro)


@router.delete("/cola")
def vaciar_cola():
    """Vacía toda la fila de contratistas."""
    return ContratistasService.vaciar_cola()


@router.post("/iniciar")
def iniciar_proceso():
    """Inicia el bot Selenium para generar gafetes, cargarlos a Aryve y borrarlos al terminar."""
    ok, msg = ContratistasService.iniciar_procesamiento()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}


@router.post("/detener")
def detener_proceso():
    """Detiene la ejecución del bot de manera segura."""
    return ContratistasService.detener_ejecucion()


@router.get("/estado")
def obtener_estado():
    """Devuelve el progreso en vivo, logs de terminal y estado de ejecución."""
    return ContratistasService.obtener_estado()

