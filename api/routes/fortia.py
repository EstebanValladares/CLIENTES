from fastapi import APIRouter, HTTPException, Query
from core.fortia_service import FortiaService

router = APIRouter(prefix="/api/fortia", tags=["Bajas FORTIA"])

@router.get("/cruce")
def obtener_cruce_bajas():
    """Devuelve los resultados de la última consulta de bajas de FORTIA contra Enkontrol."""
    return FortiaService.obtener_cruce_actual()

@router.post("/consultar-bajas")
def consultar_bajas_fortia(
    dias_atras: int = Query(30, ge=1, le=365, description="Días hacia atrás para consultar en FORTIA"),
    headless: bool = Query(True, description="Ejecutar Chrome en segundo plano sin ventana")
):
    """Ejecuta la consulta automatizada del reporte 2411 en FORTIA en segundo plano."""
    ok, msg = FortiaService.iniciar_consulta_bajas_asincrona(dias_atras=dias_atras, headless=headless)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}

@router.get("/estado-bot")
def estado_bot_fortia():
    """Consulta el estado en vivo y logs del proceso de consulta a FORTIA."""
    return FortiaService.obtener_estado_bot()
