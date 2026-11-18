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
    tool_buscar_usuario,
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
            Eres el Asistente Centinela del Dashboard EK10 de Grupo Velas (la simpática y astuta tostada inteligente).
            Estás hablando con {usuario}.
            
            Información disponible del sistema:
            Usuarios encontrados:
            {resumen_usuarios or "Ninguno específico para esta búsqueda."}

            Documentación aprendida:
            {resumen_docs or "Sin notas adicionales."}

            Instrucciones de Respuesta:
            1. Responde de forma muy natural, amistosa, directa y profesional (como un compañero de equipo de confianza).
            2. NUNCA uses términos técnicos robóticos como "Grafo Local", "nodos", "aristas" o "tabla hash".
            3. Si preguntan por una persona (ej. Claudia Padilla), di claramente quién es, su puesto, área y correo.
            4. Si preguntan por una obra (ej. HFA), resume el total de lotes y el estado de homologación.
            5. Usa viñetas limpias y emojis agradables.
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
        p_lower = pregunta.lower()

        # 1. Búsqueda de Usuarios / Colaboradores / Puestos / Correos
        palabras_usuario = [
            "usuario", "colaborador", "compañero", "compañera", "quién es", "quien es",
            "sabes si", "conoces a", "persona", "correo", "email", "puesto", "trabaja",
            "contacto", "encargado", "líder", "lider", "broker"
        ]
        es_pregunta_usuario = any(w in p_lower for w in palabras_usuario)

        # Buscar en la plantilla de usuarios de Grupo Velas
        res_usuarios = tool_buscar_usuario(pregunta, limite=3)
        if res_usuarios.get("ok") and res_usuarios.get("total", 0) > 0 and (es_pregunta_usuario or len(res_usuarios["usuarios"]) <= 3):
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

        # 2. Detección de Escalatorias de Precios (SOC Enkontrol)
        if any(w in p_upper for w in ["ESCALATORIA", "ESCALATORIAS", "PRECIO", "PRECIOS", "INSUMO", "ADITIVA", "ADITIVAS"]):
            datos_esc = tool_consultar_escalatorias()
            if datos_esc.get("ok") and datos_esc.get("escalatorias_recientes"):
                lista = datos_esc["escalatorias_recientes"]
                lineas = [f"📈 **Estas son las últimas escalatorias autorizadas en Enkontrol:**"]
                for esc in lista[:4]:
                    lineas.append(f"• **{esc['clave']}**: {esc['nombre']} ({esc['numero_insumos']} insumos) [{esc['estatus_desc']}]")
                lineas.append("\n💡 *Puedes revisarlas a detalle abriendo la consulta de Escalatorias en la barra flotante.*")
                return {
                    "ok": True,
                    "motor": "Escalatorias Enkontrol",
                    "pregunta": pregunta,
                    "respuesta": "\n".join(lineas)
                }

        # 3. Detección de Obras específicas (ej. HFA, DQA, DQC, C38, C39, 008, 024, 045)
        coincidencias_obra = re.findall(r"\b([A-Z0-9]{3,4})\b", p_upper)
        # Filtrar palabras comunes que coinciden con 3-4 letras
        palabras_ignorar = {"PARA", "LOTE", "OBRA", "TODO", "ESTA", "BIEN", "HOLA", "HACE", "CUAL", "CUAN", "DONDE", "COMO"}
        for palabra in coincidencias_obra:
            if palabra in palabras_ignorar:
                continue
            diag = tool_consultar_obra(palabra)
            if diag.get("ok"):
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

        # 4. Búsqueda en documentación y memoria aprendida
        docs = tool_buscar_conocimiento(pregunta)
        if docs.get("ok") and docs.get("documentos"):
            doc = docs["documentos"][0]
            return {
                "ok": True,
                "motor": "Base de Conocimiento",
                "pregunta": pregunta,
                "respuesta": f"📚 **De las guías y reglas del sistema ({doc['nombre_archivo']}):**\n\n{doc['resumen']}"
            }

        # 5. Si preguntó por un usuario pero no se encontró
        if es_pregunta_usuario:
            return {
                "ok": True,
                "motor": "Búsqueda de Usuarios",
                "pregunta": pregunta,
                "respuesta": "🔍 No encontré a ningún colaborador registrado con ese nombre en la plantilla de usuarios de Grupo Velas. Verifica que el nombre esté bien escrito o prueba con su apellido o correo."
            }

        # 6. Fallback conversacional limpio, humano y amigable (CERO texto técnico de grafos)
        return {
            "ok": True,
            "motor": "Asistente",
            "pregunta": pregunta,
            "respuesta": (
                f"🤔 No encontré datos sobre eso en el sistema por el momento.\n\n"
                f"💡 **Puedes preguntarme por:**\n"
                f"• **Colaboradores:** *'¿Quién es Claudia Padilla?'* o *'Busca al líder de ventas'*\n"
                f"• **Obras y Lotes:** *'¿Cómo está la obra HFA?'* o *'Lotes de DQA'*\n"
                f"• **Precios:** *'¿Qué escalatorias tenemos autorizadas?'*\n"
                f"• **Reglas:** *'¿Cuándo se marca la clave en verde?'*"
            )
        }
