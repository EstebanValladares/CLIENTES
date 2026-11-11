"""
Core Domain: Servicio de Escalatoria de Precios & Obras (Enkontrol / Aryve SOC)
Permite consultas instantáneas O(1) de:
- Clave de Escalatoria (ej. ESC-PRECIO-TAM-0002, AD - ARMEX, etc.)
- Obras y Centros de Costo afectados
- Insumos y Precios autorizados (PrecioMoneda pactado)
- Búsqueda directa de Insumos por Obra (Vista tipo Enkontrol SOC)
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
        # Verificar si la tabla de insumos requiere actualización de esquema
        cur.execute("PRAGMA table_info(escalatoria_insumos)")
        cols = [r[1] for r in cur.fetchall()]
        if cols and "obra_clave" not in cols:
            cur.execute("DROP TABLE escalatoria_insumos")

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
                escalatoria_clave TEXT,
                id_insumo INTEGER,
                clave TEXT,
                nombre TEXT,
                precio REAL DEFAULT 0,
                precio_ppto REAL DEFAULT 0,
                precio_anterior REAL,
                moneda TEXT,
                id_obra INTEGER,
                obra_clave TEXT,
                obra_nombre TEXT,
                centro_costo TEXT,
                proyecto TEXT,
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_insumos_cve ON escalatoria_insumos(clave)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_insumos_nom ON escalatoria_insumos(nombre)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_insumos_obr_cve ON escalatoria_insumos(obra_clave)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_esc_insumos_obr_nom ON escalatoria_insumos(obra_nombre)")
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

            cur.execute("""
                SELECT DISTINCT obra, centro_costo, proyecto 
                FROM escalatoria_obras 
                WHERE id_escalatoria = ? 
                LIMIT 6
            """, (esc_id,))
            obras_list = [dict(o) for o in cur.fetchall()]
            item["obras_resumen"] = obras_list

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
    def consultar_insumos_por_obra(
        cls,
        obra: Optional[str] = None,
        insumo: Optional[str] = None,
        clave: Optional[str] = None,
        limite: int = 150
    ) -> Dict[str, Any]:
        """
        Consulta directa de INSUMOS de una obra (Vista dividida de Enkontrol SOC):
        Dado un filtro de Obra (ej. AR0 o VISTA LAGUNA) y/o Insumo (ej. 1040025 o Armex),
        devuelve:
        1. Lista de insumos autorizados con su PrecioMoneda (pactado), ppto y clave.
        2. Árbol WBS de la Obra (Proyecto -> Centro de Costo -> Obra) idéntico a Enkontrol.
        3. Información del folio de escalatoria que autorizó esos insumos.
        """
        conn = cls._get_connection()
        cur = conn.cursor()

        # Si se busca por obra y aún no tenemos insumos para esa obra en escalatoria_insumos,
        # buscar la escalatoria que contiene esa obra y descargar los insumos al vuelo
        obra_str = (obra or "").strip()
        if obra_str:
            cur.execute("""
                SELECT COUNT(*) FROM escalatoria_insumos 
                WHERE obra_clave LIKE ? OR obra_nombre LIKE ? OR centro_costo LIKE ? OR proyecto LIKE ?
            """, (f"%{obra_str}%", f"%{obra_str}%", f"%{obra_str}%", f"%{obra_str}%"))
            count_ins = cur.fetchone()[0]

            if count_ins == 0:
                # Buscar qué escalatoria afecta a esta obra
                cur.execute("""
                    SELECT DISTINCT id_escalatoria FROM escalatoria_obras 
                    WHERE obra LIKE ? OR centro_costo LIKE ? OR proyecto LIKE ?
                    LIMIT 3
                """, (f"%{obra_str}%", f"%{obra_str}%", f"%{obra_str}%"))
                cand_ids = [r[0] for r in cur.fetchall()]
                for cid in cand_ids:
                    cls._cargar_insumos_detallados_escalatoria(cid, conn)

        where_parts = []
        params = []

        if obra_str:
            o_term = f"%{obra_str}%"
            where_parts.append("""
                (
                    ei.obra_clave LIKE ? 
                    OR ei.obra_nombre LIKE ? 
                    OR ei.centro_costo LIKE ? 
                    OR ei.proyecto LIKE ?
                    OR ei.id_escalatoria IN (
                        SELECT id_escalatoria FROM escalatoria_obras 
                        WHERE obra LIKE ? OR centro_costo LIKE ? OR proyecto LIKE ?
                    )
                )
            """)
            params.extend([o_term, o_term, o_term, o_term, o_term, o_term, o_term])

        if insumo and insumo.strip():
            i_term = f"%{insumo.strip()}%"
            where_parts.append("(ei.clave LIKE ? OR ei.nombre LIKE ?)")
            params.extend([i_term, i_term])

        if clave and clave.strip():
            c_term = f"%{clave.strip()}%"
            where_parts.append("(ei.escalatoria_clave LIKE ?)")
            params.append(c_term)

        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        query_insumos = f"""
            SELECT 
                ei.id_insumo,
                ei.clave,
                ei.nombre,
                ei.precio,
                ei.precio_ppto,
                ei.precio_anterior,
                ei.moneda,
                ei.id_escalatoria,
                ei.escalatoria_clave,
                ei.obra_nombre,
                ei.obra_clave,
                ei.centro_costo,
                ei.proyecto
            FROM escalatoria_insumos ei
            {where_sql}
            ORDER BY ei.precio DESC, ei.nombre ASC
            LIMIT ?
        """
        cur.execute(query_insumos, params + [limite])
        raw_insumos = cur.fetchall()

        # Agrupar insumos únicos por (clave, nombre) para la vista limpia de Enkontrol
        insumos_agrupados = []
        vistos = set()
        for r in raw_insumos:
            d = dict(r)
            k = (d.get("clave") or "", d.get("nombre") or "")
            if k in vistos:
                continue
            vistos.add(k)
            insumos_agrupados.append(d)

        # Obtener estructura WBS de Obras coincidentes
        obras_query = """
            SELECT DISTINCT proyecto, centro_costo, obra, id_obra, id_escalatoria
            FROM escalatoria_obras
        """
        if obra_str:
            obras_query += " WHERE obra LIKE ? OR centro_costo LIKE ? OR proyecto LIKE ?"
            cur.execute(obras_query + " LIMIT 50", (f"%{obra_str}%", f"%{obra_str}%", f"%{obra_str}%"))
        else:
            cur.execute(obras_query + " LIMIT 30")
        obras_raw = [dict(o) for o in cur.fetchall()]

        # Estructurar Árbol WBS (Proyecto -> Centro Costo -> Obra)
        arbol_wbs = {}
        for o in obras_raw:
            p_nom = o.get("proyecto") or "Proyecto General"
            cc_nom = o.get("centro_costo") or "Centro de Costos"
            obr_nom = o.get("obra") or "Obra"

            if p_nom not in arbol_wbs:
                arbol_wbs[p_nom] = {}
            if cc_nom not in arbol_wbs[p_nom]:
                arbol_wbs[p_nom][cc_nom] = []
            if obr_nom not in arbol_wbs[p_nom][cc_nom]:
                arbol_wbs[p_nom][cc_nom].append({
                    "nombre": obr_nom,
                    "id_obra": o.get("id_obra"),
                    "id_escalatoria": o.get("id_escalatoria")
                })

        conn.close()
        return {
            "total_insumos": len(insumos_agrupados),
            "insumos": insumos_agrupados,
            "obras_wbs": arbol_wbs,
            "total_obras": len(obras_raw),
            "filtro_obra": obra_str,
            "filtro_insumo": insumo or ""
        }

    @classmethod
    def _cargar_insumos_detallados_escalatoria(cls, id_escalatoria: int, conn: sqlite3.Connection):
        """Descarga e indexa los insumos completos con PrecioMoneda y Obra para un ID de escalatoria"""
        session = cls._crear_sesion_enkontrol()
        if not session:
            return

        url = f"https://suite.ekloud.net:1445/Aryve/base/soc/SOCEscalatoriaPrecios/Get/GetInsumosEscalatoria/?id={id_escalatoria}"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://suite.ekloud.net:1445/Aryve/"}

        try:
            res = session.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    cur = conn.cursor()
                    # Obtener clave de la escalatoria
                    cur.execute("SELECT clave FROM escalatorias WHERE id = ?", (id_escalatoria,))
                    row_esc = cur.fetchone()
                    esc_clave = row_esc[0] if row_esc else f"ESC-{id_escalatoria}"

                    # IMPORTANTE: Enkontrol GetInsumosEscalatoria devuelve todo el catálogo general
                    # y cada objeto tiene su campo 'IdEscalatoria'.
                    # Solo debemos registrar los insumos que pertenezcan a id_escalatoria.
                    for it in data:
                        esc_id_item = it.get("IdEscalatoria")
                        if esc_id_item is not None and esc_id_item != id_escalatoria:
                            continue

                        ins_obj = it.get("Insumo") or {}
                        clave = str(ins_obj.get("Clave") or it.get("Clave") or "").strip()
                        nombre = str(ins_obj.get("Nombre") or it.get("Nombre") or "").strip()
                        id_insumo = it.get("IdInsumo") or ins_obj.get("ID")

                        # PRECIOMONEDA es el precio unitario pactado en Enkontrol (ej. 15.85)
                        precio = float(it.get("PrecioMoneda") or it.get("Precio") or 0.0)
                        precio_ppto = float(it.get("PrecioPresupuesto") or 0.0)
                        precio_ant = float(it.get("PrecioAnterior")) if it.get("PrecioAnterior") is not None else None

                        moneda_obj = it.get("Moneda") or {}
                        moneda = moneda_obj.get("MoneySymbol") or (moneda_obj.get("Clave") or "MXN")

                        obr_obj = it.get("Obra") or {}
                        id_obra = it.get("IdObra") or obr_obj.get("ID")
                        obr_cve = str(obr_obj.get("Clave") or "")
                        obr_nom = str(obr_obj.get("Nombre") or "")

                        cc_obj = it.get("CentroCostos") or {}
                        cc_nom = str(cc_obj.get("Nombre") or cc_obj.get("Clave") or "")

                        proy_obj = it.get("Proyecto") or {}
                        proy_nom = str(proy_obj.get("Nombre") or proy_obj.get("Clave") or "")

                        cur.execute("""
                            INSERT INTO escalatoria_insumos (
                                id_escalatoria, escalatoria_clave, id_insumo, clave, nombre,
                                precio, precio_ppto, precio_anterior, moneda,
                                id_obra, obra_clave, obra_nombre, centro_costo, proyecto
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            id_escalatoria, esc_clave, id_insumo, clave, nombre,
                            precio, precio_ppto, precio_ant, moneda,
                            id_obra, obr_cve, obr_nom, cc_nom, proy_nom
                        ))
                    conn.commit()
        except Exception:
            pass

    @classmethod
    def obtener_insumos_clave_obra(
        cls,
        id_escalatoria: int,
        obra: Optional[str] = None,
        insumo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retorna los insumos de una clave/escalatoria específica,
        filtrando opcionalmente por la obra y/o insumo buscado.
        """
        conn = cls._get_connection()
        cur = conn.cursor()

        # Si aún no tiene insumos indexados en escalatoria_insumos para este id, cargarlos
        cur.execute("SELECT COUNT(*) FROM escalatoria_insumos WHERE id_escalatoria = ?", (id_escalatoria,))
        if cur.fetchone()[0] == 0:
            cls._cargar_insumos_detallados_escalatoria(id_escalatoria, conn)

        where_parts = ["id_escalatoria = ?"]
        params = [id_escalatoria]

        if obra and obra.strip():
            o_term = f"%{obra.strip()}%"
            where_parts.append("""
                (
                    obra_clave LIKE ? 
                    OR obra_nombre LIKE ? 
                    OR centro_costo LIKE ? 
                    OR proyecto LIKE ?
                )
            """)
            params.extend([o_term, o_term, o_term, o_term])

        if insumo and insumo.strip():
            i_term = f"%{insumo.strip()}%"
            where_parts.append("(clave LIKE ? OR nombre LIKE ?)")
            params.extend([i_term, i_term])

        where_sql = "WHERE " + " AND ".join(where_parts)
        cur.execute(f"""
            SELECT 
                clave,
                nombre,
                precio,
                precio_ppto,
                precio_anterior,
                moneda,
                obra_clave,
                obra_nombre,
                centro_costo,
                proyecto
            FROM escalatoria_insumos
            {where_sql}
            ORDER BY precio DESC, nombre ASC
        """, params)
        rows = cur.fetchall()

        insumos = []
        vistos = set()
        for r in rows:
            d = dict(r)
            k = (d.get("clave") or "", d.get("nombre") or "", d.get("precio") or 0.0)
            if k in vistos:
                continue
            vistos.add(k)
            insumos.append(d)

        cur.execute("SELECT clave, nombre, estatus, estatus_desc, fecha_autorizacion, modificado_por FROM escalatorias WHERE id = ?", (id_escalatoria,))
        esc_row = cur.fetchone()
        esc_info = dict(esc_row) if esc_row else {}

        cur.execute("SELECT COUNT(DISTINCT clave) FROM escalatoria_insumos WHERE id_escalatoria = ?", (id_escalatoria,))
        total_sin_filtro = cur.fetchone()[0]

        conn.close()
        return {
            "id_escalatoria": id_escalatoria,
            "escalatoria": esc_info,
            "obra_filtro": obra or "",
            "insumo_filtro": insumo or "",
            "total_insumos": len(insumos),
            "total_clave_sin_filtro": total_sin_filtro,
            "insumos": insumos
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

        cur.execute("""
            SELECT proyecto, centro_costo, obra, id_obra 
            FROM escalatoria_obras 
            WHERE id_escalatoria = ? 
            ORDER BY obra ASC
        """, (id_escalatoria,))
        resultado["obras"] = [dict(o) for o in cur.fetchall()]

        cur.execute("""
            SELECT id_insumo, clave, nombre, precio, precio_ppto, precio_anterior, moneda 
            FROM escalatoria_insumos 
            WHERE id_escalatoria = ? 
            ORDER BY precio DESC, id ASC
        """, (id_escalatoria,))
        insumos = [dict(i) for i in cur.fetchall()]

        if not insumos:
            cls._cargar_insumos_detallados_escalatoria(id_escalatoria, conn)
            cur.execute("""
                SELECT id_insumo, clave, nombre, precio, precio_ppto, precio_anterior, moneda 
                FROM escalatoria_insumos 
                WHERE id_escalatoria = ? 
                ORDER BY precio DESC, id ASC
            """, (id_escalatoria,))
            insumos = [dict(i) for i in cur.fetchall()]

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
    def sincronizar_desde_enkontrol(cls, incluir_obras: bool = True) -> Dict[str, Any]:
        """
        Sincroniza todas las escalatorias desde Enkontrol 10 Cloud (GetAll)
        y sus obras/insumos asociados para búsquedas completas por obra.
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

            # ========================================================
            # SINCRONIZACIÓN DE OBRAS ASOCIADAS A CADA ESCALATORIA
            # ========================================================
            if incluir_obras:
                try:
                    url_obras = "https://suite.ekloud.net:1445/Aryve/base/soc/SOCEscalatoriaPrecios/Get/GetObrasEscalatoria/?id=0"
                    res_o = session.get(url_obras, headers=headers, timeout=12)
                    if res_o.status_code == 200:
                        obras_data = res_o.json()
                        if isinstance(obras_data, list):
                            cur.execute("DELETE FROM escalatoria_obras")
                            for o in obras_data:
                                real_esc_id = o.get("IdEscalatoria")
                                if not real_esc_id:
                                    continue
                                cur.execute("""
                                    INSERT INTO escalatoria_obras (id_escalatoria, proyecto, centro_costo, obra, id_obra)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (
                                    real_esc_id,
                                    o.get("_Proyecto") or (o.get("Proyecto") or {}).get("Nombre"),
                                    o.get("_CentroCosto") or (o.get("CentroCosto") or {}).get("Nombre"),
                                    o.get("_Obra") or (o.get("Obra") or {}).get("Nombre"),
                                    o.get("IdObra")
                                ))
                except Exception as ex_o:
                    print(f"Aviso al sincronizar obras de escalatorias: {ex_o}")

            # ========================================================
            # SINCRONIZACIÓN PRECISA DE INSUMOS Y PRECIOS POR CLAVE
            # ========================================================
            try:
                url_ins = "https://suite.ekloud.net:1445/Aryve/base/soc/SOCEscalatoriaPrecios/Get/GetInsumosEscalatoria/?id=0"
                res_i = session.get(url_ins, headers=headers, timeout=18)
                if res_i.status_code == 200:
                    ins_data = res_i.json()
                    if isinstance(ins_data, list) and len(ins_data) > 0:
                        cur.execute("DELETE FROM escalatoria_insumos")
                        cur.execute("SELECT id, clave FROM escalatorias")
                        map_claves = {r[0]: r[1] for r in cur.fetchall()}

                        for it in ins_data:
                            real_esc_id = it.get("IdEscalatoria")
                            if not real_esc_id:
                                continue

                            esc_clave = map_claves.get(real_esc_id, f"ESC-{real_esc_id}")
                            ins_obj = it.get("Insumo") or {}
                            clave = str(ins_obj.get("Clave") or it.get("Clave") or "").strip()
                            nombre = str(ins_obj.get("Nombre") or it.get("Nombre") or "").strip()
                            id_insumo = it.get("IdInsumo") or ins_obj.get("ID")

                            precio = float(it.get("PrecioMoneda") or it.get("Precio") or 0.0)
                            precio_ppto = float(it.get("PrecioPresupuesto") or 0.0)
                            precio_ant = float(it.get("PrecioAnterior")) if it.get("PrecioAnterior") is not None else None

                            moneda_obj = it.get("Moneda") or {}
                            moneda = moneda_obj.get("MoneySymbol") or (moneda_obj.get("Clave") or "MXN")

                            obr_obj = it.get("Obra") or {}
                            id_obra = it.get("IdObra") or obr_obj.get("ID")
                            obr_cve = str(obr_obj.get("Clave") or "")
                            obr_nom = str(obr_obj.get("Nombre") or "")

                            cc_obj = it.get("CentroCostos") or {}
                            cc_nom = str(cc_obj.get("Nombre") or cc_obj.get("Clave") or "")

                            proy_obj = it.get("Proyecto") or {}
                            proy_nom = str(proy_obj.get("Nombre") or proy_obj.get("Clave") or "")

                            cur.execute("""
                                INSERT INTO escalatoria_insumos (
                                    id_escalatoria, escalatoria_clave, id_insumo, clave, nombre,
                                    precio, precio_ppto, precio_anterior, moneda,
                                    id_obra, obra_clave, obra_nombre, centro_costo, proyecto
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                real_esc_id, esc_clave, id_insumo, clave, nombre,
                                precio, precio_ppto, precio_ant, moneda,
                                id_obra, obr_cve, obr_nom, cc_nom, proy_nom
                            ))
            except Exception as ex_i:
                print(f"Aviso al sincronizar insumos de escalatorias: {ex_i}")

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
