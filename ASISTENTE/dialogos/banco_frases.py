"""
Banco de Diálogos, Personalidad y Saludos Contextuales del Asistente Centinela.
"""

import datetime
import random
from typing import Dict, Any


def obtener_saludo_contextual(nombre_usuario: str, nombre_asistente: str, dms_pendientes: int = 0) -> Dict[str, str]:
    hora = datetime.datetime.now().hour
    u = nombre_usuario or "Colaborador"
    bot = nombre_asistente or "Toastie"

    if hora < 12:
        tiempo = "¡Buenos días"
    elif hora < 19:
        tiempo = "¡Buenas tardes"
    else:
        tiempo = "¡Buenas noches"

    saludo_header = f"👋 {tiempo}, {u}!"

    if dms_pendientes > 0:
        cuerpo = f"Soy {bot}. Tienes {dms_pendientes} mensaje(s) nuevo(s) de tu equipo esperándote en el chat. ¡Aquí sigo al tiro!"
    else:
        frases_calma = [
            f"Soy {bot}. Todo tranquilo por aquí: cero alertas críticas y tus lotes sincronizados. Te avisaré si cae un correo o mensaje.",
            f"Soy {bot}. ¡A darle con todo hoy! Cualquier novedad en tus obras o en el chat te lo canto aquí mismo.",
            f"Soy {bot}. Sistema al 100%. Estoy aquí en la esquina cuidando tus pendientes mientras operas."
        ]
        cuerpo = random.choice(frases_calma)

    return {
        "titulo": saludo_header,
        "texto": cuerpo,
        "subtexto": f"Centinela activo: {bot}"
    }


def obtener_frase_clic(nombre_asistente: str) -> str:
    bot = nombre_asistente or "Toastie"
    frases = [
        f"¡OMFG HELLO! Aquí sigo en la esquina. Si un compañero te escribe en el chat, te lo digo al instante.",
        f"¡Presente! Soy {bot}. Todo el sistema operativo está vigilado: Obras, Chat y Escalatorias.",
        f"¿Todo bien, jefe? Recuerda que el Mapeo de Lotes y Escalatorias están a un clic en la barra flotante.",
        f"¡A la orden! Cero correos pendientes por ahora. Si algo cambia, brincaré con un globo de aviso.",
        f"¡Toast power! Monitoreando la nube de Enkontrol y el chat local en tiempo real."
    ]
    return random.choice(frases)


def obtener_frase_bautizo(nuevo_nombre: str) -> str:
    return f"¡Me encanta ese nombre! A partir de ahora me llamo {nuevo_nombre}. ¡Estaré aquí en la esquina cuidando tus pendientes!"
