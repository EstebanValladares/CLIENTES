"""
Interfaz interactiva de consola para KHIARA (Rich Terminal).
Permite chatear con el agente, aprender proyectos en tiempo real e inspeccionar el grafo.
"""

import sys
import time
import logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live

# Silenciar logs internos técnicos de agno y librerías para una interfaz limpia
logging.getLogger("agno").setLevel(logging.CRITICAL)
logging.getLogger("google.genai").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
from khiara.core.config import tiene_api_key, GEMINI_API_KEY
from khiara.core.agente import crear_agente_khiara
from khiara.grafo.red import RedConocimiento
from khiara.grafo.indexador import IndexadorProyecto
from khiara.herramientas.explorador import (
    red_global,
    tool_consultar_reportes_rea,
    tool_escanear_pantalla_rea,
    tool_consultar_duckdb,
    tool_buscar_memoria_semantica,
    tool_listar_tablas_bd_relacional,
    tool_ejecutar_codigo_python,
    tool_registrar_regla_evolutiva,
    tool_consultar_reglas_evolutivas,
    tool_generar_repo_map,
    tool_consultar_alertas_centinela,
    tool_cargar_openapi,
    tool_buscar_endpoints_api,
    tool_consultar_glosario_negocio,
    tool_interpretar_consulta_negocio,
    memoria_evolutiva_global,
    cruce_repos_global,
    centinela_global
)

console = Console()


def iniciar_consola_interactiva():
    console.print(Panel.fit(
        "[bold cyan]KHIARA[/bold cyan] - [bold white]Agente Autónomo Multitareas & Red de Conocimiento[/bold white]\n"
        "[dim]Impulsado por Agno, NetworkX y Google Gemini[/dim]",
        border_style="cyan"
    ))

    metricas = red_global.metricas()
    console.print(f"[green]✔ Red de Conocimiento lista:[/green] {metricas['total_nodos']} nodos indexados, {metricas['total_relaciones']} relaciones.\n")

    if not tiene_api_key():
        console.print("[yellow]⚠ Aviso: GEMINI_API_KEY no detectada en .env o entorno.[/yellow]")
        console.print("[dim]Puedes colocar tu API Key en el archivo .env para razonamiento con LLM.[/dim]\n")

    try:
        agente = crear_agente_khiara()
    except Exception as e:
        console.print(f"[red]Error inicializando agente: {e}[/red]")
        return

    console.print("[bold yellow]Comandos disponibles:[/bold yellow]")
    console.print("  [cyan]/aprender <ruta>[/cyan]  -> Escanea e indexa un proyecto completo en el grafo")
    console.print("  [cyan]/api <url|ruta>[/cyan]    -> Conecta la API de FastAPI/OpenAPI del Dashboard")
    console.print("  [cyan]/ontologia [termino][/cyan]-> Consulta la 'Llave Maestra' (Glosario de Negocio Velas)")
    console.print("  [cyan]/cruzar[/cyan]           -> Detecta tablas y módulos cruzados entre repositorios")
    console.print("  [cyan]/repomap[/cyan]          -> Mapeo compacto de todos los proyectos (Estilo Aider)")
    console.print("  [cyan]/reglas [tema][/cyan]    -> Consulta o lista las reglas aprendidas (Estilo Mem0)")
    console.print("  [cyan]/centinela [on|off][/cyan]-> Activa o desactiva la auditoría proactiva en segundo plano")
    console.print("  [cyan]/duck <sql>[/cyan]       -> Ejecuta consulta analítica DuckDB sobre CSV/Parquet/JSON")
    console.print("  [cyan]/memoria <texto>[/cyan]  -> Búsqueda semántica en la memoria vectorial")
    console.print("  [cyan]/tablas[/cyan]           -> Lista tablas del servidor externo (SQL Server / MySQL)")
    console.print("  [cyan]/run <codigo>[/cyan]     -> Ejecuta código Python seguro en el sandbox")
    console.print("  [cyan]/rea [termino][/cyan]     -> Consulta los reportes y selectores del módulo REA")
    console.print("  [cyan]/escanear[/cyan]         -> Dispara escaneo en vivo de la pantalla abierta en Chrome (9222)")
    console.print("  [cyan]/salir[/cyan]            -> Cierra la sesión\n")

    # Saludo inicial proactivo de KHIARA
    saludo_khiara = (
        "¡Hola Esteban! Soy **KHIARA**, tu colega de ingeniería y análisis autónomo. 🧠✨\n\n"
        "Tengo cargada la Red de Conocimiento, el motor analítico DuckDB y la radiografía web de Aryve.\n"
        "¿En qué proyecto o análisis te gustaría que nos enfoquemos hoy?"
    )
    console.print(Panel(Markdown(saludo_khiara), title="[bold cyan]KHIARA[/bold cyan]", border_style="cyan"))
    console.print("")

    while True:
        try:
            entrada = Prompt.ask("[bold cyan]Tú[/bold cyan]").strip()
            if not entrada:
                continue

            if entrada.lower() in {"/salir", "exit", "quit"}:
                console.print("[cyan]Hasta luego. KHIARA desactivada.[/cyan]")
                break

            if entrada.startswith("/aprender"):
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    console.print("[red]Uso: /aprender C:/ruta/al/proyecto[/red]")
                    continue
                ruta_proy = partes[1].strip()
                console.print(f"[yellow]⏳ Escaneando y aprendiendo del proyecto en '{ruta_proy}'...[/yellow]")
                indexador = IndexadorProyecto(red_global)
                res = indexador.aprender_proyecto(ruta_proy)
                if res["ok"]:
                    console.print(f"[green]✔ Proyecto '{res['proyecto']}' aprendido con éxito![/green]")
                    console.print(f"  • Archivos indexados: {res['archivos_indexados']}")
                    console.print(f"  • Tablas de BD: {res['tablas_db_indexadas']}")
                    console.print(f"  • Total nodos en el grafo: {res['metricas_grafo']['total_nodos']}")
                else:
                    console.print(f"[red]Error: {res['error']}[/red]")
                continue

            if entrada.lower() == "/grafo":
                m = red_global.metricas()
                console.print(f"[bold cyan]Estado de la Red de Conocimiento:[/bold cyan]")
                console.print(f"  • Total Nodos: {m['total_nodos']}")
                console.print(f"  • Total Relaciones: {m['total_relaciones']}")
                console.print(f"  • Desglose: {m['nodos_por_tipo']}")
                continue

            if entrada.lower() == "/cruzar":
                console.print("[yellow]⏳ Analizando intersecciones y tablas compartidas entre repositorios...[/yellow]")
                res = cruce_repos_global.detectar_y_enlazar_intersecciones()
                console.print(Panel(
                    f"✔ Cruce completado:\n• Proyectos analizados: {res['total_proyectos']}\n• Nuevas intersecciones enlazadas: {res['intersecciones_creadas']}\n" +
                    ("\n".join(res.get("detalles", [])) if res.get("detalles") else "No se detectaron nuevas intersecciones pendientes."),
                    title="[bold cyan]Cruce Multi-Repositorio (GraphRAG)[/bold cyan]",
                    border_style="cyan"
                ))
                continue

            if entrada.lower() == "/repomap":
                mapa = tool_generar_repo_map()
                console.print(Panel(mapa, title="[bold cyan]Repo-Map Compacto (Estilo Aider)[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/reglas"):
                partes = entrada.split(maxsplit=1)
                tema = partes[1].strip() if len(partes) > 1 else ""
                res = tool_consultar_reglas_evolutivas(tema)
                console.print(Panel(res, title="[bold cyan]Reglas Evolutivas (Mem0)[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/centinela"):
                partes = entrada.split(maxsplit=1)
                opcion = partes[1].strip().lower() if len(partes) > 1 else "status"
                if opcion == "on":
                    # Registrar proyectos del grafo en el centinela
                    g = red_global.grafo
                    for n, a in g.nodes(data=True):
                        if a.get("tipo") == "PROYECTO" and a.get("ruta_absoluta"):
                            centinela_global.registrar_ruta(a["ruta_absoluta"])
                    centinela_global.iniciar()
                    console.print("[green]✔ Centinela proactivo activado en segundo plano.[/green]")
                elif opcion == "off":
                    centinela_global.detener()
                    console.print("[yellow]✔ Centinela proactivo detenido.[/yellow]")
                else:
                    est = centinela_global.estado()
                    console.print(Panel(
                        f"Estado del Centinela:\n• Activo: {est['activo']}\n• Intervalo de escaneo: {est['intervalo_segundos']}s\n• Proyectos vigilados: {est['total_rutas_vigiladas']}\n• Alertas totales: {est['total_alertas_registradas']}",
                        title="[bold cyan]Centinela Proactivo[/bold cyan]",
                        border_style="cyan"
                    ))
                continue

            if entrada.startswith("/api"):
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    eps = tool_buscar_endpoints_api()
                    console.print(Panel(eps, title="[bold cyan]Endpoints API Registrados[/bold cyan]", border_style="cyan"))
                    continue
                param = partes[1].strip()
                if param.startswith("http") or param.endswith(".json"):
                    console.print(f"[yellow]⏳ Conectando e ingiriendo OpenAPI desde '{param}'...[/yellow]")
                    res = tool_cargar_openapi(param)
                    console.print(Panel(res, title="[bold cyan]Conector OpenAPI[/bold cyan]", border_style="cyan"))
                else:
                    eps = tool_buscar_endpoints_api(param)
                    console.print(Panel(eps, title=f"[bold cyan]Endpoints para '{param}'[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/ontologia"):
                partes = entrada.split(maxsplit=1)
                term = partes[1].strip() if len(partes) > 1 else ""
                res = tool_consultar_glosario_negocio(term)
                console.print(Panel(res, title="[bold cyan]Llave Maestra: Ontología de Negocio[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/duck"):
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    console.print("[red]Uso: /duck SELECT * FROM 'archivo.csv' LIMIT 5[/red]")
                    continue
                sql = partes[1].strip()
                res = tool_consultar_duckdb(sql)
                console.print(Panel(res, title="[bold cyan]DuckDB Engine[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/memoria"):
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    console.print("[red]Uso: /memoria <texto o concepto a buscar>[/red]")
                    continue
                q = partes[1].strip()
                res = tool_buscar_memoria_semantica(q)
                console.print(Panel(res, title="[bold cyan]Memoria Vectorial Semántica[/bold cyan]", border_style="cyan"))
                continue

            if entrada.lower() == "/tablas":
                console.print("[yellow]⏳ Conectando e inspeccionando tablas en la base de datos externa...[/yellow]")
                res = tool_listar_tablas_bd_relacional()
                console.print(Panel(res, title="[bold cyan]Base de Datos Externa[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/run"):
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    console.print("[red]Uso: /run print('hola')[/red]")
                    continue
                codigo = partes[1].strip()
                res = tool_ejecutar_codigo_python(codigo)
                console.print(Panel(res, title="[bold cyan]Sandbox Python[/bold cyan]", border_style="cyan"))
                continue

            if entrada.startswith("/rea"):
                partes = entrada.split(maxsplit=1)
                termino = partes[1].strip() if len(partes) > 1 else ""
                res = tool_consultar_reportes_rea(termino)
                console.print(Panel(res, title="[bold cyan]Módulo REA (DOM X-Ray)[/bold cyan]", border_style="cyan"))
                continue

            if entrada.lower() == "/escanear":
                console.print("[yellow]⏳ Ejecutando escaneo en vivo de pantalla con REA (Chrome CDP 9222)...[/yellow]")
                res = tool_escanear_pantalla_rea()
                console.print(Panel(res, title="[bold cyan]Resultado Escaneo REA[/bold cyan]", border_style="cyan"))
                continue

            # Verificar si el centinela proactivo tiene alertas no leídas
            alertas_nuevas = centinela_global.obtener_alertas_recientes(solo_no_leidas=True)
            if alertas_nuevas:
                for alt in alertas_nuevas:
                    mods = f"modificados: {', '.join(alt.get('modificados', []))}" if alt.get("modificados") else ""
                    news = f"nuevos: {', '.join(alt.get('nuevos', []))}" if alt.get("nuevos") else ""
                    console.print(f"[bold yellow]🔔 Centinela Proactivo:[/bold yellow] Cambios en '{alt.get('proyecto')}': {news} {mods}")

            # Inyectar reglas evolutivas relevantes de forma automática
            bloque_reglas = memoria_evolutiva_global.formatear_bloque_contexto(entrada)
            prompt_final = entrada + (f"\n\n{bloque_reglas}" if bloque_reglas else "")

            # Consulta normal al agente con streaming directo en tiempo real
            for intento in range(1, 4):
                try:
                    console.print("\n[bold cyan]KHIARA:[/bold cyan] ", end="")
                    texto_acumulado = ""
                    for chunk in agente.run(prompt_final, stream=True):
                        c = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if c:
                            texto_acumulado += c
                            console.print(c, end="")

                    console.print("\n")

                    if "503" in texto_acumulado and "UNAVAILABLE" in texto_acumulado:
                        if intento < 3:
                            time.sleep(1.5 * intento)
                            continue
                        console.print("[yellow]⚠ Google AI experimentó un pico temporal de alta demanda. Por favor repite tu consulta.[/yellow]\n")
                    break

                except Exception as err:
                    if ("503" in str(err) or "UNAVAILABLE" in str(err)) and intento < 3:
                        time.sleep(1.5 * intento)
                        continue
                    console.print(f"\n[red]Aviso técnico: {err}[/red]\n")
                    break

        except KeyboardInterrupt:
            console.print("\n[cyan]Sesión interrumpida.[/cyan]")
            break
        except Exception as e:
            console.print(f"[red]Error durante la consulta: {e}[/red]")
