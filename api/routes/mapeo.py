"""
API Route: Mapeo de Lotes y Centros de Costos (Enkontrol / Aryve)
Permite buscar rápidamente por:
- CC
- MANZANA
- LOTE
- NO. INTERIOR
- ID LOTE EK (ej. 570345)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from core.mapeo_service import MapeoService

router = APIRouter(prefix="/api/mapeo", tags=["Mapeo"])


@router.get("/resumen")
def obtener_resumen():
    """Retorna estadísticas generales y catálogo de CCs para dropdowns."""
    return MapeoService.obtener_resumen()


@router.get("/lotes")
def consultar_lotes(
    cc: Optional[str] = Query(None),
    manzana: Optional[str] = Query(None),
    lote: Optional[str] = Query(None),
    no_int: Optional[str] = Query(None),
    id_lote_ek: Optional[str] = Query(None),
    busqueda: Optional[str] = Query(None),
    limite: int = Query(150, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Consulta paginada e instantánea de lotes con filtros específicos o búsqueda libre."""
    return MapeoService.consultar_lotes(
        cc=cc,
        manzana=manzana,
        lote=lote,
        no_int=no_int,
        id_lote_ek=id_lote_ek,
        busqueda=busqueda,
        limite=limite,
        offset=offset
    )


@router.post("/sincronizar")
def sincronizar_desde_enkontrol():
    """Fuerza la sincronización en vivo desde la base de datos de Enkontrol."""
    res = MapeoService.sincronizar_desde_enkontrol()
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Error sincronizando"))
    return res
