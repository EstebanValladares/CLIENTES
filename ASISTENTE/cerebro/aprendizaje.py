"""
Módulo de Aprendizaje e Ingesta de Conocimiento para el Asistente.
Lee repositorios, carpetas, manuales, archivos (.md, .txt, .json, .csv) y los memoriza en SQLite.
"""

import os
import glob
import json
import datetime
from typing import Dict, Any, List, Optional
from ASISTENTE.cerebro.config_cerebro import CONOCIMIENTO_DIR, DB_GRAFO_PATH
from ASISTENTE.cerebro.grafo_conocimiento import GrafoConocimiento


class ModuloAprendizaje:
    _ultimo_escaneo_ts = 0.0

    @classmethod
    def asegurar_aprendizaje_al_dia(cls):
        """Verifica de forma automática e imperceptible si hay archivos en la carpeta de conocimiento."""
        import time
        ahora = time.time()
        if ahora - cls._ultimo_escaneo_ts > 15:
            cls._ultimo_escaneo_ts = ahora
            try:
                cls.escanear_carpeta_conocimiento()
            except Exception:
                pass

    @classmethod
    def inicializar_tablas(cls):
        conn = GrafoConocimiento.get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conocimiento_documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave TEXT UNIQUE,
                nombre_archivo TEXT,
                ruta TEXT,
                categoria TEXT,
                resumen TEXT,
                contenido TEXT,
                fecha_ingesta TEXT
            )
        """)
        conn.commit()
        conn.close()

    @classmethod
    def aprender_texto(cls, titulo: str, contenido: str, categoria: str = "MANUAL") -> Dict[str, Any]:
        """Aprende una lección o información directamente en la memoria del asistente."""
        cls.inicializar_tablas()
        conn = GrafoConocimiento.get_db()
        cur = conn.cursor()

        clave = f"doc_{int(datetime.datetime.now().timestamp()*1000)}"
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resumen = contenido[:200] + ("..." if len(contenido) > 200 else "")

        cur.execute("""
            INSERT INTO conocimiento_documentos (clave, nombre_archivo, ruta, categoria, resumen, contenido, fecha_ingesta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (clave, titulo, "manual", categoria, resumen, contenido, ahora))

        conn.commit()
        conn.close()

        # Conectar al grafo en transacción separada
        nodo_id = f"DOC_{clave}"
        GrafoConocimiento.agregar_nodo(nodo_id, "DOCUMENTO", titulo, {
            "categoria": categoria,
            "resumen": resumen,
            "tamano": len(contenido)
        })

        return {
            "ok": True,
            "clave": clave,
            "titulo": titulo,
            "mensaje": f"Documento '{titulo}' memorizado y conectado al grafo de conocimiento"
        }

    @classmethod
    def escanear_carpeta_conocimiento(cls, ruta_carpeta: Optional[str] = None) -> Dict[str, Any]:
        """Escanea una carpeta en busca de archivos .txt, .md, .json y los memoriza."""
        cls.inicializar_tablas()
        directorio = ruta_carpeta or CONOCIMIENTO_DIR
        os.makedirs(directorio, exist_ok=True)

        patrones = ["*.md", "*.txt", "*.json", "*.csv"]
        archivos_encontrados = []
        for pat in patrones:
            archivos_encontrados.extend(glob.glob(os.path.join(directorio, pat)))

        procesados = 0
        conn = GrafoConocimiento.get_db()
        cur = conn.cursor()

        documentos_a_enlazar = []

        for ruta in archivos_encontrados:
            try:
                nombre = os.path.basename(ruta)
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                    contenido = f.read()

                clave = f"file_{nombre.replace('.', '_')}"
                ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                resumen = contenido[:250].strip() + ("..." if len(contenido) > 250 else "")

                cur.execute("""
                    INSERT INTO conocimiento_documentos (clave, nombre_archivo, ruta, categoria, resumen, contenido, fecha_ingesta)
                    VALUES (?, ?, ?, 'ARCHIVO', ?, ?, ?)
                    ON CONFLICT(clave) DO UPDATE SET
                        contenido = excluded.contenido,
                        resumen = excluded.resumen,
                        fecha_ingesta = excluded.fecha_ingesta
                """, (clave, nombre, ruta, resumen, contenido, ahora))

                documentos_a_enlazar.append({
                    "id": f"DOC_{clave}",
                    "nombre": nombre,
                    "ruta": ruta,
                    "resumen": resumen,
                    "tamano": len(contenido)
                })

                procesados += 1
            except Exception:
                pass

        conn.commit()
        conn.close()

        # Enlazar en el grafo
        for doc in documentos_a_enlazar:
            GrafoConocimiento.agregar_nodo(doc["id"], "DOCUMENTO", doc["nombre"], {
                "archivo": doc["nombre"],
                "ruta": doc["ruta"],
                "resumen": doc["resumen"],
                "tamano": doc["tamano"]
            })

        return {
            "ok": True,
            "archivos_detectados": len(archivos_encontrados),
            "archivos_procesados": procesados,
            "directorio": directorio
        }

    @classmethod
    def buscar_en_conocimiento(cls, consulta: str, limite: int = 5) -> List[Dict[str, Any]]:
        """Busca en todos los textos y documentos aprendidos."""
        cls.inicializar_tablas()
        conn = GrafoConocimiento.get_db()
        cur = conn.cursor()

        terminos = [t.strip() for t in consulta.split() if len(t.strip()) > 2]
        if not terminos:
            terminos = [consulta.strip()]

        condiciones = " OR ".join(["contenido LIKE ? OR nombre_archivo LIKE ?"] * len(terminos))
        params = []
        for t in terminos:
            params.extend([f"%{t}%", f"%{t}%"])

        cur.execute(f"""
            SELECT id, clave, nombre_archivo, categoria, resumen, fecha_ingesta
            FROM conocimiento_documentos
            WHERE {condiciones}
            ORDER BY id DESC
            LIMIT ?
        """, (*params, limite))

        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
