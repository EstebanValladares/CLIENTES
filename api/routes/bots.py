from fastapi import APIRouter, Query, HTTPException
from core.bot_service import BotRunnerService

router = APIRouter(prefix="/api/bots", tags=["Bots & Selenium"])

@router.get("/catalogo")
def obtener_catalogo():
    return BotRunnerService.obtener_catalogo()

@router.post("/ejecutar/{bot_id}")
def ejecutar_bot(bot_id: str):
    resultado = BotRunnerService.ejecutar_bot(bot_id)
    if not resultado["ok"]:
        raise HTTPException(status_code=400, detail=resultado["error"])
    return resultado

@router.get("/logs/{bot_id}")
def obtener_logs(bot_id: str, desde: int = Query(0, ge=0)):
    return BotRunnerService.obtener_logs(bot_id, desde_linea=desde)

