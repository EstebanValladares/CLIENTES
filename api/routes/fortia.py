from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Dict, Any, Optional
import shutil
import tempfile
from pathlib import Path

from core.fortia_service import FortiaService

router = APIRouter(prefix="/api/fortia", tags=["Bajas FORTIA"])

@router.get("/cruce")
def obtener_cruce_bajas():
    """Devuelve el cruce de bajas de FORTIA contra los usuarios de Enkontrol."""
    return FortiaService.obtener_cruce_actual()

@router.post("/consultar-bajas")
def consultar_bajas_fortia(
    dias_atras: int = Query(30, ge=1, le=365, description="Días hacia atrás para consultar en FORTIA"),
    headless: bool = Query(True, description="Ejecutar Chrome en segundo plano sin ventana")
):
    """Lanza el bot oficial de FORTIA (reporte 2411) en segundo plano."""
    ok, msg = FortiaService.iniciar_consulta_bajas_asincrona(dias_atras=dias_atras, headless=headless)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}

@router.get("/estado-bot")
def estado_bot_fortia():
    """Consulta el estado en vivo y logs del bot de Selenium de FORTIA."""
    return FortiaService.obtener_estado_bot()

@router.post("/reprocesar")
def forzar_reprocesar_cruce():
    """Recalcula el cruce entre el último reporte de FORTIA y los usuarios de Enkontrol."""
    resultado = FortiaService.procesar_ultimo_reporte_descargado()
    if not resultado.get("ok"):
        raise HTTPException(status_code=404, detail=resultado.get("error", "Error procesando reporte"))
    return resultado

@router.post("/cargar-excel")
async def cargar_excel_bajas(archivo: UploadFile = File(...)):
    """Permite al usuario subir un Excel de Altas y Bajas de FORTIA para cruzarlo al instante."""
    if not archivo.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser un formato Excel (.xlsx o .xls)")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(archivo.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        bajas = FortiaService.leer_excel_bajas(tmp_path)
        if not bajas:
            raise HTTPException(status_code=400, detail="No se encontraron registros de bajas válidos en el archivo Excel.")
        cruce = FortiaService.cruzar_con_usuarios_enkontrol(bajas)
        cruce["ok"] = True
        cruce["archivo_origen"] = archivo.filename
        return cruce
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
