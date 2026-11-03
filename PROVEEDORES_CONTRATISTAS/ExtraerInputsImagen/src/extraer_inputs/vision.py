"""Paso 2: estructura del formulario con el modelo de vision local (Ollama)."""

from __future__ import annotations

import json
from pathlib import Path

import ollama

from extraer_inputs import config
from extraer_inputs.logging_config import obtener_logger

log = obtener_logger(__name__)

PROMPT = """Eres un extractor de datos. Analiza la captura de pantalla de un formulario.
Devuelve ÚNICAMENTE un JSON con esta forma:
{"campos": [{"etiqueta": "...", "valor": "...", "tipo": "texto|numero|fecha|checkbox|select|vacio"}],
 "tablas": [{"encabezados": ["..."], "filas": [["..."]]}]}
Reglas:
- Copia los valores EXACTAMENTE como aparecen: no corrijas, no traduzcas, no formatees, no completes.
- Si un input está vacío, valor = "" y tipo = "vacio".
- Checkbox: valor "true" o "false". Select/combo: el texto visible seleccionado.
- Etiqueta = el texto del label asociado al input (a la izquierda o arriba).
- No incluyas botones, menús, títulos de ventana, barras de tareas ni texto que no sea un campo.
- Si no puedes leer un valor con certeza, valor = null.
- Respeta el orden visual: de arriba abajo y de izquierda a derecha."""

#: Formulario conocido (ej. EK9 del portal): solo se piden los valores de las etiquetas dadas, en un
#: JSON plano. En CPU lo que mas tarda es generar la respuesta; asi sale varias veces mas corta.
PROMPT_CAMPOS = """Eres un extractor de datos. La imagen es la captura de un formulario.
Para cada etiqueta de la lista devuelve el texto visible DENTRO de su input (cuadro de texto o combo):
{etiquetas}
Reglas:
- Copia el valor EXACTAMENTE como aparece: no corrijas, no traduzcas, no formatees, no completes.
- Solo el contenido del input: no incluyas la etiqueta ni textos de casillas o etiquetas vecinas.
- Input vacio -> "". Etiqueta que no aparece en la imagen o valor ilegible -> null.
- Combo/select: el texto visible seleccionado."""


class ErrorOllama(RuntimeError):
    """Ollama no esta disponible o devolvio una respuesta invalida."""


def _cliente() -> ollama.Client:
    return ollama.Client(host=config.OLLAMA_URL, timeout=config.TIMEOUT_OLLAMA_SEG)


def verificar_ollama() -> str | None:
    """None si Ollama corre y tiene el modelo; si no, el mensaje (en espanol) para solucionarlo."""
    try:
        modelos = [m.model for m in _cliente().list().models]
    except Exception:  # conexion rechazada, timeout, etc.
        return (f"Ollama no responde en {config.OLLAMA_URL}.\n"
                "  - Instale Ollama para Windows: https://ollama.com/download (o: winget install Ollama.Ollama)\n"
                "  - Abra la aplicacion Ollama (icono en la bandeja) o ejecute: ollama serve")
    # GET /api/tags; un nombre sin etiqueta equivale a ":latest"
    nombre = config.MODELO_VISION if ":" in config.MODELO_VISION else config.MODELO_VISION + ":latest"
    if nombre not in modelos:
        return (f"El modelo '{nombre}' no esta descargado en Ollama (modelos: {', '.join(modelos) or 'ninguno'}).\n"
                f"  - Ejecute: ollama pull {nombre}")
    return None


def _validar(respuesta: str) -> dict:
    datos = json.loads(respuesta)
    if not isinstance(datos, dict):
        raise ValueError("la respuesta no es un objeto JSON")
    campos = datos.get("campos") or []
    tablas = datos.get("tablas") or []
    if not isinstance(campos, list) or not isinstance(tablas, list):
        raise ValueError("'campos' y 'tablas' deben ser listas")
    limpios = []
    for c in campos:
        if isinstance(c, dict) and "etiqueta" in c:
            valor = c.get("valor")
            limpios.append({"etiqueta": str(c.get("etiqueta") or "").strip(),
                            "valor": None if valor is None else str(valor),
                            "tipo": str(c.get("tipo") or "texto").strip().lower()})
    return {"campos": limpios, "tablas": [t for t in tablas if isinstance(t, dict)]}


def _esquema_campos(etiquetas: list[str]) -> dict:
    """JSON schema {etiqueta: string|null} para la salida estructurada de Ollama."""
    return {"type": "object", "properties": {e: {"type": ["string", "null"]} for e in etiquetas},
            "required": list(etiquetas)}


def _validar_campos(respuesta: str, etiquetas: list[str]) -> dict:
    datos = json.loads(respuesta)
    if not isinstance(datos, dict):
        raise ValueError("la respuesta no es un objeto JSON")
    campos = []
    for e in etiquetas:
        valor = datos.get(e)
        campos.append({"etiqueta": e, "valor": None if valor is None else str(valor),
                       "tipo": "texto" if valor else "vacio"})
    return {"campos": campos, "tablas": []}


def _registrar_tiempos(imagen: Path, respuesta) -> None:
    """Tokens y segundos de Ollama: lectura de la imagen (prompt) y generacion de la respuesta."""
    seg = lambda ns: (ns or 0) / 1e9  # noqa: E731
    log.info("%s: Ollama %.0f s (imagen+prompt %d tokens en %.0f s, respuesta %d tokens en %.0f s).",
             imagen.name, seg(respuesta.total_duration), respuesta.prompt_eval_count or 0,
             seg(respuesta.prompt_eval_duration), respuesta.eval_count or 0, seg(respuesta.eval_duration))


def extraer_estructura(imagen: Path, etiquetas: list[str] | None = None) -> dict:
    """{"campos": [...], "tablas": [...]} de la imagen. Con `etiquetas` (formulario conocido) solo se
    piden esos campos. Un reintento si falla; luego ErrorOllama."""
    if etiquetas:
        prompt = PROMPT_CAMPOS.format(etiquetas="\n".join(f"- {e}" for e in etiquetas))
        formato: str | dict = _esquema_campos(etiquetas)
    else:
        prompt, formato = PROMPT, "json"
    ultimo_error: Exception | None = None
    for intento in (1, 2):
        try:
            respuesta = _cliente().chat(
                model=config.MODELO_VISION,
                messages=[{"role": "user", "content": prompt, "images": [str(imagen)]}],
                format=formato,
                options={"temperature": 0},
            )
            _registrar_tiempos(imagen, respuesta)
            if etiquetas:
                return _validar_campos(respuesta.message.content, etiquetas)
            return _validar(respuesta.message.content)
        except Exception as e:  # error de conexion, JSON invalido o forma inesperada
            ultimo_error = e
            log.warning("Ollama fallo con %s (intento %d/2): %s", imagen.name, intento, e)
    raise ErrorOllama(f"Ollama no devolvio un JSON valido para {imagen.name}: {ultimo_error}")
