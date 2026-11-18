"""
Motor Analítico Ultrarrápido con DuckDB.
Permite a KHIARA ejecutar consultas SQL analíticas directamente sobre
archivos CSV, Excel (.xlsx, .xls), Parquet, JSON y bases de datos SQLite
sin necesidad de levantar servidores ni bases de datos intermedias.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd


class MotorDuckDB:
    def __init__(self, ruta_trabajo: Optional[str] = None):
        self.ruta_trabajo = Path(ruta_trabajo).resolve() if ruta_trabajo else Path.cwd()
        self.conexion = duckdb.connect(database=":memory:")

    def consultar(self, consulta_sql: str, limite: int = 50) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL en memoria.
        Soporta sintaxis estándar DuckDB, por ejemplo:
        - SELECT * FROM 'datos.csv' WHERE edad > 30
        - SELECT * FROM 'ventas.parquet' GROUP BY categoria
        - SELECT * FROM read_json_auto('reporte.json')
        """
        sql = consulta_sql.strip()
        sql_upper = sql.upper()

        # Seguridad básica de sólo lectura
        palabras_prohibidas = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE TABLE"]
        for p in palabras_prohibidas:
            if sql_upper.startswith(p) or f" {p} " in sql_upper:
                return {
                    "ok": False,
                    "error": f"Operación no permitida: KHIARA solo ejecuta consultas analíticas de lectura ({p})."
                }

        try:
            # Ejecutar con DuckDB
            rel = self.conexion.sql(sql)
            if rel is None:
                return {"ok": True, "filas": [], "columnas": [], "total": 0}

            df = rel.limit(limite).df()
            columnas = list(df.columns)
            filas = df.to_dict(orient="records")

            return {
                "ok": True,
                "columnas": columnas,
                "total_mostrado": len(filas),
                "filas": filas
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Error ejecutando consulta en DuckDB: {str(e)}"
            }

    def describir_archivo(self, ruta_archivo: str) -> Dict[str, Any]:
        """
        Analiza e inspecciona cualquier archivo de datos (CSV, JSON, Parquet, Excel)
        devolviendo columnas, tipos de datos, cantidad estimada de filas y primeras filas.
        """
        p = Path(ruta_archivo)
        if not p.is_absolute():
            p = (self.ruta_trabajo / p).resolve()

        if not p.exists():
            return {"ok": False, "error": f"El archivo '{ruta_archivo}' no existe."}

        ext = p.suffix.lower()
        ruta_str = str(p).replace("\\", "/")

        try:
            if ext in {".xlsx", ".xls"}:
                # Cargar con pandas y registrar en DuckDB
                df = pd.read_excel(p, nrows=200)
                nombre_tabla = f"excel_{p.stem.replace(' ', '_').replace('-', '_')}"
                self.conexion.register(nombre_tabla, df)
                sql_desc = f"DESCRIBE {nombre_tabla}"
                total_filas = len(df)
                muestra = df.head(5).to_dict(orient="records")
            elif ext == ".csv":
                sql_desc = f"DESCRIBE SELECT * FROM read_csv_auto('{ruta_str}')"
                res_count = self.conexion.execute(f"SELECT COUNT(*) AS total FROM read_csv_auto('{ruta_str}')").fetchone()
                total_filas = res_count[0] if res_count else 0
                muestra = self.conexion.execute(f"SELECT * FROM read_csv_auto('{ruta_str}') LIMIT 5").df().to_dict(orient="records")
            elif ext == ".parquet":
                sql_desc = f"DESCRIBE SELECT * FROM read_parquet('{ruta_str}')"
                res_count = self.conexion.execute(f"SELECT COUNT(*) AS total FROM read_parquet('{ruta_str}')").fetchone()
                total_filas = res_count[0] if res_count else 0
                muestra = self.conexion.execute(f"SELECT * FROM read_parquet('{ruta_str}') LIMIT 5").df().to_dict(orient="records")
            elif ext == ".json":
                sql_desc = f"DESCRIBE SELECT * FROM read_json_auto('{ruta_str}')"
                res_count = self.conexion.execute(f"SELECT COUNT(*) AS total FROM read_json_auto('{ruta_str}')").fetchone()
                total_filas = res_count[0] if res_count else 0
                muestra = self.conexion.execute(f"SELECT * FROM read_json_auto('{ruta_str}') LIMIT 5").df().to_dict(orient="records")
            else:
                return {"ok": False, "error": f"Formato no soportado por el motor DuckDB: {ext}"}

            esquema_df = self.conexion.sql(sql_desc).df()
            columnas_info = esquema_df.to_dict(orient="records")

            return {
                "ok": True,
                "archivo": p.name,
                "extension": ext,
                "tamano_kb": round(p.stat().st_size / 1024, 2),
                "total_filas": total_filas,
                "columnas": columnas_info,
                "muestra_primeras_5_filas": muestra
            }
        except Exception as e:
            return {"ok": False, "error": f"Error describiendo archivo con DuckDB: {str(e)}"}
