"""
Motor de Razonamiento Cognitivo del Asistente (ReAct + Grafos + Gemini API).
Combina el Grafo de Conocimiento local con Google Gemini para diagnósticos y respuestas inteligentes.
"""

import os
import re
from typing import Dict, Any, List, Optional
from ASISTENTE.cerebro.config_cerebro import obtener_gemini_api_key, DEFAULT_MODEL
from ASISTENTE.cerebro.grafo_conocimiento import GrafoConocimiento
from ASISTENTE.cerebro.aprendizaje import ModuloAprendizaje
from ASISTENTE.cerebro.herramientas import (
    tool_metricas_totales,
    tool_buscar_usuario,
    tool_buscar_usuarios_por_area,
    tool_consultar_obra,
    tool_buscar_lotes,
    tool_consultar_escalatorias,
    tool_buscar_conocimiento,
    tool_explorar_carpetas,
    tool_consultar_insumos
)


class MotorRazonamiento:
    @classmethod
    def procesar_consulta(cls, pregunta: str, usuario: str = "Esteban") -> Dict[str, Any]:
        """
        Punto de entrada principal para responder consultas con razonamiento.
        Usa Gemini API si la clave está configurada; de lo contrario usa el motor inteligente local.
        """
        api_key = obtener_gemini_api_key()

        if api_key:
            return cls._razonar_con_gemini(pregunta, usuario, api_key)
        else:
            return cls._razonar_con_datos_locales(pregunta, usuario)

    @classmethod
    def _razonar_con_gemini(cls, pregunta: str, usuario: str, api_key: str) -> Dict[str, Any]:
        """Razona utilizando el modelo Google Gemini con contexto de negocio y herramientas."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            # Métricas generales del sistema
            m = tool_metricas_totales()

            # Extraer contexto previo relevante
            docs_relevantes = ModuloAprendizaje.buscar_en_conocimiento(pregunta, limite=3)
            resumen_docs = "\n".join([f"- {d['nombre_archivo']}: {d['resumen']}" for d in docs_relevantes])

            # Si pregunta por un usuario, buscar en Usuarios.json
            usuarios_rel = tool_buscar_usuario(pregunta, limite=3)
            resumen_usuarios = ""
            if usuarios_rel.get("ok") and usuarios_rel.get("usuarios"):
                resumen_usuarios = "\n".join([
                    f"- {u['nombre_completo']} | Puesto: {u['puesto']} | Área: {u['area']} | Email: {u['email']}"
                    for u in usuarios_rel["usuarios"]
                ])

            system_instruction = f"""
            Eres el Asistente Centinela del Dashboard EK10 de Grupo Velas.
            Estás platicando con {usuario}.
            
            Información global del sistema:
            - Usuarios totales: {m['usuarios_totales']} ({m['usuarios_activos']} activos)
            - Puestos: {m['puestos_totales']}
            - Obras (Centros de costo): {m['obras_totales']}
            - Lotes totales: {m['lotes_totales']} (Equivalencias EK10: {m['lotes_ek10_totales']})
            - Escalatorias autorizadas: {m['escalatorias_totales']}

            Usuarios coincidentes:
            {resumen_usuarios or "Ninguno específico para esta búsqueda."}

            Documentación aprendida:
            {resumen_docs or "Sin notas adicionales."}

            Instrucciones de Respuesta:
            1. Responde de forma natural, amigable, clara y profesional.
            2. NUNCA uses términos técnicos como "Grafo Local", "nodos", "aristas" o "tabla hash".
            3. Si preguntan por totales o conteos, da los números exactos con viñetas.
            4. Si preguntan por una persona, detalla su puesto, área y correo.
            5. Si preguntan por una obra, resume sus lotes y homologación.
            """

            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=pregunta,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )

            texto_respuesta = response.text or "No se pudo generar respuesta."

            return {
                "ok": True,
                "motor": "Gemini 2.5 Flash",
                "pregunta": pregunta,
                "respuesta": texto_respuesta
            }

        except Exception as e:
            # Fallback elegante a datos locales
            res_local = cls._razonar_con_datos_locales(pregunta, usuario)
            return res_local

    @classmethod
    def _razonar_con_datos_locales(cls, pregunta: str, usuario: str) -> Dict[str, Any]:
        """Motor inteligente local (100% offline) que consulta directamente las bases de datos del Dashboard."""
        p_upper = pregunta.upper()
        p_lower = pregunta.lower().strip()

        # =============================================================
        # 1. PREGUNTAS DE CONTEOS, TOTALES Y MÉTRICAS (¿CUÁNTOS HAY?)
        # =============================================================
        es_pregunta_conteo = any(w in p_lower for w in ["cuantos", "cuántos", "cuantas", "cuántas", "total de", "cantidad de", "numero de", "número de", "hay ahorita", "guardados"])
        
        # A) Conteo de Usuarios / Colaboradores / Personas
        if es_pregunta_conteo and any(w in p_lower for w in ["usuario", "colaborador", "persona", "empleado", "gente", "puesto"]):
            m = tool_metricas_totales()
            areas_str = ", ".join([f"{k} ({v})" for k, v in list(m["areas_principales"].items())[:4]])
            return {
                "ok": True,
                "motor": "Plantilla de Usuarios",
                "pregunta": pregunta,
                "respuesta": (
                    f"👥 **Actualmente tenemos {m['usuarios_totales']:,} usuarios guardados** en la plantilla de Grupo Velas:\n"
                    f"• **Colaboradores Activos:** {m['usuarios_activos']:,}\n"
                    f"• **Puestos y Posiciones Catalogadas:** {m['puestos_totales']:,}\n"
                    f"• **Principales Áreas:** {areas_str}\n\n"
                    f"💡 *Puedes preguntarme por alguien en específico (ej. '¿Quién es Claudia Padilla?' o 'Busca al líder de ventas').*"
                )
            }

        # B) Conteo de Obras / Centros de Costo
        if es_pregunta_conteo and any(w in p_lower for w in ["obra", "obras", "cc", "ccs", "centro de costo", "centros de costo", "fraccionamiento"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Mapeo de Obras",
                "pregunta": pregunta,
                "respuesta": (
                    f"🏗️ **Tenemos {m['obras_totales']:,} centros de costo (obras)** registrados en Enkontrol:\n"
                    f"• **Total de Lotes en Obras:** {m['lotes_totales']:,}\n"
                    f"• **Lotes con Equivalencia en Suite EK10:** {m['lotes_ek10_totales']:,}\n\n"
                    f"💡 *Si quieres analizar una obra en particular, solo dime su clave (ej. '¿Cómo va HFA?' o 'DQA').*"
                )
            }

        # C) Conteo de Lotes
        if es_pregunta_conteo and any(w in p_lower for w in ["lote", "lotes", "vivienda", "viviendas"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Mapeo de Lotes",
                "pregunta": pregunta,
                "respuesta": (
                    f"🏠 **Tenemos {m['lotes_totales']:,} lotes registrados** en el Mapeo Maestro de Enkontrol 9:\n"
                    f"• **Lotes vinculados a la Suite EK10:** {m['lotes_ek10_totales']:,}\n"
                    f"• **Distribuidos en:** {m['obras_totales']:,} centros de costo diferentes."
                )
            }

        # D) Conteo de Escalatorias
        if es_pregunta_conteo and any(w in p_lower for w in ["escalatoria", "escalatorias", "aditiva", "aditivas"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Escalatorias Enkontrol",
                "pregunta": pregunta,
                "respuesta": (
                    f"📈 **Tenemos {m['escalatorias_totales']} escalatorias y aditivas de precios** autorizadas en SOC Enkontrol.\n"
                    f"Ajustan costos de insumos clave como acero, block 12, armex y tinacos."
                )
            }

        # E) Preguntas de Resumen General ("¿Qué información tienes?", "¿Qué datos manejas?")
        if any(w in p_lower for w in ["que informacion tienes", "qué información tienes", "que datos tienes", "qué datos tienes", "resumen general", "que sabes hacer", "qué sabes"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Resumen General",
                "pregunta": pregunta,
                "respuesta": (
                    f"📊 **Información disponible en mi memoria para ti:**\n"
                    f"• **Plantilla de Usuarios:** {m['usuarios_totales']:,} colaboradores ({m['usuarios_activos']:,} activos) y {m['puestos_totales']:,} puestos.\n"
                    f"• **Mapeo de Obras:** {m['obras_totales']:,} centros de costo.\n"
                    f"• **Inventario de Lotes:** {m['lotes_totales']:,} lotes ({m['lotes_ek10_totales']:,} con clave EK10).\n"
                    f"• **Escalatorias de Precios:** {m['escalatorias_totales']} aditivas en SOC Enkontrol.\n\n"
                    f"Pregúntame sobre cualquier persona, obra, lote o material y te daré los datos."
                )
            }

        # =============================================================
        # F) Consultas sobre carpetas, estructura o archivos del sistema
        # =============================================================
        if any(w in p_lower for w in ["carpeta", "carpetas", "directorio", "directorios", "archivo", "archivos", "donde estan los datos", "dónde están los datos", "estructura del", "base de datos", "bases de datos"]):
            exp = tool_explorar_carpetas(p_lower)
            if exp.get("tema") != "GENERAL":
                det = exp.get("detalle", {})
                archivos_str = "\n".join([f"  • `{a}`" for a in det.get("archivos_clave", [])])
                return {
                    "ok": True,
                    "motor": "Explorador de Archivos y Carpetas",
                    "pregunta": pregunta,
                    "respuesta": (
                        f"📁 **Carpeta `{det.get('ruta')}` ({exp.get('tema')}):**\n"
                        f"_{det.get('descripcion')}_\n\n"
                        f"**Archivos principales:**\n{archivos_str}\n\n"
                        f"**Datos que contiene:** {det.get('datos_disponibles')}"
                    )
                }
            else:
                carpetas = exp.get("carpetas", {})
                lineas = ["🗂️ **Ecosistema de carpetas y datos conectados:**\n"]
                for k, v in carpetas.items():
                    lineas.append(f"• **`{v['ruta']}`** ({k}): {v['descripcion']}")
                lineas.append("\n💡 *Puedes pedirme detalles de cualquier carpeta (ej. '¿Qué hay en OBRAS?' o '¿Qué hay en data?').*")
                return {
                    "ok": True,
                    "motor": "Explorador de Archivos",
                    "pregunta": pregunta,
                    "respuesta": "\n".join(lineas)
                }

        # =============================================================
        # 2. BÚSQUEDA DE COLABORADORES POR ÁREA O DEPARTAMENTO
        # =============================================================
        areas_conocidas = ["sistemas", "ventas", "titulación", "titulacion", "postventa", "call center", "broker", "obra", "proyectos", "administracion", "administración"]
        for area_key in areas_conocidas:
            if area_key in p_lower and any(w in p_lower for w in ["quienes", "quiénes", "usuarios de", "personas de", "equipo de", "trabajan en", "en el area", "en el área"]):
                matches_area = tool_buscar_usuarios_por_area(area_key, limite=5)
                if matches_area:
                    lineas = [f"💼 **Colaboradores encontrados en {area_key.upper()}:**"]
                    for u in matches_area:
                        lineas.append(f"• **{u['nombre']}** - {u['puesto']}\n  Correo: `{u['email']}`")
                    return {
                        "ok": True,
                        "motor": "Directorio de Áreas",
                        "pregunta": pregunta,
                        "respuesta": "\n".join(lineas)
                    }

        # =============================================================
        # 3. BÚSQUEDA DE UN USUARIO / PERSONA ESPECÍFICA
        # =============================================================
        palabras_usuario = [
            "usuario", "colaborador", "compañero", "compañera", "quién es", "quien es",
            "sabes si", "conoces a", "persona", "correo", "email", "puesto", "trabaja",
            "contacto", "encargado", "líder", "lider"
        ]
        es_pregunta_persona = any(w in p_lower for w in palabras_usuario)

        res_usuarios = tool_buscar_usuario(pregunta, limite=3)
        if res_usuarios.get("ok") and res_usuarios.get("total", 0) > 0 and (es_pregunta_persona or len(res_usuarios["usuarios"]) <= 3):
            lista = res_usuarios["usuarios"]
            if len(lista) == 1:
                u = lista[0]
                texto = (
                    f"👤 **¡Sí! Encontré a {u['nombre_completo']}:**\n"
                    f"• **Puesto:** {u['puesto']}\n"
                    f"• **Área:** {u['area']}\n"
                    f"• **Correo:** `{u['email']}`\n"
                    f"• **Estatus:** {u['estatus']}"
                )
            else:
                texto = f"👥 **Encontré {res_usuarios['total']} colaboradores que coinciden:**\n\n"
                for u in lista:
                    texto += (
                        f"• **{u['nombre_completo']}**\n"
                        f"  Puesto: {u['puesto']} ({u['area']})\n"
                        f"  Correo: `{u['email']}`\n\n"
                    )
            return {
                "ok": True,
                "motor": "Plantilla de Usuarios",
                "pregunta": pregunta,
                "respuesta": texto.strip()
            }

        # =============================================================
        # 4. DETECCIÓN DE ESCALATORIAS E INSUMOS DE PRECIOS
        # =============================================================
        # Búsqueda de materiales / insumos específicos
        palabras_insumo = ["insumo", "insumos", "material", "materiales", "block", "acero", "cemento", "tinaco", "alambre", "mortero", "varilla", "armex"]
        if any(w in p_lower for w in palabras_insumo) and not es_pregunta_conteo:
            terminos_clave = [w for w in re.findall(r"\w+", p_lower) if w in ["block", "acero", "cemento", "tinaco", "alambre", "mortero", "varilla", "armex", "concreto", "tuberia", "cable", "pintura", "impermeabilizante"]]
            term_search = terminos_clave[0] if terminos_clave else "material"
            res_insumos = tool_consultar_insumos(term_search, limite=4)
            if res_insumos.get("ok") and res_insumos.get("total", 0) > 0:
                lineas = [f"🧱 **Resultados para '{term_search.upper()}':**"]
                for item in res_insumos["resultados"]:
                    lineas.append(f"• **{item['tipo']}**: {item['insumo']}\n  _{item['fuente']}_")
                return {
                    "ok": True,
                    "motor": "Catálogo de Insumos y Escalatorias",
                    "pregunta": pregunta,
                    "respuesta": "\n".join(lineas)
                }

        if any(w in p_upper for w in ["ESCALATORIA", "ESCALATORIAS", "PRECIO", "PRECIOS", "INSUMO", "ADITIVA", "ADITIVAS"]):
            datos_esc = tool_consultar_escalatorias()
            if datos_esc.get("ok") and datos_esc.get("escalatorias_recientes"):
                lista = datos_esc["escalatorias_recientes"]
                lineas = [f"📈 **Últimas escalatorias autorizadas en SOC Enkontrol:**"]
                for esc in lista[:4]:
                    lineas.append(f"• **{esc['clave']}**: {esc['nombre']} ({esc['numero_insumos']} insumos) [{esc['estatus_desc']}]")
                lineas.append("\n💡 *Puedes revisarlas a detalle abriendo la consulta de Escalatorias en la barra flotante.*")
                return {
                    "ok": True,
                    "motor": "Escalatorias Enkontrol",
                    "pregunta": pregunta,
                    "respuesta": "\n".join(lineas)
                }

        # =============================================================
        # 5. DETECCIÓN DE OBRAS ESPECÍFICAS (ej. HFA, DQA, DQC, C38, C39)
        # =============================================================
        coincidencias_obra = re.findall(r"\b([A-Z0-9]{3,4})\b", p_upper)
        palabras_ignorar = {"PARA", "LOTE", "OBRA", "TODO", "ESTA", "BIEN", "HOLA", "HACE", "CUAL", "CUAN", "DONDE", "COMO", "TIENE", "HAY"}
        for palabra in coincidencias_obra:
            if palabra in palabras_ignorar:
                continue
            diag = tool_consultar_obra(palabra)
            if diag.get("ok"):
                if diag.get("es_catalogo_obras"):
                    return {
                        "ok": True,
                        "motor": "Catálogo de Obras y Presupuestos",
                        "pregunta": pregunta,
                        "respuesta": (
                            f"🏗️ **Obra: {diag.get('nombre')} (Clave {diag.get('obra')}):**\n"
                            f"• **Presupuesto Clave:** `{diag.get('presupuesto_clave')}`\n"
                            f"• **Importe Presupuestado:** ${diag.get('importe_total', 0):,.2f} {diag.get('moneda')}\n"
                            f"• **Partidas Presupuestadas:** {diag.get('total_partidas')}\n"
                            f"• **Frentes de Trabajo:** {diag.get('total_frentes')}\n"
                            f"• **Tarjetas de Análisis:** {diag.get('total_tarjetas')}"
                        )
                    }

                total_lt = diag.get("total_lotes_obra") or diag.get("total_lotes_registrados", 0)
                lotes_hom = diag.get("lotes_con_suite_ek10") or diag.get("lotes_homologados_ek10", 0)
                lotes_pend = diag.get("lotes_pendientes_homologar") or diag.get("lotes_pendientes", 0)
                salud = diag.get("salud_homologacion", "0%")
                coinciden = diag.get("lotes_con_id_enk_coincidente", 0)

                respuesta = (
                    f"🏗️ **Estado de la Obra {palabra}:**\n"
                    f"• **Total Lotes:** {total_lt}\n"
                    f"• **Con Suite EK10 vinculada:** {lotes_hom}\n"
                    f"• **Coincidencia Exacta (Clave en Verde):** {coinciden}\n"
                    f"• **Lotes Pendientes por Vincular:** {lotes_pend}\n"
                    f"• **Índice de Sincronización:** {salud}\n\n"
                    f"💡 *Para ver cada lote con sus claves, abre el Mapeo de Lotes en la barra flotante.*"
                )
                return {
                    "ok": True,
                    "motor": "Diagnóstico de Obra",
                    "pregunta": pregunta,
                    "respuesta": respuesta
                }

        # =============================================================
        # 6. BÚSQUEDA EN DOCUMENTACIÓN Y BASE DE CONOCIMIENTO
        # =============================================================
        docs = tool_buscar_conocimiento(pregunta)
        if docs.get("ok") and docs.get("documentos"):
            doc = docs["documentos"][0]
            return {
                "ok": True,
                "motor": "Base de Conocimiento",
                "pregunta": pregunta,
                "respuesta": f"📚 **De las guías y reglas del sistema ({doc['nombre_archivo']}):**\n\n{doc['resumen']}"
            }

        # Si preguntó por un usuario específico y no se encontró
        if es_pregunta_persona:
            return {
                "ok": True,
                "motor": "Búsqueda de Usuarios",
                "pregunta": pregunta,
                "respuesta": "🔍 No encontré a ningún colaborador registrado con ese nombre en la plantilla de Grupo Velas. Verifica que el nombre esté bien escrito o prueba con su apellido o correo."
            }

        # =============================================================
        # 7. FALLBACK CONVERSACIONAL LIMPIO Y AMIGABLE
        # =============================================================
        return {
            "ok": True,
            "motor": "Asistente",
            "pregunta": pregunta,
            "respuesta": (
                f"🤔 No encontré datos sobre eso en el sistema por el momento.\n\n"
                f"💡 **Puedes preguntarme por:**\n"
                f"• **Totales:** *'¿Cuántos usuarios hay?'* o *'¿Cuántas obras tenemos?'*\n"
                f"• **Personas:** *'¿Quién es Claudia Padilla?'* o *'¿Quiénes están en sistemas?'*\n"
                f"• **Obras y Lotes:** *'¿Cómo está la obra HFA?'* o *'Lotes de DQA'*\n"
                f"• **Precios:** *'¿Qué escalatorias tenemos autorizadas?'*\n"
                f"• **Reglas:** *'¿Cuándo se marca la clave en verde?'*"
            )
        }
