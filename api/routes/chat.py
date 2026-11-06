"""
API Route: Rutas del Chat Interno (Equipo y Torre de Control)
"""
from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from core.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class MensajeInput(BaseModel):
    canal: str = "general"
    remitente_id: str
    remitente_nombre: str
    texto: str
    remitente_rol: Optional[str] = "Colaborador"
    remitente_avatar: Optional[str] = ""
    destinatario_id: Optional[str] = ""
    destinatario_nombre: Optional[str] = ""

class PresenciaInput(BaseModel):
    usuario_id: str
    nombre: str
    puesto: Optional[str] = ""
    area: Optional[str] = ""
    avatar: Optional[str] = ""
    es_torre: Optional[bool] = False

class LeidoInput(BaseModel):
    canal: str
    usuario_id: str

@router.get("/mi-identidad")
def obtener_mi_identidad():
    """Detecta la identidad local del usuario en este equipo (Master o Cliente)."""
    return ChatService.obtener_identidad_local()

@router.get("/usuarios")
def obtener_usuarios_chat(usuario_actual: str = Query("")):
    """Retorna compañeros disponibles y su estado de conexión reciente."""
    res_proxy = ChatService.proxy_torre_get("/api/chat/usuarios", params={"usuario_actual": usuario_actual})
    if res_proxy is not None:
        return res_proxy
    return {"ok": True, "usuarios": ChatService.obtener_usuarios_presencia(usuario_actual)}

@router.get("/mensajes")
def obtener_mensajes_canal(canal: str = Query("general"), desde_id: int = Query(0), limite: int = Query(80), usuario_id: Optional[str] = Query(None)):
    """Obtiene el historial o nuevos mensajes de un canal o chat privado 1 a 1."""
    res_proxy = ChatService.proxy_torre_get("/api/chat/mensajes", params={"canal": canal, "desde_id": desde_id, "limite": limite, "usuario_id": usuario_id})
    if res_proxy is not None:
        return res_proxy
    mensajes = ChatService.obtener_mensajes(canal=canal, limite=limite, desde_id=desde_id, usuario_solicitante=usuario_id)
    return {"ok": True, "canal": canal, "mensajes": mensajes}

@router.post("/enviar")
def enviar_mensaje(msg: MensajeInput):
    """Envía un mensaje al canal grupal o en privado a un compañero."""
    res_proxy = ChatService.proxy_torre_post("/api/chat/enviar", json_data=msg.dict())
    if res_proxy is not None:
        return res_proxy
    res = ChatService.enviar_mensaje(
        canal=msg.canal,
        remitente_id=msg.remitente_id,
        remitente_nombre=msg.remitente_nombre,
        texto=msg.texto,
        remitente_rol=msg.remitente_rol or "Colaborador",
        remitente_avatar=msg.remitente_avatar or "",
        destinatario_id=msg.destinatario_id or "",
        destinatario_nombre=msg.destinatario_nombre or ""
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Error al enviar mensaje"))
    return res

@router.post("/presencia")
def registrar_presencia(presencia: PresenciaInput):
    """Heartbeat para indicar que el usuario tiene el dashboard abierto."""
    res_proxy = ChatService.proxy_torre_post("/api/chat/presencia", json_data=presencia.dict())
    if res_proxy is not None:
        return res_proxy
    res = ChatService.registrar_presencia(
        usuario_id=presencia.usuario_id,
        nombre=presencia.nombre,
        puesto=presencia.puesto or "",
        area=presencia.area or "",
        avatar=presencia.avatar or "",
        es_torre=bool(presencia.es_torre)
    )
    return res

@router.post("/leido")
def marcar_mensajes_leidos(body: LeidoInput):
    """Marca como leídos los mensajes de la conversación activa."""
    res_proxy = ChatService.proxy_torre_post("/api/chat/leido", json_data=body.dict())
    if res_proxy is not None:
        return res_proxy
    ok = ChatService.marcar_como_leidos(body.canal, body.usuario_id)
    return {"ok": ok}

@router.get("/resumen")
def obtener_resumen_canales(usuario_id: str = Query(...)):
    """Obtiene no leídos globales y por cada contacto 1 a 1."""
    res_proxy = ChatService.proxy_torre_get("/api/chat/resumen", params={"usuario_id": usuario_id})
    if res_proxy is not None:
        return res_proxy
    resumen = ChatService.obtener_resumen_canales(usuario_id)
    return {"ok": True, "resumen": resumen}

@router.get("/conversaciones")
def obtener_conversaciones(usuario_id: str = Query(...)):
    """Retorna las conversaciones activas estilo WhatsApp para el usuario."""
    res_proxy = ChatService.proxy_torre_get("/api/chat/conversaciones", params={"usuario_id": usuario_id})
    if res_proxy is not None:
        return res_proxy
    conversaciones = ChatService.obtener_conversaciones(usuario_id)
    return {"ok": True, "conversaciones": conversaciones}

