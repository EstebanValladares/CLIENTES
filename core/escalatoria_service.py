"""
Core Domain: Servicio de Escalatoria de Precios & Obras (Enkontrol / Aryve SOC)
Permite consultas instantáneas O(1) de:
- Clave de Escalatoria (ej. ESC-PRECIO-TAM-0002, AD - ARMEX, etc.)
- Obras y Centros de Costo afectados
- Insumos y Precios autorizados
- Historial de autorizaciones y usuarios
- Caché local en SQLite (data/escalatorias.db) para uso offline o red lenta
- Sincronización en vivo con Enkontrol 10 Cloud (SOCEscalatoriaPrecios)
"""

import os
import sqlite3
import json
import time
import threading
import requests
import urllib3
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "escalatorias.db")

_lock_sync = threading.Lock()
_sincronizando_ahora = False


class EscalatoriaService:
    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cls._crear_tablas_si_no_existen(conn)
        return conn

    @classmethod
    def _crear_tablas_si_no_existen(cls, conn: sqlite3.Connection):
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalatorias (
                id INTEGER PRIMARY KEY,
                clave TEXT NOT NULL,
                nombre TEXT,
                estatus TEXT,
                estatus_desc TEXT,
                creado TEXT,
                creado_por TEXT,
                modificado TEXT,
                modificado_por TEXT,
                fecha_autorizacion TEXT,
                numero_insumos INTEGER DEFAULT 0,
                cc_codigo TEXT,
                cc_nombre TEXT,
                plantilla TEXT,
                raw_json TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalatoria_obras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_escalatoria INTEGER,
                proyecto TEXT,
                centro_costo TEXT,
                obra TEXT,
                id_obra INTEGER,
                FOREIGN KEY(id_escalatoria) REFERENCES escalatorias(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalatoria_insumos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_escalatoria INTEGER,
                id_insumo INTEGER,
                clave TEXT,
                nombre TEXT,
                precio REAL DEFAULT 0,
                precio_ppto REAL DEFAULT 0,
                precio_anterior REAL,
                moneda TEXT,
                FOREIGN KEY(id_escalatoria) REFERENCES escalatorias(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalatoria_meta (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                fecha TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_clave ON escalatorias(clave)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_cc ON escalatorias(cc_codigo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_obras_esc ON escalatoria_obras(id_escalatoria)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_obras_obra ON escalatoria_obras(obra)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_obras_cc ON escalatoria_obras(centro_costo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_insumos_esc ON escalatoria_insumos(id_escalatoria)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_insumos_nombre ON escalatoria_insumos(nombre)")
        conn.commit()

    @classmethod
    def obtener_resumen(cls) -> Dict[str, Any]:
        """KPIs rápidos del módulo de escalatorias"""
        conn = cls._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM escalatorias")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM escalatorias WHERE UPPER(estatus) = 'AUT' OR UPPER(estatus_desc) LIKE '%AUTORIZAD%'")
        autorizadas = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT obra) FROM escalatoria_obras WHERE obra IS NOT NULL AND obra != ''")
        obras_vinculadas = cur.fetchone()[0]

        cur.execute("SELECT valor, fecha FROM escalatoria_meta WHERE clave = 'ultima_sincronizacion'")
        row_meta = cur.fetchone()
        ultima_sync = row_meta["fecha"] if row_meta else None
        total_sync = row_meta["valor"] if row_meta else str(total)

        conn.close()
        return {
            "total_escalatorias": total,
            "autorizadas": autorizadas,
            "obras_vinculadas": obras_vinculadas,
            "ultima_sincronizacion": ultima_sync,
            "total_sync": total_sync,
            "sincronizando": _sincronizando_ahora
        }

    @classmethod
    def consultar(
        cls,
        busqueda: Optional[str] = None,
        obra: Optional[str] = None,
        clave: Optional[str] = None,
        insumo: Optional[str] = None,
        estatus: Optional[str] = None,
        limite: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Búsqueda multi-criterio de alta velocidad:
        - Si buscas por obra (ej. AR0 o VISTA LAGUNA), busca en las escalatorias que aplican a esa obra.
        - Si buscas por clave (ej. ESC-PRECIO-TAM-0002 o AD - ARMEX), busca por clave exacta o parcial.
        - Si buscas por insumo (ej. Cemento o Armex), busca en las escalatorias que modifican ese insumo.
        """
        conn = cls._get_connection()
        cur = conn.cursor()

        # Si no hay registros aún, intentar carga inicial en segundo plano o retornar vacío
        cur.execute("SELECT COUNT(*) FROM escalatorias")
        count_existente = cur.fetchone()[0]
        if count_existente == 0:
            conn.close()
            return {
                "total": 0,
                "limite": limite,
                "offset": offset,
                "registros": [],
                "requiere_sync": True
            }

        where_clauses = []
        params = []

        if clave and clave.strip():
            where_clauses.append("e.clave LIKE ?")
            params.append(f"%{clave.strip()}%")

        if estatus and estatus.strip() and estatus.upper() != "TODOS":
            where_clauses.append("(UPPER(e.estatus) = ? OR UPPER(e.estatus_desc) LIKE ?)")
            params.append(estatus.strip().upper())
            params.append(f"%{estatus.strip().upper()}%")

        if obra and obra.strip():
            o_term = f"%{obra.strip()}%"
            where_clauses.append("""
                e.id IN (
                    SELECT DISTINCT id_escalatoria FROM escalatoria_obras 
                    WHERE obra LIKE ? OR centro_costo LIKE ? OR proyecto LIKE ?
                )
            """)
            params.extend([o_term, o_term, o_term])

        if insumo and insumo.strip():
            i_term = f"%{insumo.strip()}%"
            where_clauses.append("""
                e.id IN (
                    SELECT DISTINCT id_escalatoria FROM escalatoria_insumos 
                    WHERE nombre LIKE ? OR clave LIKE ?
                )
            """)
            params.extend([i_term, i_term])

        if busqueda and busqueda.strip():
            b_term = f"%{busqueda.strip()}%"
            where_clauses.append("""
                (
                    e.clave LIKE ? 
                    OR e.nombre LIKE ? 
                    OR e.cc_codigo LIKE ? 
                    OR e.cc_nombre LIKE ?
                    OR e.creado_por LIKE ?
                    OR e.modificado_por LIKE ?
                    OR e.id IN (
                        SELECT DISTINCT id_escalatoria FROM escalatoria_obras 
                        WHERE obra LIKE ? OR centro_costo LIKE ? OR proyecto LIKE ?
                    )
                    OR e.id IN (
                        SELECT DISTINCT id_escalatoria FROM escalatoria_insumos 
                        WHERE nombre LIKE ? OR clave LIKE ?
                    )
                )
            """)
            params.extend([b_term] * 11)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Total filtrado
        count_query = f"SELECT COUNT(*) FROM escalatorias e {where_sql}"
        cur.execute(count_query, params)
        total_filtrados = cur.fetchone()[0]

        # Consulta paginada
        data_query = f"""
            SELECT 
                e.id,
                e.clave,
                e.nombre,
                e.estatus,
                e.estatus_desc,
                e.creado,
                e.creado_por,
                e.fecha_autorizacion,
                e.modificado_por,
                e.numero_insumos,
                e.cc_codigo,
                e.cc_nombre,
                e.plantilla
            FROM escalatorias e
            {where_sql}
            ORDER BY e.id DESC
            LIMIT ? OFFSET ?
        """
        cur.execute(data_query, params + [limite, offset])
        rows = cur.fetchall()

        registros = []
        for r in rows:
            item = dict(r)
            esc_id = item["id"]

            # Obtener resumen de hasta 5 obras afectadas
            cur.execute("""
                SELECT DISTINCT obra, centro_costo, proyecto 
                FROM escalatoria_obras 
                WHERE id_escalatoria = ? 
                LIMIT 6
            """, (esc_id,))
            obras_list = [dict(o) for o in cur.fetchall()]
            item["obras_resumen"] = obras_list

            # Contar total de obras
            cur.execute("SELECT COUNT(DISTINCT obra) FROM escalatoria_obras WHERE id_escalatoria = ?", (esc_id,))
            item["total_obras"] = cur.fetchone()[0]

            registros.append(item)

        conn.close()
        return {
            "total": total_filtrados,
            "limite": limite,
            "offset": offset,
            "registros": registros,
            "requiere_sync": False
        }

    @classmethod
    def obtener_detalle(cls, id_escalatoria: int) -> Optional[Dict[str, Any]]:
        """Obtiene la información completa de una escalatoria con todos sus insumos y obras"""
        conn = cls._get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM escalatorias WHERE id = ?", (id_escalatoria,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        resultado = dict(row)

        # Obras asociadas
        cur.execute("""
            SELECT proyecto, centro_costo, obra, id_obra 
            FROM escalatoria_obras 
            WHERE id_escalatoria = ? 
            ORDER BY obra ASC
        """, (id_escalatoria,))
        resultado["obras"] = [dict(o) for o in cur.fetchall()]

        # Insumos y precios
        cur.execute("""
            SELECT id_insumo, clave, nombre, precio, precio_ppto, precio_anterior, moneda 
            FROM escalatoria_insumos 
            WHERE id_escalatoria = ? 
            ORDER BY id ASC
        """, (id_escalatoria,))
        insumos = [dict(i) for i in cur.fetchall()]

        # Si aún no tiene insumos en base local, intentar consultarlos al vuelo de Enkontrol Cloud
        if not insumos:
            insumos = cls._consultar_insumos_en_vivo(id_escalatoria)
            if insumos:
                # Guardarlos en local para caché rápida futura
                for ins in insumos:
                    cur.execute("""
                        INSERT INTO escalatoria_insumos (id_escalatoria, id_insumo, clave, nombre, precio, precio_ppto, precio_anterior, moneda)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        id_escalatoria,
                        ins.get("id_insumo"),
                        ins.get("clave"),
                        ins.get("nombre"),
                        ins.get("precio", 0),
                        ins.get("precio_ppto", 0),
                        ins.get("precio_anterior"),
                        ins.get("moneda")
                    ))
                conn.commit()

        resultado["insumos"] = insumos
        conn.close()
        return resultado

    @classmethod
    def _crear_sesion_enkontrol(cls) -> Optional[requests.Session]:
        """Crea una sesión autenticada con Enkontrol 10 Cloud"""
        load_dotenv(os.path.join(BASE_DIR, ".env"))
        user = os.getenv("EK10_USER", "").strip()
        pwd = os.getenv("EK10_PASS", "").strip()

        if not user or not pwd:
            return None

        session = requests.Session()
        session.verify = False

        login_url = ""
        data = {"username": user, "password": pwd, "returnUrl": "", "msj": ""}
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://suite.ekloud.net:1445/Aryve/"}

        try:
            r = session.post(login_url, data=data, headers=headers, timeout=12)
            if r.status_code == 200 and ".AspNet.ApplicationCookie" in session.cookies:
                return session
        except Exception:
            pass
        return None

    @classmethod
    def _consultar_insumos_en_vivo(cls, id_escalatoria: int) -> List[Dict[str, Any]]:
        """Consulta los insumos directamente desde el endpoint de Enkontrol Cloud"""
        session = cls._crear_sesion_enkontrol()
        if not session:
            return []

        url = f"https://suite.ekloud.net:1445/Aryve/base/soc/SOCEscalatoriaPrecios/Get/GetInsumosEscalatoria/?id={id_escalatoria}"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://suite.ekloud.net:1445/Aryve/"}

        try:
            res = session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                insumos_limpios = []
                # Evitar duplicados por obra agrupando por insumo
                vistos = set()
                if isinstance(data, list):
                    for item in data:
                        ins_obj = item.get("Insumo") or {}
                        clave = str(ins_obj.get("Clave") or item.get("Clave") or "").strip()
                        nombre = str(ins_obj.get("Nombre") or item.get("Nombre") or "").strip()
                        id_insumo = item.get("IdInsumo") or ins_obj.get("ID")
                        key_uniq = clave or nombre or id_insumo
                        if key_uniq and key_uniq in vistos:
                            continue
                        vistos.add(key_uniq)

                        precio = float(item.get("Precio") or 0.0)
                        precio_ppto = float(item.get("PrecioPresupuesto") or 0.0)
                        precio_anterior = float(item.get("PrecioAnterior")) if item.get("PrecioAnterior") is not None else None
                        moneda_obj = item.get("Moneda") or {}
                        moneda = moneda_obj.get("MoneySymbol") or "MXN"

                        insumos_limpios.append({
                            "id_insumo": id_insumo,
                            "clave": clave,
                            "nombre": nombre,
                            "precio": precio,
                            "precio_ppto": precio_ppto,
                            "precio_anterior": precio_anterior,
                            "moneda": moneda
                        })
                return insumos_limpios
        except Exception:
            pass
        return []

    @classmethod
    def sincronizar_desde_enkontrol(cls, incluir_obras: bool = True) -> Dict[str, Any]:
        """
        Sincroniza todas las escalatorias desde Enkontrol 10 Cloud (GetAll)
        y opcionalmente sus obras asociadas para búsquedas completas por obra.
        """
        global _sincronizando_ahora
        with _lock_sync:
            if _sincronizando_ahora:
                return {"ok": False, "mensaje": "Ya hay una sincronización en curso."}
            _sincronizando_ahora = True

        try:
            session = cls._crear_sesion_enkontrol()
            if not session:
                return {
                    "ok": False,
                    "mensaje": "No se pudo iniciar sesión en Enkontrol 10 Cloud. Verifica las credenciales en .env."
                }

            url_all = "https://suite.ekloud.net:1445/Aryve/base/soc/SOCEscalatoriaPrecios/api/GetAll/"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://suite.ekloud.net:1445/Aryve/"}

            res = session.post(url_all, json={"parametros": {}}, headers=headers, timeout=20)
            if res.status_code != 200:
                return {
                    "ok": False,
                    "mensaje": f"Error al consultar Enkontrol Cloud (HTTP {res.status_code})."
                }

            lista = res.json()
            if not isinstance(lista, list):
                return {"ok": False, "mensaje": "Respuesta no esperada del servidor Cloud."}

            conn = cls._get_connection()
            cur = conn.cursor()

            ahora_str = time.strftime("%Y-%m-%d %H:%M:%S")
            total_procesadas = 0

            for item in lista:
                esc_id = item.get("ID")
                if not esc_id:
                    continue

                clave = str(item.get("Clave") or "").strip()
                nombre = str(item.get("Nombre") or "").strip()
                creado = str(item.get("Creado") or "")
                creado_por_obj = item.get("CreadoPor") or {}
                creado_por = str(creado_por_obj.get("NombreCompleto") or creado_por_obj.get("Nombre") or "")

                modificado = str(item.get("Modificado") or "")
                modificado_por_obj = item.get("ModificadoPor") or {}
                modificado_por = str(modificado_por_obj.get("NombreCompleto") or modificado_por_obj.get("Nombre") or "")

                fecha_aut = str(item.get("FechaAutorizacion") or "")

                estatus_obj = item.get("Estatus") or {}
                estatus = str(item.get("EstatusAutorizacion") or estatus_obj.get("Clave") or "")
                estatus_desc = str(estatus_obj.get("Nombre") or "")

                num_insumos = int(item.get("NumeroInsumos") or 0)

                # Centro de Costos / Plaza
                cc_obj = item.get("CCA") or item.get("CentroCosto") or {}
                cc_codigo = str(cc_obj.get("Clave") or item.get("CC") or "")
                cc_nombre = str(cc_obj.get("Nombre") or "")

                plantilla_obj = item.get("Plantilla") or {}
                plantilla = str(plantilla_obj.get("Nombre") or "")

                cur.execute("""
                    INSERT INTO escalatorias (
                        id, clave, nombre, estatus, estatus_desc, creado, creado_por,
                        modificado, modificado_por, fecha_autorizacion, numero_insumos,
                        cc_codigo, cc_nombre, plantilla
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        clave=excluded.clave,
                        nombre=excluded.nombre,
                        estatus=excluded.estatus,
                        estatus_desc=excluded.estatus_desc,
                        creado=excluded.creado,
                        creado_por=excluded.creado_por,
                        modificado=excluded.modificado,
                        modificado_por=excluded.modificado_por,
                        fecha_autorizacion=excluded.fecha_autorizacion,
                        numero_insumos=excluded.numero_insumos,
                        cc_codigo=excluded.cc_codigo,
                        cc_nombre=excluded.cc_nombre,
                        plantilla=excluded.plantilla
                """, (
                    esc_id, clave, nombre, estatus, estatus_desc, creado, creado_por,
                    modificado, modificado_por, fecha_aut, num_insumos,
                    cc_codigo, cc_nombre, plantilla
                ))
                total_procesadas += 1

                # Si se solicitan obras y aún no tiene registros de obras para este ID
                if incluir_obras:
                    cur.execute("SELECT COUNT(*) FROM escalatoria_obras WHERE id_escalatoria = ?", (esc_id,))
                    if cur.fetchone()[0] == 0:
                        try:
                            url_obras = f"https://suite.ekloud.net:1445/Aryve/base/soc/SOCEscalatoriaPrecios/Get/GetObrasEscalatoria/?id={esc_id}"
                            res_o = session.get(url_obras, headers=headers, timeout=6)
                            if res_o.status_code == 200:
                                obras_data = res_o.json()
                                if isinstance(obras_data, list):
                                    for o in obras_data:
                                        cur.execute("""
                                            INSERT INTO escalatoria_obras (id_escalatoria, proyecto, centro_costo, obra, id_obra)
                                            VALUES (?, ?, ?, ?, ?)
                                        """, (
                                            esc_id,
                                            o.get("_Proyecto") or (o.get("Proyecto") or {}).get("Nombre"),
                                            o.get("_CentroCosto") or (o.get("CentroCosto") or {}).get("Nombre"),
                                            o.get("_Obra") or (o.get("Obra") or {}).get("Nombre"),
                                            o.get("IdObra")
                                        ))
                        except Exception:
                            pass

            # Guardar metadatos
            cur.execute("""
                INSERT INTO escalatoria_meta (clave, valor, fecha)
                VALUES ('ultima_sincronizacion', ?, ?)
                ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, fecha=excluded.fecha
            """, (str(total_procesadas), ahora_str))

            conn.commit()
            conn.close()

            return {
                "ok": True,
                "mensaje": f"¡Sincronización exitosa! Se actualizaron {total_procesadas} escalatorias de precios.",
                "total_escalatorias": total_procesadas,
                "fecha": ahora_str
            }
        except Exception as e:
            return {"ok": False, "mensaje": f"Error inesperado al sincronizar: {str(e)}"}
        finally:
            _sincronizando_ahora = False
