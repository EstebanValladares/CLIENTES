"""
Cerebro Antigravity SDK para KHIARA.
Ejecuta el motor agéntico nativo de Google Antigravity (`google-antigravity`)
con streaming de tokens, soporte multimodal (imágenes/capturas de Aryve),
persistencia por sesión y herramientas directas de DASHBOARD_EK10.
"""

import os
import uuid
import base64
from pathlib import Path
from typing import Optional, AsyncGenerator, Dict

from khiara.core.config import GEMINI_API_KEY, DEFAULT_MODEL, MEMORIA_DIR, BASE_DIR
from khiara.herramientas.explorador import (
    tool_busqueda_general_local_dashboard,
    tool_busqueda_profunda_conexiones_externas,
    tool_consultar_catalogo_obras,
    tool_consultar_presupuesto_insumos_oc,
    tool_ubicar_insumo_en_obra,
    tool_consultar_movimientos_insumo,
    tool_consultar_escalatoria_precios,
    tool_consultar_grupos_insumos,
    tool_consultar_db_ek9_ocs,
    tool_consultar_sql_local,
    tool_buscar_usuarios_locales,
    tool_iniciar_creacion_usuario,
    tool_consultar_estado_creacion_usuario,
    tool_iniciar_creacion_posicion,
    tool_consultar_estado_creacion_posicion,
    tool_registrar_regla_evolutiva,
    tool_consultar_reglas_evolutivas,
    memoria_evolutiva_global,
)
from khiara.herramientas.conector_gmail import (
    tool_consultar_correos_recientes,
    tool_leer_correo_completo,
)

DASHBOARD_ROOT = BASE_DIR.parent
ANTIGRAVITY_SAVE_DIR = MEMORIA_DIR / "antigravity_sesiones"
CAPTURAS_DIR = MEMORIA_DIR / "capturas"
ANTIGRAVITY_SAVE_DIR.mkdir(parents=True, exist_ok=True)
CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)

# Mapa de session_id del widget -> conversation_id de Antigravity
_CONVERSACIONES_AGY: Dict[str, str] = {}


def antigravity_disponible() -> bool:
    try:
        import google.antigravity  # noqa: F401
        return True
    except Exception:
        return False


def limpiar_sesion_antigravity(session_id: Optional[str] = None):
    if session_id:
        _CONVERSACIONES_AGY.pop(session_id, None)
    else:
        _CONVERSACIONES_AGY.clear()


def _construir_instrucciones_khiara() -> str:
    partes = [
        "Eres KHIARA: Asistente autónoma de ingeniería y soporte de DASHBOARD_EK10 (Grupo Velas), impulsada por Google Antigravity.",
        "",
        "⚡ FORMATO Y LONGITUD (ADAPTABLE):",
        "- Para consultas rápidas o datos puntuales, sé breve y directa (2 a 4 líneas).",
        "- Si el usuario hace una pregunta extensa, compleja, o pide explicación detallada/a fondo, responde con la profundidad completa, pasos claros y tablas comparativas necesarias.",
        "- Responde siempre en español claro.",
        "- Si el usuario adjunta una captura de pantalla de Aryve/Enkontrol, analiza exactamente los campos visibles (Compañía, Centro de Costos, Insumo, Contratación, mensajes de error) y da el diagnóstico y solución directa.",
        "- Si algo no existe localmente, no arrojes errores técnicos; ofrece amablemente buscar más a fondo.",
    ]

    archivo_ek10 = MEMORIA_DIR / "conocimiento_ek10.md"
    if archivo_ek10.exists():
        try:
            txt = archivo_ek10.read_text(encoding="utf-8").strip()
            if txt:
                partes.append("\n📚 CONOCIMIENTO OPERATIVO VERIFICADO EK10 / ARYVE:")
                partes.append(txt)
        except Exception:
            pass

    try:
        memoria_evolutiva_global._cargar_reglas()
        reglas = memoria_evolutiva_global.listar_todas()
        if reglas:
            partes.append("\n🧠 REGLAS APRENDIDAS DEL EQUIPO:")
            for r in reglas[-20:]:
                partes.append(f"• [{r.get('categoria', 'REGLA')}] {r.get('regla', '')}")
    except Exception:
        pass

    return "\n".join(partes)


def _guardar_imagen_base64(imagen_b64: str) -> Optional[Path]:
    """Decodifica un dataURL o base64 de imagen y lo guarda temporalmente para entrada multimodal."""
    if not imagen_b64:
        return None
    try:
        ext = "png"
        datos = imagen_b64.strip()
        if "," in datos and datos.startswith("data:image/"):
            header, datos = datos.split(",", 1)
            if "jpeg" in header or "jpg" in header:
                ext = "jpg"
            elif "webp" in header:
                ext = "webp"
        raw = base64.b64decode(datos)
        ruta = CAPTURAS_DIR / f"captura_{uuid.uuid4().hex[:10]}.{ext}"
        ruta.write_bytes(raw)
        return ruta
    except Exception:
        return None


async def stream_antigravity(
    mensaje: str,
    session_id: str = "khiara_sesion_principal",
    imagen_base64: Optional[str] = None,
    modelo_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Ejecuta un turno de conversación usando el Google Antigravity SDK con streaming nativo.
    Soporta texto puro o multimodal (texto + imagen/captura de Aryve).
    """
    from google.antigravity import Agent, LocalAgentConfig
    from google.antigravity.types import Image, RetryConfig

    conv_id = _CONVERSACIONES_AGY.get(session_id)
    config = LocalAgentConfig(
        system_instructions=_construir_instrucciones_khiara(),
        model=modelo_id or DEFAULT_MODEL,
        api_key=GEMINI_API_KEY if GEMINI_API_KEY else None,
        workspaces=[str(DASHBOARD_ROOT)],
        save_dir=str(ANTIGRAVITY_SAVE_DIR),
        conversation_id=conv_id,
        retry_config=RetryConfig(max_retries=2),
        tools=[
            tool_busqueda_general_local_dashboard,
            tool_busqueda_profunda_conexiones_externas,
            tool_consultar_catalogo_obras,
            tool_consultar_presupuesto_insumos_oc,
            tool_ubicar_insumo_en_obra,
            tool_consultar_movimientos_insumo,
            tool_consultar_escalatoria_precios,
            tool_consultar_grupos_insumos,
            tool_consultar_db_ek9_ocs,
            tool_consultar_sql_local,
            tool_buscar_usuarios_locales,
            tool_iniciar_creacion_usuario,
            tool_consultar_estado_creacion_usuario,
            tool_iniciar_creacion_posicion,
            tool_consultar_estado_creacion_posicion,
            tool_registrar_regla_evolutiva,
            tool_consultar_reglas_evolutivas,
            tool_consultar_correos_recientes,
            tool_leer_correo_completo,
        ],
    )

    ruta_img = _guardar_imagen_base64(imagen_base64) if imagen_base64 else None
    try:
        async with Agent(config=config) as agent:
            if ruta_img and ruta_img.exists():
                prompt_text = mensaje.strip() or "Analiza esta captura de pantalla y dime qué ocurre y cómo resolverlo."
                payload = [prompt_text, Image.from_file(str(ruta_img))]
            else:
                payload = mensaje

            response = await agent.chat(payload)
            if getattr(agent, "conversation_id", None):
                _CONVERSACIONES_AGY[session_id] = agent.conversation_id

            async for token in response:
                if token:
                    yield str(token)
    finally:
        # Limpiar captura temporal para no acumular archivos innecesarios
        if ruta_img and ruta_img.exists():
            try:
                ruta_img.unlink()
            except Exception:
                pass
