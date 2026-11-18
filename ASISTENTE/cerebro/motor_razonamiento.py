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
    tool_consultar_insumos,
    tool_consultar_claves_posiciones,
    tool_consultar_insumo_en_obra
)


class MotorRazonamiento:
    @classmethod
    def procesar_consulta(cls, pregunta: str, usuario: str = "Esteban") -> Dict[str, Any]:
        """
        Punto de entrada principal para responder consultas con razonamiento.
        Usa Gemini API si la clave está configurada; de lo contrario usa el motor inteligente local.
        """
        # Asegurar de forma automática que cualquier documento nuevo esté indexado
        try:
            ModuloAprendizaje.asegurar_aprendizaje_al_dia()
        except Exception:
            pass

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
        # 0. CONSULTAS SOBRE POSICIONES / PUESTOS / CLAVES (PRIORIDAD ALTA)
        # =============================================================
        palabras_pos = ["posicion", "posiciones", "posision", "posisiones", "puesto", "puestos"]
        if any(w in p_lower for w in palabras_pos) and any(w in p_lower for w in ["clave", "crear", "ultima", "última", "siguiente", "nueva", "disponible", "cuales", "cuáles", "catalogo", "catálogo", "cuantas", "cuántas"]):
            info_pos = tool_consultar_claves_posiciones()
            if info_pos.get("ok"):
                if any(w in p_lower for w in ["ultima", "última"]):
                    return {"ok": True, "motor": "Posiciones", "pregunta": pregunta, "respuesta": f"La última clave registrada es `{info_pos['ultima_clave']}` ({info_pos['ultimo_puesto_nombre']})."}
                if any(w in p_lower for w in ["siguiente", "crear", "disponible", "nueva"]):
                    return {"ok": True, "motor": "Posiciones", "pregunta": pregunta, "respuesta": f"La siguiente clave para crear es `{info_pos['siguiente_clave']}` (última: `{info_pos['ultima_clave']}`)."}
                return {"ok": True, "motor": "Posiciones", "pregunta": pregunta, "respuesta": f"Hay **{info_pos['total_posiciones']} posiciones** catalogadas (última: `{info_pos['ultima_clave']}`, siguiente: `{info_pos['siguiente_clave']}`)."}

        # =============================================================
        # 0.1 CONSULTAS SOBRE ESCALATORIAS DE PRECIO / ADITIVAS (PRIORIDAD ALTA)
        # =============================================================
        palabras_esc = ["escalatoria", "escalatorias", "aditiva", "aditivas", "ajuste de precio", "ajustes de precio"]
        es_consulta_escalatoria = any(w in p_lower for w in palabras_esc)

        if es_consulta_escalatoria:
            coincidencias_candidatas = re.findall(r"\b([A-Z0-9]{2,6})\b", p_upper)
            palabras_ignorar_esc = {
                "PARA", "LOTE", "OBRA", "TODO", "ESTA", "BIEN", "HOLA", "HACE",
                "CUAL", "CUAN", "DONDE", "COMO", "TIENE", "TIENEN", "HAY", "PRECIO",
                "PRECIOS", "SOC", "ENK", "SABES", "TIENEN", "DE", "LA", "EL", "LAS", "LOS",
                "QUE", "EN", "TOTAL", "TOTALES", "TODAS", "TODOS", "UN", "UNA", "POR", "CON",
                "DEL", "MAS", "SIN", "SUS", "MIS", "TUS", "SON", "ERA", "FUE", "SER", "VER", "DAR"
            }
            obra_detectada = None
            for cand in coincidencias_candidatas:
                if cand not in palabras_ignorar_esc:
                    test_esc = tool_consultar_escalatorias(obra_o_cc=cand)
                    if test_esc.get("ok") and test_esc.get("total_escalatorias", 0) > 0:
                        obra_detectada = cand
                        break

            if obra_detectada:
                terminos_mat = [w for w in re.findall(r"\w+", p_lower) if w in ["acero", "block", "concreto", "tinaco", "alambre", "mortero", "varilla", "armex", "malla", "cemento"]]
                if terminos_mat:
                    mat = terminos_mat[0]
                    res_mat = tool_consultar_insumo_en_obra(mat, obra_detectada)
                    if res_mat.get("ok") and res_mat.get("total", 0) > 0:
                        lineas = [f"**{mat.upper()} en {obra_detectada}:**"]
                        for i in res_mat["resultados"][:3]:
                            lineas.append(f"• {i['nombre']}: ${i['precio']:,.2f} {i['moneda']} (base: ${i['precio_ppto']:,.2f}) [{i['escalatoria_clave']}]")
                        return {"ok": True, "motor": "Insumo en Obra", "pregunta": pregunta, "respuesta": "\n".join(lineas)}

                res_esc = tool_consultar_escalatorias(obra_o_cc=obra_detectada)
                tot = res_esc.get("total_escalatorias", 0)
                lista = res_esc.get("escalatorias", [])
                lineas = [f"La obra **{obra_detectada}** tiene **{tot} escalatorias** autorizadas en SOC:"]
                for e in lista[:5]:
                    lineas.append(f"• {e['clave']}: {e['nombre']}")
                return {"ok": True, "motor": "Escalatorias por Obra", "pregunta": pregunta, "respuesta": "\n".join(lineas)}

            terminos_ins = [w for w in re.findall(r"\w+", p_lower) if w in ["acero", "block", "concreto", "tinaco", "alambre", "mortero", "varilla", "armex", "malla", "cemento"]]
            if terminos_ins:
                term = terminos_ins[0]
                res_ins = tool_consultar_escalatorias(termino_insumo=term)
                if res_ins.get("ok") and (res_ins.get("escalatorias") or res_ins.get("insumos_detalles")):
                    lineas = [f"**Escalatorias de {term.upper()} autorizadas en SOC:**"]
                    for e in res_ins.get("escalatorias", [])[:3]:
                        lineas.append(f"• {e['clave']}: {e['nombre']}")
                    return {"ok": True, "motor": "Escalatorias por Insumo", "pregunta": pregunta, "respuesta": "\n".join(lineas)}

            res_gen = tool_consultar_escalatorias()
            return {
                "ok": True,
                "motor": "Escalatorias",
                "pregunta": pregunta,
                "respuesta": f"Hay **{res_gen.get('total_escalatorias', 98)} escalatorias autorizadas** en SOC ({res_gen.get('total_insumos_afectados', 10500):,} insumos en {res_gen.get('total_obras_con_escalatorias', 121)} obras)."
            }

        # =============================================================
        # 1. PREGUNTAS DE CONTEOS, TOTALES Y MÉTRICAS (¿CUÁNTOS HAY?)
        # =============================================================
        es_pregunta_conteo = any(w in p_lower for w in ["cuantos", "cuántos", "cuantas", "cuántas", "total de", "cantidad de", "numero de", "número de", "hay ahorita", "guardados"])
        
        # A) Conteo de Usuarios / Colaboradores / Personas
        if es_pregunta_conteo and any(w in p_lower for w in ["usuario", "colaborador", "persona", "empleado", "gente"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Usuarios",
                "pregunta": pregunta,
                "respuesta": f"Hay **{m['usuarios_totales']:,} usuarios** guardados (**{m['usuarios_activos']:,} activos**) en {m['puestos_totales']} puestos."
            }

        # B) Conteo de Obras / Centros de Costo
        if es_pregunta_conteo and any(w in p_lower for w in ["obra", "obras", "cc", "ccs", "centro de costo", "centros de costo"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Obras",
                "pregunta": pregunta,
                "respuesta": f"Tenemos **{m['obras_totales']:,} centros de costo** ({m['lotes_totales']:,} lotes totales, {m['lotes_ek10_totales']:,} con clave EK10)."
            }

        # C) Conteo de Lotes
        if es_pregunta_conteo and any(w in p_lower for w in ["lote", "lotes", "vivienda", "viviendas"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Lotes",
                "pregunta": pregunta,
                "respuesta": f"Hay **{m['lotes_totales']:,} lotes** registrados ({m['lotes_ek10_totales']:,} vinculados a EK10) en {m['obras_totales']} obras."
            }

        # D) Conteo de Escalatorias
        if es_pregunta_conteo and any(w in p_lower for w in ["escalatoria", "escalatorias", "aditiva", "aditivas"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Escalatorias",
                "pregunta": pregunta,
                "respuesta": f"Hay **{m['escalatorias_totales']} escalatorias autorizadas** en SOC Enkontrol."
            }

        # E) Preguntas de Resumen General ("¿Qué información tienes?", "¿Qué datos manejas?")
        if any(w in p_lower for w in ["que informacion tienes", "qué información tienes", "que datos tienes", "qué datos tienes", "resumen general", "que sabes hacer", "qué sabes"]):
            m = tool_metricas_totales()
            return {
                "ok": True,
                "motor": "Resumen General",
                "pregunta": pregunta,
                "respuesta": f"Datos en memoria: {m['usuarios_totales']:,} usuarios, {m['puestos_totales']} puestos, {m['obras_totales']:,} obras, {m['lotes_totales']:,} lotes y {m['escalatorias_totales']} escalatorias."
            }

        # =============================================================
        # F) Consultas sobre carpetas, estructura o archivos del sistema
        # =============================================================
        if any(w in p_lower for w in ["carpeta", "carpetas", "directorio", "directorios", "archivo", "archivos", "donde estan los datos", "dónde están los datos", "estructura del", "base de datos", "bases de datos"]):
            exp = tool_explorar_carpetas(p_lower)
            if exp.get("tema") != "GENERAL":
                det = exp.get("detalle", {})
                archivos_str = ", ".join([f"`{a}`" for a in det.get("archivos_clave", [])])
                return {
                    "ok": True,
                    "motor": "Carpetas",
                    "pregunta": pregunta,
                    "respuesta": f"📁 **{det.get('ruta')}** ({exp.get('tema')}): {det.get('descripcion')}. Archivos: {archivos_str}."
                }
            else:
                carpetas = exp.get("carpetas", {})
                lineas = ["Carpetas principales conectadas:"]
                for k, v in carpetas.items():
                    lineas.append(f"• `{v['ruta']}` ({k}): {v['descripcion']}")
                return {
                    "ok": True,
                    "motor": "Carpetas",
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
                    lineas = [f"Colaboradores en **{area_key.upper()}**:"]
                    for u in matches_area:
                        lineas.append(f"• **{u['nombre']}** - {u['puesto']} (`{u['email']}`)")
                    return {
                        "ok": True,
                        "motor": "Directorio de Áreas",
                        "pregunta": pregunta,
                        "respuesta": "\n".join(lineas)
                    }

        # =============================================================
        # 3. BÚSQUEDA DE UN USUARIO / PERSONA ESPECÍFICA (INTERPRETANDO CAMPO SOLICITADO)
        # =============================================================
        palabras_usuario = [
            "usuario", "colaborador", "compañero", "compañera", "quién es", "quien es",
            "sabes si", "conoces a", "persona", "correo", "email", "puesto", "trabaja",
            "contacto", "encargado", "líder", "lider", "id de", "id del", "cual es el id", "cuál es el id"
        ]
        es_pregunta_persona = any(w in p_lower for w in palabras_usuario)

        res_usuarios = tool_buscar_usuario(pregunta, limite=3)
        if res_usuarios.get("ok") and res_usuarios.get("total", 0) > 0 and (es_pregunta_persona or len(res_usuarios["usuarios"]) <= 3):
            lista = res_usuarios["usuarios"]
            if len(lista) == 1:
                u = lista[0]
                nom = u['nombre_completo']
                # Si específicamente pidió el ID
                if any(w in p_lower for w in ["id", "identificador"]):
                    return {
                        "ok": True,
                        "motor": "Usuarios",
                        "pregunta": pregunta,
                        "respuesta": f"El ID de **{nom}** es **{u.get('id', 'N/D')}**."
                    }
                # Si específicamente pidió el correo / email
                if any(w in p_lower for w in ["correo", "email"]):
                    return {
                        "ok": True,
                        "motor": "Usuarios",
                        "pregunta": pregunta,
                        "respuesta": f"El correo de **{nom}** es `{u.get('email', 'N/D')}`."
                    }
                # Si específicamente pidió el puesto / posición
                if any(w in p_lower for w in ["puesto", "posicion", "posicion de"]):
                    return {
                        "ok": True,
                        "motor": "Usuarios",
                        "pregunta": pregunta,
                        "respuesta": f"El puesto de **{nom}** es **{u['puesto']}** ({u['area']})."
                    }
                # Si específicamente pidió el estatus
                if any(w in p_lower for w in ["estatus", "activo", "vigente"]):
                    return {
                        "ok": True,
                        "motor": "Usuarios",
                        "pregunta": pregunta,
                        "respuesta": f"El estatus de **{nom}** es **{u['estatus']}**."
                    }
                # Pregunta general sobre la persona: respuesta limpia y directa
                return {
                    "ok": True,
                    "motor": "Usuarios",
                    "pregunta": pregunta,
                    "respuesta": f"👤 **{nom}** (ID: {u.get('id')})\n• Puesto: {u['puesto']} ({u['area']})\n• Correo: `{u['email']}`\n• Estatus: {u['estatus']}"
                }
            else:
                texto = f"👥 Coincidencias ({res_usuarios['total']}):\n"
                for u in lista:
                    texto += f"• **{u['nombre_completo']}** (ID: {u.get('id')}) - {u['puesto']} (`{u['email']}`)\n"
                return {
                    "ok": True,
                    "motor": "Usuarios",
                    "pregunta": pregunta,
                    "respuesta": texto.strip()
                }

        # =============================================================
        # 4. DETECCIÓN DE ESCALATORIAS E INSUMOS DE PRECIOS
        # =============================================================
        # Búsqueda de materiales / insumos específicos
        palabras_insumo = ["insumo", "insumos", "material", "materiales", "block", "acero", "cemento", "tinaco", "alambre", "mortero", "varilla", "armex", "precio", "costo"]
        if any(w in p_lower for w in palabras_insumo) and not es_pregunta_conteo:
            terminos_clave = [w for w in re.findall(r"\w+", p_lower) if w in ["block", "acero", "cemento", "tinaco", "alambre", "mortero", "varilla", "armex", "concreto", "tuberia", "cable", "pintura", "impermeabilizante", "malla"]]
            term_search = terminos_clave[0] if terminos_clave else "material"

            # Revisar si se menciona una obra en específico (ej. "precio del block en AUS")
            coincidencias_cand = [w for w in re.findall(r"\b([A-Z0-9]{2,5})\b", p_upper) if w not in {"PARA", "LOTE", "OBRA", "TODO", "ESTA", "BIEN", "HOLA", "HACE", "CUAL", "CUAN", "DONDE", "COMO", "TIENE", "HAY", "LOS", "LAS", "DEL", "CON", "POR", "QUE", "MAS", "PRECIO", "COSTO"}]
            for c_cand in coincidencias_cand:
                res_ins_obra = tool_consultar_insumo_en_obra(term_search, c_cand)
                if res_ins_obra.get("ok") and res_ins_obra.get("total", 0) > 0:
                    lineas = [f"🧱 **{term_search.upper()} en Obra {c_cand}:**"]
                    for i in res_ins_obra["resultados"][:3]:
                        lineas.append(f"• **{i['nombre']}**: ${i['precio']:,.2f} {i['moneda']} (Presupuesto original: ${i['precio_ppto']:,.2f}) [{i['escalatoria_clave']}]")
                    return {
                        "ok": True,
                        "motor": "Insumo en Obra",
                        "pregunta": pregunta,
                        "respuesta": "\n".join(lineas)
                    }

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

        # =============================================================
        # 5. DETECCIÓN DE OBRAS ESPECÍFICAS (ej. HFA, DQA, DQC, C38, C39)
        # =============================================================
        coincidencias_obra = re.findall(r"\b([A-Z0-9]{3,4})\b", p_upper)
        palabras_ignorar = {
            "PARA", "LOTE", "OBRA", "TODO", "ESTA", "BIEN", "HOLA", "HACE",
            "CUAL", "CUAN", "DONDE", "COMO", "TIENE", "HAY", "LOS", "LAS",
            "DEL", "CON", "POR", "QUE", "MAS", "SUS", "MIS", "TUS", "SON",
            "ERA", "FUE", "SER", "VER", "DAR", "UNOS", "UNAS", "CREAR",
            "CLAVE", "ULTIMO", "ULTIMA", "PUESTO", "USUARIO", "USUARIOS",
            "SABES", "TIENEN", "PUEDE", "DATOS", "PUESTOS", "POSICION", "POSICIONES"
        }
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

                respuesta = f"🏗️ **Obra {palabra}:** {total_lt} lotes ({lotes_hom} en EK10, {coinciden} clave verde, sincronización: {salud})."
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
                "respuesta": f"📚 **{doc['nombre_archivo']}:** {doc['resumen']}"
            }

        # Si preguntó por un usuario específico y no se encontró
        if es_pregunta_persona:
            return {
                "ok": True,
                "motor": "Búsqueda de Usuarios",
                "pregunta": pregunta,
                "respuesta": "No encontré ningún colaborador registrado con ese nombre."
            }

        # =============================================================
        # 7. FALLBACK DIRECTO Y LIMPIO
        # =============================================================
        return {
            "ok": True,
            "motor": "Asistente",
            "pregunta": pregunta,
            "respuesta": "No encontré registro de eso en las bases del sistema."
        }
