"""
Extractor Autónomo de Aprendizaje y Reflexión para KHIARA.
Analiza las conversaciones en segundo plano para extraer hechos, preferencias de usuario
y correcciones de datos, consolidándolos en la Memoria Evolutiva persistente.
"""

import re
import logging
from typing import Optional, Dict, Any
from khiara.cerebro.memoria_evolutiva import memoria_evolutiva_global

logger = logging.getLogger("khiara.aprendizaje")


PATRONES_PREFERENCIA = [
    r"(?:prefiero|me gusta|acostumbro|muestra|dame|responde)\s+(?:que|las|los|con|en)\s+(.+)",
    r"(?:siempre|a partir de ahora|de ahora en adelante)\s+(.+)",
    r"(?:no me muestres|evita)\s+(.+)"
]

PATRONES_REGLA_NEGOCIO = [
    r"(?:la obra|el proyecto)\s+([A-Z0-9]{3,4})\s+(?:tiene|es|usa|cuenta con|cambió a)\s+(.+)",
    r"(?:el contratista|el proveedor|el residente)\s+(?:de|para)\s+([A-Za-z0-9\s]+)\s+es\s+(.+)",
    r"(?:el insumo|el material)\s+([A-Za-z0-9\s]+)\s+se (?:usa|ubica|encuentra)\s+en\s+(.+)"
]

PATRONES_CORRECCION = [
    r"(?:no es|no se llama|corrige|el dato correcto es|te equivocaste,? es)\s+(.+)",
    r"(?:en realidad|de hecho)\s+(?:es|son)\s+(.+)"
]

PATRONES_HECHO_EXPLICITO = [
    r"(?:recuerda que|ten en cuenta que|guarda que|memoriza que)\s+(.+)",
    r"(?:mi nombre es|mi puesto es|mi correo es)\s+(.+)"
]


def analizar_y_aprender_de_turno(
    mensaje_usuario: str,
    respuesta_khiara: str,
    usuario_id: str = "esteban"
) -> Optional[Dict[str, Any]]:
    """
    Analiza un mensaje de usuario para detectar intenciones de enseñanza o preferencias.
    Si detecta un hecho o regla relevante, la persiste en Memoria Evolutiva.
    Retorna los datos de la regla aprendida o None.
    """
    if not mensaje_usuario or len(mensaje_usuario.strip()) < 5:
        return None

    texto = mensaje_usuario.strip()

    # 1. Hechos explícitos pedidos por el usuario
    for pat in PATRONES_HECHO_EXPLICITO:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            regla = m.group(0).strip()
            res = memoria_evolutiva_global.registrar_regla(
                texto_regla=regla,
                categoria="HECHO_SISTEMA",
                proyecto_asociado=usuario_id
            )
            return res

    # 2. Correcciones de datos
    for pat in PATRONES_CORRECCION:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            regla = f"Corrección indicada por {usuario_id}: {m.group(0).strip()}"
            res = memoria_evolutiva_global.registrar_regla(
                texto_regla=regla,
                categoria="CORRECCION_DATO",
                proyecto_asociado=usuario_id
            )
            return res

    # 3. Preferencias del usuario
    for pat in PATRONES_PREFERENCIA:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            regla = f"Preferencia de {usuario_id}: {m.group(0).strip()}"
            res = memoria_evolutiva_global.registrar_regla(
                texto_regla=regla,
                categoria="PREFERENCIA_USUARIO",
                proyecto_asociado=usuario_id
            )
            return res

    # 4. Reglas de negocio u obras
    for pat in PATRONES_REGLA_NEGOCIO:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            regla = m.group(0).strip()
            res = memoria_evolutiva_global.registrar_regla(
                texto_regla=regla,
                categoria="REGLA_NEGOCIO",
                proyecto_asociado=usuario_id
            )
            return res

    return None
