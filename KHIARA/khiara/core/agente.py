"""
Agente KHIARA impulsado por Agno y Google Gemini.
Combina razonamiento ReAct, llamadas a funciones y grafos de conocimiento.
"""

import os
import requests
from typing import Optional, List, Dict, Any
from khiara.core.config import (
    GEMINI_API_KEY,
    DEFAULT_MODEL,
    KHIARA_PROVIDER,
    GROQ_API_KEY,
    OLLAMA_HOST,
    CONVERSACIONES_DB_FILE
)


class _ChunkLigero:
    def __init__(self, content: str):
        self.content = content


class AgenteLigeroREST:
    """
    Agente de respaldo 100% Python puro (usa solo `requests`) para equipos CLIENTES
    donde no esté instalado `agno` o `google-antigravity` (ej. Python 3.14).
    Mantiene historial por sesión, instrucciones completas de EK10 y soporte de streaming.
    """
    def __init__(self, modelo_id: str, api_key: str, instructions: List[str]):
        self.modelo_id = modelo_id or "gemini-3.5-flash-lite"
        self.api_key = api_key
        self.system_text = "\n".join(instructions)
        self._historial: Dict[str, List[Dict[str, Any]]] = {}

    def _generar_texto(self, mensaje: str, session_id: str = "default") -> str:
        if not self.api_key:
            return "KHIARA activa en modo local (configura GEMINI_API_KEY en .env para consultas abiertas con IA)."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.modelo_id}:generateContent?key={self.api_key}"
        hist = self._historial.setdefault(session_id, [])
        hist.append({"role": "user", "parts": [{"text": str(mensaje)}]})
        if len(hist) > 12:
            hist[:] = hist[-12:]
        payload = {
            "systemInstruction": {"parts": [{"text": self.system_text}]},
            "contents": hist,
        }
        try:
            r = requests.post(url, json=payload, timeout=20)
            if r.status_code == 200:
                data = r.json()
                cands = data.get("candidates") or []
                if cands:
                    parts = (cands[0].get("content") or {}).get("parts") or []
                    texto = "".join(str(p.get("text", "")) for p in parts).strip()
                    if texto:
                        hist.append({"role": "model", "parts": [{"text": texto}]})
                        return texto
            return f'{{"error": {{"code": {r.status_code}, "message": "HTTP {r.status_code}"}}}}'
        except Exception as e:
            return f'{{"error": {{"code": 503, "message": "{str(e)}"}}}}'

    def run(self, mensaje: str, stream: bool = False, user_id: Optional[str] = None, session_id: Optional[str] = None, **kwargs):
        sid = session_id or user_id or "default"
        texto = self._generar_texto(mensaje, session_id=sid)
        if stream:
            def _gen():
                palabras = texto.split(" ")
                bloque = []
                for p in palabras:
                    bloque.append(p)
                    if len(bloque) >= 4:
                        yield _ChunkLigero(" ".join(bloque) + " ")
                        bloque = []
                if bloque:
                    yield _ChunkLigero(" ".join(bloque))
            return _gen()
        return _ChunkLigero(texto)
from khiara.herramientas.explorador import (
    tool_consultar_grafo,
    tool_consultar_sql_local,
    tool_calcular_formula,
    tool_consultar_reportes_rea,
    tool_escanear_pantalla_rea,
    tool_consultar_duckdb,
    tool_describir_archivo_datos,
    tool_consultar_bd_relacional,
    tool_listar_tablas_bd_relacional,
    tool_buscar_memoria_semantica,
    tool_guardar_recuerdo_memoria,
    tool_ejecutar_codigo_python,
    tool_crear_o_editar_archivo,
    tool_registrar_regla_evolutiva,
    tool_consultar_reglas_evolutivas,
    tool_trazar_camino_multi_repo,
    tool_generar_repo_map,
    tool_consultar_alertas_centinela,
    tool_cargar_openapi,
    tool_buscar_endpoints_api,
    tool_consultar_endpoint_api,
    tool_consultar_glosario_negocio,
    tool_interpretar_consulta_negocio,
    tool_buscar_usuarios_locales,
    tool_escanear_carpetas_proyecto,
    tool_buscar_texto_en_archivos_locales,
    tool_consultar_catalogo_obras,
    tool_consultar_presupuesto_insumos_oc,
    tool_busqueda_general_local_dashboard,
    tool_busqueda_profunda_conexiones_externas,
    tool_iniciar_creacion_usuario,
    tool_consultar_estado_creacion_usuario,
    tool_iniciar_creacion_posicion,
    tool_consultar_estado_creacion_posicion,
    tool_ubicar_insumo_en_obra,
    tool_consultar_movimientos_insumo,
    tool_consultar_escalatoria_precios,
    tool_consultar_grupos_insumos,
    tool_consultar_db_ek9_ocs,
    memoria_evolutiva_global,
    red_global
)
from khiara.herramientas.conector_gmail import (
    tool_guardar_credenciales_gmail,
    tool_consultar_correos_recientes,
    tool_leer_correo_completo,
    tool_descargar_adjunto_correo
)


def crear_agente_khiara(
    modelo_id: Optional[str] = None,
    proveedor: Optional[str] = None,
    session_id: Optional[str] = None
) -> Any:
    """Crea e inicializa el agente KHIARA con soporte multi-proveedor y fallback 100% Python puro si Agno no está instalado."""
    prov = (proveedor or KHIARA_PROVIDER).lower()
    model_name = modelo_id or DEFAULT_MODEL

    instrucciones = [
        "Eres KHIARA: Asistente autónoma de ingeniería y soporte de DASHBOARD_EK10.",
        "",
        "⚡ FORMATO Y LONGITUD DE RESPUESTAS (REGLA FUNDAMENTAL):",
        "- SÉ BREVE, CONCISA Y VE DIRECTO AL GRANO.",
        "- El chat es una ventanita compacta tipo widget en la pantalla del usuario. NUNCA escribas respuestas gigantes ni párrafos largos que llenen la ventana.",
        "- Da respuestas cortas de 2 a 4 oraciones o viñetas muy puntuales con los datos clave.",
        "- Evita saludos repetitivos o introducciones largas, ve directo al dato o solución.",
        "- Si el usuario quiere más profundidad o detalles técnicos, te los pedirá.",
        "",
        "🔄 ESTRATEGIA DE BÚSQUEDA EN DOS NIVELES (LOCAL vs A FONDO):",
        "1. NIVEL 1 (LOCAL PRIMERO): Toda consulta ordinaria se responde usando la información LOCAL de las carpetas de DASHBOARD_EK10 (Obras, Insumos, Usuarios, Proveedores, Archivos y Bases de Datos locales). Usa 'tool_busqueda_general_local_dashboard', 'tool_consultar_catalogo_obras', 'tool_consultar_presupuesto_insumos_oc', 'tool_buscar_usuarios_locales'.",
        "2. MANEJO AMABLE DE NO ENCONTRADO (CERO ERRORES): Si algo no aparece en los archivos locales, NUNCA arrojes errores técnicos, ni códigos de error, ni digas que falló la conexión. Responde amablemente:",
        "   'No encontré información sobre [término] en los archivos locales del Dashboard. ¿Te gustaría que busque más a fondo en las bases de datos y conexiones externas?'",
        "3. NIVEL 2 (BÚSQUEDA A FONDO BAJO CONFIRMACIÓN): Si el usuario responde 'sí', 'busca más a fondo', 'revisa en la base de datos', etc., EJECUTA 'tool_busqueda_profunda_conexiones_externas' para consultar APIs en vivo de Aryve, SQLite de escalatorias, mapeo de lotes y servidores externos.",
        "",
        "🤖 CREACIÓN Y ALTA CONVERSACIONAL (USUARIOS Y POSICIONES):",
        "- Si el usuario dice que quiere dar de alta o crear un usuario/colaborador: ENTREVÍSTALO PASO A PASO con amabilidad:",
        "  1. Pide su Nombre y Apellidos completos.",
        "  2. Pide su Correo corporativo (ej. usuario@grupovelas.com).",
        "  3. Pide su Puesto o Posición (puedes sugerir puestos o claves POS-XXXX existentes con 'tool_buscar_usuarios_locales').",
        "- Antes de ejecutar la acción, muestra una breve tarjeta de confirmación de los datos y pregúntale: '¿Deseas que proceda con el alta en Aryve?'",
        "- Solo cuando el usuario confirme ('sí', 'adelante', 'crear'), ejecuta 'tool_iniciar_creacion_usuario'.",
        "- Para puestos nuevos: pide la clave (ej. POS-1090), nombre del puesto y categoría, confirma y ejecuta 'tool_iniciar_creacion_posicion'.",
        "- Si te preguntan '¿cómo va el alta?' o el progreso, consulta con 'tool_consultar_estado_creacion_usuario' o 'tool_consultar_estado_creacion_posicion'.",
        "",
        "🛠️ Reglas Específicas de Herramientas:",
        "• Creación y altas -> 'tool_iniciar_creacion_usuario', 'tool_consultar_estado_creacion_usuario', 'tool_iniciar_creacion_posicion', 'tool_consultar_estado_creacion_posicion'",
        "• Búsqueda global local en todo el proyecto -> 'tool_busqueda_general_local_dashboard'",
        "• Búsqueda profunda en conexiones/bases de datos -> 'tool_busqueda_profunda_conexiones_externas'",
        "• Obras (275 obras) -> 'tool_consultar_catalogo_obras'",
        "• Insumos y Presupuestos (Presupuesto Real, Requisitado, Comprado, Por Comprar) -> 'tool_consultar_presupuesto_insumos_oc'",
        "• DÓNDE SE ENCUENTRA UN INSUMO (Frentes, Partidas, Lotes y OCs) -> 'tool_ubicar_insumo_en_obra' y 'tool_consultar_movimientos_insumo'",
        "• ESCALATORIA DE PRECIOS E INSUMOS ESCALADOS (Obras, precios, insumos) -> 'tool_consultar_escalatoria_precios'",
        "• TIPOS Y GRUPOS DE INSUMOS (Tipo 1 al 9, grupos 01..68, validar existencia) -> 'tool_consultar_grupos_insumos'",
        "• Usuarios locales (1,122 usuarios) -> 'tool_buscar_usuarios_locales'",
        "• Carpetas y Archivos -> 'tool_escanear_carpetas_proyecto' y 'tool_buscar_texto_en_archivos_locales'",
        "• Código y Grafo -> 'tool_consultar_grafo'",
        "• SQLite locales -> 'tool_consultar_sql_local'",
        "• Responde siempre en español, con precisión y brevedad impecable."
    ]

    # Inyección automática de Conocimiento Operativo EK10 (conocimiento_ek10.md)
    from khiara.core.config import MEMORIA_DIR
    archivo_ek10 = MEMORIA_DIR / "conocimiento_ek10.md"
    if archivo_ek10.exists():
        try:
            contenido_ek10 = archivo_ek10.read_text(encoding="utf-8").strip()
            if contenido_ek10:
                instrucciones.append("\n📚 CONOCIMIENTO OPERATIVO VERIFICADO EK10 / ARYVE:")
                instrucciones.append(contenido_ek10)
        except Exception:
            pass

    # Inyección automática de Reglas Evolutivas aprendidas (reglas_evolutivas.json)
    try:
        memoria_evolutiva_global._cargar_reglas()
        reglas_guardadas = memoria_evolutiva_global.listar_todas()
        if reglas_guardadas:
            bloque_reglas = ["\n🧠 REGLAS Y APRENDIZAJES GUARDADOS POR EL EQUIPO:"]
            for r in reglas_guardadas[-25:]:
                bloque_reglas.append(f"• [{r.get('categoria', 'REGLA')}] {r.get('regla', '')}")
            instrucciones.extend(bloque_reglas)
    except Exception:
        pass

    try:
        from agno.agent import Agent
        from agno.models.google import Gemini
        from agno.db.in_memory import InMemoryDb
    except ImportError:
        return AgenteLigeroREST(modelo_id=model_name, api_key=GEMINI_API_KEY, instructions=instrucciones)

    # Selección de proveedor LLM
    if prov == "groq" and GROQ_API_KEY:
        try:
            from agno.models.groq import Groq
            m_id = modelo_id or "llama-3.3-70b-versatile"
            model = Groq(id=m_id, api_key=GROQ_API_KEY)
        except Exception:
            model = Gemini(id=model_name, api_key=GEMINI_API_KEY if GEMINI_API_KEY else None)
    elif prov == "ollama":
        try:
            from agno.models.ollama import Ollama
            m_id = modelo_id or "qwen2.5:7b"
            model = Ollama(id=m_id, host=OLLAMA_HOST)
        except Exception:
            model = Gemini(id=model_name, api_key=GEMINI_API_KEY if GEMINI_API_KEY else None)
    else:
        if GEMINI_API_KEY and not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        model = Gemini(
            id=model_name,
            api_key=GEMINI_API_KEY if GEMINI_API_KEY else None,
            client_params={"http_options": {"retry_options": {"attempts": 2}}}
        )

    # Persistencia de conversaciones en SQLite (o memoria en contingencia)
    try:
        from agno.db.sqlite import SqliteDb
        db = SqliteDb(db_file=str(CONVERSACIONES_DB_FILE))
    except Exception:
        db = InMemoryDb()

    agente = Agent(
        name="KHIARA",
        model=model,
        instructions=instrucciones,
        db=db,
        session_id=session_id or "khiara_sesion_principal",
        add_history_to_context=True,
        num_history_messages=8,
        read_chat_history=True,
        tools=[
            tool_iniciar_creacion_usuario,
            tool_consultar_estado_creacion_usuario,
            tool_iniciar_creacion_posicion,
            tool_consultar_estado_creacion_posicion,
            tool_busqueda_general_local_dashboard,
            tool_busqueda_profunda_conexiones_externas,
            tool_consultar_catalogo_obras,
            tool_consultar_presupuesto_insumos_oc,
            tool_ubicar_insumo_en_obra,
            tool_consultar_movimientos_insumo,
            tool_consultar_escalatoria_precios,
            tool_consultar_grupos_insumos,
            tool_consultar_db_ek9_ocs,
            tool_buscar_usuarios_locales,
            tool_escanear_carpetas_proyecto,
            tool_buscar_texto_en_archivos_locales,
            tool_registrar_regla_evolutiva,
            tool_consultar_reglas_evolutivas,
            tool_consultar_sql_local,
            tool_consultar_reportes_rea,
            tool_guardar_credenciales_gmail,
            tool_consultar_correos_recientes,
            tool_leer_correo_completo
        ],
        markdown=True
    )
    return agente
