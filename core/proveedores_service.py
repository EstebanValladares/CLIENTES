"""
Core Domain: Servicios de Proveedores (Generador, Cola y Ejecución Asíncrona).
"""
import os
import sys
import csv
import json
import threading
import datetime
from typing import Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIR_PROV = os.path.join(BASE_DIR, "PROVEEDORES")
RUTA_CSV_PROV = os.path.join(DIR_PROV, "datos.csv")
RUTA_REGISTRO_JSON = os.path.join(DIR_PROV, "registro_proveedores.json")

COLUMNAS_CSV = [
    "TIPO PERSONA", "CLAVE", "NOMBRE", "PATERNO", "MATERNO",
    "RFC", "NOMBRE CORTO", "CALLE", "EXT", "COLONIA", "CP"
]

class ProveedoresService:
    _cola_memoria: List[Dict[str, Any]] = []
    _estado_actual: Dict[str, Any] = {
        "ejecutando": False,
        "ok": None,
        "mensaje": "Listo",
        "logs": []
    }

    @classmethod
    def calcular_claves(cls, nombre: str, tipo_persona: str, paterno: str = "") -> Dict[str, str]:
        try:
            if DIR_PROV not in sys.path:
                sys.path.append(DIR_PROV)
            from generador_nombres import (
                generar_clave_proveedor,
                generar_nombre_corto,
                generar_clave_persona_fisica,
                generar_nombre_corto_persona_fisica
            )
            nom = nombre.strip().upper()
            pat = paterno.strip().upper()

            if tipo_persona == "FÍSICA":
                clave = generar_clave_persona_fisica(nom, pat) if nom else "EK-PROV-..."
                corto = generar_nombre_corto_persona_fisica(nom, pat) if nom else "..."
            else:
                clave = generar_clave_proveedor(nom) if nom else "EK-PROV-..."
                corto = generar_nombre_corto(nom) if nom else "..."

            return {"clave": clave, "nombre_corto": corto}
        except Exception as e:
            return {"clave": f"EK-PROV-{nombre[:6].upper()}", "nombre_corto": nombre[:15].upper()}

    @classmethod
    def obtener_cola(cls) -> List[Dict[str, Any]]:
        if not cls._cola_memoria and os.path.exists(RUTA_CSV_PROV):
            try:
                with open(RUTA_CSV_PROV, "r", encoding="utf-8") as f:
                    lector = csv.DictReader(f)
                    cls._cola_memoria = [row for row in lector if row.get("NOMBRE")]
            except Exception:
                pass
        return cls._cola_memoria

    @classmethod
    def sincronizar_csv(cls):
        try:
            with open(RUTA_CSV_PROV, "w", newline="\n", encoding="utf-8") as f:
                escritor = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
                escritor.writeheader()
                for item in cls._cola_memoria:
                    fila = {col: str(item.get(col, "")).strip().upper() for col in COLUMNAS_CSV}
                    escritor.writerow(fila)
        except Exception as e:
            print(f"[ProveedoresService] Error sincronizando datos.csv: {e}")

    @classmethod
    def agregar_a_cola(cls, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        registro = {
            "TIPO PERSONA": str(item.get("tipo_persona") or item.get("TIPO PERSONA", "MORAL")).strip().upper(),
            "NOMBRE": str(item.get("nombre") or item.get("NOMBRE", "")).strip().upper(),
            "PATERNO": str(item.get("paterno") or item.get("PATERNO", "")).strip().upper(),
            "MATERNO": str(item.get("materno") or item.get("MATERNO", "")).strip().upper(),
            "CLAVE": str(item.get("clave") or item.get("CLAVE", "")).strip().upper(),
            "NOMBRE CORTO": str(item.get("nombre_corto") or item.get("NOMBRE CORTO", "")).strip().upper(),
            "RFC": str(item.get("rfc") or item.get("RFC", "")).strip().upper(),
            "CALLE": str(item.get("calle") or item.get("CALLE", "")).strip().upper(),
            "EXT": str(item.get("ext") or item.get("EXT", "")).strip().upper(),
            "COLONIA": str(item.get("colonia") or item.get("COLONIA", "")).strip().upper(),
            "CP": str(item.get("cp") or item.get("CP", "")).strip().upper()
        }
        cls._cola_memoria.append(registro)
        cls.sincronizar_csv()
        return cls._cola_memoria

    @classmethod
    def eliminar_de_cola(cls, idx: int) -> List[Dict[str, Any]]:
        if 0 <= idx < len(cls._cola_memoria):
            cls._cola_memoria.pop(idx)
            cls.sincronizar_csv()
        return cls._cola_memoria

    @classmethod
    def vaciar_cola(cls) -> List[Dict[str, Any]]:
        cls._cola_memoria = []
        cls.sincronizar_csv()
        return []

    @classmethod
    def obtener_estado_ejecucion(cls) -> Dict[str, Any]:
        return cls._estado_actual

    @classmethod
    def iniciar_procesamiento_cola(cls):
        if cls._estado_actual["ejecutando"]:
            return False, "Ya hay un proceso de alta de proveedores en ejecución."
        if not cls._cola_memoria:
            return False, "No hay proveedores en la lista para procesar."

        cls._estado_actual = {
            "ejecutando": True,
            "ok": None,
            "mensaje": f"Iniciando Selenium para {len(cls._cola_memoria)} proveedores...",
            "logs": [f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Iniciando procesamiento en segundo plano..."]
        }

        hilo = threading.Thread(target=cls._worker_cola, args=(list(cls._cola_memoria),), daemon=True)
        hilo.start()
        return True, "Procesamiento de proveedores iniciado en segundo plano."

    @classmethod
    def _worker_cola(cls, cola: List[Dict[str, Any]]):
        try:
            if DIR_PROV not in sys.path:
                sys.path.append(DIR_PROV)
            from ejecutor_proveedores import procesar_cola_proveedores

            def log_callback(msg):
                texto = str(msg).strip()
                if texto:
                    cls._estado_actual["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {texto}")
                    cls._estado_actual["mensaje"] = texto

            ok, msg = procesar_cola_proveedores(cola, log_callback=log_callback)
            cls._estado_actual["ok"] = ok
            cls._estado_actual["mensaje"] = msg
            if ok:
                cls._cola_memoria = []
                cls.sincronizar_csv()
        except Exception as e:
            cls._estado_actual["ok"] = False
            cls._estado_actual["mensaje"] = f"Error en Selenium: {str(e)}"
            cls._estado_actual["logs"].append(f"[ERROR]: {str(e)}")
        finally:
            cls._estado_actual["ejecutando"] = False

    @classmethod
    def obtener_registrados(cls) -> List[Dict[str, str]]:
        if os.path.exists(RUTA_REGISTRO_JSON):
            try:
                with open(RUTA_REGISTRO_JSON, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    return [{"id": str(p.get("id", "")), "clave": str(p.get("clave", ""))} for p in datos if p.get("id")]
            except Exception:
                pass
        return []
