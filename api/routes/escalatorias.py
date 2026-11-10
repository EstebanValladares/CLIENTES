"""
API Route: Escalatoria de Precios & Obras (Enkontrol / Aryve SOC)
Permite buscar instantáneamente por:
- Obra / Centro de Costos / Proyecto
- Clave de Escalatoria (ej. ESC-PRECIO-TAM-0002, AD - ARMEX, etc.)
- Insumo
- Resumen y estadísticas
- Sincronización en vivo con botón manual
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from core.escalatoria_service import EscalatoriaService

router = APIRouter(prefix="/api/escalatorias", tags=["Escalatorias"])


@router.get("/resumen")
def obtener_resumen():
    """Retorna KPIs generales y última sincronización."""
    return EscalatoriaService.obtener_resumen()


@router.get("/buscar")
def buscar_escalatorias(
    busqueda: Optional[str] = Query(None),
    obra: Optional[str] = Query(None),
    clave: Optional[str] = Query(None),
    insumo: Optional[str] = Query(None),
    estatus: Optional[str] = Query(None),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Consulta paginada e instantánea de escalatorias y sus obras asociadas."""
    return EscalatoriaService.consultar(
        busqueda=busqueda,
        obra=obra,
        clave=clave,
        insumo=insumo,
        estatus=estatus,
        limite=limite,
        offset=offset
    )


@router.get("/{id_escalatoria}/detalle")
def obtener_detalle_escalatoria(id_escalatoria: int):
    """Retorna el detalle completo de una escalatoria con sus obras e insumos."""
    detalle = EscalatoriaService.obtener_detalle(id_escalatoria)
    if not detalle:
        raise HTTPException(status_code=404, detail="Escalatoria no encontrada.")
    return detalle


@router.post("/sincronizar")
def sincronizar_desde_enkontrol():
    """Fuerza la sincronización en vivo desde Enkontrol 10 Cloud."""
    return EscalatoriaService.sincronizar_desde_enkontrol(incluir_obras=True)
