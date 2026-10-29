"""
Repositorio de persistencia para la cola de proveedores (`datos.csv`)
y el historial de proveedores registrados en Aryve (`registro_proveedores.json`).
"""
import csv
import json
import os
from typing import Any, Dict, Iterable, List, Mapping, Union

from config.settings import RUTA_DATOS_CSV, RUTA_REGISTRO_JSON
from domain.models import COLUMNAS_CSV, ProveedorData


def leer_cola_csv(ruta_csv: str = RUTA_DATOS_CSV) -> List[Dict[str, str]]:
    """Lee todos los proveedores pendientes en `datos.csv` como diccionarios normalizados."""
    if not os.path.exists(ruta_csv):
        return []
    try:
        with open(ruta_csv, mode="r", encoding="utf-8-sig", errors="replace") as f:
            lector = csv.DictReader(f)
            return [
                ProveedorData.from_dict(fila).to_csv_dict()
                for fila in lector
                if fila.get("NOMBRE") and str(fila.get("NOMBRE")).strip()
            ]
    except Exception as e:
        print(f"[REPO] Error leyendo '{ruta_csv}': {e}")
        return []


def guardar_en_csv(
    ruta_csv: str,
    registro: Union[ProveedorData, Mapping[str, Any]],
) -> Dict[str, str]:
    """
    Anexa un registro al archivo `datos.csv` respetando el orden de `COLUMNAS_CSV`
    y asegurando el volcado a disco (`fsync`).
    """
    prov = registro if isinstance(registro, ProveedorData) else ProveedorData.from_dict(registro)
    fila_dict = prov.to_csv_dict()

    existe_archivo = os.path.exists(ruta_csv)
    contenido_previo = ""
    if existe_archivo:
        try:
            with open(ruta_csv, mode="r", encoding="utf-8") as f:
                contenido_previo = f.read()
        except Exception:
            contenido_previo = ""

    with open(ruta_csv, mode="a", newline="\n", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
        if not existe_archivo or len(contenido_previo.strip()) == 0:
            escritor.writeheader()
        elif not contenido_previo.endswith("\n"):
            f.write("\n")

        escritor.writerow(fila_dict)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

    return fila_dict


def sobrescribir_cola_csv(
    registros: Iterable[Union[ProveedorData, Mapping[str, Any]]],
    ruta_csv: str = RUTA_DATOS_CSV,
) -> None:
    """Sobrescribe `datos.csv` con la lista indicada (o deja solo la cabecera si está vacía)."""
    try:
        with open(ruta_csv, mode="w", newline="\n", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
            escritor.writeheader()
            for item in registros:
                prov = item if isinstance(item, ProveedorData) else ProveedorData.from_dict(item)
                escritor.writerow(prov.to_csv_dict())
    except Exception as e:
        print(f"[REPO] Error sobrescribiendo '{ruta_csv}': {e}")


def leer_registrados_json(ruta_json: str = RUTA_REGISTRO_JSON) -> List[Dict[str, str]]:
    """Devuelve la lista de proveedores dados de alta en `registro_proveedores.json`."""
    if not os.path.exists(ruta_json):
        return []
    try:
        with open(ruta_json, mode="r", encoding="utf-8") as f:
            datos = json.load(f)
            if isinstance(datos, list):
                return [
                    {"id": str(item.get("id", "")), "clave": str(item.get("clave", ""))}
                    for item in datos
                    if isinstance(item, dict)
                ]
    except Exception:
        pass
    return []


def registrar_proveedor_json(
    clave: str,
    id_generado: Any,
    ruta_json: str = RUTA_REGISTRO_JSON,
) -> Dict[str, str]:
    """
    Inserta o actualiza (upsert por `clave`) el par `{"id": ..., "clave": ...}`
    en `registro_proveedores.json`.
    """
    registros = leer_registrados_json(ruta_json)
    clave_str = str(clave or "").strip().upper()
    id_str = str(id_generado if id_generado else "Pendiente").strip()

    nuevo_item = {"id": id_str, "clave": clave_str}
    actualizado = False

    for idx, reg in enumerate(registros):
        if str(reg.get("clave", "")).strip().upper() == clave_str:
            registros[idx] = nuevo_item
            actualizado = True
            break

    if not actualizado:
        registros.append(nuevo_item)

    try:
        with open(ruta_json, mode="w", encoding="utf-8") as f:
            json.dump(registros, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[REPO] Error al escribir en '{ruta_json}': {e}")

    return nuevo_item

