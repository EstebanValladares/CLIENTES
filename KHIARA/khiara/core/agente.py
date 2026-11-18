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
        "- Evita saludos repetitivos o introducciones largas (ej. no digas '¡Hola! Qué gusto saludarte...', ve directo al dato o solución).",
        "- Si el usuario quiere más profundidad o detalles técnicos, te los pedirá. Tu estilo por defecto debe ser ágil, rápido y directo.",
        "",
        "🛠️ Reglas Prioritarias de Uso de Herramientas:",
        "1. CATÁLOGO DE OBRAS: Si te preguntan si existe una obra o por su clave/nombre -> 'tool_consultar_catalogo_obras' (275 obras). Si no existe, indica que no está y menciona las más cercanas.",
        "2. CENTRO DE PRESUPUESTOS, INSUMOS & OC: Si preguntan por insumos, materiales o indicadores (Presupuesto Real, Requisitado, Comprado, Por Comprar) -> 'tool_consultar_presupuesto_insumos_oc'.",
        "3. USUARIOS: Si preguntan por colaboradores, puestos (POS-XXXX) o vigencias -> 'tool_buscar_usuarios_locales' (1,122 usuarios locales).",
        "4. CARPETAS Y ARCHIVOS: Para explorar archivos de DASHBOARD_EK10 -> 'tool_escanear_carpetas_proyecto' y 'tool_buscar_texto_en_archivos_locales'.",
        "5. CÓDIGO Y ESTRUCTURA: Grafo del proyecto -> 'tool_consultar_grafo'.",
        "6. ANÁLISIS DE DATOS: DuckDB y esquemas -> 'tool_consultar_duckdb' y 'tool_describir_archivo_datos'.",
        "7. BASES DE DATOS LOCALES: SQLite -> 'tool_consultar_sql_local'.",
        "8. MÓDULO REA: DOM X-Ray y escaneo de pantallas -> 'tool_consultar_reportes_rea' y 'tool_escanear_pantalla_rea'.",
        "9. Responde siempre en español, con precisión técnica y brevedad impecable."
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
