# -*- coding: utf-8 -*-
"""
extraer_gemini.py
-----------------
Lee la captura de "Datos Generales" de proveedores (EK9) con Google Gemini y devuelve los
campos en el mismo orden y formato que ocr_ek9.leer_captura (CSV CAMPO,VALOR).

Requiere: pip install google-genai  y la variable de entorno GEMINI_API_KEY.
Modelo: GEMINI_MODELO (por omision gemini-flash-latest).

Uso: python extraer_gemini.py captura.png [...]
"""

import os
import re
import time
import sys
from typing import List

from pydantic import BaseModel, Field

import ocr_ek9

MODELO = os.environ.get("GEMINI_MODELO", "gemini-3.8-flash")
MODELOS_RESPALDO = ["gemini-flash-latest", "gemini-3.7-flash"]  # si el principal esta saturado
TIPOS_IMAGEN = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".webp": "image/webp"}

INSTRUCCIONES = """Eres un capturista de datos. La imagen es la pestana "Datos Generales" de la pantalla
de proveedores de un ERP (EnKontrol). Extrae cada campo EXACTAMENTE como aparece en la imagen.

Reglas:
- Copia el texto tal cual: mayusculas, acentos, Ñ, guiones del RFC y espacios. No corrijas ortografia
  ni completes datos que no se vean. Campo vacio -> "".
- Casillas (Persona Fisica, Cemex, Obliga CFDI, Filial, Factoraje): true si tienen palomita.
- Estatus General: el texto de la opcion marcada (Vigente, Cancelado o Habilitado por password).
- Listas desplegables: el valor que muestran.
- hay_apellidos: true si la pantalla tiene los campos "A. Paterno" y "A. Materno".
- hay_cemex: true si la pantalla tiene la casilla "Cemex".
- dudas: lista de valores que no se leen con seguridad (letras o numeros parecidos en el RFC,
  CP, numero de proveedor, nombres). Indica el campo y por que. Lista vacia si todo es claro."""


class DatosProveedor(BaseModel):
    proveedor: str = Field(description="Numero en el cuadro Proveedor")
    persona_fisica: bool
    hay_cemex: bool
    cemex: bool
    obliga_cfdi: bool
    filial: bool
    factoraje: bool
    nombre: str
    hay_apellidos: bool
    a_paterno: str
    a_materno: str
    direccion: str
    calle: str
    colonia: str
    deleg_mpio: str = Field(description="Deleg. ó Mpio.")
    ciudad: str
    codigo_postal: str
    nac_ext: str = Field(description="Nac. ó Ext.")
    nombre_corto: str
    rfc: str = Field(description="R.F.C. tal como se ve, con guiones")
    no_pyme: str
    id_fiscal: str
    tipo_soc: str
    tipo_tercero: str
    tipo_operacion: str
    tipo_proveedor: str
    confir_pago: str
    clave_id: str
    estatus_general: str
    empleado: str
    nacionalidad: str
    dudas: List[str]


# Nombre del campo en el CSV -> atributo de DatosProveedor (mismo orden que ocr_ek9.CAMPOS)
ATRIBUTO = {
    "Proveedor": "proveedor", "Persona Fisica": "persona_fisica", "Cemex": "cemex",
    "Obliga CFDI": "obliga_cfdi", "Filial": "filial", "Factoraje": "factoraje", "Nombre": "nombre",
    "A. Paterno": "a_paterno", "A. Materno": "a_materno", "Dirección": "direccion", "Calle": "calle",
    "Colonia": "colonia", "Deleg. ó Mpio.": "deleg_mpio", "Ciudad": "ciudad",
    "Código Postal": "codigo_postal", "Nac. ó Ext.": "nac_ext", "Nombre Corto": "nombre_corto",
    "R.F.C.": "rfc", "No. Pyme": "no_pyme", "ID Fiscal": "id_fiscal", "Tipo Soc.": "tipo_soc",
    "Tipo de Tercero": "tipo_tercero", "Tipo de Operación": "tipo_operacion",
    "Tipo de Proveedor": "tipo_proveedor", "Confir. pago": "confir_pago", "Clave ID": "clave_id",
    "Estatus General": "estatus_general", "Empleado": "empleado", "Nacionalidad": "nacionalidad",
}


class ErrorGemini(RuntimeError):
    pass


_cliente = None


def mensaje_corto(e):
    """Texto breve del error de la API para mostrarlo en el portal."""
    texto = e.message or ""
    if e.code == 429 and "quota" in texto.lower():
        limite = re.search(r"limit: (\d+)", texto)
        espera = re.search(r"retry in ([\dhms.]+?)(?:\d*\.\d+)?s", texto)
        return ("cuota de Gemini agotada" + (f" (limite {limite.group(1)} lecturas por dia)" if limite else "")
                + (f"; se reanuda en {espera.group(1).rstrip('.')}" if espera else ""))
    if e.code in (500, 503, 504):
        return "Gemini saturado temporalmente"
    return f"Gemini error {e.code}: {texto.splitlines()[0][:150] if texto else ''}"


def leer_captura(contenido, extension=".png"):
    """bytes de la imagen -> (campos [(nombre, valor)], dudas). Lanza ErrorGemini."""
    try:
        from google import genai
        from google.genai import errors, types
    except ImportError:
        raise ErrorGemini("Falta el paquete google-genai (pip install google-genai)")
    if not os.environ.get("GEMINI_API_KEY"):
        raise ErrorGemini("No esta definida la variable GEMINI_API_KEY")
    tipo = TIPOS_IMAGEN.get(extension.lower())
    if not tipo:
        raise ErrorGemini(f"Formato no soportado: {extension}")
    global _cliente
    if _cliente is None:
        # El cliente se conserva: si se crea en la misma expresion de la llamada, Python lo
        # cierra antes de enviar la peticion ("the client has been closed")
        _cliente = genai.Client()
    configuracion = types.GenerateContentConfig(
        system_instruction=INSTRUCCIONES,
        response_mime_type="application/json",
        response_schema=DatosProveedor,
        temperature=0,
    )
    contenido_msg = [types.Part.from_bytes(data=contenido, mime_type=tipo), "Extrae los campos de esta captura."]
    respuesta, ultimo_error = None, None
    # Saturacion (503) o limite (429) son temporales: se reintenta con espera y luego con el
    # modelo de respaldo
    for modelo in dict.fromkeys([MODELO] + MODELOS_RESPALDO):
        for espera in (0, 3, 8):
            time.sleep(espera)
            try:
                respuesta = _cliente.models.generate_content(model=modelo, contents=contenido_msg, config=configuracion)
                break
            except errors.APIError as e:
                ultimo_error = mensaje_corto(e)
                if e.code == 404:
                    break  # modelo no disponible para esta cuenta: se prueba el siguiente
                if e.code == 429 and "quota" in (e.message or "").lower():
                    break  # cuota agotada: reintentar no sirve; el siguiente modelo tiene su propia cuota
                if e.code not in (429, 500, 503, 504):
                    raise ErrorGemini(ultimo_error)
            except Exception as e:  # red, DNS, timeout
                raise ErrorGemini(f"No se pudo consultar Gemini: {e}")
        if respuesta is not None:
            break
    if respuesta is None:
        raise ErrorGemini(ultimo_error or "Gemini no respondio")
    datos = respuesta.parsed
    if datos is None:
        raise ErrorGemini("Gemini no devolvio datos validos")

    campos = []
    for nombre, _, siempre in ocr_ek9.CAMPOS:
        if nombre == "Cemex" and not datos.hay_cemex:
            continue
        if nombre in ("A. Paterno", "A. Materno") and not datos.hay_apellidos:
            continue
        valor = getattr(datos, ATRIBUTO[nombre])
        if isinstance(valor, bool):
            valor = "Sí" if valor else "No"
        valor = re.sub(r"\s+", " ", str(valor)).strip()
        if ocr_ek9.TIPO[nombre] == "numero":
            valor = re.sub(r"\D", "", valor)
        elif ocr_ek9.TIPO[nombre] == "rfc":
            valor = ocr_ek9.limpiar_rfc(valor)
        campos.append((nombre, valor))
    encontrados = {n for n, _ in campos}
    dudas = [f"Gemini: {d}" for d in datos.dudas] + ocr_ek9.dudas_de(campos, encontrados)
    return campos, dudas


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        with open(ruta, "rb") as f:
            campos, dudas = leer_captura(f.read(), os.path.splitext(ruta)[1])
        print(f"===== {ruta}  ({MODELO})")
        for nombre, valor in campos:
            print(f"  {nombre:20} {valor}")
        for d in dudas:
            print("  [REVISAR]", d)
