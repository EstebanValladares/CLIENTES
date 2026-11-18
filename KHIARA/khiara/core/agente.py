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
        "1. USUARIOS Y COLABORADORES LOCALES: Si te preguntan si existe un usuario, por su puesto, correo, vigencia o ID en el sistema, USA INMEDIATAMENTE 'tool_buscar_usuarios_locales'. El proyecto cuenta con 1,122 usuarios locales en USUARIOS/data/Usuarios.json. NUNCA respondas que un usuario no existe sin haberlo buscado primero con esa herramienta, y NUNCA intentes consultar SQL Server externo para usuarios locales.",
        "2. EXPLORACIÓN DE CARPETAS Y ARCHIVOS: Para ver qué archivos y carpetas componen DASHBOARD_EK10, usa 'tool_escanear_carpetas_proyecto'. Para buscar cadenas de texto dentro del código o archivos locales, usa 'tool_buscar_texto_en_archivos_locales'.",
        "3. Estructura y código de proyectos -> 'tool_consultar_grafo'.",
        "4. Conceptos, notas y preferencias personales aprendidas en la sesión -> 'tool_buscar_memoria_semantica'.",
        "5. Archivos de datos analíticos (CSV, Excel, Parquet, JSON) -> 'tool_describir_archivo_datos' y 'tool_consultar_duckdb'.",
        "6. Bases de datos SQLite locales (.db, .sqlite como mapeo_lotes.db, escalatorias.db) -> 'tool_consultar_sql_local'.",
        "7. Matemáticas y variaciones numéricas -> 'tool_calcular_formula'.",
        "8. Pantallas web, Select2, botones y XPaths de Aryve -> 'tool_consultar_reportes_rea'.",
        "9. Escaneo en vivo de pantalla en Chrome (9222) -> 'tool_escanear_pantalla_rea'.",
        "10. Pruebas de código, transformaciones complejas o gráficos -> 'tool_ejecutar_codigo_python'.",
        "11. Guardar hechos nuevos o preferencias del usuario -> 'tool_guardar_recuerdo_memoria'.",
        "12. Si el usuario te indica una regla permanente, memorízala con 'tool_registrar_regla_evolutiva'.",
        "13. Si te preguntan por reglas memorizadas -> 'tool_consultar_reglas_evolutivas'.",
        "14. Trazabilidad entre repositorios -> 'tool_trazar_camino_multi_repo'.",
        "15. Resumen compacto de repositorios (Repo-Map) -> 'tool_generar_repo_map'.",
        "16. Alertas de cambios detectados por el centinela -> 'tool_consultar_alertas_centinela'.",
        "17. Para entender términos y jerga de la empresa (escalatorias, claves POS-XXXX, homologación de lotes, aditivas) -> 'tool_interpretar_consulta_negocio' o 'tool_consultar_glosario_negocio'.",
        "18. Si necesitas consumir datos de la API de FastAPI del Dashboard -> busca endpoints con 'tool_buscar_endpoints_api' y llama en vivo con 'tool_consultar_endpoint_api'.",
        "19. Consultas externas (SOLO cuando el usuario explícitamente pida consultar Enkontrol SQL Server externo) -> 'tool_listar_tablas_bd_relacional' y 'tool_consultar_bd_relacional'.",
        "20. Conexión Gmail del usuario -> 'tool_guardar_credenciales_gmail', 'tool_consultar_correos_recientes', 'tool_leer_correo_completo' y 'tool_descargar_adjunto_correo'.",
        "21. Crear o actualizar scripts en el proyecto -> 'tool_crear_o_editar_archivo'.",
        "22. Responde siempre en español con calidez, rigor técnico y claridad."
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
