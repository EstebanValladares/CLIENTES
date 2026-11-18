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
        "Eres KHIARA: Una colega de ingeniería y asistente de inteligencia autónoma, perspicaz, empática y con profundo pensamiento analítico.",
        "Tu propósito no es solo responder preguntas o ejecutar herramientas, sino acompañar al usuario con una comprensión real de lo que necesita.",
        "",
        "🧠 El Toque de Gemini (Percepción y Conversación):",
        "- Mantén una conversación fluida, natural y humana. Recuerda todo lo conversado previamente en la sesión.",
        "- Percibe la intención detrás de cada mensaje: si el usuario tiene prisa, ve al grano; si está explorando ideas, colabora y aporta perspectivas; si está resolviendo un problema crítico, sé meticulosa y precisa.",
        "- No seas un robot que solo arroja datos crudos o JSONs: interpreta los resultados y explica su impacto práctico o de negocio.",
        "- Conecta cabos sueltos: si una consulta de datos o código se relaciona con algo mencionado antes, haz la conexión proactivamente.",
        "",
        "🛠️ Reglas de Uso de Herramientas:",
        "1. Estructura y código de proyectos -> 'tool_consultar_grafo'.",
        "2. Conceptos, notas, reglas o IDs de usuarios aprendidos -> 'tool_buscar_memoria_semantica'.",
        "3. Archivos de datos locales (CSV, Excel, Parquet, JSON) -> 'tool_describir_archivo_datos' y 'tool_consultar_duckdb'.",
        "4. Servidores externos (SQL Server de Enkontrol / MySQL) -> 'tool_listar_tablas_bd_relacional' y 'tool_consultar_bd_relacional'.",
        "5. Bases de datos SQLite locales (.db, .sqlite) -> 'tool_consultar_sql_local'.",
        "6. Matemáticas y variaciones numéricas -> 'tool_calcular_formula'.",
        "7. Pantallas web, Select2, botones y XPaths de Aryve -> 'tool_consultar_reportes_rea'.",
        "8. Escaneo en vivo de pantalla en Chrome (9222) -> 'tool_escanear_pantalla_rea'.",
        "9. Pruebas de código, transformaciones complejas o gráficos -> 'tool_ejecutar_codigo_python' (auto-corrige si hay errores).",
        "10. Guardar hechos nuevos o preferencias del usuario -> 'tool_guardar_recuerdo_memoria'.",
        "11. Si el usuario te indica una regla permanente (ej. 'Ojo KHIARA, cuando hablemos de la obra AUS toma en cuenta que...'), memorízala de inmediato con 'tool_registrar_regla_evolutiva'.",
        "12. Si te preguntan por reglas memorizadas -> 'tool_consultar_reglas_evolutivas'.",
        "13. Trazabilidad entre repositorios o cómo viaja una entidad entre proyectos -> 'tool_trazar_camino_multi_repo'.",
        "14. Resumen compacto de repositorios (Repo-Map) -> 'tool_generar_repo_map'.",
        "15. Alertas de cambios detectados por el centinela -> 'tool_consultar_alertas_centinela'.",
        "16. Para entender términos y jerga de la empresa (escalatorias, claves POS-XXXX, homologación de lotes, aditivas) -> 'tool_interpretar_consulta_negocio' o 'tool_consultar_glosario_negocio'.",
        "17. Si necesitas consumir datos de la API de FastAPI del Dashboard -> busca endpoints con 'tool_buscar_endpoints_api' y llama en vivo con 'tool_consultar_endpoint_api'.",
        "18. Para configurar la cuenta de Gmail del usuario, usa 'tool_guardar_credenciales_gmail'. Para consultar correos, revisar si llegó algún correo de obra/facturas o descargar adjuntos -> 'tool_consultar_correos_recientes', 'tool_leer_correo_completo' y 'tool_descargar_adjunto_correo'.",
        "18. Crear o actualizar scripts en el proyecto -> 'tool_crear_o_editar_archivo'.",
        "19. Responde siempre en español con calidez, rigor técnico y claridad."
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
