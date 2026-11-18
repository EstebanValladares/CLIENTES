"""
Conector Universal de Bases de Datos Relacionales (SQLAlchemy).
Permite a KHIARA conectarse a servidores externos (SQL Server de Enkontrol/Aryve,
MySQL, PostgreSQL o SQLite) en modo ESTRICTA LECTURA para inspeccionar tablas
y responder preguntas sobre datos de negocio en tiempo real.
"""

import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine


class ConectorDBRelacional:
    def __init__(self, url_conexion: Optional[str] = None):
        self.url = url_conexion or self._construir_url_desde_env()
        self._engine: Optional[Engine] = None

    def _construir_url_desde_env(self) -> Optional[str]:
        """Construye la URL de conexión a partir de variables de entorno."""
        if os.getenv("DB_URL"):
            return os.getenv("DB_URL")

        tipo = os.getenv("DB_TYPE", "").lower()
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "")
        user = os.getenv("DB_USER", "")
        pwd = os.getenv("DB_PASSWORD", "")
        db = os.getenv("DB_NAME", "")

        if tipo == "mysql":
            puerto = f":{port}" if port else ":3306"
            return f"mysql+pymysql://{user}:{pwd}@{host}{puerto}/{db}"
        elif tipo in {"sqlserver", "mssql"}:
            puerto = f":{port}" if port else ""
            driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
            return f"mssql+pyodbc://{user}:{pwd}@{host}{puerto}/{db}?driver={driver.replace(' ', '+')}"
        elif tipo in {"postgres", "postgresql"}:
            puerto = f":{port}" if port else ":5432"
            return f"postgresql://{user}:{pwd}@{host}{puerto}/{db}"
        return None

    def obtener_engine(self) -> Engine:
        """Devuelve o inicializa la instancia de SQLAlchemy Engine."""
        if self._engine is None:
            if not self.url:
                raise ValueError(
                    "No se ha configurado ninguna URL de conexión a base de datos. "
                    "Configura DB_URL o DB_TYPE/DB_HOST/DB_USER/DB_PASSWORD en tu .env"
                )
            self._engine = create_engine(self.url, pool_pre_ping=True)
        return self._engine

    def listar_tablas(self) -> Dict[str, Any]:
        """Obtiene la lista de todas las tablas existentes en la base de datos."""
        try:
            engine = self.obtener_engine()
            inspector = inspect(engine)
            tablas = inspector.get_table_names()
            return {"ok": True, "total_tablas": len(tablas), "tablas": tablas}
        except Exception as e:
            return {"ok": False, "error": f"Error conectando a la base de datos: {str(e)}"}

    def describir_tabla(self, nombre_tabla: str) -> Dict[str, Any]:
        """Devuelve columnas, tipos de datos y claves de una tabla específica."""
        try:
            engine = self.obtener_engine()
            inspector = inspect(engine)
            columnas_raw = inspector.get_columns(nombre_tabla)
            columnas = [
                {
                    "nombre": col["name"],
                    "tipo": str(col["type"]),
                    "permite_nulo": col.get("nullable", True),
                    "clave_primaria": bool(col.get("primary_key", False))
                }
                for col in columnas_raw
            ]
            pk = inspector.get_pk_constraint(nombre_tabla).get("constrained_columns", [])
            return {
                "ok": True,
                "tabla": nombre_tabla,
                "columnas": columnas,
                "clave_primaria": pk
            }
        except Exception as e:
            return {"ok": False, "error": f"Error inspeccionando tabla '{nombre_tabla}': {str(e)}"}

    def consultar(self, sql_query: str, limite: int = 50) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL en modo ESTRICTA LECTURA.
        Solo se permiten SELECT, SHOW, DESCRIBE, EXPLAIN.
        """
        sql = sql_query.strip()
        sql_upper = sql.upper()

        # Validación de lectura
        permitidos = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "EXEC SP_COLUMNS", "EXEC SP_HELP")
        if not any(sql_upper.startswith(p) for p in permitidos):
            return {
                "ok": False,
                "error": "Operación denegada por seguridad: Solo se permiten consultas de lectura (SELECT, SHOW, DESCRIBE)."
            }

        palabras_riesgo = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ", "CREATE "]
        if any(p in sql_upper for p in palabras_riesgo):
            return {
                "ok": False,
                "error": "Operación denegada: La consulta contiene palabras reservadas de modificación."
            }

        try:
            engine = self.obtener_engine()
            with engine.connect() as conn:
                resultado = conn.execute(text(sql))
                if resultado.returns_rows:
                    filas_raw = resultado.fetchmany(limite)
                    columnas = list(resultado.keys())
                    filas = [dict(zip(columnas, fila)) for fila in filas_raw]
                    # Convertir tipos no serializables a string
                    filas_sanitizadas = []
                    for f in filas:
                        sanitizado = {k: (str(v) if not isinstance(v, (int, float, bool, str, type(None))) else v) for k, v in f.items()}
                        filas_sanitizadas.append(sanitizado)

                    return {
                        "ok": True,
                        "columnas": columnas,
                        "total_mostrado": len(filas_sanitizadas),
                        "filas": filas_sanitizadas
                    }
                return {"ok": True, "mensaje": "Consulta ejecutada sin registros de retorno."}
        except Exception as e:
            return {"ok": False, "error": f"Error ejecutando SQL en la base de datos externa: {str(e)}"}
