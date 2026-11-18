"""
Indexador de Proyectos de KHIARA.
Aprende automáticamente de cualquier repositorio o carpeta: extrae estructura,
esquemas de bases de datos SQLite, archivos JSON, código Python y endpoints.
"""

import os
import ast
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from khiara.grafo.red import RedConocimiento


class IndexadorProyecto:
    IGNORAR_CARPETAS = {
        ".git", "__pycache__", "node_modules", "venv", ".venv",
        "env", "dist", "build", ".idea", ".vscode", "temp", "tmp",
        "KHIARA", "scratch", "CLIENTES", "output", "capturas", "reportes"
    }

    IGNORAR_EXTENSIONES = {
        ".pyc", ".pyo", ".exe", ".dll", ".so", ".zip", ".tar", ".gz",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf"
    }

    def __init__(self, red: RedConocimiento):
        self.red = red

    def aprender_proyecto(self, ruta_proyecto: str) -> Dict[str, Any]:
        """Escanea e indexa todo el conocimiento de un proyecto en el grafo."""
        p = Path(ruta_proyecto).resolve()
        if not p.exists() or not p.is_dir():
            return {"ok": False, "error": f"La ruta '{ruta_proyecto}' no existe o no es una carpeta"}

        proyecto_id = f"PROYECTO::{p.name}"
        self.red.agregar_nodo(proyecto_id, tipo="PROYECTO", datos={
            "nombre": p.name,
            "ruta_absoluta": str(p)
        })

        archivos_procesados = 0
        tablas_procesadas = 0

        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in self.IGNORAR_CARPETAS]
            rel_root = os.path.relpath(root, p)
            dir_id = f"DIR::{p.name}/{rel_root.replace(chr(92), '/')}" if rel_root != "." else proyecto_id

            if dir_id != proyecto_id:
                self.red.agregar_nodo(dir_id, tipo="DIRECTORIO", datos={"nombre": os.path.basename(root)})
                self.red.agregar_relacion(proyecto_id, dir_id, "CONTIENE_CARPETA")

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.IGNORAR_EXTENSIONES:
                    continue

                file_path = os.path.join(root, file)
                rel_file = os.path.relpath(file_path, p).replace(chr(92), "/")
                file_id = f"ARCHIVO::{p.name}/{rel_file}"

                tamano_kb = round(os.path.getsize(file_path) / 1024, 2)
                self.red.agregar_nodo(file_id, tipo="ARCHIVO", datos={
                    "nombre": file,
                    "extension": ext,
                    "ruta_relativa": rel_file,
                    "tamano_kb": tamano_kb
                })
                self.red.agregar_relacion(dir_id, file_id, "CONTIENE_ARCHIVO")
                archivos_procesados += 1

                # Extracción profunda según tipo
                if ext in {".sqlite", ".db", ".sqlite3"}:
                    tablas = self._indexar_sqlite(file_path, file_id)
                    tablas_procesadas += len(tablas)
                elif ext == ".py":
                    self._indexar_python(file_path, file_id)
                elif ext == ".json":
                    self._indexar_json(file_path, file_id)

        self.red.guardar()
        return {
            "ok": True,
            "proyecto": p.name,
            "archivos_indexados": archivos_procesados,
            "tablas_db_indexadas": tablas_procesadas,
            "metricas_grafo": self.red.metricas()
        }

    def _indexar_sqlite(self, db_path: str, file_id: str) -> List[str]:
        tablas_encontradas = []
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tablas = [r[0] for r in cursor.fetchall()]

            for t in tablas:
                try:
                    cursor.execute(f"PRAGMA table_info({t});")
                    cols = [c[1] for c in cursor.fetchall()]
                    cursor.execute(f"SELECT COUNT(*) FROM {t};")
                    count = cursor.fetchone()[0]
                except Exception:
                    cols, count = [], 0

                tabla_id = f"TABLA::{Path(db_path).name}::{t}"
                self.red.agregar_nodo(tabla_id, tipo="TABLA_DB", datos={
                    "tabla": t,
                    "archivo_db": Path(db_path).name,
                    "columnas": cols,
                    "total_registros": count
                })
                self.red.agregar_relacion(file_id, tabla_id, "ALMACENA_TABLA")
                tablas_encontradas.append(t)
            conn.close()
        except Exception:
            pass
        return tablas_encontradas

    def _indexar_python(self, py_path: str, file_id: str):
        try:
            with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
                arbol = ast.parse(f.read())
            for item in arbol.body:
                if isinstance(item, ast.FunctionDef):
                    func_id = f"FUNC::{file_id}::{item.name}"
                    args = [a.arg for a in item.args.args]
                    self.red.agregar_nodo(func_id, tipo="FUNCION", datos={"nombre": item.name, "argumentos": args})
                    self.red.agregar_relacion(file_id, func_id, "DEFINE_FUNCION")
                elif isinstance(item, ast.ClassDef):
                    class_id = f"CLASE::{file_id}::{item.name}"
                    metodos = [m.name for m in item.body if isinstance(m, ast.FunctionDef)]
                    self.red.agregar_nodo(class_id, tipo="CLASE", datos={"nombre": item.name, "metodos": metodos})
                    self.red.agregar_relacion(file_id, class_id, "DEFINE_CLASE")
        except Exception:
            pass

    def _indexar_json(self, json_path: str, file_id: str):
        try:
            with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            if isinstance(data, list):
                resumen = f"Lista de {len(data)} elementos"
                claves = list(data[0].keys()) if data and isinstance(data[0], dict) else []
            elif isinstance(data, dict):
                resumen = f"Objeto con claves: {', '.join(list(data.keys())[:8])}"
                claves = list(data.keys())
            else:
                resumen, claves = "Dato primitivo", []
            self.red.agregar_nodo(f"SCHEMA::{file_id}", tipo="JSON_SCHEMA", datos={"resumen": resumen, "claves": claves[:15]})
            self.red.agregar_relacion(file_id, f"SCHEMA::{file_id}", "DESCRIBE_ESTRUCTURA")
        except Exception:
            pass
