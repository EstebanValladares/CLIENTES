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
    tool_consultar_obra,
    tool_buscar_lotes,
    tool_consultar_escalatorias,
    tool_buscar_conocimiento
)


class MotorRazonamiento:
    @classmethod
    def procesar_consulta(cls, pregunta: str, usuario: str = "Esteban") -> Dict[str, Any]:
        """
        Punto de entrada principal para responder consultas con razonamiento.
        Usa Gemini API si la clave está configurada; de lo contrario usa el motor de grafos local.
        """
        api_key = obtener_gemini_api_key()

        if api_key:
            return cls._razonar_con_gemini(pregunta, usuario, api_key)
        else:
            return cls._razonar_con_grafos_local(pregunta, usuario)

    @classmethod
    def _razonar_con_gemini(cls, pregunta: str, usuario: str, api_key: str) -> Dict[str, Any]:
        """Razona utilizando el modelo Google Gemini con contexto de negocio y grafos."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            # Extraer contexto previo del grafo
            stats = GrafoConocimiento.obtener_estadisticas_grafo()
            docs_relevantes = ModuloAprendizaje.buscar_en_conocimiento(pregunta, limite=3)
            resumen_docs = "\n".join([f"- {d['nombre_archivo']}: {d['resumen']}" for d in docs_relevantes])

            system_instruction = f"""
            Eres el Asistente Centinela del Dashboard EK10 de Grupo Velas (la famosa tostada inteligente).
            Tu rol es ayudar a {usuario} y al equipo operativo a auditar lotes, obras, escalatorias y procesos.
            
            Información del Grafo de Conocimiento Local:
            - Nodos registrados: {stats.get('total_nodos', 0)}
            - Distribución: {stats.get('distribucion_tipos', {})}
            
            Conocimiento y Documentación aprendida:
            {resumen_docs or "Sin documentos adicionales."}

            Instrucciones de Respuesta:
            1. Sé claro, conciso, útil y amigable (con tono constructivo y profesional).
            2. Usa viñetas breves y emojis oportunos (🍞, 📈, 🏗️, ✅).
            3. Si preguntan por una obra específica (ej. HFA, DQA), enfócate en el estado de sus lotes y homologación.
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
                "motor": f"Gemini ({DEFAULT_MODEL})",
                "pregunta": pregunta,
                "respuesta": texto_respuesta,
                "documentos_usados": len(docs_relevantes)
            }

        except Exception as e:
            # Si falla la llamada externa (red, cuota), hacer fallback elegante al motor de grafos
            res_local = cls._razonar_con_grafos_local(pregunta, usuario)
            res_local["aviso_fallback"] = f"Se usó el motor local de grafos por incidencia con la API: {str(e)}"
            return res_local

    @classmethod
    def _razonar_con_grafos_local(cls, pregunta: str, usuario: str) -> Dict[str, Any]:
        """Motor de inferencia determinístico basado en grafos locales de SQLite (100% offline)."""
        p_upper = pregunta.upper()

        # 1. Detección de consultas sobre Escalatorias de Precios
        if any(w in p_upper for w in ["ESCALATORIA", "ESCALATORIAS", "PRECIO", "PRECIOS", "INSUMO"]):
            datos_esc = tool_consultar_escalatorias()
            if datos_esc.get("ok") and datos_esc.get("escalatorias_recientes"):
                lista = datos_esc["escalatorias_recientes"]
                lineas = [f"📈 **Escalatorias recientes registradas en SOC Enkontrol:**"]
                for esc in lista[:4]:
                    lineas.append(f"• **{esc['clave']}** - {esc['nombre']} ({esc['numero_insumos']} insumos) [{esc['estatus_desc']}]")
                lineas.append("\nPuedes revisarlas a detalle abriendo la consulta flotante de Escalatorias.")
                return {
                    "ok": True,
                    "motor": "Grafo Local (Escalatorias)",
                    "pregunta": pregunta,
                    "respuesta": "\n".join(lineas)
                }

        # 2. Detección de consulta sobre Obras específicas (ej. HFA, DQA, DQC, C38, C39)
        coincidencias_obra = re.findall(r"\b([A-Z0-9]{3,4})\b", p_upper)
        for palabra in coincidencias_obra:
            diag = tool_consultar_obra(palabra)
            if diag.get("ok"):
                total_lt = diag.get("total_lotes_obra") or diag.get("total_lotes_registrados", 0)
                lotes_hom = diag.get("lotes_con_suite_ek10") or diag.get("lotes_homologados_ek10", 0)
                lotes_pend = diag.get("lotes_pendientes_homologar") or diag.get("lotes_pendientes", 0)
                salud = diag.get("salud_homologacion", "0%")
                coinciden = diag.get("lotes_con_id_enk_coincidente", 0)

                respuesta = (
                    f"🏗️ **Diagnóstico Inteligente de Obra: {palabra}**\n"
                    f"• **Total Lotes de la Obra:** {total_lt}\n"
                    f"• **Lotes con Suite EK10 vinculada:** {lotes_hom}\n"
                    f"• **Lotes con Coincidencia Oficial (Verde):** {coinciden}\n"
                    f"• **Lotes Pendientes por Homologar:** {lotes_pend}\n"
                    f"• **Índice de Sincronización:** {salud}\n\n"
                    f"💡 *Tip:* Puedes consultar cada lote con sus claves Enkontrol abriendo la herramienta **Mapeo de Lotes**."
                )
                return {
                    "ok": True,
                    "motor": "Grafo Local (Diagnóstico de Obra)",
                    "pregunta": pregunta,
                    "respuesta": respuesta
                }

        # 3. Búsqueda en documentación y memoria aprendida
        docs = tool_buscar_conocimiento(pregunta)
        if docs.get("ok") and docs.get("documentos"):
            doc = docs["documentos"][0]
            return {
                "ok": True,
                "motor": "Grafo Local (Conocimiento Aprendido)",
                "pregunta": pregunta,
                "respuesta": f"📚 **De mi base de conocimiento ({doc['nombre_archivo']}):**\n\n{doc['resumen']}"
            }

        # 4. Respuesta general y estado del grafo
        stats = GrafoConocimiento.obtener_estadisticas_grafo()
        return {
            "ok": True,
            "motor": "Grafo Local (Estado General)",
            "pregunta": pregunta,
            "respuesta": (
                f"🍞 **Cerebro Centinela Activo**\n"
                f"Tengo indexados **{stats.get('total_nodos', 0)} nodos** y **{stats.get('total_aristas', 0)} conexiones** en mi grafo de conocimiento.\n\n"
                f"💡 **Puedes preguntarme cosas como:**\n"
                f"• *'¿Cómo está la obra HFA?'* (Diagnostico lotes y homologación)\n"
                f"• *'¿Hay escalatorias nuevas?'* (Reviso precios e insumos)\n"
                f"• O déjame archivos en `ASISTENTE/cerebro/conocimiento/` para aprender de ellos."
            )
        }
