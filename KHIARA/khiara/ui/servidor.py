"""
Servidor Web y Widget Interactivo de KHIARA con Avatar Animado en Rive.
Conecta la gatita animada con el cerebro de KHIARA mediante streaming (SSE).
"""

import os
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from khiara.core.agente import crear_agente_khiara
from khiara.cerebro.ontologia import GlosarioNegocio

_agente_instancia = None

def get_agente():
    global _agente_instancia
    if _agente_instancia is None:
        _agente_instancia = crear_agente_khiara()
    return _agente_instancia

app = FastAPI(title="KHIARA - Tu Compañera Felina de IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIR_ACTUAL = Path(__file__).parent
STATIC_DIR = DIR_ACTUAL / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class ChatRequest(BaseModel):
    mensaje: str

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = DIR_ACTUAL / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>KHIARA UI no encontrada</h1>"

@app.get("/demo", response_class=HTMLResponse)
async def demo():
    demo_path = DIR_ACTUAL / "demo_dashboard.html"
    if demo_path.exists():
        return demo_path.read_text(encoding="utf-8")
    return "<h1>Demo no encontrada</h1>"

@app.get("/api/status")
async def status():
    return {
        "nombre": "KHIARA",
        "avatar": "Muza Cat Companion",
        "motor": "gemini-3.1-flash-lite",
        "capacidades": ["Tool Calling", "DuckDB", "REA Aryve", "FastAPI Connector", "Ontología Velas"],
        "estado": "lista"
    }

@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """Genera streaming de la respuesta del agente KHIARA."""
    agente = get_agente()
    
    async def generador():
        try:
            # Enviamos evento de pensamiento
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'thinking'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Ejecución en hilo para no bloquear el bucle de eventos
            loop = asyncio.get_event_loop()
            respuesta = await loop.run_in_executor(None, lambda: agente.run(req.mensaje, stream=False))
            
            # Enviamos evento de respuesta
            texto = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
            
            # Chunking suave para simular flujo de habla
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

def iniciar_servidor(host="0.0.0.0", port=8501):
    import uvicorn
    uvicorn.run("khiara.ui.servidor:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    iniciar_servidor()
