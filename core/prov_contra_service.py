"""
Core Domain: Servicio Unificado de Proveedores y Contratistas (EK10 / Aryve).
Integra consultas a Enkontrol (sp_proveedores), extracción de capturas (OCR/Gemini/DB),
gestión de cola/historial (SQLite vertical CSV) y ejecución automatizada con Selenium.
"""

import os
import sys
import re
import json
import io
import time
import shutil
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROV_CONTRA_DIR = os.path.join(BASE_DIR, "PROVEEDORES_CONTRATISTAS", "AltaProveedores")

if PROV_CONTRA_DIR not in sys.path:
    sys.path.insert(0, PROV_CONTRA_DIR)

# Importar submódulos de AltaProveedores de forma segura
try:
    import alta_proveedores as ap
    import alta_contratistas as ac
    import consulta_proveedor as cp
    import extraer_imagen as ei
    from proveedor_csv import leer_archivo, normalizar, decodificar
except Exception as e:
    print(f"[ProvContraService] Advertencia importando módulos base de AltaProveedores: {e}")

CARPETA_DATOS = os.path.join(PROV_CONTRA_DIR, "Datos")
CARPETA_IMAGENES = os.path.join(CARPETA_DATOS, "imagenes")
CARPETA_CSV = os.path.join(CARPETA_DATOS, "csv")
BD_PATH = os.path.join(CARPETA_DATOS, "historial.db")
CAMPOS_ID = ("id ek10", "id contratista ek10")


class TrabajoProvContra:
    candado = threading.Lock()
    activo = False
    estado: Dict[str, Any] = {
        "activo": False,
        "inicio": "",
        "fin": "",
        "modo": "",
        "lineas": [],
        "resultados": [],
        "total_lineas": 0
    }


class CapturaLogHandler(logging.Handler):
    def emit(self, record):
        linea = self.format(record)
        TrabajoProvContra.estado["lineas"].append(linea)


class ProvContraService:
    _lock = threading.Lock()

    @classmethod
    def iniciar_bd(cls):
        """Inicializa directorios y tablas SQLite."""
        os.makedirs(CARPETA_IMAGENES, exist_ok=True)
        os.makedirs(CARPETA_CSV, exist_ok=True)
        with cls.conexion() as con:
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
                    actualizado TEXT,
                    en_historial INTEGER DEFAULT 1
                )
            """)
            columnas = {c["name"] for c in con.execute("PRAGMA table_info(registros)")}
            if "en_historial" not in columnas:
                con.execute("ALTER TABLE registros ADD COLUMN en_historial INTEGER DEFAULT 1")

    @classmethod
    def conexion(cls) -> sqlite3.Connection:
        con = sqlite3.connect(BD_PATH, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    @classmethod
    def _ahora(cls) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def registro_a_json(cls, fila, con_campos: bool = False) -> Dict[str, Any]:
        """Convierte una fila de la BD y la enriquece con datos del CSV."""
        r = dict(fila)
        try:
            r["dudas"] = json.loads(r.get("dudas") or "[]")
        except Exception:
            r["dudas"] = []

        r.update({
            "tipo_persona": "",
            "clave_proveedor": "",
            "id_ek10": "",
            "id_contratista": "",
            "faltantes": [],
            "error_csv": "",
            "rfc": "",
            "calle": "",
            "cp": "",
            "colonia": ""
        })

        if r.get("csv") and os.path.exists(r["csv"]):
            try:
                p = leer_archivo(r["csv"])
                c = p.get("campos", {})
                r.update({
                    "tipo_persona": p.get("tipo_persona", "MORAL"),
                    "clave_proveedor": p.get("clave", ""),
                    "faltantes": p.get("faltantes", []),
                    "id_ek10": c.get("id ek10", ""),
                    "id_contratista": c.get("id contratista ek10", ""),
                    "rfc": c.get("rfc", ""),
                    "calle": c.get("calle", ""),
                    "cp": c.get("codigo postal", ""),
                    "colonia": c.get("colonia", "")
                })
                if con_campos:
                    r["campos"] = [[p["etiquetas"].get(k, k), v] for k, v in c.items() if k not in CAMPOS_ID]
            except Exception as e:
                r["error_csv"] = str(e)

        r["archivo_csv"] = os.path.basename(r.get("csv", ""))
        r["tiene_imagen"] = bool(r.get("imagen") and os.path.exists(r["imagen"]))
        return r

    @classmethod
    def obtener_todos(cls) -> List[Dict[str, Any]]:
        """Lista todos los registros ordenados por id descendente."""
        cls.iniciar_bd()
        with cls.conexion() as con:
            filas = con.execute("SELECT * FROM registros ORDER BY id DESC").fetchall()
        return [cls.registro_a_json(f) for f in filas]

    @classmethod
    def obtener_por_id(cls, id_registro: int, con_campos: bool = True) -> Optional[Dict[str, Any]]:
        cls.iniciar_bd()
        with cls.conexion() as con:
            fila = con.execute("SELECT * FROM registros WHERE id = ?", (id_registro,)).fetchone()
        if fila:
            return cls.registro_a_json(fila, con_campos=con_campos)
        return None

    @classmethod
    def consultar_base_ek10(cls, numpro: str) -> Dict[str, Any]:
        """
        Consulta Enkontrol directamente por número de proveedor (sp_proveedores),
        genera el CSV vertical oficial y lo inserta en el historial / pre-registro.
        """
        cls.iniciar_bd()
        num_clean = re.sub(r"\D", "", str(numpro))
        if not num_clean:
            raise ValueError("El número de proveedor debe contener dígitos válidos.")

        # Consultar en SQL Anywhere
        campos, dudas = cp.leer_proveedor(num_clean)
        p = ei.validar(campos)

        numero = p["campos"].get("proveedor", num_clean)
        nombre = p["campos"].get("nombre", f"PROVEEDOR {numero}")

        with cls.conexion() as con:
            previo = con.execute("SELECT * FROM registros WHERE proveedor = ? AND proveedor <> ''", (numero,)).fetchone()
            if previo is not None:
                r = cls.registro_a_json(previo)
                if r.get("id_ek10") or r.get("id_contratista"):
                    r["aviso"] = f"El proveedor {numero} ya existe en el historial con IDs asignados (ID EK10: {r.get('id_ek10')})."
                    return r

            ruta_csv = previo["csv"] if previo is not None else os.path.join(CARPETA_CSV, ei.nombre_archivo(campos))
            ei.escribir_csv(ruta_csv, campos)

            datos = (
                numero,
                nombre,
                "",  # sin imagen porque viene de DB directa
                ruta_csv,
                json.dumps(dudas, ensure_ascii=False),
                cls._ahora()
            )

            if previo is not None:
                con.execute(
                    "UPDATE registros SET proveedor=?, nombre=?, imagen=?, csv=?, dudas=?, actualizado=?,"
                    " res_proveedor='', res_contratista='', en_historial=1 WHERE id=?",
                    datos + (previo["id"],)
                )
                id_reg = previo["id"]
            else:
                id_reg = con.execute(
                    "INSERT INTO registros (proveedor, nombre, imagen, csv, dudas, actualizado, creado, en_historial, quiere_proveedor, quiere_contratista)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1)",
                    datos + (cls._ahora(),)
                ).lastrowid

        res = cls.obtener_por_id(id_reg, con_campos=True)
        if res:
            res["mensaje"] = f"Proveedor {numero} consultado exitosamente desde la base de datos de Enkontrol."
        return res or {}

    @classmethod
    def procesar_captura(cls, contenido_bytes: bytes, filename: str, lector: str = "db") -> Dict[str, Any]:
        """
        Lee una captura de pantalla EK9, extrae campos según lector (db, gemini, ocr),
        guarda la imagen y el CSV, y registra en la BD.
        """
        cls.iniciar_bd()
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ei.TIPOS_IMAGEN:
            raise ValueError(f"Formato de imagen no soportado: {ext}. Utilice PNG, JPG, JPEG o WEBP.")

        # Lector
        lector = lector.lower().strip()
        campos, dudas = [], []

        if lector == "db":
            # Lee número de proveedor con OCR y resto de la base
            campos, dudas = cp.leer_desde_base(contenido_bytes, ext) if hasattr(cp, "leer_desde_base") else cls._leer_con_ocr_y_db(contenido_bytes, ext)
        elif lector == "gemini":
            try:
                import extraer_gemini as eg
                campos, dudas = eg.leer_captura(contenido_bytes, ext)
            except Exception as e_gem:
                dudas.append(f"Fallo en Gemini ({e_gem}), recurriendo a OCR local...")
                import ocr_ek9
                campos, _ = ocr_ek9.leer_imagen(contenido_bytes, ext)
        else:
            import ocr_ek9
            campos, dudas = ocr_ek9.leer_imagen(contenido_bytes, ext)

        p = ei.validar(campos)
        numero = p["campos"].get("proveedor", "")
        nombre = p["campos"].get("nombre", "")

        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_imagen = os.path.join(CARPETA_IMAGENES, f"{sello}_{os.path.basename(filename)}")
        with open(ruta_imagen, "wb") as f:
            f.write(contenido_bytes)

        ruta_csv = os.path.join(CARPETA_CSV, ei.nombre_archivo(campos))
        ei.escribir_csv(ruta_csv, campos)

        with cls.conexion() as con:
            id_reg = con.execute(
                "INSERT INTO registros (proveedor, nombre, imagen, csv, dudas, actualizado, creado, en_historial, quiere_proveedor, quiere_contratista)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1, 0)",
                (numero, nombre, ruta_imagen, ruta_csv, json.dumps(dudas, ensure_ascii=False), cls._ahora(), cls._ahora())
            ).lastrowid

        return cls.obtener_por_id(id_reg, con_campos=True) or {}

    @classmethod
    def _leer_con_ocr_y_db(cls, contenido_bytes: bytes, ext: str) -> Tuple[List[Any], List[str]]:
        """Fallback: lee numpro de OCR y consulta DB."""
        import ocr_ek9
        campos_ocr, _ = ocr_ek9.leer_imagen(contenido_bytes, ext)
        numpro = next((v for k, v in campos_ocr if normalizar(k) == "proveedor"), "")
        if numpro and re.sub(r"\D", "", numpro):
            try:
                return cp.leer_proveedor(numpro)
            except Exception as e:
                return campos_ocr, [f"No se pudo consultar DB ({e}); se utilizó OCR directo."]
        return campos_ocr, ["No se detectó número de proveedor; se utilizó OCR directo."]

    @classmethod
    def guardar_registro(cls, id_registro: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza campos, casillas o estado de historial."""
        fila = cls.obtener_por_id(id_registro, con_campos=True)
        if not fila:
            raise ValueError(f"Registro {id_registro} no encontrado.")

        if "campos" in payload and payload["campos"]:
            campos = [(str(c).strip(), str(v).strip()) for c, v in payload["campos"]
                      if str(c).strip() and normalizar(str(c)) not in CAMPOS_ID]
            # Conservar IDs previos
            if fila.get("id_ek10"):
                campos.append(("ID EK10", fila["id_ek10"]))
            if fila.get("id_contratista"):
                campos.append(("ID Contratista EK10", fila["id_contratista"]))

            ei.validar(campos)
            ei.escribir_csv(fila["csv"], campos)

        with cls.conexion() as con:
            for campo in ("quiere_proveedor", "quiere_contratista", "en_historial"):
                if campo in payload:
                    con.execute(f"UPDATE registros SET {campo} = ? WHERE id = ?", (int(bool(payload[campo])), id_registro))
            con.execute("UPDATE registros SET actualizado = ? WHERE id = ?", (cls._ahora(), id_registro))

        return cls.obtener_por_id(id_registro, con_campos=True) or {}

    @classmethod
    def eliminar_registro(cls, id_registro: int) -> bool:
        fila = cls.obtener_por_id(id_registro)
        if not fila:
            return False

        with cls.conexion() as con:
            con.execute("DELETE FROM registros WHERE id = ?", (id_registro,))

        # Si no tenía ID en EK10, podemos limpiar archivos de prueba
        if not fila.get("id_ek10") and not fila.get("id_contratista"):
            for ruta in (fila.get("csv"), fila.get("imagen")):
                if ruta and os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except Exception:
                        pass
        return True

    @classmethod
    def iniciar_trabajo(cls, ids_proveedor: List[int], ids_contratista: List[int], guardar: bool = False, ids_verificar: List[int] = None) -> Dict[str, Any]:
        """Inicia el bot Selenium en segundo plano con captura de logs en vivo."""
        ids_verificar = ids_verificar or []
        with TrabajoProvContra.candado:
            if TrabajoProvContra.activo:
                raise RuntimeError("Ya hay una automatización en ejecución.")

            TrabajoProvContra.activo = True
            TrabajoProvContra.estado = {
                "activo": True,
                "inicio": cls._ahora(),
                "fin": "",
                "lineas": [f"[{cls._ahora()}] Iniciando bot Selenium... Modo: {'REAL (Guardar)' if guardar else 'PRUEBA (Sin guardar)'}"],
                "resultados": [],
                "modo": "VERIFICAR" if ids_verificar and not (ids_proveedor or ids_contratista) else "REAL" if guardar else "PRUEBA",
                "total_lineas": 1
            }

        hilo = threading.Thread(
            target=cls._worker_ejecucion,
            args=(ids_proveedor, ids_contratista, guardar, ids_verificar),
            daemon=True
        )
        hilo.start()
        return TrabajoProvContra.estado

    @classmethod
    def _worker_ejecucion(cls, ids_proveedor: List[int], ids_contratista: List[int], guardar: bool, ids_verificar: List[int]):
        handler = CapturaLogHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"))
        
        logger_ap = logging.getLogger("alta_proveedores")
        logger_ap.addHandler(handler)
        logger_ac = logging.getLogger("alta_contratistas")
        logger_ac.addHandler(handler)

        resultados = TrabajoProvContra.estado["resultados"]
        try:
            with cls.conexion() as con:
                filas = {f["id"]: f for f in con.execute("SELECT * FROM registros").fetchall()}

            def anotar(campo, ids, resumen, etiqueta):
                for id_reg, (_, estatus) in zip(ids, resumen):
                    with cls.conexion() as con:
                        con.execute(
                            f"UPDATE registros SET {campo} = ?, actualizado = ? WHERE id = ?",
                            (f"{cls._ahora()} {estatus}", cls._ahora(), id_reg)
                        )
                    resultados.append({"id": id_reg, "paso": etiqueta, "estatus": str(estatus)})

            if ids_verificar:
                logger_ap.info(f"Verificando {len(ids_verificar)} registros en EK10...")
                rutas = [filas[i]["csv"] for i in ids_verificar if i in filas and filas[i]["csv"]]
                resumen = ap.ejecutar(rutas, solo_verificar=True)
                anotar("res_proveedor", ids_verificar, resumen, "Verificar")

            if ids_proveedor:
                logger_ap.info(f"Procesando alta de {len(ids_proveedor)} proveedor(es)...")
                rutas = [filas[i]["csv"] for i in ids_proveedor if i in filas and filas[i]["csv"]]
                resumen = ap.ejecutar(rutas, guardar=guardar)
                anotar("res_proveedor", ids_proveedor, resumen, "Proveedor")

            if ids_contratista:
                logger_ap.info(f"Procesando alta de {len(ids_contratista)} contratista(s)...")
                # Solo los que ya tienen ID EK10 (o recién obtenido)
                listos = []
                sin_id = []
                for i in ids_contratista:
                    reg = cls.obtener_por_id(i)
                    if reg and reg.get("id_ek10"):
                        listos.append(i)
                    else:
                        sin_id.append(i)

                if sin_id:
                    logger_ap.warning(f"{len(sin_id)} contratista(s) omitido(s): falta ID EK10 de Proveedor.")
                    anotar("res_contratista", sin_id, [("", "SIN ID EK10 (requiere alta previa de proveedor)")] * len(sin_id), "Contratista")

                if listos:
                    rutas = [filas[i]["csv"] for i in listos if i in filas and filas[i]["csv"]]
                    resumen = ac.ejecutar(rutas, guardar=guardar)
                    anotar("res_contratista", listos, resumen, "Contratista")

            TrabajoProvContra.estado["lineas"].append(f"[{cls._ahora()}] Automatización completada exitosamente.")
        except Exception as e:
            logger_ap.exception(f"Error durante el trabajo de automatización: {e}")
            resultados.append({"id": None, "paso": "Error", "estatus": f"ERROR: {e}"})
            TrabajoProvContra.estado["lineas"].append(f"[{cls._ahora()}] [ERROR]: {e}")
        finally:
            logger_ap.removeHandler(handler)
            logger_ac.removeHandler(handler)
            TrabajoProvContra.estado.update({
                "activo": False,
                "fin": cls._ahora(),
                "total_lineas": len(TrabajoProvContra.estado["lineas"])
            })
            TrabajoProvContra.activo = False

    @classmethod
    def obtener_estado_trabajo(cls, desde_linea: int = 0) -> Dict[str, Any]:
        estado = dict(TrabajoProvContra.estado)
        lineas = estado.get("lineas", [])
        estado["total_lineas"] = len(lineas)
        estado["lineas"] = lineas[desde_linea:]
        return estado

    @classmethod
    def limpiar_terminal(cls):
        TrabajoProvContra.estado["lineas"] = [f"[{cls._ahora()}] Consola reiniciada. Sistema listo."]
        TrabajoProvContra.estado["total_lineas"] = len(TrabajoProvContra.estado["lineas"])
