# -*- coding: utf-8 -*-
"""
portal.py
---------
Mini portal local (Flask) para el alta de proveedores y contratistas en EK10.

  - Se suben capturas de la pantalla de proveedores (EK9); cada una se convierte en el CSV
    CAMPO,VALOR y queda en el historial. Lector: OCR de Windows (ocr_ek9.py, por omision) o,
    con PORTAL_LECTOR=claude y ANTHROPIC_API_KEY, la API de Anthropic (extraer_imagen.py).
  - Por cada registro se marca si se dara de alta como Proveedor y/o como Contratista.
  - Se ejecuta en ese momento o despues desde el historial (modo prueba o real); el bot
    escribe en el CSV el "ID EK10" y el "ID Contratista EK10" de lo que se registra.

Datos en CARPETA_DATOS: carpetas imagenes y csv, y el archivo historial.db.
Uso:
  python portal.py                        -> abre http://localhost:5055
  python portal.py --importar carpeta ... -> registra en el historial los proveedor_*.csv existentes
"""

import json
import logging
import os
import re
import sqlite3
import sys
import glob
import subprocess
import tempfile
import threading
from datetime import datetime

from flask import Flask, abort, jsonify, render_template, request, send_file

import alta_contratistas
import alta_proveedores as ap
import consulta_proveedor
import explorar_formulario as ek
import extraer_gemini
import extraer_imagen as ei
import extraer_local
import ocr_ek9
from proveedor_csv import leer_archivo, normalizar

CONGELADO = getattr(sys, "frozen", False)
CARPETA_BASE = os.path.dirname(os.path.abspath(sys.executable if CONGELADO else __file__))
CARPETA_RECURSOS = getattr(sys, "_MEIPASS", CARPETA_BASE)  # templates empaquetados con PyInstaller
CARPETA_DATOS = os.environ.get("PORTAL_DATOS", os.path.join(CARPETA_BASE, "Datos"))
CARPETA_IMAGENES = os.path.join(CARPETA_DATOS, "imagenes")
CARPETA_CSV = os.path.join(CARPETA_DATOS, "csv")
BD = os.path.join(CARPETA_DATOS, "historial.db")
PUERTO = int(os.environ.get("PORTAL_PUERTO", "5055"))
# Campos que escribe el bot; no se editan desde el portal
CAMPOS_ID = ("id ek10", "id contratista ek10")
# Lector de imagenes:
#   "gemini" (por omision si hay GEMINI_API_KEY): Gemini + OCR de Windows en paralelo para
#            comparar los campos clave; si Gemini falla se usa el OCR.
#   "ocr"    : solo OCR de Windows (sin internet ni API key).
#   "claude" : API de Anthropic (requiere ANTHROPIC_API_KEY).
#   "local"  : Ollama qwen2.5vl + PaddleOCR del proyecto ExtraerInputsImagen (sin internet,
#              varios minutos por imagen en CPU) + OCR de Windows para casillas, Estatus General
#              y comparar los campos clave. Ver extraer_local.py.
#   "db"     : lee SOLO el numero de proveedor de la imagen (OCR de Windows) y trae el resto de
#              campos de la base de EK10 (sp_proveedores). Exacto y rapido. Requiere EK_DB_PASSWORD.
#              Ver consulta_proveedor.py.
LECTOR = os.environ.get("PORTAL_LECTOR", "gemini" if os.environ.get("GEMINI_API_KEY") else "ocr").strip().lower()
# Campos que se comparan entre Gemini y el OCR (con ellos se revisan duplicados y el catalogo de CP)
CAMPOS_CLAVE = ("Proveedor", "R.F.C.", "Código Postal")


def leer_imagen(contenido, extension):
    """bytes de la captura -> (campos [(campo, valor)], dudas). Lanza ValueError con el motivo."""
    if extension not in ei.TIPOS_IMAGEN:
        raise ValueError(f"Formato no soportado: {extension} (use png, jpg, gif o webp)")
    if LECTOR == "claude":
        try:
            captura = ei.extraer(contenido, extension)
        except ei.ErrorExtraccion as e:
            raise ValueError(str(e))
        return [(c.campo.strip(), c.valor.strip()) for c in captura.campos], list(captura.dudas)
    if LECTOR == "gemini":
        return leer_con_respaldo_ocr(contenido, extension, "Gemini",
                                     lambda: extraer_gemini.leer_captura(contenido, extension),
                                     extraer_gemini.ErrorGemini)
    if LECTOR == "local":
        # El modelo local solo lee los textos; casillas y Estatus General salen del OCR de Windows
        return leer_con_respaldo_ocr(contenido, extension, "El lector local",
                                     lambda: extraer_local.extraer_json(contenido, extension),
                                     extraer_local.ErrorLocal, extraer_local.resultado)
    if LECTOR == "db":
        return leer_desde_base(contenido, extension)
    return ocr_en_proceso_aparte(contenido, extension)


def leer_desde_base(contenido, extension):
    """Lee solo el numero de proveedor de la imagen (OCR) y trae el resto de la base de EK10.
    Si la base falla, cae al OCR completo de Windows avisando que revise todo."""
    try:
        campos_ocr, dudas_ocr = ocr_en_proceso_aparte(contenido, extension)
    except ValueError as e:
        raise ValueError(f"No se pudo leer el numero de proveedor de la imagen: {e}")
    numero = re.sub(r"\D", "", dict(campos_ocr).get("Proveedor", ""))
    if not numero:
        raise ValueError("No se encontro el numero de proveedor en la imagen; suba una captura mas clara.")
    try:
        return consulta_proveedor.leer_proveedor(numero)
    except consulta_proveedor.ErrorConsulta as e:
        log.warning("Base EK10 no disponible para el proveedor %s (%s); se usa el OCR de Windows.", numero, e)
        return campos_ocr, [f"No se consulto la base ({e}); datos leidos por OCR, revise todos"] + dudas_ocr


def leer_con_respaldo_ocr(contenido, extension, nombre, leer, error, convertir=lambda datos, _: datos):
    """Lector principal (Gemini o local) con el OCR de Windows en paralelo como control y respaldo.
    leer() -> datos del lector (lanza `error`); convertir(datos, campos_ocr) -> (campos, dudas)."""
    resultado_ocr = {}

    def ocr():
        try:
            resultado_ocr["datos"] = ocr_en_proceso_aparte(contenido, extension)
        except ValueError as e:
            resultado_ocr["error"] = str(e)

    hilo = threading.Thread(target=ocr, daemon=True)
    hilo.start()
    try:
        datos = leer()
    except error as e:
        hilo.join()
        if "datos" not in resultado_ocr:
            raise ValueError(f"{nombre}: {e} | OCR: {resultado_ocr.get('error', 'sin resultado')}")
        log.warning("%s no respondio (%s); se usa el OCR de Windows.", nombre, e)
        campos, dudas = resultado_ocr["datos"]
        return campos, [f"Se uso el OCR de Windows porque {nombre} no respondio ({e}); revise todos los datos"] + dudas
    hilo.join()
    campos_ocr = resultado_ocr["datos"][0] if "datos" in resultado_ocr else []
    campos, dudas = convertir(datos, campos_ocr)
    leidos_ocr, valores = dict(campos_ocr), dict(campos)
    for campo in CAMPOS_CLAVE:
        a, b = valores.get(campo, ""), leidos_ocr.get(campo, "")
        if a and b and a != b:
            dudas.insert(0, f"Verifique {campo}: {nombre} leyo '{a}' y el OCR '{b}'")
    return campos, dudas


# El OCR de Windows (WinRT) no convive con Selenium/Flask en el mismo proceso: usarlo mientras corre
# un bot tumbaba el portal (codigo 139). Por eso corre en un proceso aparte. Antes se arrancaba el
# .exe entero en cada imagen (unos 13 s de desempaquetado del onefile + imports); ahora se mantiene
# UN worker vivo (--ocr-server) que carga una sola vez y atiende cada imagen por stdin/stdout (~2 s).
_ocr_worker = None
_ocr_lock = threading.Lock()


def _cmd_worker():
    return [sys.executable, "--ocr-server"] if CONGELADO else [sys.executable, os.path.abspath(__file__), "--ocr-server"]


def _asegurar_worker():
    """Devuelve el worker de OCR vivo; lo arranca (o reinicia si murio). Usar bajo _ocr_lock."""
    global _ocr_worker
    if _ocr_worker is None or _ocr_worker.poll() is not None:
        _ocr_worker = subprocess.Popen(_cmd_worker(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, bufsize=0,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log.info("Worker de OCR iniciado (pid %s).", _ocr_worker.pid)
    return _ocr_worker


def _leer_linea_con_timeout(proc, timeout):
    """Lee una linea del stdout del worker con limite de tiempo. None si se agoto (worker colgado)."""
    import queue
    cola = queue.Queue()
    threading.Thread(target=lambda: cola.put(proc.stdout.readline()), daemon=True).start()
    try:
        return cola.get(timeout=timeout)
    except queue.Empty:
        return None


def ocr_en_proceso_aparte(contenido, extension, _reintento=False):
    """Lee la imagen con el worker de OCR persistente y devuelve (campos, dudas)."""
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
        f.write(contenido)
        ruta = f.name
    try:
        with _ocr_lock:
            worker = _asegurar_worker()
            try:
                worker.stdin.write((ruta + "\n").encode("utf-8"))
                worker.stdin.flush()
                linea = _leer_linea_con_timeout(worker, 180)
            except (BrokenPipeError, OSError):
                linea = b""
    finally:
        try:
            os.remove(ruta)
        except OSError:
            pass
    if linea is None:  # el worker se colgo: matarlo para que el siguiente intento lo reinicie
        with _ocr_lock:
            _terminar_worker()
        raise ValueError("La lectura de la imagen tardo demasiado")
    if not linea:  # el worker murio: reiniciarlo y reintentar una vez
        if _reintento:
            raise ValueError("No se pudo leer la imagen (el lector de OCR se detuvo)")
        log.warning("El worker de OCR se detuvo; se reinicia y se reintenta.")
        return ocr_en_proceso_aparte(contenido, extension, _reintento=True)
    try:
        datos = json.loads(linea.decode("utf-8", "replace").strip())
    except ValueError:
        raise ValueError("No se pudo leer la imagen (respuesta invalida del OCR)")
    if datos.get("error"):
        raise ValueError(datos["error"])
    return [tuple(c) for c in datos["campos"]], datos["dudas"]


def _terminar_worker():
    """Detiene el worker de OCR (al cerrar el portal o si se colgo). Usar bajo _ocr_lock."""
    global _ocr_worker
    if _ocr_worker is not None and _ocr_worker.poll() is None:
        try:
            _ocr_worker.kill()
        except OSError:
            pass
    _ocr_worker = None


def precalentar_ocr():
    """Arranca el worker y le hace una lectura en blanco para que la primera subida real sea rapida."""
    try:
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            Image.new("RGB", (200, 60), "white").save(f.name)
            ruta = f.name
        try:
            ocr_en_proceso_aparte(open(ruta, "rb").read(), ".png")
        finally:
            os.remove(ruta)
        log.info("Worker de OCR precalentado.")
    except Exception as e:  # el precalentado nunca debe tumbar el portal
        log.warning("No se pudo precalentar el OCR: %s", e)


def ocr_servidor():
    """Modo --ocr-server: carga el OCR una vez y atiende, por cada linea de stdin (ruta de imagen),
    una linea JSON en stdout. Termina al cerrarse stdin."""
    salida = sys.stdout.buffer
    for linea in sys.stdin.buffer:
        ruta = linea.decode("utf-8", "replace").strip()
        if not ruta:
            continue
        try:
            with open(ruta, "rb") as f:
                campos, dudas = ocr_ek9.leer_captura(f.read())
            respuesta = {"campos": campos, "dudas": dudas}
        except (ocr_ek9.ErrorOCR, OSError) as e:
            respuesta = {"error": str(e)}
        except Exception as e:  # un fallo en una imagen no debe tumbar el worker
            respuesta = {"error": f"Error inesperado al leer la imagen: {e}"}
        salida.write((json.dumps(respuesta, ensure_ascii=False) + "\n").encode("utf-8"))
        salida.flush()


def ocr_desde_linea_de_comandos(ruta):
    """Modo --ocr: lee UNA imagen y escribe una linea JSON en stdout (uso suelto, sin worker)."""
    try:
        with open(ruta, "rb") as f:
            campos, dudas = ocr_ek9.leer_captura(f.read())
        print(json.dumps({"campos": campos, "dudas": dudas}))
    except (ocr_ek9.ErrorOCR, OSError) as e:
        print(json.dumps({"error": str(e)}))

app = Flask(__name__, template_folder=os.path.join(CARPETA_RECURSOS, "templates"))
app.json.sort_keys = False
log = ap.log


# =============================================================================
# HISTORIAL (SQLite)
# =============================================================================
def conexion():
    con = sqlite3.connect(BD)
    con.row_factory = sqlite3.Row
    return con


def iniciar_bd():
    for carpeta in (CARPETA_IMAGENES, CARPETA_CSV):
        os.makedirs(carpeta, exist_ok=True)
    with conexion() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor TEXT,
                nombre TEXT,
                imagen TEXT,
                csv TEXT NOT NULL,
                dudas TEXT DEFAULT '[]',
                quiere_proveedor INTEGER DEFAULT 1,
                quiere_contratista INTEGER DEFAULT 0,
                res_proveedor TEXT DEFAULT '',
                res_contratista TEXT DEFAULT '',
                creado TEXT,
                actualizado TEXT
            )""")
        # en_historial = 0: imagen recien subida, pendiente de revisar en el paso 1
        columnas = {c["name"] for c in con.execute("PRAGMA table_info(registros)")}
        if "en_historial" not in columnas:
            con.execute("ALTER TABLE registros ADD COLUMN en_historial INTEGER DEFAULT 1")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def registro_json(fila, con_campos=False):
    """Fila de la BD + lo que dice el CSV en este momento (IDs, tipo de persona, clave)."""
    r = dict(fila)
    r["dudas"] = json.loads(r.get("dudas") or "[]")
    r.update(tipo_persona="", clave_proveedor="", id_ek10="", id_contratista="", faltantes=[], error_csv="")
    try:
        p = leer_archivo(r["csv"])
        c = p["campos"]
        r.update(tipo_persona=p["tipo_persona"], clave_proveedor=p["clave"], faltantes=p["faltantes"],
                 id_ek10=c.get("id ek10", ""), id_contratista=c.get("id contratista ek10", ""))
        if con_campos:
            r["campos"] = [[p["etiquetas"][k], v] for k, v in c.items() if k not in CAMPOS_ID]
    except (OSError, ValueError) as e:
        r["error_csv"] = str(e)
    r["archivo_csv"] = os.path.basename(r["csv"])
    return r


def obtener(id_registro):
    with conexion() as con:
        fila = con.execute("SELECT * FROM registros WHERE id = ?", (id_registro,)).fetchone()
    if fila is None:
        abort(404)
    return fila


# =============================================================================
# PAGINA Y API
# =============================================================================
@app.get("/")
def inicio():
    falta_api_key = LECTOR == "claude" and not os.environ.get("ANTHROPIC_API_KEY")
    return render_template("portal.html", falta_api_key=falta_api_key, carpeta_datos=CARPETA_DATOS,
                           lector={"claude": "Claude (API de Anthropic)",
                                   "gemini": f"Gemini ({extraer_gemini.MODELO}) + OCR de Windows",
                                   "local": extraer_local.DESCRIPCION,
                                   "db": f"Base EK10 {consulta_proveedor.BASE} (numero por OCR + datos de sp_proveedores)"}
                           .get(LECTOR, "OCR de Windows"))


@app.get("/api/registros")
def listar():
    with conexion() as con:
        filas = con.execute("SELECT * FROM registros ORDER BY id DESC").fetchall()
    return jsonify([registro_json(f) for f in filas])


@app.get("/api/registros/<int:id_registro>")
def detalle(id_registro):
    return jsonify(registro_json(obtener(id_registro), con_campos=True))


@app.post("/api/imagenes")
def subir_imagen():
    """Recibe una imagen, la convierte en CSV y crea (o actualiza) su registro."""
    archivo = request.files.get("imagen")
    if archivo is None or not archivo.filename:
        return jsonify(error="No se recibio la imagen"), 400
    extension = os.path.splitext(archivo.filename)[1].lower()
    contenido = archivo.read()
    try:
        campos, dudas = leer_imagen(contenido, extension)
    except ValueError as e:
        return jsonify(error=str(e)), 422
    try:
        p = ei.validar(campos)
    except ValueError as e:
        return jsonify(error=f"La imagen no parece ser de un proveedor: {e}"), 422
    numero = p["campos"].get("proveedor", "")

    with conexion() as con:
        previo = con.execute("SELECT * FROM registros WHERE proveedor = ? AND proveedor <> ''",
                             (numero,)).fetchone() if numero else None
        if previo is not None:
            r = registro_json(previo)
            if r["id_ek10"] or r["id_contratista"]:
                # Ya se dio de alta algo con ese CSV: no se pisa
                r["aviso"] = f"El proveedor {numero} ya esta en el historial y tiene IDs de EK10; no se modifico."
                return jsonify(r)
        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_imagen = os.path.join(CARPETA_IMAGENES, f"{sello}_{os.path.basename(archivo.filename)}")
        with open(ruta_imagen, "wb") as f:
            f.write(contenido)
        ruta_csv = previo["csv"] if previo is not None else os.path.join(CARPETA_CSV, ei.nombre_archivo(campos))
        ei.escribir_csv(ruta_csv, campos)
        datos = (numero, p["campos"].get("nombre", ""), ruta_imagen, ruta_csv,
                 json.dumps(dudas, ensure_ascii=False), ahora())
        # La imagen nueva (o releida) queda en el paso 1 hasta que se agregue al historial
        if previo is not None:
            con.execute("UPDATE registros SET proveedor=?, nombre=?, imagen=?, csv=?, dudas=?, actualizado=?,"
                        " res_proveedor='', res_contratista='', en_historial=0 WHERE id=?", datos + (previo["id"],))
            id_registro = previo["id"]
        else:
            id_registro = con.execute(
                "INSERT INTO registros (proveedor, nombre, imagen, csv, dudas, actualizado, creado, en_historial)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0)", datos + (ahora(),)).lastrowid
    log.info("Portal: imagen %s -> %s", archivo.filename, ruta_csv)
    r = registro_json(obtener(id_registro), con_campos=True)
    if previo is not None:
        r["aviso"] = f"El proveedor {numero} ya estaba en el historial; se actualizo su CSV."
    return jsonify(r)


@app.put("/api/registros/<int:id_registro>")
def guardar_registro(id_registro):
    """Guarda las casillas Proveedor/Contratista, el paso (en_historial) y, si vienen, los campos del CSV."""
    fila = obtener(id_registro)
    datos = request.get_json(force=True) or {}
    if "campos" in datos:
        actual = registro_json(fila)
        campos = [(str(c).strip(), str(v).strip()) for c, v in datos["campos"]
                  if str(c).strip() and normalizar(str(c)) not in CAMPOS_ID]
        # Los IDs que escribio el bot se conservan
        campos += [(etiqueta, valor) for etiqueta, valor in
                   (("ID EK10", actual["id_ek10"]), ("ID Contratista EK10", actual["id_contratista"])) if valor]
        try:
            ei.validar(campos)
        except ValueError as e:
            return jsonify(error=str(e)), 422
        ei.escribir_csv(fila["csv"], campos)
    with conexion() as con:
        for campo in ("quiere_proveedor", "quiere_contratista", "en_historial"):
            if campo in datos:
                con.execute(f"UPDATE registros SET {campo} = ? WHERE id = ?", (int(bool(datos[campo])), id_registro))
        con.execute("UPDATE registros SET actualizado = ? WHERE id = ?", (ahora(), id_registro))
    return jsonify(registro_json(obtener(id_registro), con_campos=True))


@app.delete("/api/registros/<int:id_registro>")
def borrar_registro(id_registro):
    """
    Quita el registro. Del historial se conservan los archivos; una imagen descartada en el
    paso 1 (nunca agregada al historial y sin IDs de EK10) borra tambien su CSV e imagen.
    """
    fila = obtener(id_registro)
    r = registro_json(fila)
    with conexion() as con:
        con.execute("DELETE FROM registros WHERE id = ?", (id_registro,))
    if not fila["en_historial"] and not (r["id_ek10"] or r["id_contratista"]):
        for ruta in (fila["csv"], fila["imagen"]):
            # Solo archivos del portal (no CSV importados de otras carpetas)
            if ruta and os.path.abspath(ruta).startswith(os.path.abspath(CARPETA_DATOS)):
                try:
                    os.remove(ruta)
                except OSError:
                    pass
    return jsonify(ok=True)


@app.get("/imagen/<int:id_registro>")
def ver_imagen(id_registro):
    fila = obtener(id_registro)
    if not fila["imagen"] or not os.path.exists(fila["imagen"]):
        abort(404)
    return send_file(fila["imagen"])


@app.get("/csv/<int:id_registro>")
def descargar_csv(id_registro):
    fila = obtener(id_registro)
    return send_file(fila["csv"], as_attachment=True, download_name=os.path.basename(fila["csv"]))


# =============================================================================
# EJECUCION DE LOS BOTS (un trabajo a la vez, en segundo plano)
# =============================================================================
class Trabajo:
    candado = threading.Lock()
    activo = False
    estado = {"activo": False, "inicio": "", "fin": "", "modo": "", "lineas": [], "resultados": []}


class CapturaLog(logging.Handler):
    def emit(self, record):
        Trabajo.estado["lineas"].append(self.format(record))


def ejecutar_trabajo(ids_proveedor, ids_contratista, guardar, ids_verificar=()):
    manejador = CapturaLog()
    manejador.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"))
    log.addHandler(manejador)
    resultados = Trabajo.estado["resultados"]
    try:
        with conexion() as con:
            filas = {f["id"]: f for f in con.execute("SELECT * FROM registros").fetchall()}

        def anotar(campo, ids, resumen, etiqueta):
            for id_registro, (_, estatus) in zip(ids, resumen):
                with conexion() as con:
                    con.execute(f"UPDATE registros SET {campo} = ?, actualizado = ? WHERE id = ?",
                                (f"{ahora()} {estatus}", ahora(), id_registro))
                resultados.append({"id": id_registro, "paso": etiqueta, "estatus": estatus})

        if ids_verificar:
            resumen = ap.ejecutar([filas[i]["csv"] for i in ids_verificar], solo_verificar=True)
            anotar("res_proveedor", ids_verificar, resumen, "Verificar")
        if ids_proveedor:
            resumen = ap.ejecutar([filas[i]["csv"] for i in ids_proveedor], guardar)
            anotar("res_proveedor", ids_proveedor, resumen, "Proveedor")
        if ids_contratista:
            # Solo los que ya tienen ID EK10 (puede haberse escrito en el paso anterior)
            listos, sin_id = [], []
            for i in ids_contratista:
                (listos if registro_json(filas[i])["id_ek10"] else sin_id).append(i)
            anotar("res_contratista", sin_id, [("", "SIN ID EK10 (falta el alta del proveedor)")] * len(sin_id),
                   "Contratista")
            if listos:
                resumen = alta_contratistas.ejecutar([filas[i]["csv"] for i in listos], guardar)
                anotar("res_contratista", listos, resumen, "Contratista")
    except Exception as e:  # el hilo no debe morir sin avisar al portal
        log.exception("Error en el trabajo: %s", e)
        resultados.append({"id": None, "paso": "Trabajo", "estatus": f"ERROR: {e}"})
    finally:
        log.removeHandler(manejador)
        Trabajo.estado.update(activo=False, fin=ahora())
        Trabajo.activo = False


@app.post("/api/ejecutar")
def ejecutar():
    datos = request.get_json(force=True) or {}
    ids_proveedor = [int(i) for i in datos.get("proveedor", [])]
    ids_contratista = [int(i) for i in datos.get("contratista", [])]
    ids_verificar = [int(i) for i in datos.get("verificar", [])]
    guardar = bool(datos.get("guardar"))
    # Solo se dan de alta registros del historial (no lo pendiente de revisar en el paso 1);
    # verificar en EK10 se permite tambien en el paso 1 porque no crea nada
    with conexion() as con:
        en_historial = {f["id"] for f in con.execute("SELECT id FROM registros WHERE en_historial = 1")}
    ids_proveedor = [i for i in ids_proveedor if i in en_historial]
    ids_contratista = [i for i in ids_contratista if i in en_historial]
    if not ids_proveedor and not ids_contratista and not ids_verificar:
        return jsonify(error="No hay registros seleccionados"), 400
    if not (ek.Config.USUARIO and ek.Config.PASSWORD):
        return jsonify(error="Sin credenciales de EK10 (EKLOUD_USUARIO / EKLOUD_PASSWORD)"), 400
    with Trabajo.candado:
        if Trabajo.activo:
            return jsonify(error="Ya hay una ejecucion en curso"), 409
        Trabajo.activo = True
        Trabajo.estado = {"activo": True, "inicio": ahora(), "fin": "", "lineas": [], "resultados": [],
                          "modo": "VERIFICAR" if ids_verificar and not (ids_proveedor or ids_contratista)
                          else "REAL" if guardar else "PRUEBA"}
    threading.Thread(target=ejecutar_trabajo, args=(ids_proveedor, ids_contratista, guardar, ids_verificar),
                     daemon=True).start()
    return jsonify(Trabajo.estado)


@app.get("/api/trabajo")
def trabajo():
    desde = request.args.get("desde", 0, type=int)
    estado = dict(Trabajo.estado)
    estado["total_lineas"] = len(estado["lineas"])
    estado["lineas"] = estado["lineas"][desde:]
    return jsonify(estado)


def importar(carpetas):
    """Registra en el historial CSV existentes (en su ubicacion actual), con la imagen
    <numero>*.png/jpg de la misma carpeta si la hay. Los que ya estan registrados se omiten."""
    with conexion() as con:
        existentes = {os.path.normcase(f["csv"]) for f in con.execute("SELECT csv FROM registros")}
        for carpeta in carpetas:
            for ruta in sorted(glob.glob(os.path.join(carpeta, "**", "proveedor_*.csv"), recursive=True)):
                ruta = os.path.abspath(ruta)
                if os.path.normcase(ruta) in existentes:
                    continue
                try:
                    c = leer_archivo(ruta)["campos"]
                except (OSError, ValueError) as e:
                    log.warning("No se importa %s: %s", ruta, e)
                    continue
                numero = c.get("proveedor", "")
                imagen = next((i for i in glob.glob(os.path.join(os.path.dirname(ruta), f"{numero}*"))
                               if os.path.splitext(i)[1].lower() in ei.TIPOS_IMAGEN), "") if numero else ""
                con.execute("INSERT INTO registros (proveedor, nombre, imagen, csv, quiere_proveedor,"
                            " creado, actualizado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (numero, c.get("nombre", ""), imagen, ruta, int(not c.get("id ek10")), ahora(), ahora()))
                log.info("Importado al historial: %s", ruta)


def dueno_del_puerto(puerto):
    """PID que escucha en 127.0.0.1:<puerto> (netstat) o None."""
    salida = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) >= 5 and partes[1].endswith(f":{puerto}") and partes[3] == "LISTENING":
            return int(partes[4])
    return None


def liberar_puerto(puerto):
    """
    True si el puerto queda libre. Si un portal anterior se cayo, sus hijos (chromedriver/Chrome
    de un bot a medias) heredan el socket y lo mantienen ocupado: se cierran esos huerfanos.
    Si hay un portal vivo, no se toca y se devuelve False.
    """
    pid = dueno_del_puerto(puerto)
    if pid is None:
        return True
    vivo = str(pid) in subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True,
                                      text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    if vivo:
        return False
    log.warning("El puerto %d lo retienen procesos huerfanos de un portal anterior (PID %d); se cierran.", puerto, pid)
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"$h = Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq {pid} }};"
                    " foreach ($p in $h) { Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $p.ProcessId }"
                    " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };"
                    " Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }"],
                   capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return dueno_del_puerto(puerto) is None


def main():
    if "--ocr-server" in sys.argv:
        ocr_servidor()
        return
    if "--ocr" in sys.argv:
        ocr_desde_linea_de_comandos(sys.argv[sys.argv.index("--ocr") + 1])
        return
    ap.configurar_log()
    iniciar_bd()
    if "--importar" in sys.argv:
        importar([a for a in sys.argv[sys.argv.index("--importar") + 1:] if not a.startswith("--")])
        return
    if not liberar_puerto(PUERTO):
        log.warning("Ya hay un portal abierto en http://localhost:%d; se usa ese.", PUERTO)
        if "--sin-navegador" not in sys.argv:
            __import__("webbrowser").open(f"http://localhost:{PUERTO}")
        return
    log.info("Portal en http://localhost:%d (datos en %s)", PUERTO, CARPETA_DATOS)
    if "--sin-navegador" not in sys.argv:
        threading.Timer(1.5, lambda: __import__("webbrowser").open(f"http://localhost:{PUERTO}")).start()
    # El OCR corre en un worker aparte; se precalienta en segundo plano para que la primera subida
    # no pague el arranque. En modo "gemini"/"ocr"/"local"/"db" ese worker lee la captura.
    if LECTOR != "claude":
        threading.Thread(target=precalentar_ocr, daemon=True).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=False, threaded=True)


if __name__ == "__main__":
    main()
