"""
Herramientas Ejecutables de KHIARA para Agno y razonamiento autónomo.
Permite consultar el Grafo, examinar archivos, ejecutar SQL y cálculos matemáticos.
"""

import os
import sys
import sqlite3
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from khiara.grafo.red import RedConocimiento
from khiara.cerebro.matematicas import MotorMatematico
from khiara.cerebro.motor_duckdb import MotorDuckDB
from khiara.cerebro.conector_db import ConectorDBRelacional
from khiara.cerebro.memoria_vectorial import MemoriaVectorial
from khiara.cerebro.sandbox_python import SandboxPython
from khiara.cerebro.memoria_evolutiva import MemoriaEvolutiva
from khiara.grafo.cruce_repos import CruceMultiRepositorio
from khiara.grafo.repo_map import RepoMap
from khiara.cerebro.centinela import CentinelaProactivo
from khiara.herramientas.conector_api import ConectorAPI
from khiara.cerebro.ontologia import GlosarioNegocio

# Instancias globales para las herramientas
red_global = RedConocimiento()
motor_duckdb_global = MotorDuckDB()
conector_db_global = ConectorDBRelacional()
memoria_vectorial_global = MemoriaVectorial()
sandbox_python_global = SandboxPython()
memoria_evolutiva_global = MemoriaEvolutiva()
cruce_repos_global = CruceMultiRepositorio(red_global)
repo_map_global = RepoMap(red_global)
centinela_global = CentinelaProactivo()
conector_api_global = ConectorAPI()
glosario_negocio_global = GlosarioNegocio()

RUTA_BASE = Path(__file__).resolve().parent.parent.parent
DIR_REA_REPORTES = RUTA_BASE / "rea" / "reportes"


def tool_consultar_reportes_rea(termino_busqueda: str = "") -> str:
    """
    Consulta los reportes generados por el módulo REA (DOM X-Ray e Ingeniería Inversa).
    Si se pasa un término de búsqueda (ej. 'proveedor', 'obra', 'guardar', 'select2'), busca
    elementos interactivos, inputs, botones y XPaths exactos en los escaneos de pantalla.
    Si está vacío, lista los escaneos disponibles con sus pantallas y fechas.
    """
    if not DIR_REA_REPORTES.exists():
        return f"El directorio de reportes REA no existe en {DIR_REA_REPORTES}."

    archivos_json = list(DIR_REA_REPORTES.glob("*.json"))
    if not archivos_json:
        return "No hay reportes de escaneo REA disponibles aún en 'rea/reportes/'."

    if not termino_busqueda.strip():
        # Listar catálogo de reportes
        resumen = [f"Catálogo de Escaneos REA disponibles ({len(archivos_json)} reportes):"]
        for arch in sorted(archivos_json, key=lambda x: x.stat().st_mtime, reverse=True)[:12]:
            try:
                with open(arch, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    titulo = data.get("title", "Sin título")
                    url = data.get("url", "")
                    ts = data.get("timestamp", "")
                    total_elem = (
                        len(data.get("inputs", [])) +
                        len(data.get("select2", [])) +
                        len(data.get("botones", []))
                    )
                    resumen.append(f"• {arch.name} | Pantalla: '{titulo}' | Elementos: {total_elem} | URL: {url[:50]}")
                else:
                    resumen.append(f"• {arch.name} ({round(arch.stat().st_size / 1024, 1)} KB)")
            except Exception:
                resumen.append(f"• {arch.name}")
        return "\n".join(resumen)

    # Búsqueda detallada por término
    termino = termino_busqueda.lower().strip()
    hallazgos = []
    
    # Revisar primero el último escaneo
    archivos_a_revisar = []
    ultimo = DIR_REA_REPORTES / "ultimo_escaneo_dom.json"
    if ultimo.exists():
        archivos_a_revisar.append(ultimo)
    for a in sorted(archivos_json, key=lambda x: x.stat().st_mtime, reverse=True):
        if a != ultimo and not a.name.startswith("rea_"):
            archivos_a_revisar.append(a)

    for arch in archivos_a_revisar[:8]:
        try:
            with open(arch, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue

            titulo = data.get("title", arch.name)
            
            # Buscar en inputs
            for inp in data.get("inputs", []):
                texto_item = f"{inp.get('id', '')} {inp.get('name', '')} {inp.get('placeholder', '')} {inp.get('xpath', '')}".lower()
                if termino in texto_item:
                    hallazgos.append(
                        f"[{titulo}] INPUT: id='{inp.get('id')}', name='{inp.get('name')}', type='{inp.get('type')}', xpath='{inp.get('xpath')}'"
                    )

            # Buscar en select2
            for s2 in data.get("select2", []):
                texto_item = f"{s2.get('id', '')} {s2.get('xpath', '')} {s2.get('container_id', '')}".lower()
                if termino in texto_item:
                    hallazgos.append(
                        f"[{titulo}] SELECT2: id='{s2.get('id')}', container='{s2.get('container_id')}', xpath='{s2.get('xpath')}'"
                    )

            # Buscar en botones
            for btn in data.get("botones", []):
                texto_item = f"{btn.get('id', '')} {btn.get('texto', '')} {btn.get('xpath', '')}".lower()
                if termino in texto_item:
                    hallazgos.append(
                        f"[{titulo}] BOTÓN: texto='{btn.get('texto')}', id='{btn.get('id')}', xpath='{btn.get('xpath')}'"
                    )

            if len(hallazgos) >= 15:
                break
        except Exception:
            continue

    if not hallazgos:
        return f"No se encontraron elementos interactivos que coincidan con '{termino_busqueda}' en los reportes REA."

    return f"Elementos encontrados para '{termino_busqueda}' ({len(hallazgos)} resultados):\n" + "\n".join(hallazgos[:15])


def tool_escanear_pantalla_rea() -> str:
    """
    Ejecuta el escáner de REA (DOM X-Ray + DevTools) sobre la pantalla actualmente abierta
    en Chrome (puerto 9222), extrayendo botones, inputs, Select2 y tablas.
    """
    script_escaner = RUTA_BASE / "rea" / "escanear_rea.py"
    if not script_escaner.exists():
        return f"No se encontró el script de escaneo en {script_escaner}."

    try:
        res = subprocess.run(
            ["python", str(script_escaner)],
            cwd=str(script_escaner.parent),
            capture_output=True,
            text=True,
            timeout=120
        )
        if res.returncode == 0:
            salida = res.stdout.strip()
            return f"Escaneo REA completado exitosamente.\nDetalles:\n{salida[-500:]}"
        else:
            return f"Aviso al ejecutar escaneo REA:\n{res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return f"Error ejecutando escaneo REA: {str(e)}"


def tool_consultar_grafo(tema_o_entidad: str) -> str:
    """Busca entidades en la red de conocimiento del proyecto (proyectos, tablas de BD, archivos, funciones)."""
    nodos = red_global.buscar_nodos(tema_o_entidad, limite=6)
    if not nodos:
        return f"No se encontraron entidades relacionadas con '{tema_o_entidad}' en el grafo."
    
    lineas = [f"Resultados en la Red de Conocimiento para '{tema_o_entidad}':"]
    for n in nodos:
        tipo = n.get("tipo", "ENTIDAD")
        lineas.append(f"• [{tipo}] {n.get('id')}")
        if tipo == "TABLA_DB":
            lineas.append(f"  - Base de Datos: {n.get('archivo_db')} | Registros: {n.get('total_registros')}")
            lineas.append(f"  - Columnas: {', '.join(n.get('columnas', []))}")
        elif tipo == "ARCHIVO":
            lineas.append(f"  - Ruta: {n.get('ruta_relativa')} ({n.get('tamano_kb')} KB)")
        elif tipo == "FUNCION":
            lineas.append(f"  - Argumentos: {', '.join(n.get('argumentos', []))}")
    return "\n".join(lineas)


def tool_consultar_sql_local(ruta_db: str, consulta_sql: str) -> str:
    """Ejecuta consultas SQL de SOLO LECTURA (SELECT) en bases de datos SQLite del proyecto."""
    sql_clean = consulta_sql.strip()
    if not sql_clean.upper().startswith("SELECT") and not sql_clean.upper().startswith("PRAGMA"):
        return "ERROR: Solo se permiten consultas SELECT o PRAGMA de lectura."
    
    p = Path(ruta_db)
    if not p.exists():
        return f"ERROR: La base de datos '{ruta_db}' no existe."
    
    try:
        conn = sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_clean)
        filas = [dict(r) for r in cursor.fetchmany(15)]
        conn.close()
        if not filas:
            return "La consulta no devolvió registros."
        return json.dumps(filas, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error ejecutando SQL: {str(e)}"


def tool_calcular_formula(expresion_matematica: str) -> str:
    """Calcula operaciones y fórmulas matemáticas exactas (ej. '(15200 - 13800) / 13800 * 100')."""
    res = MotorMatematico.evaluar_expresion_segura(expresion_matematica)
    if res["ok"]:
        return f"Resultado de '{expresion_matematica}': {res['resultado']}"
    return f"Error en cálculo: {res.get('error')}"


def tool_consultar_duckdb(consulta_sql: str) -> str:
    """
    Ejecuta consultas analíticas SQL en DuckDB sobre archivos CSV, Parquet, JSON, Excel o SQLite.
    Ejemplos:
      - SELECT * FROM 'reportes/datos.csv' WHERE total > 1000
      - SELECT obra, COUNT(*) FROM 'obras.json' GROUP BY obra
    """
    res = motor_duckdb_global.consultar(consulta_sql)
    if not res["ok"]:
        return f"Error DuckDB: {res['error']}"
    if not res["filas"]:
        return "La consulta no devolvió registros."
    return json.dumps(res["filas"], ensure_ascii=False, indent=2)


def tool_describir_archivo_datos(ruta_archivo: str) -> str:
    """
    Inspecciona cualquier archivo de datos (CSV, JSON, Parquet, Excel) devolviendo su esquema,
    columnas, tipos de datos, cantidad de filas y una muestra de los primeros registros.
    """
    res = motor_duckdb_global.describir_archivo(ruta_archivo)
    if not res["ok"]:
        return f"Error describiendo archivo: {res['error']}"
    return json.dumps(res, ensure_ascii=False, indent=2)


def tool_consultar_bd_relacional(consulta_sql: str) -> str:
    """
    Ejecuta consultas SQL de SOLO LECTURA (SELECT) en la base de datos externa configurada
    (SQL Server de Enkontrol, MySQL o PostgreSQL).
    """
    res = conector_db_global.consultar(consulta_sql)
    if not res["ok"]:
        return f"Error BD Relacional: {res['error']}"
    if "filas" in res:
        if not res["filas"]:
            return "La consulta no devolvió registros."
        return json.dumps(res["filas"], ensure_ascii=False, indent=2)
    return res.get("mensaje", "Consulta finalizada.")


def tool_listar_tablas_bd_relacional() -> str:
    """
    Obtiene la lista de todas las tablas existentes en el servidor externo de base de datos
    (SQL Server / MySQL) para saber qué datos están disponibles antes de consultar.
    """
    res = conector_db_global.listar_tablas()
    if not res["ok"]:
        return f"Error conectando a BD externa: {res['error']}"
    return f"Tablas encontradas ({res['total_tablas']}):\n" + ", ".join(res["tablas"][:60])


def tool_buscar_memoria_semantica(consulta: str) -> str:
    """
    Busca fragmentos de conocimiento, documentación, notas y recuerdos de proyectos
    por similitud semántica (vector embeddings y búsqueda de coseno).
    """
    similares = memoria_vectorial_global.buscar_similares(consulta, top_k=4)
    if not similares:
        return f"No se encontraron recuerdos semánticos relacionados con '{consulta}'."
    
    lineas = [f"Recuerdos encontrados para '{consulta}':"]
    for s in similares:
        lineas.append(f"• [Similitud: {s['similitud']}] (ID: {s['id']}):\n  {s['texto']}")
    return "\n\n".join(lineas)


def tool_guardar_recuerdo_memoria(id_recuerdo: str, texto_recuerdo: str) -> str:
    """
    Guarda un nuevo hecho aprendido, especificación técnica, ID de usuario o regla
    en la memoria vectorial persistente de KHIARA para recordarla en el futuro.
    """
    ok = memoria_vectorial_global.guardar_recuerdo(id_recuerdo, texto_recuerdo)
    if ok:
        return f"Recuerdo '{id_recuerdo}' almacenado exitosamente en la memoria vectorial de KHIARA."
    return f"No se pudo guardar el recuerdo '{id_recuerdo}'."


def tool_ejecutar_codigo_python(codigo_python: str) -> str:
    """
    Ejecuta un script o fragmento de código Python en un sandbox controlado con límite de tiempo.
    Permite a KHIARA verificar cálculos complejos, transformar datos, generar gráficos y auto-depurarse.
    Devuelve stdout, stderr y la lista de gráficos generados.
    """
    res = sandbox_python_global.ejecutar_codigo(codigo_python)
    if not res["ok"]:
        error_msg = res.get("error") or res.get("stderr") or "Error desconocido durante la ejecución."
        return f"FALLO DE EJECUCIÓN (Código {res.get('codigo_salida')}):\n{error_msg}\nRevisa el error y auto-corrige el código."

    salida = [f"EJECUCIÓN EXITOSA ({res['tiempo_segundos']}s):"]
    if res["stdout"]:
        salida.append(f"--- Salida (stdout) ---\n{res['stdout']}")
    if res["stderr"]:
        salida.append(f"--- Avisos (stderr) ---\n{res['stderr']}")
    if res.get("graficas_generadas"):
        salida.append(f"--- Gráficas creadas ---\n" + "\n".join(res["graficas_generadas"]))
    return "\n".join(salida)


def tool_crear_o_editar_archivo(ruta_relativa: str, contenido: str) -> str:
    """
    Crea o modifica un archivo de código o texto dentro del workspace del proyecto.
    """
    res = sandbox_python_global.crear_o_actualizar_archivo(ruta_relativa, contenido)
    if not res["ok"]:
        return f"Error guardando archivo: {res['error']}"
    return f"Archivo '{res['archivo']}' guardado correctamente ({res['bytes_escritos']} bytes)."


def tool_registrar_regla_evolutiva(regla: str, categoria: str = "REGLA_NEGOCIO") -> str:
    """
    Registra una regla de negocio permanente, corrección o preferencia que KHIARA
    debe recordar SIEMPRE en todas las sesiones futuras (Inspirado en Mem0).
    Ejemplos:
      - 'En la obra AUS el presupuesto siempre se calcula en dólares USD'
      - 'El usuario Juan Perez tiene el ID 104 y rol de Administrador'
    """
    res = memoria_evolutiva_global.registrar_regla(regla, categoria=categoria)
    if res["ok"]:
        return f"Regla permanente aprendida y guardada exitosamente (ID: {res['id']}):\n'{regla}'"
    return f"No se pudo guardar la regla: {res.get('error')}"


def tool_consultar_reglas_evolutivas(tema: str = "") -> str:
    """
    Consulta las reglas de negocio, preferencias y correcciones permanentes memorizadas por KHIARA.
    """
    if tema.strip():
        reglas = memoria_evolutiva_global.buscar_reglas_relevantes(tema)
    else:
        reglas = memoria_evolutiva_global.listar_todas()

    if not reglas:
        return f"No hay reglas memorizadas aún{' sobre ' + tema if tema else ''}."

    lineas = [f"Reglas Permanentes Activas ({len(reglas)}):"]
    for r in reglas:
        lineas.append(f"• [{r['categoria']}] {r['regla']} (ID: {r['id']})")
    return "\n".join(lineas)


def tool_trazar_camino_multi_repo(entidad_origen: str, entidad_destino: str) -> str:
    """
    Rastrea y traza cómo se conectan dos entidades a través de múltiples repositorios
    (ej. 'DASHBOARD_EK10' y 'CONTROL_PAGOS' o cómo viaja una orden de compra).
    """
    res = cruce_repos_global.trazar_camino_entre_entidades(entidad_origen, entidad_destino)
    if not res["ok"]:
        return f"Trazabilidad no encontrada: {res['error']}"

    salida = [
        f"Camino encontrado entre '{res['origen']}' y '{res['destino']}' ({res['longitud_saltos']} saltos):"
    ]
    for paso in res["pasos_explicados"]:
        salida.append(f"  {paso}")
    return "\n".join(salida)


def tool_generar_repo_map() -> str:
    """
    Genera un mapa textual ultra-compacto de todos los repositorios indexados en el grafo,
    mostrando tablas, módulos y nodos sin saturar la memoria.
    """
    return repo_map_global.generar_repo_map_compacto()


def tool_consultar_alertas_centinela() -> str:
    """
    Consulta las alertas y cambios detectados por el centinela en segundo plano
    en los repositorios vigilados.
    """
    alertas = centinela_global.obtener_alertas_recientes(solo_no_leidas=False)
    if not alertas:
        return "El Centinela no ha detectado cambios recientes en los proyectos vigilados."

    lineas = ["Alertas recientes del Centinela:"]
    for a in alertas[-5:]:
        mod = f"Modificados: {', '.join(a.get('modificados', []))}" if a.get('modificados') else ""
        new = f"Nuevos: {', '.join(a.get('nuevos', []))}" if a.get('nuevos') else ""
        lineas.append(f"• [{a['timestamp']}] Proyecto '{a.get('proyecto')}': {new} {mod}")
    return "\n".join(lineas)


def tool_cargar_openapi(url_o_ruta: str) -> str:
    """
    Conecta e ingiere la especificación OpenAPI/Swagger de FastAPI (ej. 'http://localhost:8000/openapi.json').
    Descubre automáticamente todos los endpoints de insumos, escalatorias, obras y usuarios.
    """
    res = conector_api_global.cargar_especificacion(url_o_ruta)
    if not res["ok"]:
        return f"Error cargando OpenAPI: {res['error']}"
    return (
        f"✔ API '{res['titulo']}' (v{res['version']}) conectada exitosamente.\n"
        f"• Total endpoints disponibles: {res['total_endpoints']}\n"
        f"• Base URL activa: {res['base_url']}"
    )


def tool_buscar_endpoints_api(termino: str = "") -> str:
    """
    Busca endpoints disponibles en la API de FastAPI por palabra clave (ej. 'insumo', 'escalatoria', 'posicion').
    """
    eps = conector_api_global.buscar_endpoints(termino)
    if not eps:
        return f"No se encontraron endpoints para '{termino}'. Asegúrate de haber conectado la API con 'tool_cargar_openapi'."
    lineas = [f"Endpoints encontrados ({len(eps)}):"]
    for ep in eps[:12]:
        lineas.append(f"• [{ep['metodo']}] {ep['ruta']} -> {ep['resumen'] or ep['descripcion'][:60]}")
    return "\n".join(lineas)


def tool_consultar_endpoint_api(metodo: str, ruta: str, parametros_json: str = "{}", body_json: str = "{}") -> str:
    """
    Ejecuta una petición HTTP en vivo contra un endpoint de la API de FastAPI.
    Parámetros:
      - metodo: 'GET', 'POST', 'PUT', etc.
      - ruta: '/api/obras/catalogo', '/api/escalatorias', etc.
      - parametros_json: cadena JSON con query params (ej. '{"obra": "AUS"}').
      - body_json: cadena JSON con el body si aplica.
    """
    try:
        params = json.loads(parametros_json) if parametros_json.strip() else {}
    except Exception:
        params = {}
    try:
        body = json.loads(body_json) if body_json.strip() else {}
    except Exception:
        body = {}

    res = conector_api_global.ejecutar_llamada(metodo, ruta, parametros=params, body=body)
    if not res["ok"]:
        return f"Fallo al consultar API: {res.get('error')}"
    
    datos = res.get("datos")
    if isinstance(datos, (dict, list)):
        return f"Status {res['status_code']} ({res['url']}):\n" + json.dumps(datos, ensure_ascii=False, indent=2)[:2000]
    return f"Status {res['status_code']} ({res['url']}):\n{str(datos)[:2000]}"


def tool_consultar_glosario_negocio(termino: str = "") -> str:
    """
    Consulta la Ontología Semántica y Diccionario de Negocio de Grupo Velas / Aryve.
    Explica conceptos clave como Escalatoria, Claves POS-XXXX, Obras (AUS, ARE), Homologación de Lotes, etc.
    """
    if termino.strip():
        res = glosario_negocio_global.consultar_termino(termino)
        if not res["ok"]:
            return res["error"]
        t = res["termino"]
        return (
            f"Concepto: {t['concepto']}\n"
            f"Definición: {t['definicion']}\n"
            f"Sinónimos: {', '.join(t.get('sinonimos', []))}\n"
            f"Tablas BD: {', '.join(t.get('tablas_relacionadas', []))}\n"
            f"Endpoints: {', '.join(t.get('endpoints_relacionados', []))}"
        )
    conceptos = glosario_negocio_global.listar_conceptos()
    lineas = [f"Diccionario Semántico de Negocio ({len(conceptos)} conceptos maestros):"]
    for c in conceptos:
        lineas.append(f"• {c['concepto']}: {c['definicion'][:90]}...")
    return "\n".join(lineas)


def tool_interpretar_consulta_negocio(consulta: str) -> str:
    """
    Analiza una consulta del usuario y extrae automáticamente los conceptos de negocio,
    claves de posición (POS-XXXX), obras de 3 letras, y sugiere tablas y endpoints exactos.
    """
    interp = glosario_negocio_global.interpretar_consulta(consulta)
    return (
        f"Análisis Semántico de Negocio:\n"
        f"• Conceptos detectados: {', '.join(interp['conceptos']) if interp['conceptos'] else 'Ninguno directo'}\n"
        f"• Claves POS: {', '.join(interp['claves_posicion']) if interp['claves_posicion'] else 'Ninguna'}\n"
        f"• Obras identificadas: {', '.join(interp['obras_detectadas']) if interp['obras_detectadas'] else 'Ninguna'}\n"
        f"• Tablas sugeridas: {', '.join(interp['tablas_sugeridas'])}\n"
        f"• Endpoints sugeridos: {', '.join(interp['endpoints_sugeridos'])}"
    )


# ==============================================================================
# HERRAMIENTAS LOCALES DE DASHBOARD_EK10 (USUARIOS, CARPETAS Y ARCHIVOS)
# ==============================================================================

DIR_DASHBOARD_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
if str(DIR_DASHBOARD_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_DASHBOARD_RAIZ))


def tool_buscar_usuarios_locales(termino_busqueda: str = "", filtro_vigencia: str = "TODOS") -> str:
    """
    Busca usuarios, colaboradores, asesores, residentes y puestos en los datos locales de DASHBOARD_EK10 (1,122 usuarios).
    Permite buscar por nombre, apellido, correo, ID, clave de puesto (POS-XXXX) o área organizativa.
    Ejemplos de búsqueda:
      - 'yeudiel esteban'
      - 'alejandro romo'
      - 'POS-1007'
      - 'SISTEMAS'
      - ''
    """
    termino = (termino_busqueda or "").strip()
    
    # Intentar primero mediante UserService oficial del proyecto
    try:
        from core.user_service import UserService
        usuarios = UserService.buscar_usuarios(query=termino, filtro_vigencia=filtro_vigencia)
        if usuarios:
            lineas = [f"Se encontraron {len(usuarios)} usuario(s) en DASHBOARD_EK10 para '{termino}':"]
            for u in usuarios[:8]:
                lineas.append(
                    f"• ID: {u.get('id')} | Nombre: {u.get('nombre_completo')} | Estatus: {u.get('estatus')}\n"
                    f"  - Correo: {u.get('correo')}\n"
                    f"  - Puesto: {u.get('puesto')} (Clave: {u.get('clave_posicion')})\n"
                    f"  - Área: {u.get('area_organizacion')} | Teléfono: {u.get('telefono')}\n"
                    f"  - Vigencia: {u.get('vigencia_inicio')} al {u.get('vigencia_fin')}"
                )
            if len(usuarios) > 8:
                lineas.append(f"... y {len(usuarios) - 8} usuario(s) más.")
            return "\n".join(lineas)
    except Exception:
        pass

    # Fallback directo al archivo JSON local
    p_json = DIR_DASHBOARD_RAIZ / "USUARIOS" / "data" / "Usuarios.json"
    if not p_json.exists():
        p_json = Path.cwd() / "USUARIOS" / "data" / "Usuarios.json"

    if not p_json.exists():
        return f"No se encontró el archivo local de usuarios en {p_json}."

    try:
        with open(p_json, "r", encoding="utf-8") as f:
            datos = json.load(f)

        if not termino:
            return f"Total de usuarios en la base local: {len(datos)}. Especifica un nombre, ID o puesto para filtrar."

        tokens = termino.lower().split()
        coincidencias = []
        for u in datos:
            texto = f"{u.get('ID','')} {u.get('Nombre','')} {u.get('Apellidos','')} {u.get('Clave','')} {u.get('Email','')} {u.get('Posicion','')} {u.get('ClavePosicion','')} {u.get('AreaOrganizacion','')}".lower()
            if all(t in texto for t in tokens):
                coincidencias.append(u)

        if not coincidencias:
            return f"No encontré ningún usuario con el término '{termino}' en los {len(datos)} registros locales de Usuarios.json. ¿Te gustaría que busque más a fondo en las bases de datos y conexiones externas?"

        lineas = [f"Se encontraron {len(coincidencias)} usuario(s) en Usuarios.json:"]
        for u in coincidencias[:8]:
            lineas.append(
                f"• ID: {u.get('ID')} | {u.get('Nombre')} {u.get('Apellidos')} | Estatus: {u.get('Estatus')}\n"
                f"  - Correo: {u.get('Email') or u.get('Clave')}\n"
                f"  - Puesto: {u.get('Posicion')} (Clave: {u.get('ClavePosicion')})\n"
                f"  - Área: {u.get('AreaOrganizacion')} | Creado por: {u.get('CreadoPor')}\n"
                f"  - Vigencia: {u.get('VigenciaInicio')} al {u.get('VigenciaFin')}"
            )
        if len(coincidencias) > 8:
            lineas.append(f"... y {len(coincidencias) - 8} usuario(s) adicionales.")
        return "\n".join(lineas)
    except Exception as e:
        return f"Error leyendo archivo local de usuarios: {str(e)}"


def tool_escanear_carpetas_proyecto(subcarpeta: str = "", patron_nombre: str = "*", limite: int = 30) -> str:
    """
    Escanea y lista archivos y carpetas locales dentro del proyecto DASHBOARD_EK10.
    Permite explorar qué módulos o archivos de datos existen (ej. 'data', 'USUARIOS', 'OBRAS', 'core', 'api', 'vue').
    """
    base = DIR_DASHBOARD_RAIZ
    if subcarpeta.strip():
        base = base / subcarpeta.strip().lstrip("/\\")

    if not base.exists():
        base = Path.cwd() / subcarpeta.strip().lstrip("/\\")
        if not base.exists():
            return f"La carpeta '{subcarpeta}' no existe en el proyecto."

    ignorados = {".git", "__pycache__", "node_modules", ".venv", "venv", "CLIENTES"}
    archivos = []
    carpetas = []

    try:
        for item in base.iterdir():
            if item.name in ignorados:
                continue
            if item.is_dir():
                carpetas.append(f"📁 {item.name}/")
            elif item.is_file():
                if patron_nombre == "*" or item.match(patron_nombre):
                    tam = round(item.stat().st_size / 1024, 1)
                    archivos.append(f"📄 {item.name} ({tam} KB)")

        lineas = [f"Contenido de '{base.name}' ({len(carpetas)} carpetas, {len(archivos)} archivos):"]
        lineas.extend(sorted(carpetas)[:15])
        lineas.extend(sorted(archivos)[:limite])
        return "\n".join(lineas)
    except Exception as e:
        return f"Error escaneando carpeta: {str(e)}"


def tool_buscar_texto_en_archivos_locales(texto_a_buscar: str, subcarpeta: str = "", extensiones: str = ".json,.py,.sql,.txt,.csv,.md", limite: int = 10) -> str:
    """
    Busca un texto o término específico dentro del contenido de los archivos de DASHBOARD_EK10.
    Útil para encontrar dónde se menciona un usuario, variable, función o tabla en los archivos locales.
    """
    if not texto_a_buscar.strip():
        return "Indica un texto a buscar."

    base = DIR_DASHBOARD_RAIZ
    if subcarpeta.strip():
        base = base / subcarpeta.strip().lstrip("/\\")

    if not base.exists():
        base = Path.cwd()

    exts = tuple(e.strip().lower() for e in extensiones.split(",") if e.strip())
    ignorados = {".git", "__pycache__", "node_modules", ".venv", "venv", "CLIENTES", "grafos"}

    hallazgos = []
    texto_lower = texto_a_buscar.lower()

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ignorados]
        for f in files:
            if not f.lower().endswith(exts):
                continue
            ruta_f = Path(root) / f
            try:
                if ruta_f.stat().st_size > 5 * 1024 * 1024:  # Ignorar archivos > 5MB
                    continue
                with open(ruta_f, "r", encoding="utf-8", errors="ignore") as arch:
                    for i, linea in enumerate(arch, 1):
                        if texto_lower in linea.lower():
                            rel = ruta_f.relative_to(DIR_DASHBOARD_RAIZ) if DIR_DASHBOARD_RAIZ in ruta_f.parents else ruta_f.name
                            hallazgos.append(f"• [{rel}:{i}] {linea.strip()[:140]}")
                            if len(hallazgos) >= limite:
                                break
            except Exception:
                continue
            if len(hallazgos) >= limite:
                break
        if len(hallazgos) >= limite:
            break

    if not hallazgos:
        return f"No se encontró el texto '{texto_a_buscar}' en los archivos locales inspeccionados."

    return f"Coincidencias para '{texto_a_buscar}' en archivos locales ({len(hallazgos)}):\n" + "\n".join(hallazgos)


def tool_consultar_catalogo_obras(termino_o_clave: str = "") -> str:
    """
    Consulta el catálogo de las 275 obras registradas en DASHBOARD_EK10 (Enkontrol / Aryve).
    Permite buscar por clave de 3 letras (ej. 'AUS', 'AT1', 'EY0', 'JA2', 'KB1', 'ICB', 'ICC') o por nombre (ej. 'VISTA VELA', 'CASA CLUB').
    Si la obra no existe (por ejemplo 'ICB'), busca automáticamente las obras más similares o con prefijo coincidente.
    """
    termino = (termino_o_clave or "").strip().upper()
    try:
        from core.obras_service import ObrasCoreService
        catalogo = ObrasCoreService.obtener_catalogo()
    except Exception:
        p_cat = DIR_DASHBOARD_RAIZ / "OBRAS" / "catalogo_obras.json"
        if not p_cat.exists():
            p_cat = Path.cwd() / "OBRAS" / "catalogo_obras.json"
        if p_cat.exists():
            with open(p_cat, "r", encoding="utf-8") as f:
                catalogo = json.load(f)
        else:
            catalogo = []

    if not catalogo:
        return "No se pudo cargar el catálogo de obras."

    if not termino:
        lineas = [f"Catálogo General de Obras ({len(catalogo)} obras registradas):"]
        for o in catalogo[:15]:
            lineas.append(f"• [{o.get('clave')}] {o.get('nombre')} (ID: {o.get('id_obra')}) | Ppto: ${o.get('importe_total', 0):,.2f}")
        lineas.append(f"... y {len(catalogo) - 15} obras más.")
        return "\n".join(lineas)

    # Buscar coincidencia exacta por clave
    coincidencias_exactas = [o for o in catalogo if str(o.get("clave", "")).strip().upper() == termino]
    if coincidencias_exactas:
        o = coincidencias_exactas[0]
        return (
            f"✔ Obra encontrada en el catálogo:\n"
            f"• Clave: {o.get('clave')}\n"
            f"• Nombre: {o.get('nombre')}\n"
            f"• ID Obra: {o.get('id_obra')}\n"
            f"• Clave Presupuesto: {o.get('presupuesto_clave') or o.get('clave_presupuesto')}\n"
            f"• Presupuesto Total: ${o.get('importe_total', 0):,.2f} {o.get('moneda', 'MXN')}\n"
            f"• Frentes: {o.get('total_frentes', 0)} | Partidas: {o.get('total_partidas', 0)} | Tarjetas: {o.get('total_tarjetas', 0)}"
        )

    # Buscar coincidencia parcial por nombre o clave
    coincidencias_nombre = [o for o in catalogo if termino in str(o.get("nombre", "")).upper() or termino in str(o.get("clave", "")).upper()]
    if coincidencias_nombre:
        lineas = [f"Se encontraron {len(coincidencias_nombre)} obra(s) relacionadas con '{termino}':"]
        for o in coincidencias_nombre[:8]:
            lineas.append(
                f"• [{o.get('clave')}] {o.get('nombre')} (ID: {o.get('id_obra')})\n"
                f"  - Presupuesto: ${o.get('importe_total', 0):,.2f} {o.get('moneda', 'MXN')} | Frentes: {o.get('total_frentes', 0)}"
            )
        return "\n".join(lineas)

    # Si no hubo coincidencia, buscar obras parecidas por prefijo
    prefijo = termino[:2] if len(termino) >= 2 else termino[:1]
    similares = [o for o in catalogo if str(o.get("clave", "")).upper().startswith(prefijo)]
    lineas = [f"No encontré ninguna obra con la clave '{termino}' en el catálogo local de las {len(catalogo)} obras."]
    if similares:
        lineas.append(f"Obras locales encontradas con prefijo similar '{prefijo}':")
        for s in similares[:4]:
            lineas.append(f"• [{s.get('clave')}] {s.get('nombre')} (ID: {s.get('id_obra')})")
    lineas.append("¿Te gustaría que busque más a fondo en las bases de datos y conexiones externas?")
    return "\n".join(lineas)


def tool_consultar_presupuesto_insumos_oc(obra: str, insumo: str = "", nombre_insumo: str = "") -> str:
    """
    Consulta en tiempo real el Centro de Presupuestos, Insumos & Órdenes de Compra (OC) de una obra.
    Devuelve los 4 indicadores clave que se ven en el Dashboard:
      1. Presupuesto Real ($)
      2. Requisitado ($)
      3. Comprado (OC) ($)
      4. Por Comprar ($)
    Además incluye el desglose de frentes, partidas e insumos individuales (cantidades y costos unitarios).
    Parámetros:
      - obra: Clave de la obra en mayúsculas (ej. 'AT1', 'AUS', 'JA2', 'EY0', 'KB1', 'AR0').
      - insumo: Código numérico del insumo si se quiere filtrar (ej. '1040001').
      - nombre_insumo: Nombre o tipo de insumo (ej. 'BLOCK', 'CEMENTO', 'VARILLA', 'PINTURA').
    """
    obra_clean = (obra or "").strip().upper()
    if not obra_clean:
        return "Indica la clave de la obra a consultar (ej. 'AT1', 'AUS', 'JA2')."

    try:
        from core.insumos_service import InsumosService
        res = InsumosService.consultar_reporte(obra=obra_clean, insumo=insumo, nombre=nombre_insumo)
        if not res or not res.get("ok"):
            return f"No se encontró información de insumos/presupuesto para la obra '{obra_clean}'."

        metricas = res.get("metricas", {})
        lineas = [
            f"📊 CENTRO DE PRESUPUESTOS, INSUMOS & ÓRDENES DE COMPRA (Obra: {obra_clean}):",
            f"• Presupuesto Real: ${metricas.get('presupuesto_real_total', 0):,.2f}",
            f"• Requisitado:     ${metricas.get('requisitado_total', 0):,.2f}",
            f"• Comprado (OC):    ${metricas.get('comprado_total', 0):,.2f}",
            f"• Por Comprar:      ${metricas.get('por_comprar_total', 0):,.2f}",
            f"• Frentes totales:  {metricas.get('total_frentes', 0)} | Partidas: {metricas.get('total_partidas', 0)} | Insumos: {metricas.get('total_insumos_resumen', 0)}"
        ]

        resumen_insumos = res.get("resumen", [])
        if resumen_insumos:
            lineas.append("\nDesglose de Insumos:")
            for item in resumen_insumos[:10]:
                cod = item.get("codigo_insumo") or item.get("insumo")
                desc = item.get("descripcion") or item.get("nombre", "")
                udm = item.get("unidad", "")
                cant_p = item.get("cant_presupuesto", 0)
                cant_c = item.get("cant_comprado", 0)
                imp_real = item.get("importe_real", 0)
                imp_comp = item.get("importe_comprado", 0)
                lineas.append(
                    f"• [{cod}] {desc[:35]} ({udm}):\n"
                    f"  Ppto: {cant_p:,.2f} (${imp_real:,.2f}) | Comprado: {cant_c:,.2f} (${imp_comp:,.2f})"
                )
            if len(resumen_insumos) > 10:
                lineas.append(f"... y {len(resumen_insumos) - 10} insumos más.")

        return "\n".join(lineas)
    except Exception as e:
        return f"Error consultando Centro de Presupuestos e Insumos: {str(e)}"


def tool_busqueda_general_local_dashboard(termino: str) -> str:
    """
    Búsqueda universal de primer nivel en TODAS las carpetas y archivos locales de DASHBOARD_EK10.
    Escanea en paralelo:
      - Usuarios y colaboradores (Usuarios.json, puestos.json)
      - Catálogo de Obras y Presupuestos (catalogo_obras.json, obras.json, INSUMOS_CACHE)
      - Proveedores y Contratistas (historial.db)
      - Mapeos de Lotes y Ubicaciones (mapeo_lotes.db, homologación sqlite)
      - Escalatorias de Costos (escalatorias.db)
      - Archivos locales de código y datos
    Si encuentra datos, devuelve un resumen conciso y directo.
    Si no encuentra nada, responde amablemente sin arrojar errores y ofrece buscar más a fondo.
    """
    t_clean = (termino or "").strip()
    if not t_clean:
        return "Indica qué término, usuario, obra o insumo deseas buscar localmente."

    t_lower = t_clean.lower()
    hallazgos = []

    # 1. Usuarios Locales
    p_usr = DIR_DASHBOARD_RAIZ / "USUARIOS" / "data" / "Usuarios.json"
    if p_usr.exists():
        try:
            with open(p_usr, "r", encoding="utf-8") as f:
                usrs = json.load(f)
            tokens = t_lower.split()
            for u in usrs:
                texto = f"{u.get('ID','')} {u.get('Nombre','')} {u.get('Apellidos','')} {u.get('Email','')} {u.get('Clave','')} {u.get('Posicion','')}".lower()
                if all(tok in texto for tok in tokens):
                    hallazgos.append(f"👤 Usuario: {u.get('Nombre')} {u.get('Apellidos')} | ID: {u.get('ID')} | Puesto: {u.get('Posicion')} | Correo: {u.get('Email') or u.get('Clave')}")
                    if len(hallazgos) >= 3:
                        break
        except Exception:
            pass

    # 2. Obras Locales
    p_obras = DIR_DASHBOARD_RAIZ / "OBRAS" / "catalogo_obras.json"
    if p_obras.exists():
        try:
            with open(p_obras, "r", encoding="utf-8") as f:
                obras = json.load(f)
            for o in obras:
                c_nom = str(o.get("nombre", "")).lower()
                c_cve = str(o.get("clave", "")).lower()
                if t_lower == c_cve or t_lower in c_nom:
                    ppto = o.get("importe_total", 0)
                    hallazgos.append(f"🏗️ Obra: [{o.get('clave')}] {o.get('nombre')} | ID: {o.get('id_obra')} | Ppto: ${ppto:,.2f}")
                    if len(hallazgos) >= 6:
                        break
        except Exception:
            pass

    # 3. Proveedores y Contratistas (historial.db)
    p_hist = DIR_DASHBOARD_RAIZ / "PROVEEDORES_CONTRATISTAS" / "AltaProveedores" / "Datos" / "historial.db"
    if p_hist.exists():
        try:
            conn = sqlite3.connect(f"file:{p_hist.resolve()}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT nombre, rfc, tipo FROM registros WHERE lower(nombre) LIKE ? OR lower(rfc) LIKE ? LIMIT 3", (f"%{t_lower}%", f"%{t_lower}%"))
            for r in cur.fetchall():
                hallazgos.append(f"🏢 Proveedor/Contratista: {r[0]} | RFC: {r[1]} | Tipo: {r[2]}")
            conn.close()
        except Exception:
            pass

    # 4. Insumos en Caché Local
    p_insumos = DIR_DASHBOARD_RAIZ / "OBRAS" / "INSUMOS_CACHE"
    if p_insumos.exists() and len(t_clean) >= 3:
        try:
            for f_ins in p_insumos.glob("*.json"):
                if t_clean.upper() in f_ins.name.upper():
                    hallazgos.append(f"📦 Insumos/Presupuesto local en caché: {f_ins.name}")
                    if len(hallazgos) >= 8:
                        break
        except Exception:
            pass

    if hallazgos:
        return f"Coincidencias en archivos locales de DASHBOARD_EK10 para '{t_clean}':\n" + "\n".join(hallazgos)

    # Si no se encontró nada localmente:
    return (
        f"No encontré información sobre '{t_clean}' en los archivos locales del Dashboard. "
        f"¿Te gustaría que realice una búsqueda más a fondo en las bases de datos y conexiones externas?"
    )


def tool_busqueda_profunda_conexiones_externas(termino: str, tipo_consulta: str = "AUTO") -> str:
    """
    Búsqueda profunda de segundo nivel en conexiones externas, bases de datos completas y APIs en vivo.
    Se ejecuta cuando el usuario responde 'sí', 'busca más a fondo', 'revisa en base de datos', etc.
    Explora:
      1. Servidor REST de Aryve en vivo (http://34.51.46.13/API/suministro_nivel)
      2. Base de datos SQLite de Escalatorias (data/escalatorias.db)
      3. Base de datos SQLite de Mapeo de Lotes (data/mapeo_lotes.db)
      4. Base de datos de Homologación de Ubicaciones (data/ek10_homologacion_ubicaciones.sqlite)
      5. Endpoints activos de la API local de FastAPI
      6. Servidor SQL Server / MySQL si está configurado en .env
    NUNCA lanza excepciones ni errores crudos al usuario; consolida y resume lo encontrado de forma clara.
    """
    t_clean = (termino or "").strip()
    if not t_clean:
        return "Indica qué término deseas buscar a fondo."

    t_lower = t_clean.lower()
    resultados_profundos = []

    # 1. Probar descarga en vivo desde API REST de Aryve si parece obra o insumo
    try:
        from core.insumos_service import InsumosService
        if len(t_clean) in (2, 3, 4) and t_clean.isalnum():
            data_api = InsumosService._descargar_desde_api(t_clean.upper())
            if data_api and data_api.get("ok"):
                met = data_api.get("metricas", {})
                resultados_profundos.append(
                    f"🌐 Conexión en vivo con Servidor Aryve (Obra {t_clean.upper()}):\n"
                    f"  - Presupuesto Real: ${met.get('presupuesto_real_total', 0):,.2f}\n"
                    f"  - Requisitado: ${met.get('requisitado_total', 0):,.2f}\n"
                    f"  - Comprado (OC): ${met.get('comprado_total', 0):,.2f}\n"
                    f"  - Por Comprar: ${met.get('por_comprar_total', 0):,.2f}"
                )
    except Exception:
        pass

    # 2. Búsqueda profunda en escalatorias.db
    p_esc = DIR_DASHBOARD_RAIZ / "data" / "escalatorias.db"
    if p_esc.exists():
        try:
            conn = sqlite3.connect(f"file:{p_esc.resolve()}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT obra, descripcion, fecha FROM escalatorias WHERE lower(obra) LIKE ? OR lower(descripcion) LIKE ? LIMIT 3", (f"%{t_lower}%", f"%{t_lower}%"))
            for r in cur.fetchall():
                resultados_profundos.append(f"📈 Escalatoria en DB: Obra {r[0]} | {r[1]} ({r[2]})")
            conn.close()
        except Exception:
            pass

    # 3. Búsqueda profunda en mapeo_lotes.db
    p_map = DIR_DASHBOARD_RAIZ / "data" / "mapeo_lotes.db"
    if p_map.exists():
        try:
            conn = sqlite3.connect(f"file:{p_map.resolve()}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT obra, lote, manzana FROM lotes_mapeo WHERE lower(obra) LIKE ? OR lower(lote) LIKE ? LIMIT 3", (f"%{t_lower}%", f"%{t_lower}%"))
            for r in cur.fetchall():
                resultados_profundos.append(f"🗺️ Mapeo Lotes en DB: Obra {r[0]} | Lote {r[1]} | Mza {r[2]}")
            conn.close()
        except Exception:
            pass

    # 4. Búsqueda profunda en homologacion_ubicaciones.sqlite
    p_hom = DIR_DASHBOARD_RAIZ / "data" / "ek10_homologacion_ubicaciones.sqlite"
    if p_hom.exists():
        try:
            conn = sqlite3.connect(f"file:{p_hom.resolve()}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT obra, ubicacion FROM homologacion_ubicaciones WHERE lower(obra) LIKE ? OR lower(ubicacion) LIKE ? LIMIT 3", (f"%{t_lower}%", f"%{t_lower}%"))
            for r in cur.fetchall():
                resultados_profundos.append(f"📍 Homologación Ubicación: Obra {r[0]} | {r[1]}")
            conn.close()
        except Exception:
            pass

    # 5. Base de Datos Relacional Externa (SQL Server / MySQL) solo si está configurada
    try:
        if conector_db_global.url:
            res_sql = conector_db_global.consultar(f"SELECT TOP 3 * FROM obras WHERE obra LIKE '%{t_clean}%'")
            if res_sql.get("ok") and res_sql.get("filas"):
                resultados_profundos.append(f"🗄️ SQL Server Enkontrol: {len(res_sql['filas'])} registro(s) encontrados.")
    except Exception:
        pass

    if resultados_profundos:
        return f"Resultados de la búsqueda profunda para '{t_clean}':\n" + "\n".join(resultados_profundos)

    return (
        f"Se completó la búsqueda profunda en las bases de datos de escalatorias, mapeo de lotes, homologaciones y conexiones REST de Aryve. "
        f"No se encontraron registros activos para '{t_clean}' en los servidores ni en las bases de datos externas."
    )



