"""
Ruta oficial del Agente KHIARA para DASHBOARD_EK10.
Conecta el widget interactivo (Gatita Rive) con el cerebro de KHIARA mediante streaming nativo (SSE).
Incluye persistencia de conversaciones en SQLite, extracción autónoma de aprendizaje y soporte multi-proveedor.
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KHIARA_DIR = os.path.join(BASE_DIR, "KHIARA")
if KHIARA_DIR not in sys.path:
    sys.path.insert(0, KHIARA_DIR)

from khiara.core.agente import crear_agente_khiara
from khiara.core.logger_fallas import registrar_falla, obtener_ultimas_fallas
from khiara.cerebro.extractor_aprendizaje import analizar_y_aprender_de_turno
from khiara.core.config import (
    DEFAULT_MODEL,
    KHIARA_PROVIDER,
    GROQ_API_KEY,
    OLLAMA_HOST,
    GEMINI_API_KEY,
    CONVERSACIONES_DB_FILE
)

router = APIRouter(tags=["KHIARA"])

_agente_instancia = None
_sesion_actual = "khiara_sesion_principal"
_proveedor_actual = KHIARA_PROVIDER
_modelo_actual = DEFAULT_MODEL


def get_agente():
    global _agente_instancia, _proveedor_actual, _modelo_actual, _sesion_actual
    if _agente_instancia is None:
        _agente_instancia = crear_agente_khiara(
            modelo_id=_modelo_actual,
            proveedor=_proveedor_actual,
            session_id=_sesion_actual
        )
    return _agente_instancia


def reiniciar_agente(nuevo_session_id: Optional[str] = None):
    global _agente_instancia, _sesion_actual
    _agente_instancia = None
    if nuevo_session_id:
        _sesion_actual = nuevo_session_id
    return get_agente()


class ChatRequest(BaseModel):
    mensaje: str
    usuario_id: Optional[str] = "esteban"
    session_id: Optional[str] = None


class ConfigModelRequest(BaseModel):
    proveedor: Optional[str] = None # "gemini", "groq", "ollama"
    modelo: Optional[str] = None


@router.post("/api/chat/limpiar")
def limpiar_sesion_chat():
    """Reinicia la memoria de sesión del agente KHIARA."""
    import time
    nuevo_id = f"sesion_{int(time.time())}"
    reiniciar_agente(nuevo_session_id=nuevo_id)
    return {"ok": True, "mensaje": "Sesión reiniciada con éxito", "session_id": nuevo_id}


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
        "proveedor": _proveedor_actual,
        "motor": _modelo_actual,
        "persistencia": "SQLite (conversaciones.db)",
        "aprendizaje_activo": True,
        "disponibles": {
            "gemini": bool(GEMINI_API_KEY),
            "groq": bool(GROQ_API_KEY),
            "ollama_host": OLLAMA_HOST
        },
        "capacidades": [
            "Streaming Nativo de Tokens (SSE)",
            "Tool Calling (38 herramientas)",
            "Persistencia y Memoria Evolutiva (SQLite)",
            "Extracción Autónoma de Aprendizaje",
            "Grafo de Conocimiento (NetworkX)",
            "DuckDB",
            "REA Aryve"
        ],
        "estado": "lista"
    }


@router.post("/api/khiara/motor")
def cambiar_motor(req: ConfigModelRequest):
    """Permite alternar entre proveedores ultra-rápidos (groq, ollama, gemini) en caliente."""
    global _proveedor_actual, _modelo_actual
    if req.proveedor:
        _proveedor_actual = req.proveedor.lower().strip()
    if req.modelo:
        _modelo_actual = req.modelo.strip()
    elif _proveedor_actual == "groq":
        _modelo_actual = "llama-3.3-70b-versatile"
    elif _proveedor_actual == "ollama":
        _modelo_actual = "qwen2.5:7b"
    else:
        _modelo_actual = DEFAULT_MODEL
        
    reiniciar_agente()
    return {
        "ok": True,
        "proveedor": _proveedor_actual,
        "modelo": _modelo_actual,
        "mensaje": f"KHIARA ahora está operando con {_proveedor_actual} ({_modelo_actual})"
    }


@router.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """
    Genera streaming nativo token por token de KHIARA para el widget de la gatita.
    - Primer token en < 800ms
    - Escudo visual contra errores 400/429
    - Extracción de aprendizaje y guardado persistente en SQLite
    """
    agente = get_agente()
    loop = asyncio.get_running_loop()
    
    async def generador():
        nonlocal agente
        queue = asyncio.Queue()
        tokens_acumulados = []
        is_error = False
        empezo_hablar = False

        # 1. Animación inicial: pensativa
        yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'thinking'})}\n\n"
        await asyncio.sleep(0.01)

        def worker():
            try:
                user = req.usuario_id or "esteban"
                sess = req.session_id or f"sesion_{user}"
                gen = agente.run(req.mensaje, stream=True, user_id=user, session_id=sess)
                for chunk in gen:
                    c = getattr(chunk, "content", None)
                    if c:
                        loop.call_soon_threadsafe(queue.put_nowait, ("token", c))
                loop.call_soon_threadsafe(queue.put_nowait, ("end", None))
            except Exception as e_run:
                loop.call_soon_threadsafe(queue.put_nowait, ("exception", str(e_run)))

        # Ejecutar generador de tokens en el threadpool
        fut = loop.run_in_executor(None, worker)

        # 2. Transmisión token por token
        while True:
            tipo, valor = await queue.get()

            if tipo == "end":
                break

            elif tipo == "exception":
                is_error = True
                registrar_falla(req.mensaje, "STREAM_EXCEPTION", valor)
                agente = reiniciar_agente()
                msg_amable = "Esa información o servicio no se encuentra disponible por el momento. He registrado la incidencia para darle seguimiento. ¿Hay algo más en lo que pueda apoyarte?"
                if not empezo_hablar:
                    yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
                yield f"data: {json.dumps({'tipo': 'texto', 'valor': msg_amable})}\n\n"
                break

            elif tipo == "token":
                tokens_acumulados.append(valor)
                texto_total = "".join(tokens_acumulados)

                # Detección preventiva de errores crudos devueltos por el LLM en formato JSON
                if len(tokens_acumulados) <= 5 and ('"error":' in texto_total or '"code": 400' in texto_total or '"code": 429' in texto_total or 'INVALID_ARGUMENT' in texto_total):
                    is_error = True
                    registrar_falla(req.mensaje, "STREAM_RAW_API_ERROR", texto_total[:300])
                    agente = reiniciar_agente()
                    msg_amable = "Esa información o servicio no se encuentra disponible por el momento. Ya registré la consulta para revisarla. ¿Deseas preguntar otro dato?"
                    if not empezo_hablar:
                        yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
                    yield f"data: {json.dumps({'tipo': 'texto', 'valor': msg_amable})}\n\n"
                    break

                if not empezo_hablar:
                    yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
                    empezo_hablar = True

                # Enviar token al widget
                yield f"data: {json.dumps({'tipo': 'texto', 'valor': valor})}\n\n"

        # 3. Final de la respuesta
        yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'idle'})}\n\n"
        yield f"data: {json.dumps({'tipo': 'fin', 'valor': True})}\n\n"

        # 4. Extracción de aprendizaje automático en segundo plano
        if not is_error and tokens_acumulados:
            respuesta_texto = "".join(tokens_acumulados)
            try:
                loop.run_in_executor(
                    None,
                    lambda: analizar_y_aprender_de_turno(
                        req.mensaje,
                        respuesta_texto,
                        usuario_id=req.usuario_id or "esteban"
                    )
                )
            except Exception:
                pass

    return StreamingResponse(generador(), media_type="text/event-stream")
