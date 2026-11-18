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
                # Si ocurrió una desincronización de turnos en el historial de Gemini (código 400), reiniciar sesión y reintentar
                err_str = str(e_run)
                if "function call turn" in err_str or "INVALID_ARGUMENT" in err_str or "400" in err_str:
                    agente = reiniciar_agente()
                    respuesta = await loop.run_in_executor(None, lambda: agente.run(req.mensaje, stream=False))
                else:
                    raise e_run
            
            # Evento de habla
            texto = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
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
            # En caso de error, limpiar la instancia para la siguiente pregunta
            reiniciar_agente()
            yield f"data: {json.dumps({'tipo': 'error', 'valor': f'Ocurrió un detalle: {str(e)}'})}\n\n"

    return StreamingResponse(generador(), media_type="text/event-stream")
