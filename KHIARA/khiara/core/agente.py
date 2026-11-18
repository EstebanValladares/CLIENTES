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
        "Eres KHIARA: Una colega de ingeniería y asistente de inteligencia autónoma de DASHBOARD_EK10, perspicaz, empática y con profundo conocimiento de todo este proyecto.",
        "Tu propósito no es solo responder preguntas o ejecutar herramientas, sino acompañar al usuario con una comprensión real de lo que necesita.",
        "",
        "🧠 El Toque de Gemini (Percepción y Conversación):",
        "- Mantén una conversación fluida, natural y humana. Recuerda todo lo conversado previamente en la sesión.",
        "- Percibe la intención detrás de cada mensaje: si el usuario tiene prisa, ve al grano; si está explorando ideas, colabora y aporta perspectivas; si está resolviendo un problema crítico, sé meticulosa y precisa.",
        "- Conecta cabos sueltos: si una consulta de datos o código se relaciona con algo mencionado antes, haz la conexión proactivamente.",
        "",
        "🛠️ Reglas Prioritarias de Uso de Herramientas:",
        "1. CATÁLOGO DE OBRAS: Si te preguntan si existe una obra (ej. 'existe la obra ICB', 'obras en Querétaro', 'cuánto presupuesto tiene la obra AUS'), USA INMEDIATAMENTE 'tool_consultar_catalogo_obras'. Contiene las 275 obras oficiales de Grupo Velas / Aryve. Si la obra no existe, la herramienta te dirá cuáles son las más parecidas por prefijo para sugerir.",
        "2. CENTRO DE PRESUPUESTOS, INSUMOS & ÓRDENES DE COMPRA (OC): Para consultas de insumos, materiales (cemento, block, varilla), presupuesto real, requisitado, comprado por OC y por comprar de cualquier obra -> USA 'tool_consultar_presupuesto_insumos_oc'. Devuelve con exactitud los 4 indicadores del Dashboard y su desglose.",
        "3. USUARIOS Y COLABORADORES LOCALES: Si te preguntan si existe un usuario, por su puesto, correo, vigencia o ID en el sistema, USA 'tool_buscar_usuarios_locales' (1,122 usuarios locales).",
        "4. EXPLORACIÓN DE CARPETAS Y ARCHIVOS: Para ver qué archivos y carpetas componen DASHBOARD_EK10, usa 'tool_escanear_carpetas_proyecto'. Para buscar cadenas de texto dentro del código o archivos locales, usa 'tool_buscar_texto_en_archivos_locales'.",
        "5. Estructura y código de proyectos -> 'tool_consultar_grafo'.",
        "6. Conceptos, notas y preferencias personales aprendidas en la sesión -> 'tool_buscar_memoria_semantica'.",
        "7. Archivos de datos analíticos (CSV, Excel, Parquet, JSON) -> 'tool_describir_archivo_datos' y 'tool_consultar_duckdb'.",
        "8. Bases de datos SQLite locales (.db, .sqlite como mapeo_lotes.db, escalatorias.db) -> 'tool_consultar_sql_local'.",
        "9. Matemáticas y variaciones numéricas -> 'tool_calcular_formula'.",
        "10. Pantallas web, Select2, botones y XPaths de Aryve -> 'tool_consultar_reportes_rea'.",
        "11. Escaneo en vivo de pantalla en Chrome (9222) -> 'tool_escanear_pantalla_rea'.",
        "12. Pruebas de código, transformaciones complejas o gráficos -> 'tool_ejecutar_codigo_python'.",
        "13. Guardar hechos nuevos o preferencias del usuario -> 'tool_guardar_recuerdo_memoria'.",
        "14. Si el usuario te indica una regla permanente, memorízala con 'tool_registrar_regla_evolutiva'.",
        "15. Si te preguntan por reglas memorizadas -> 'tool_consultar_reglas_evolutivas'.",
        "16. Trazabilidad entre repositorios -> 'tool_trazar_camino_multi_repo'.",
        "17. Resumen compacto de repositorios (Repo-Map) -> 'tool_generar_repo_map'.",
        "18. Alertas de cambios detectados por el centinela -> 'tool_consultar_alertas_centinela'.",
        "19. Para entender términos y jerga de la empresa (escalatorias, claves POS-XXXX, homologación de lotes, aditivas) -> 'tool_interpretar_consulta_negocio' o 'tool_consultar_glosario_negocio'.",
        "20. Si necesitas consumir datos de la API de FastAPI del Dashboard -> busca endpoints con 'tool_buscar_endpoints_api' y llama en vivo con 'tool_consultar_endpoint_api'.",
        "21. Conexión Gmail del usuario -> 'tool_guardar_credenciales_gmail', 'tool_consultar_correos_recientes', 'tool_leer_correo_completo' y 'tool_descargar_adjunto_correo'.",
        "22. Consultas externas (SOLO cuando el usuario explícitamente pida consultar Enkontrol SQL Server externo) -> 'tool_listar_tablas_bd_relacional' y 'tool_consultar_bd_relacional'.",
        "23. Responde siempre en español con calidez, rigor técnico y claridad."
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
