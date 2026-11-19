"""
Ruta oficial del Agente KHIARA para DASHBOARD_EK10.
Conecta el widget interactivo (Gatita Rive) con el cerebro de KHIARA mediante streaming (SSE).
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KHIARA_DIR = os.path.join(BASE_DIR, "KHIARA")
if KHIARA_DIR not in sys.path:
    sys.path.insert(0, KHIARA_DIR)

from khiara.core.agente import crear_agente_khiara
from khiara.core.logger_fallas import registrar_falla, obtener_ultimas_fallas

router = APIRouter(tags=["KHIARA"])

_agente_instancia = None

def get_agente():
    global _agente_instancia
    if _agente_instancia is None:
        _agente_instancia = crear_agente_khiara()
    return _agente_instancia

def reiniciar_agente():
    global _agente_instancia
    _agente_instancia = None
    return get_agente()


class ChatRequest(BaseModel):
    mensaje: str


@router.post("/api/chat/limpiar")
def limpiar_sesion_chat():
    """Reinicia la memoria de sesión del agente KHIARA."""
    reiniciar_agente()
    return {"ok": True, "mensaje": "Sesión reiniciada con éxito"}


@router.get("/api/khiara/logs")
def ver_logs_fallas(limite: int = 30):
    """Devuelve las últimas incidencias y errores registrados en fallas_khiara.log."""
    fallas = obtener_ultimas_fallas(limite=limite)
    return {"total": len(fallas), "logs": fallas}


@router.get("/api/khiara/status")
@router.get("/api/status")
def status_khiara():
    return {
        "nombre": "KHIARA",
        "avatar": "Gatita Rive Companion",
        "motor": "gemini-3.5-flash-lite",
        "capacidades": [
            "Tool Calling",
            "Grafo de Conocimiento (NetworkX)",
            "DuckDB",
            "REA Aryve",
            "Ontología Velas"
        ],
        "estado": "lista"
    }


@router.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """Genera streaming de la respuesta del agente KHIARA para el widget de la gatita con autorrecuperación."""
    agente = get_agente()
    loop = asyncio.get_event_loop()
    
    async def generador():
        nonlocal agente
        try:
            # Evento inicial de pensamiento
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'thinking'})}\n\n"
            await asyncio.sleep(0.05)
            
            try:
                respuesta = await loop.run_in_executor(None, lambda: agente.run(req.mensaje, stream=False))
            except Exception as e_run:
                err_str = str(e_run)
                registrar_falla(req.mensaje, "EXCEPTION_RUN", err_str)
                agente = reiniciar_agente()
                try:
                    respuesta = await loop.run_in_executor(None, lambda: agente.run(req.mensaje, stream=False))
                except Exception as e_reintentar:
                    registrar_falla(req.mensaje, "RETRY_EXCEPTION", str(e_reintentar))
                    respuesta = "Esa información o servicio no se encuentra disponible por el momento. He registrado la incidencia para darle seguimiento. ¿Hay algo más en lo que pueda apoyarte?"
            
            # Evento de habla
            texto = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
            
            # Si Agno devolvió una cadena con el error 400/429 de la API en lugar de lanzar excepción:
            if '"error"' in texto and ('"code": 400' in texto or 'function call turn' in texto or 'INVALID_ARGUMENT' in texto or '"code": 429' in texto):
                registrar_falla(req.mensaje, "API_RAW_ERROR", texto[:300])
                agente = reiniciar_agente()
                try:
                    respuesta = await loop.run_in_executor(None, lambda: agente.run(req.mensaje, stream=False))
                    texto = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
                except Exception as e_rec:
                    registrar_falla(req.mensaje, "RECOVER_EXCEPTION", str(e_rec))
                    texto = "Esa información o servicio no se encuentra disponible por el momento. He registrado el reporte. ¿Te gustaría consultar otro dato?"
            
            # Si aún después de reintentar sigue conteniendo un error crudo de Gemini:
            if '"error"' in texto and ('"code": 400' in texto or '"code": 429' in texto or 'INVALID_ARGUMENT' in texto):
                registrar_falla(req.mensaje, "UNRESOLVED_API_ERROR", texto[:300])
                reiniciar_agente()
                texto = "Esa información o servicio no se encuentra disponible por el momento. Ya registré el detalle para revisarlo. ¿Deseas hacer otra consulta?"

            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
            
            # Streaming fluido de palabras
            palabras = texto.split(" ")
            chunk = []
            for p in palabras:
                chunk.append(p)
                if len(chunk) >= 3:
                    yield f"data: {json.dumps({'tipo': 'texto', 'valor': ' '.join(chunk) + ' '})}\n\n"
                    chunk = []
                    await asyncio.sleep(0.02)
            if chunk:
                yield f"data: {json.dumps({'tipo': 'texto', 'valor': ' '.join(chunk)})}\n\n"
                
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'idle'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'fin', 'valor': True})}\n\n"
        except Exception as e:
            # En caso de error mayor o caída imprevista, registrar en el log y dar mensaje limpio
            registrar_falla(req.mensaje, "CRITICAL_EXCEPTION", str(e))
            reiniciar_agente()
            msg_amable = "Esa información o servicio no se encuentra disponible por el momento. He guardado el reporte para verificarlo. ¿En qué más puedo ayudarte?"
            yield f"data: {json.dumps({'tipo': 'texto', 'valor': msg_amable})}\n\n"
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'idle'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'fin', 'valor': True})}\n\n"

    return StreamingResponse(generador(), media_type="text/event-stream")
