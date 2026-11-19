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
from khiara.core.flujo_alta import procesar_flujo_alta, limpiar_flujo_sesion
from khiara.cerebro.extractor_aprendizaje import (
    analizar_y_aprender_de_turno,
    detectar_comando_aprendizaje
)
from khiara.herramientas.explorador import (
    tool_consultar_escalatoria_precios,
    tool_consultar_catalogo_obras,
    tool_buscar_usuarios_locales,
    tool_consultar_estado_creacion_usuario,
    tool_consultar_grupos_insumos
)
from khiara.herramientas.conector_gmail import (
    tool_consultar_correos_recientes,
    tool_leer_correo_completo
)
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
    """Reinicia la memoria de sesión y cualquier flujo activo de alta de KHIARA."""
    import time
    from khiara.core.flujo_alta import _ESTADOS_SESION
    _ESTADOS_SESION.clear()
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


def resolver_consulta_local_directa(mensaje: str) -> Optional[str]:
    """Fast-Path local (<100ms): resuelve consultas operativas directas sin esperar a APIs externas."""
    import re
    msg_low = mensaje.lower()

    # 0. Estado / progreso de alta de usuario
    if any(k in msg_low for k in ["como va el alta", "cómo va el alta", "estado del alta", "progreso del alta", "estatus del alta"]):
        return tool_consultar_estado_creacion_usuario()
    
    # 1. Escalatorias de precios e insumos
    if any(k in msg_low for k in ["escalatoria", "escalado", "escalatorias"]):
        m_insumo = re.search(r'\b\d{5,8}\b', mensaje)
        if m_insumo:
            return tool_consultar_escalatoria_precios(termino_o_clave_insumo=m_insumo.group(0))
        m_obra = re.search(r'\b[A-Za-z0-9]{3,4}\b', mensaje)
        if m_obra and m_obra.group(0).lower() not in {"obra", "para", "como", "esta", "quien"}:
            res = tool_consultar_escalatoria_precios(obra_clave=m_obra.group(0))
            if "No se encontraron" not in res:
                return res

    # 2. Catálogo de obras
    if "obra" in msg_low and any(k in msg_low for k in ["existe", "catalogo", "catálogo"]):
        m_obra = re.search(r'\b[A-Za-z0-9]{3,4}\b', mensaje.upper())
        if m_obra and m_obra.group(0) not in {"OBRA", "PARA", "ESTA", "CUAL", "HOLA"}:
            return tool_consultar_catalogo_obras(termino_o_clave=m_obra.group(0))

    # 3. Usuarios locales
    if "usuario" in msg_low and "existe" in msg_low:
        m_nom = re.search(r'llamado\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)', mensaje, re.IGNORECASE)
        if m_nom:
            return tool_buscar_usuarios_locales(termino_busqueda=m_nom.group(1).strip())

    # 4. Correos / Gmail (evitar interceptar si el usuario está escribiendo un correo en medio de otro contexto)
    if any(k in msg_low for k in ["correo nuevo", "correos nuevos", "hay correos", "tengo correo", "tenog un correo", "revisa mi correo", "revisar correo", "bandeja", "inbox", "correos recientes", "ultimos correos", "últimos correos"]):
        solo_no_leidos = not ("todos" in msg_low or "leidos" in msg_low or "leídos" in msg_low or "recientes" in msg_low or "ultimos" in msg_low or "últimos" in msg_low)
        return tool_consultar_correos_recientes(solo_no_leidos=solo_no_leidos, limite=3)

    # 5. Catálogo de Tipos y Grupos de Insumos (Tipo 1..9, Grupos 01..68)
    m_tg1 = re.search(r"tipo\s*(\d+)\D{1,15}(?:grupo|gruipo)\s*(\d+)", msg_low)
    m_tg2 = re.search(r"(?:grupo|gruipo)\s*(\d+)\D{1,15}tipo\s*(\d+)", msg_low)
    if m_tg1:
        return tool_consultar_grupos_insumos(tipo=m_tg1.group(1), numero_grupo=m_tg1.group(2))
    if m_tg2:
        return tool_consultar_grupos_insumos(tipo=m_tg2.group(2), numero_grupo=m_tg2.group(1))
    m_solo_tipo = re.search(r"grupos?\s+(?:del?\s+)?tipo\s*(\d+)|tipo\s*(\d+)\s+grupos?", msg_low)
    if m_solo_tipo:
        t_num = m_solo_tipo.group(1) or m_solo_tipo.group(2)
        return tool_consultar_grupos_insumos(tipo=t_num)
    if any(k in msg_low for k in ["tipos de insumo", "tipos de insumos", "lista de tipos"]):
        return tool_consultar_grupos_insumos()
    m_busq_grupo = re.search(r"(?:en qu[eé] grupo|qu[eé] grupo es|qu[eé] tipo y grupo es)\s+(?:est[aá]\s+)?([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{3,30})", msg_low)
    if m_busq_grupo:
        return tool_consultar_grupos_insumos(buscar_nombre=m_busq_grupo.group(1).strip(" ?¿"))

    return None


@router.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """
    Genera streaming nativo token por token de KHIARA para el widget de la gatita.
    - Fast-Path instantáneo (<100ms) para alta de usuarios, escalatorias, obras, usuarios y Gmail
    - Streaming real de tokens para consultas abiertas con IA
    - Escudo visual contra errores 400/429/503 con autorrecuperación local directa
    """
    agente = get_agente()
    loop = asyncio.get_running_loop()
    user = req.usuario_id or "esteban"
    sess = req.session_id or f"sesion_{user}"
    
    async def generador():
        nonlocal agente
        queue = asyncio.Queue()
        tokens_acumulados = []
        is_error = False
        empezo_hablar = False

        # 1. Animación inicial: pensativa
        yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'thinking'})}\n\n"

        # ⚡ PASO 0 (INSTANTÁNEO < 10ms): Comandos de aprendizaje controlado ('aprende que...', 'qué has aprendido', 'olvida RULE_xxx')
        resp_aprend = detectar_comando_aprendizaje(req.mensaje, usuario_id=user)
        if resp_aprend:
            if "✅" in resp_aprend or "🗑️" in resp_aprend:
                agente = reiniciar_agente()
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'texto', 'valor': resp_aprend})}\n\n"
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'idle'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'fin', 'valor': True})}\n\n"
            return

        # ⚡ PASO 0.5 (INSTANTÁNEO < 50ms): Flujo conversacional de Alta de Usuarios y Posiciones
        resp_flujo = procesar_flujo_alta(sess, req.mensaje)
        if resp_flujo:
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'texto', 'valor': resp_flujo})}\n\n"
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'idle'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'fin', 'valor': True})}\n\n"
            return

        # ⚡ PASO 1 (FAST-PATH LOCAL < 100ms): Consultas operativas directas (escalatorias, Gmail, obras, usuarios)
        resp_rapida = await loop.run_in_executor(None, lambda: resolver_consulta_local_directa(req.mensaje))
        if resp_rapida:
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'texto', 'valor': resp_rapida})}\n\n"
            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'idle'})}\n\n"
            yield f"data: {json.dumps({'tipo': 'fin', 'valor': True})}\n\n"
            return

        await asyncio.sleep(0.01)

        def worker():
            try:
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
                
                # Intentar autorrecuperación directa con base de datos local
                res_directa = resolver_consulta_local_directa(req.mensaje)
                if res_directa:
                    registrar_falla(req.mensaje, "FALLBACK_LOCAL_AUTO_RECOVERED", "503/400 resuelto por base de datos local")
                    if not empezo_hablar:
                        yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
                        empezo_hablar = True
                    yield f"data: {json.dumps({'tipo': 'texto', 'valor': res_directa})}\n\n"
                    break

                msg_amable = "Esa información o servicio no se encuentra disponible por el momento. He registrado la incidencia para darle seguimiento. ¿Hay algo más en lo que pueda apoyarte?"
                if not empezo_hablar:
                    yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
                yield f"data: {json.dumps({'tipo': 'texto', 'valor': msg_amable})}\n\n"
                break

            elif tipo == "token":
                tokens_acumulados.append(valor)
                texto_total = "".join(tokens_acumulados)

                # Detección preventiva de errores crudos devueltos por el LLM en formato JSON
                if len(tokens_acumulados) <= 5 and ('"error":' in texto_total or '"code": 400' in texto_total or '"code": 429' in texto_total or '"code": 503' in texto_total or 'INVALID_ARGUMENT' in texto_total or 'high demand' in texto_total):
                    is_error = True
                    registrar_falla(req.mensaje, "STREAM_RAW_API_ERROR", texto_total[:300])
                    agente = reiniciar_agente()
                    
                    # Intentar autorrecuperación directa con base de datos local
                    res_directa = resolver_consulta_local_directa(req.mensaje)
                    if res_directa:
                        registrar_falla(req.mensaje, "FALLBACK_LOCAL_AUTO_RECOVERED", "503/400 resuelto por base de datos local")
                        if not empezo_hablar:
                            yield f"data: {json.dumps({'tipo': 'estado', 'valor': 'speaking'})}\n\n"
                            empezo_hablar = True
                        yield f"data: {json.dumps({'tipo': 'texto', 'valor': res_directa})}\n\n"
                        break

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
