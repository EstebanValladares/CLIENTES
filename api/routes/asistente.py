"""
API Route: Asistente Centinela de Esquina (OMFG Hello Toast)
Permite monitorear notificaciones proactivas, chat, escalatorias, razonamiento cognitivo y aprendizaje.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any
from ASISTENTE.asistente_service import AsistenteService
from ASISTENTE.cerebro.motor_razonamiento import MotorRazonamiento
from ASISTENTE.cerebro.grafo_conocimiento import GrafoConocimiento
from ASISTENTE.cerebro.aprendizaje import ModuloAprendizaje
from ASISTENTE.cerebro.config_cerebro import guardar_gemini_api_key, obtener_gemini_api_key

router = APIRouter(prefix="/api/asistente", tags=["Asistente"])


@router.get("/estado")
def obtener_estado(usuario_id: Optional[str] = Query(None), nombre: Optional[str] = Query(None)):
    """Retorna el estado del asistente y cualquier globo de diálogo pendiente para hablar."""
    return AsistenteService.obtener_estado_asistente(usuario_id=usuario_id, nombre_usuario=nombre)


@router.get("/saludo")
def obtener_saludo(usuario_id: Optional[str] = Query(None), nombre: Optional[str] = Query("Esteban")):
    """Genera un saludo proactivo en cuanto el usuario entra al Dashboard."""
    return AsistenteService.generar_saludo_inicial(usuario_id=usuario_id, nombre_usuario=nombre)


@router.get("/reaccion-clic")
def reaccionar_clic(usuario_id: Optional[str] = Query(None)):
    """Devuelve una frase divertida al hacer clic sobre el avatar de la tostada."""
    return AsistenteService.obtener_reaccion_clic(usuario_id=usuario_id)


@router.post("/configurar-nombre")
def configurar_nombre(payload: Dict[str, Any] = Body(...)):
    """Guarda el nombre personalizado que el usuario le asignó al asistente (bautizo inicial o edición)."""
    usuario_id = str(payload.get("usuario_id") or "default")
    nombre_asistente = str(payload.get("nombre_asistente") or "").strip()
    if not nombre_asistente:
        raise HTTPException(status_code=400, detail="El nombre del asistente no puede estar vacío")
    return AsistenteService.bautizar_asistente(usuario_id=usuario_id, nuevo_nombre=nombre_asistente)


@router.post("/hablar")
def emitir_habla(payload: Dict[str, Any] = Body(...)):
    """Dispara un globo de diálogo manual en pantalla."""
    titulo = payload.get("titulo", "Aviso del Asistente")
    mensaje = payload.get("mensaje", "")
    tipo = payload.get("tipo", "info")
    accion = payload.get("accion", "")
    return AsistenteService.emitir_mensaje_manual(titulo=titulo, mensaje=mensaje, tipo=tipo, accion=accion)


# ===================================================================
# ENDPOINTS COGNITIVOS: CEREBRO, GRAFOS, APRENDIZAJE Y GEMINI API
# ===================================================================

@router.post("/preguntar")
def consultar_cerebro(payload: Dict[str, Any] = Body(...)):
    """Procesa una consulta con razonamiento cognitivo (Gemini o Grafos locales)."""
    pregunta = str(payload.get("pregunta") or "").strip()
    usuario = str(payload.get("usuario") or "Esteban").strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")
    return MotorRazonamiento.procesar_consulta(pregunta=pregunta, usuario=usuario)


@router.post("/aprender")
def aprender_contenido(payload: Dict[str, Any] = Body(...)):
    """Permite enseñar un concepto, nota o regla al asistente para que lo memorice."""
    titulo = str(payload.get("titulo") or "").strip()
    contenido = str(payload.get("contenido") or "").strip()
    categoria = str(payload.get("categoria") or "MANUAL").strip()
    if not titulo or not contenido:
        raise HTTPException(status_code=400, detail="Título y contenido son requeridos")
    return ModuloAprendizaje.aprender_texto(titulo=titulo, contenido=contenido, categoria=categoria)


@router.post("/escanear-carpeta")
def escanear_archivos(payload: Dict[str, Any] = Body(default={})):
    """Escanea la carpeta de conocimiento (o ruta especificada) e ingesta archivos .md, .txt, .json."""
    ruta = payload.get("ruta")
    return ModuloAprendizaje.escanear_carpeta_conocimiento(ruta_carpeta=ruta)


@router.get("/grafo-stats")
def obtener_estadisticas_grafo():
    """Devuelve las métricas de nodos y conexiones en el grafo de conocimiento."""
    return {
        "ok": True,
        "grafo": GrafoConocimiento.obtener_estadisticas_grafo(),
        "gemini_disponible": bool(obtener_gemini_api_key())
    }


@router.post("/configurar-api-key")
def configurar_api_key(payload: Dict[str, Any] = Body(...)):
    """Permite registrar la API Key de Google Gemini para activar el modelo 2.5 Flash."""
    key = str(payload.get("api_key") or "").strip()
    ok = guardar_gemini_api_key(key)
    return {"ok": ok, "mensaje": "API Key de Gemini configurada con éxito" if ok else "Error al guardar"}
