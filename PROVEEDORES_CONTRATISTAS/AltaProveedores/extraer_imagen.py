# -*- coding: utf-8 -*-
"""
extraer_imagen.py
-----------------
Convierte la captura de la pantalla "Datos Generales" de un proveedor (EK9) en el CSV
vertical CAMPO,VALOR que usan alta_proveedores.py y alta_contratistas.py.

La lectura de la imagen la hace Claude (API de Anthropic): requiere la variable de entorno
ANTHROPIC_API_KEY (o un perfil de `ant auth login`).

Uso: python extraer_imagen.py captura.png [carpeta_salida]
"""

import base64
import csv
import io
import os
import re
import sys
from typing import List

try:
    import anthropic
except ImportError:
    anthropic = None
from pydantic import BaseModel, Field

from proveedor_csv import leer_proveedor, normalizar

MODELO = "claude-opus-5-5"
TIPOS_IMAGEN = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".webp": "image/webp"}

INSTRUCCIONES = """Eres un capturista de datos. Recibes una captura de la pestana "Datos Generales"
de la pantalla de proveedores de un ERP y debes extraer sus campos EXACTAMENTE como aparecen.

1. Un campo por etiqueta, en orden de lectura (izquierda a derecha, arriba hacia abajo).
   Usa la etiqueta tal como se ve, sin los dos puntos finales (p.ej. "Proveedor", "Persona Fisica",
   "Deleg. ó Mpio.", "Código Postal", "Nac. ó Ext.", "R.F.C.", "Tipo de Tercero").
2. Casillas de verificacion -> "Sí" si estan marcadas, "No" si no.
3. Botones de opcion (p.ej. Estatus General) -> solo el valor seleccionado; el campo se llama
   como su etiqueta de grupo ("Estatus General").
4. Listas desplegables -> el valor mostrado. Campos vacios -> valor "".
5. Copia el texto tal cual (mayusculas, acentos, guiones del RFC). No corrijas ni inventes.
6. dudas: textos dudosos o ilegibles (letras/numeros del RFC, CP, nombres). Describe donde estan.
   Lista vacia si todo se lee bien."""


class Campo(BaseModel):
    campo: str
    valor: str


class CapturaProveedor(BaseModel):
    campos: List[Campo] = Field(description="Campos de la pantalla en orden de lectura")
    dudas: List[str]


class ErrorExtraccion(RuntimeError):
    pass


def extraer(contenido, extension, client=None):
    """bytes de la imagen -> CapturaProveedor. Lanza ErrorExtraccion con un mensaje para el usuario."""
    tipo = TIPOS_IMAGEN.get(extension.lower())
    if not tipo:
        raise ErrorExtraccion(f"Formato no soportado: {extension} (use png, jpg, gif o webp)")
    if anthropic is None:
        raise ErrorExtraccion("El paquete 'anthropic' no está instalado. Utilice el lector 'db' o 'gemini'.")
    client = client or anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model=MODELO,
            max_tokens=16000,
            output_config={"effort": "medium"},
            # Si el modelo declina la solicitud, la API la reintenta con el modelo recomendado
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=INSTRUCCIONES,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": tipo,
                                                 "data": base64.standard_b64encode(contenido).decode("utf-8")}},
                    {"type": "text", "text": "Extrae los campos de esta captura."},
                ],
            }],
            output_format=CapturaProveedor,
        )
    except anthropic.AuthenticationError:
        raise ErrorExtraccion("API key de Anthropic invalida o no configurada (variable ANTHROPIC_API_KEY)")
    except anthropic.RateLimitError:
        raise ErrorExtraccion("Limite de uso de la API de Anthropic alcanzado; intente en unos minutos")
    except anthropic.APIStatusError as e:
        raise ErrorExtraccion(f"Error de la API de Anthropic ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise ErrorExtraccion("No hay conexion con la API de Anthropic")
    except TypeError as e:
        # Sin credenciales el SDK falla al construir los encabezados
        raise ErrorExtraccion(f"Sin credenciales de Anthropic (defina ANTHROPIC_API_KEY): {e}")
    if response.stop_reason == "refusal":
        raise ErrorExtraccion("El modelo no proceso la imagen (refusal)")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise ErrorExtraccion("La respuesta del modelo llego incompleta")
    return response.parsed_output


def texto_csv(campos):
    """[(campo, valor)] -> texto CSV con encabezado CAMPO,VALOR y saltos CRLF."""
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\r\n")
    escritor.writerow(["CAMPO", "VALOR"])
    escritor.writerows(campos)
    return salida.getvalue()


def nombre_archivo(campos):
    """proveedor_<numero>_<nombre corto>.csv, igual que los CSV existentes."""
    valores = {normalizar(c): v for c, v in campos}
    numero = re.sub(r"\D", "", valores.get("proveedor", "")) or "sin_numero"
    corto = valores.get("nombre corto") or valores.get("nombre") or "proveedor"
    corto = re.sub(r"[^a-z0-9]+", "_", normalizar(corto)).strip("_")[:40] or "proveedor"
    return f"proveedor_{numero}_{corto}.csv"


def validar(campos):
    """Interpreta los campos como lo hara el bot (tipo de persona, clave, faltantes)."""
    return leer_proveedor(texto_csv(campos), "imagen")


def escribir_csv(ruta, campos):
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        f.write(texto_csv(campos))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ruta = sys.argv[1]
    with open(ruta, "rb") as f:
        captura = extraer(f.read(), os.path.splitext(ruta)[1])
    campos = [(c.campo, c.valor) for c in captura.campos]
    destino = os.path.join(sys.argv[2] if len(sys.argv) > 2 else ".", nombre_archivo(campos))
    escribir_csv(destino, campos)
    p = validar(campos)
    print(f"CSV: {destino} | {p['tipo_persona']} | clave {p['clave']} | faltantes {p['faltantes']}")
    for d in captura.dudas:
        print("  [REVISAR]", d)
