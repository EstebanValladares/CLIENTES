"""
Agente KHIARA impulsado por Agno y Google Gemini.
Combina razonamiento ReAct, llamadas a funciones y grafos de conocimiento.
"""

import os
from typing import Optional
from agno.agent import Agent
from agno.models.google import Gemini
from agno.db.in_memory import InMemoryDb
from khiara.core.config import GEMINI_API_KEY, DEFAULT_MODEL
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
    memoria_evolutiva_global,
    red_global
)
from khiara.herramientas.conector_gmail import (
    tool_guardar_credenciales_gmail,
    tool_consultar_correos_recientes,
    tool_leer_correo_completo,
    tool_descargar_adjunto_correo
)


def crear_agente_khiara(modelo_id: Optional[str] = None) -> Agent:
    """Crea e inicializa el agente KHIARA con sus herramientas y personalidad."""
    model_name = modelo_id or DEFAULT_MODEL
    
    if GEMINI_API_KEY and not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

    model = Gemini(
        id=model_name,
        api_key=GEMINI_API_KEY if GEMINI_API_KEY else None
    )

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
        "🛠️ Reglas Específicas de Herramientas:",
        "• Búsqueda global local en todo el proyecto -> 'tool_busqueda_general_local_dashboard'",
        "• Búsqueda profunda en conexiones/bases de datos -> 'tool_busqueda_profunda_conexiones_externas'",
        "• Obras (275 obras) -> 'tool_consultar_catalogo_obras'",
        "• Insumos y Presupuestos (Presupuesto Real, Requisitado, Comprado, Por Comprar) -> 'tool_consultar_presupuesto_insumos_oc'",
        "• Usuarios locales (1,122 usuarios) -> 'tool_buscar_usuarios_locales'",
        "• Carpetas y Archivos -> 'tool_escanear_carpetas_proyecto' y 'tool_buscar_texto_en_archivos_locales'",
        "• Código y Grafo -> 'tool_consultar_grafo'",
        "• SQLite locales -> 'tool_consultar_sql_local'",
        "• Responde siempre en español, con precisión y brevedad impecable."
    ]

    agente = Agent(
        name="KHIARA",
        model=model,
        instructions=instrucciones,
        db=InMemoryDb(),
        add_history_to_context=True,
        num_history_messages=12,
        read_chat_history=True,
        tools=[
            tool_busqueda_general_local_dashboard,
            tool_busqueda_profunda_conexiones_externas,
            tool_consultar_catalogo_obras,
            tool_consultar_presupuesto_insumos_oc,
            tool_buscar_usuarios_locales,
            tool_escanear_carpetas_proyecto,
            tool_buscar_texto_en_archivos_locales,
            tool_consultar_grafo,
            tool_buscar_memoria_semantica,
            tool_guardar_recuerdo_memoria,
            tool_registrar_regla_evolutiva,
            tool_consultar_reglas_evolutivas,
            tool_trazar_camino_multi_repo,
            tool_generar_repo_map,
            tool_consultar_alertas_centinela,
            tool_consultar_glosario_negocio,
            tool_interpretar_consulta_negocio,
            tool_cargar_openapi,
            tool_buscar_endpoints_api,
            tool_consultar_endpoint_api,
            tool_consultar_duckdb,
            tool_describir_archivo_datos,
            tool_consultar_bd_relacional,
            tool_listar_tablas_bd_relacional,
            tool_consultar_sql_local,
            tool_calcular_formula,
            tool_consultar_reportes_rea,
            tool_escanear_pantalla_rea,
            tool_ejecutar_codigo_python,
            tool_crear_o_editar_archivo,
            tool_guardar_credenciales_gmail,
            tool_consultar_correos_recientes,
            tool_leer_correo_completo,
            tool_descargar_adjunto_correo
        ],
        markdown=True
    )
    return agente
