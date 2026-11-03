"""Salida en CSV (utf-8-sig para que Excel muestre bien acentos y ñ)."""

from __future__ import annotations

import csv
from pathlib import Path

from extraer_inputs.validacion import CampoValidado

COLUMNAS = ["etiqueta", "valor", "tipo", "valor_modelo", "valor_ocr", "similitud", "revisar", "critico", "motivo"]


def _fila(campo: CampoValidado) -> list:
    d = campo.como_dict()
    d["revisar"] = "true" if d["revisar"] else "false"
    d["valor_modelo"] = "null" if d["valor_modelo"] is None else d["valor_modelo"]
    d["similitud"] = "" if d["similitud"] is None else d["similitud"]
    return [d[c] for c in COLUMNAS]


def escribir_imagen(carpeta: Path, nombre_imagen: str, campos: list[CampoValidado], tablas: list[dict]) -> Path:
    """<imagen>.csv con los campos y, si hay tablas, <imagen>_tablas.csv."""
    carpeta.mkdir(parents=True, exist_ok=True)
    base = f"{Path(nombre_imagen).stem}_{Path(nombre_imagen).suffix[1:].lower()}"  # a.png y a.jpg no chocan
    ruta = carpeta / f"{base}.csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        w.writerows(_fila(c) for c in campos)
    if tablas:
        with open(carpeta / f"{base}_tablas.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            for n, tabla in enumerate(tablas, 1):
                w.writerow([f"tabla {n}"] + [str(e) for e in tabla.get("encabezados") or []])
                for fila in tabla.get("filas") or []:
                    w.writerow([""] + [str(v) for v in (fila if isinstance(fila, list) else [fila])])
    return ruta


def escribir_consolidado(ruta: Path, por_imagen: dict[str, list[CampoValidado]]) -> Path:
    """Todos los campos de todas las imagenes con la columna archivo_origen."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["archivo_origen"] + COLUMNAS)
        for archivo, campos in por_imagen.items():
            w.writerows([archivo] + _fila(c) for c in campos)
    return ruta
