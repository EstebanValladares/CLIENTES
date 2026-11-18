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


class ChatRequest(BaseModel):
    mensaje: str


@router.get("/api/khiara/status")
@router.get("/api/status")
def status_khiara():
    return {
        "nombre": "KHIARA",
        "avatar": "Gatita Rive Companion",
        "motor": "gemini-3.1-flash-lite",
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
    """Genera streaming de la respuesta del agente KHIARA para el widget de la gatita."""
    agente = get_agente()
    
    async def generador():
        try:
            # Evento inicial de pensamiento
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'thinking'})}\n\n"
            await asyncio.sleep(0.05)
            
            # Ejecución en hilo seguro para no bloquear FastAPI
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(None, lambda: agente.run(req.mensaje, stream=False))
            
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
            yield f"data: {json.dumps({'tipo': 'error', 'valor': str(e)})}\n\n"

    return StreamingResponse(generador(), media_type="text/event-stream")
