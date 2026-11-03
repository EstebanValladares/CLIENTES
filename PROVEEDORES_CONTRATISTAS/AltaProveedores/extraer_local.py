# -*- coding: utf-8 -*-
"""
extraer_local.py
----------------
Lector 100% local de la captura "Datos Generales" de proveedores (EK9) para el portal:
usa el proyecto ExtraerInputsImagen (modelo de vision qwen2.5vl en Ollama + PaddleOCR + validacion
cruzada) y devuelve los campos en el mismo orden y formato que ocr_ek9 / extraer_gemini
(CSV CAMPO,VALOR). Ninguna imagen sale del equipo.

El extractor corre en un proceso aparte con su propio Python 3.13 (.venv del proyecto, porque
paddlepaddle aun no soporta 3.14) y responde una linea JSON.

Configuracion (variables de entorno):
  EXTRACTOR_LOCAL_DIR  carpeta del proyecto (por omision C:\\GV\\Proyectos\\ExtraerInputsImagen)
  EXTRACTOR_TIMEOUT    segundos maximos por imagen (por omision 1500; en CPU tarda 3-10 min)

Uso: python extraer_local.py captura.png [...]
"""

import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

import ocr_ek9
from proveedor_csv import normalizar

CARPETA_EXTRACTOR = os.environ.get("EXTRACTOR_LOCAL_DIR", r"C:\GV\Proyectos\ExtraerInputsImagen")
TIMEOUT = int(os.environ.get("EXTRACTOR_TIMEOUT", "1500"))
DESCRIPCION = "Local: Ollama qwen2.5vl + PaddleOCR (sin internet)"
TIPOS_IMAGEN = (".png", ".jpg", ".jpeg")


class ErrorLocal(RuntimeError):
    """El extractor local no esta disponible o fallo."""


def _python_extractor():
    ruta = os.path.join(CARPETA_EXTRACTOR, ".venv", "Scripts", "python.exe")
    if not os.path.exists(ruta):
        raise ErrorLocal(f"No se encontro el extractor local en {CARPETA_EXTRACTOR} (falta .venv)")
    return ruta


#: Campos con texto en un input: los unicos que se le piden al modelo (respuesta corta = mas rapido).
#: Casillas y Estatus General se toman del OCR de Windows, que las detecta por pixeles.
CAMPOS_MODELO = [nombre for nombre, tipo, _ in ocr_ek9.CAMPOS if tipo not in ("casilla", "opcion")]


def extraer_json(contenido, extension):
    """bytes de la imagen -> dict del extractor ({"campos": [...]}). Lanza ErrorLocal."""
    if extension.lower() not in TIPOS_IMAGEN:
        raise ErrorLocal(f"El lector local solo acepta {', '.join(TIPOS_IMAGEN)} (recibido {extension})")
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
        f.write(contenido)
        ruta = f.name
    entorno = dict(os.environ, PYTHONPATH=os.path.join(CARPETA_EXTRACTOR, "src"), PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run([_python_extractor(), "-m", "extraer_inputs.json_cli", ruta,
                            "--campos", "|".join(CAMPOS_MODELO)], capture_output=True,
                           timeout=TIMEOUT, cwd=CARPETA_EXTRACTOR, env=entorno,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise ErrorLocal(f"El extractor local tardo mas de {TIMEOUT // 60} min")
    finally:
        try:
            os.remove(ruta)
        except OSError:
            pass
    lineas = r.stdout.decode("utf-8", "replace").strip().splitlines()
    try:
        datos = json.loads(lineas[-1])
    except (IndexError, ValueError):
        raise ErrorLocal(f"El extractor local no respondio (codigo {r.returncode}): "
                         f"{r.stderr.decode('utf-8', 'replace')[-300:]}")
    if datos.get("error"):
        raise ErrorLocal(datos["error"])
    return datos


def _clave(etiqueta):
    """Etiqueta comparable: 'R.F.C.:' -> 'r f c'; 'Deleg. ó Mpio.' -> 'deleg o mpio'."""
    return re.sub(r"[^a-z0-9]+", " ", normalizar(etiqueta)).strip()


def _buscar(nombre, por_etiqueta):
    """Campo extraido cuya etiqueta corresponde al campo de EK9 (exacta o muy parecida)."""
    objetivo = _clave(nombre)
    if objetivo in por_etiqueta:
        return por_etiqueta[objetivo]
    parecidas = difflib.get_close_matches(objetivo, list(por_etiqueta), n=1, cutoff=0.85)
    return por_etiqueta[parecidas[0]] if parecidas else None


def a_campos_ek9(extraidos, campos_ocr=None):
    """Campos del extractor -> (campos [(nombre EK9, valor)], dudas) con el formato del portal.
    campos_ocr: lectura del OCR de Windows (ocr_ek9); de ahi salen las casillas y el Estatus General."""
    por_etiqueta = {}
    for c in extraidos:
        # null del modelo sin respaldo en el OCR: la etiqueta no esta en la imagen (ej. A. Paterno en moral)
        if c.get("valor_modelo") is None and not c.get("valor"):
            continue
        por_etiqueta.setdefault(_clave(c["etiqueta"]), c)
    ocr = dict(campos_ocr or [])
    campos, dudas, encontrados = [], [], set()
    for nombre, tipo, siempre in ocr_ek9.CAMPOS:
        if tipo in ("casilla", "opcion") and ocr.get(nombre):
            campos.append((nombre, ocr[nombre]))
            encontrados.add(nombre)
            continue
        if not siempre and ocr and nombre not in ocr:
            # Campo opcional (apellidos, Cemex): el modelo devuelve "" aunque la etiqueta no exista;
            # el OCR de Windows solo lo reporta si encontro la etiqueta en la pantalla
            continue
        c = _buscar(nombre, por_etiqueta)
        if nombre == "Estatus General" and c is None:
            # Botones de opcion: el modelo puede devolver cada opcion como casilla
            for opcion in ocr_ek9.OPCIONES_ESTATUS:
                o = por_etiqueta.get(_clave(opcion))
                if o and str(o["valor"]).lower() in ("true", "si", "sí"):
                    c = dict(o, valor=opcion)
        if c is None:
            if siempre:
                campos.append((nombre, ""))
            continue
        encontrados.add(nombre)
        valor = "" if c["valor"] is None else str(c["valor"])
        if tipo == "casilla":
            valor = "Sí" if valor.strip().lower() in ("true", "si", "sí", "x", "1") else "No"
        valor = re.sub(r"\s+", " ", valor).strip()
        if tipo == "numero":
            valor = re.sub(r"\D", "", valor)
        elif tipo == "rfc":
            valor = ocr_ek9.limpiar_rfc(valor)
        campos.append((nombre, valor))
        digitos = lambda v: re.sub(r"\D", "", str(v or ""))  # noqa: E731
        if tipo == "numero" and digitos(c.get("valor_modelo")) == digitos(c.get("valor_ocr")) == valor:
            continue  # solo difieren en texto vecino ("11570 Persona Física"): el numero coincide
        if c.get("revisar"):
            otra = c.get("valor_modelo") if c.get("valor_modelo") not in (None, "null", valor) else c.get("valor_ocr")
            dudas.append(f"Revisar {nombre}: {c.get('motivo') or 'no coincide con el OCR'}"
                         + (f" (otra lectura: '{otra}')" if otra and otra != valor else ""))
    return campos, dudas + ocr_ek9.dudas_de(campos, encontrados)


def leer_captura(contenido, extension=".png", campos_ocr=None):
    """bytes de la imagen -> (campos [(nombre, valor)], dudas). Lanza ErrorLocal.
    campos_ocr: lectura del OCR de Windows para las casillas y el Estatus General."""
    return resultado(extraer_json(contenido, extension), campos_ocr)


def resultado(datos, campos_ocr=None):
    """Respuesta del extractor (+ OCR de Windows) -> (campos [(nombre, valor)], dudas)."""
    campos, dudas = a_campos_ek9(datos["campos"], campos_ocr)
    return campos, [f"Lector local ({datos.get('motor_ocr', 'OCR')}, {datos.get('segundos', '?')} s)"
                    " - confirme lo marcado"] + dudas if dudas else dudas


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        with open(ruta, "rb") as f:
            contenido = f.read()
        campos, dudas = leer_captura(contenido, os.path.splitext(ruta)[1], ocr_ek9.leer_captura(contenido)[0])
        print(f"===== {ruta}")
        for nombre, valor in campos:
            print(f"  {nombre:20} {valor}")
        for d in dudas:
            print("  [REVISAR]", d)
