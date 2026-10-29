"""Ojos de IA: Gemini mira la captura del fallo y explica qué ve en pantalla.

Opcional: sin API key o sin el paquete `google-genai`, simplemente se omite.
Instalación (en el venv desde el que corra el bot):  pip install -U google-genai
"""
import base64
import json
import os

from NUCLEO import config

PROMPT = """Eres un ingeniero de QA que revisa la captura de pantalla de un bot Selenium
sobre el ERP Aryve (Grupo Velas). El bot reportó este resultado:

{resumen}

Mira la captura y responde en español, máximo 8 líneas:
1. ¿Qué se ve realmente en pantalla (formulario, popup, mensaje de error, campo vacío)?
2. ¿Hay mensajes de validación en rojo, campos obligatorios vacíos o paneles sin guardar?
3. ¿Coincide lo que se ve con lo que el bot esperaba? Si no, indica la causa más probable.
4. Sugerencia concreta de arreglo."""


def analizar_captura(ruta_png, reporte):
    cfg = config.cargar()
    key = cfg.get("gemini_api_key")
    if not key or not os.path.exists(ruta_png):
        return None
    try:
        from google import genai
    except ImportError:
        return "(Visión omitida: instala `google-genai` en este venv para activar el análisis visual.)"

    resumen = json.dumps({
        "proyecto": reporte["proyecto"], "veredicto": reporte["veredicto"],
        "verificaciones_fallidas": [v for v in reporte["verificaciones"] if not v["ok"]],
        "pasos_fallidos": [p for p in reporte["pasos"] if p["estado"] == "fallo"][:10],
        "excepcion": (reporte.get("excepcion") or "")[-800:],
    }, ensure_ascii=False, indent=1)

    with open(ruta_png, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    try:
        client = genai.Client(api_key=key)
        interaction = client.interactions.create(
            model=cfg.get("modelo_vision", "gemini-3.8-flash"),
            input=[
                {"type": "image", "data": b64, "mime_type": "image/png"},
                {"type": "text", "text": PROMPT.format(resumen=resumen)},
            ],
        )
        return interaction.output_text
    except Exception as e:
        return f"(Visión falló: {e})"

