"""
Core Domain: Servicio de Trazabilidad OC, Contratos, Estimaciones e Insumos (Enkontrol / Aryve BI & Cloud Live)
Permite buscar instantáneamente por Folio de OC, Clave de Contrato (ej. ELEC, MYM, PLOM) o Número + Obra y obtener:
- Datos de la Orden de Compra (Fechas, Importes, Estatus, Comprador, Solicitante)
- Vínculo al Contrato / Subcontrato (CLAVE fundamental, Ref, nombre, contratista, vigencia)
- Vínculo a la Estimación de Obra (Número de estimación, usuario que calculó, fecha)
- Deducciones y Amortizaciones aplicadas (Anticipos, Fondo de Garantía)
- Insumos y Conceptos estimados (Clave insumo, descripción, cantidad avance, P.U., importe total)

INCLUYE FALLBACK EN VIVO (LIVE CLOUD):
Si la OC fue creada hoy o no se encuentra en el snapshot local (Aryve2),
se consulta en tiempo real al servidor oficial de Enkontrol Cloud [10.11.0.5,1433].
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional

try:
    from Shared.config import es_modo_master
except ImportError:
    def es_modo_master() -> bool:
        return True

SQL_SERVER_HOST = "10.30.0.2"
SQL_SERVER_PORT = 1433
SQL_SERVER_DB = "Aryve2"
SQL_SERVER_USER = "sa"
SQL_SERVER_PASS = "Aryve2025*"


class OcContratoService:
    @classmethod
    def _obtener_candidatos_torre(cls) -> List[str]:
        """Obtiene la lista de URLs para consultar a la Torre Master desde clientes."""
        candidatos = []
        env_url = os.getenv("TORRE_CHAT_URL") or os.getenv("TORRE_URL")
        if env_url:
            candidatos.append(env_url.rstrip("/"))

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        data_dir = os.path.join(base_dir, "data")
        for p in [os.path.join(base_dir, "conexion_torre.json"), os.path.join(data_dir, "conexion_torre.json")]:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    puerto = cfg.get("puerto", 8000)
                    if cfg.get("ip_torre"):
                        candidatos.append(f"http://{cfg['ip_torre']}:{puerto}")
                    if cfg.get("hostname_torre"):
                        candidatos.append(f"http://{cfg['hostname_torre']}:{puerto}")
                    for ip in cfg.get("ips_conocidas", []):
                        candidatos.append(f"http://{ip}:{puerto}")
                except Exception:
                    pass

        candidatos.extend([
            "http://10.10.200.31:8000",
            "http://Esteban:8000",
            "http://10.10.200.147:8000",
            "http://127.0.0.1:8000"
        ])

        vistos = set()
        unicos = []
        for c in candidatos:
            c_clean = c.rstrip("/")
            if c_clean not in vistos:
                vistos.add(c_clean)
                unicos.append(c_clean)
        return unicos

    @classmethod
    def _consultar_via_master(cls, folio, clave, obra, compania) -> Dict[str, Any]:
        """Consulta el endpoint de la Torre Master desde clientes sin pyodbc ni acceso a base de datos."""
        params = {}
        if folio: params["folio"] = str(folio)
        if clave: params["clave"] = str(clave)
        if obra: params["obra"] = str(obra)
        if compania: params["compania"] = str(compania)
        qs = urllib.parse.urlencode(params)

        for host in cls._obtener_candidatos_torre():
            url = f"{host}/api/oc-contratos/consultar?{qs}"
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "DashboardClient/1.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if isinstance(data, dict):
                            return data
            except Exception:
                continue

        criterio = f"'{folio}'" if folio else f"clave '{clave}'"
        return {
            "ok": False,
            "mensaje": f"No se pudo consultar {criterio} desde la versión de equipo. Verifica que la Torre Master (Esteban / 10.10.200.31) esté encendida."
        }

    @classmethod
    def _get_connection(cls):
        try:
            import pyodbc
        except ImportError:
            raise RuntimeError("pyodbc no está instalado en este equipo. En modo Cliente se consulta a través de la Torre Master.")

        conn_str = (
            f"Driver={{SQL Server}};"
            f"Server={SQL_SERVER_HOST},{SQL_SERVER_PORT};"
            f"Database={SQL_SERVER_DB};"
            f"UID={SQL_SERVER_USER};"
            f"PWD={SQL_SERVER_PASS};"
        )
        return pyodbc.connect(conn_str, timeout=5)

    @classmethod
    def _to_float(cls, val):
        return float(val) if val is not None else 0.0

    @classmethod
    def consultar(
        cls,
        folio: Optional[str] = None,
        clave: Optional[str] = None,
        obra: Optional[str] = None,
        compania: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Busca una OC por folio exacto, número o clave de contrato (ej. ELEC, MYM).
        1. Si es modo Cliente o no hay pyodbc, consulta vía HTTP a la Torre Master.
        2. En Master: Intenta en Aryve2 (snapshot ultra rápido) y luego fallback en vivo a Enkontrol Cloud.
        """
        folio = str(folio).strip() if (folio and isinstance(folio, (str, int))) else None
        clave = str(clave).strip().upper() if (clave and isinstance(clave, str)) else None
        obra = str(obra).strip().upper() if (obra and isinstance(obra, str)) else None
        if not isinstance(compania, int) and not (isinstance(compania, str) and compania.isdigit()):
            compania = None
        elif isinstance(compania, str):
            compania = int(compania)

        if not folio and not clave:
            return {"ok": False, "mensaje": "Ingresa el Folio de la OC o la Clave del Contrato (ej. ELEC, MYM, PLOM)."}

        # Verificar si pyodbc está instalado
        try:
            import pyodbc
            tiene_pyodbc = True
        except ImportError:
            tiene_pyodbc = False

        # Si no hay pyodbc disponible, consultar vía Master Torre como respaldo
        if not tiene_pyodbc:
            return cls._consultar_via_master(folio=folio, clave=clave, obra=obra, compania=compania)

        try:
            # 1. Intentar primero directo en Aryve2
            resultado_local = cls._consultar_aryve2(folio=folio, clave=clave, obra=obra, compania=compania)
            if resultado_local.get("ok"):
                return resultado_local

            # 2. Si no se encontró en Aryve2, consultar en vivo a Enkontrol Cloud [10.11.0.5]
            resultado_live = cls._consultar_live_cloud(folio=folio, clave=clave, obra=obra, compania=compania)
            if resultado_live.get("ok"):
                return resultado_live
        except Exception:
            if not es_modo_master():
                return cls._consultar_via_master(folio=folio, clave=clave, obra=obra, compania=compania)
            raise

        # Si ninguno lo encontró, retornar el mensaje amigable
        criterio = f"'{folio}'" if folio else f"clave '{clave}'"
        return {
            "ok": False,
            "mensaje": f"No se encontró ninguna Orden de Compra para {criterio}" + (f" en la obra '{obra}'" if obra else "") + " (verificado en Aryve2 y en Enkontrol Cloud en vivo)."
        }

    @classmethod
    def _consultar_aryve2(cls, folio, clave, obra, compania) -> Dict[str, Any]:
        try:
            conn = cls._get_connection()
            cur = conn.cursor()

            where_clauses = []
            params = []

            if clave:
                where_clauses.append("(c.clave = ? OR c.clave LIKE ?)")
                params.extend([clave, f"%{clave}%"])

            if folio:
                folio_clean = folio.upper()
                es_numero_puro = folio_clean.replace("#", "").isdigit()

                if es_numero_puro:
                    num = int(folio_clean.replace("#", ""))
                    folio_pattern = f"%-{num:08d}"
                    where_clauses.append("(oc.folio LIKE ? OR oc.folio LIKE ? OR c.correlativo = ? OR c.id = ?)")
                    params.extend([folio_pattern, f"%{num}%", num, num])
                else:
                    where_clauses.append("(oc.folio = ? OR oc.folio LIKE ? OR c.clave = ? OR c.clave LIKE ?)")
                    params.extend([folio_clean, f"%{folio_clean}%", folio_clean, f"%{folio_clean}%"])

            if obra:
                where_clauses.append("(cc.clave = ? OR o.clave = ? OR oc.folio LIKE ?)")
                params.extend([obra, obra, f"{obra}-%"])

            if compania:
                where_clauses.append("oc.idcompania = ?")
                params.append(compania)

            where_sql = " AND ".join(where_clauses)

            query_oc = f"""
                SELECT TOP 25
                    oc.id as oc_id,
                    oc.folio as oc_folio,
                    oc.fecha as oc_fecha,
                    oc.origen as oc_origen,
                    oc.importe as oc_importe,
                    oc.retencionesamortizaciones as oc_amortizaciones,
                    oc.subtotal as oc_subtotal,
                    oc.impuestostrasladados as oc_iva,
                    oc.impuestosretenidos as oc_retenciones,
                    oc.total as oc_total,
                    oc.solicitante,
                    oc.creadopor as comprador,
                    oc.autorizadopor,
                    oc.fechaautorizacion,
                    oc.estatussurtido,
                    oc.autorizacion,
                    oc.idcompania,
                    cia.razon_social as compania_nombre,
                    cia.clave as compania_clave,
                    cc.clave as cc_clave,
                    cc.nombre as cc_nombre,
                    o.id as obra_id,
                    o.clave as obra_clave,
                    o.nombre as obra_nombre,
                    prov.id as contratista_id,
                    prov.clave as contratista_clave,
                    prov.nombre as contratista_nombre,
                    prov.rfc as contratista_rfc,
                    oc.idorigen,
                    est.id as estimacion_id,
                    est.numestimacion,
                    est.fechacalculo as estimacion_fecha,
                    est.montoavance as estimacion_monto,
                    est.usuario as estimacion_usuario,
                    est.usuariocalculo as estimacion_usuario_calculo,
                    est.estatusavance as estimacion_estatus,
                    c.id as contrato_id,
                    c.clave as contrato_clave,
                    c.correlativo as contrato_correlativo,
                    c.nombre as contrato_nombre,
                    c.tipocontratacion,
                    c.fechacreado as contrato_fechacreado
                FROM ordenes_compra_ek10 oc
                LEFT JOIN companias cia ON oc.idcompania = cia.id
                LEFT JOIN centroscosto cc ON oc.idcentrocosto = cc.id
                LEFT JOIN obras o ON cc.id = o.idcentrocosto
                LEFT JOIN contratistas prov ON oc.idproveedor = prov.idproveedor
                LEFT JOIN estimacion_obra est ON (oc.origen = 'Estimación' AND oc.idorigen = est.id)
                LEFT JOIN obra_contratos c ON est.idcontratacion = c.id
                WHERE {where_sql}
                ORDER BY oc.fecha DESC
            """

            cur.execute(query_oc, params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

            if not rows:
                conn.close()
                return {"ok": False}

            oc_principal = rows[0]
            if folio:
                folio_upper = folio.upper()
                for r in rows:
                    if r["oc_folio"].strip().upper() == folio_upper:
                        oc_principal = r
                        break

            oc_data = {
                "id": oc_principal["oc_id"],
                "folio": oc_principal["oc_folio"],
                "fecha": str(oc_principal["oc_fecha"])[:19] if oc_principal["oc_fecha"] else None,
                "origen": oc_principal["oc_origen"] or "Desconocido",
                "importe": cls._to_float(oc_principal["oc_importe"]),
                "amortizaciones": cls._to_float(oc_principal["oc_amortizaciones"]),
                "subtotal": cls._to_float(oc_principal["oc_subtotal"]),
                "iva": cls._to_float(oc_principal["oc_iva"]),
                "retenciones": cls._to_float(oc_principal["oc_retenciones"]),
                "total": cls._to_float(oc_principal["oc_total"]),
                "solicitante": oc_principal["solicitante"] or "N/D",
                "comprador": oc_principal["comprador"] or "N/D",
                "autorizador": oc_principal["autorizadopor"],
                "fecha_autorizacion": str(oc_principal["fechaautorizacion"])[:19] if oc_principal["fechaautorizacion"] else None,
                "estatus_surtido": oc_principal["estatussurtido"] or "En Proceso",
                "estatus_autorizacion": oc_principal["autorizacion"] or "Sin Autorizar",
                "compania": {
                    "id": oc_principal["idcompania"],
                    "clave": oc_principal["compania_clave"],
                    "nombre": oc_principal["compania_nombre"] or f"Compañía {oc_principal['idcompania']}"
                },
                "centro_costo": {
                    "clave": oc_principal["cc_clave"],
                    "nombre": oc_principal["cc_nombre"]
                },
                "obra": {
                    "id": oc_principal["obra_id"],
                    "clave": oc_principal["obra_clave"],
                    "nombre": oc_principal["obra_nombre"] or oc_principal["cc_nombre"]
                },
                "contratista": {
                    "id": oc_principal["contratista_id"],
                    "clave": oc_principal["contratista_clave"],
                    "nombre": oc_principal["contratista_nombre"] or "N/D",
                    "rfc": oc_principal["contratista_rfc"]
                }
            }

            es_estimacion = (oc_principal["oc_origen"] == "Estimación") and (oc_principal["estimacion_id"] is not None)

            contrato_data = None
            estimacion_data = None
            insumos = []
            deducciones = []

            if es_estimacion:
                est_id = oc_principal["estimacion_id"]
                contrato_id = oc_principal["contrato_id"]

                estimacion_data = {
                    "id": est_id,
                    "numero": oc_principal["numestimacion"],
                    "folio_completo": f"{oc_principal['numestimacion']}-{est_id}",
                    "fecha_calculo": str(oc_principal["estimacion_fecha"])[:19] if oc_principal["estimacion_fecha"] else None,
                    "monto_avance": cls._to_float(oc_principal["estimacion_monto"]),
                    "usuario_creo": oc_principal["estimacion_usuario"],
                    "usuario_calculo": oc_principal["estimacion_usuario_calculo"],
                    "estatus": oc_principal["estimacion_estatus"]
                }

                if contrato_id:
                    contrato_data = {
                        "id": contrato_id,
                        "clave": oc_principal["contrato_clave"] or "N/D",
                        "correlativo": oc_principal["contrato_correlativo"],
                        "nombre": oc_principal["contrato_nombre"],
                        "tipo": oc_principal["tipocontratacion"] or "SUBCONTRATO",
                        "fecha_creado": str(oc_principal["contrato_fechacreado"])[:10] if oc_principal["contrato_fechacreado"] else None
                    }

                # Insumos de la Estimación
                cur.execute("""
                    SELECT 
                        d.id as detalle_id,
                        d.avance as cantidad,
                        d.precio,
                        (d.avance * d.precio) as importe,
                        d.capturo,
                        i.id as insumo_id,
                        i.clave as insumo_clave,
                        i.nombre as insumo_nombre,
                        u.descripcion as unidad_medida
                    FROM estimacion_obra_det d
                    LEFT JOIN ppto_insumos_kontrol pik ON d.idkontrolinsumo = pik.id
                    LEFT JOIN insumos i ON pik.idinsumo = i.id
                    LEFT JOIN unidadMedida u ON i.idunidadmedida = u.id
                    WHERE d.idestimacion = ?
                    ORDER BY d.id ASC
                """, (est_id,))
                cols_ins = [d[0] for d in cur.description]
                for r_ins in cur.fetchall():
                    row_ins = dict(zip(cols_ins, r_ins))
                    insumos.append({
                        "id": row_ins["detalle_id"],
                        "insumo_clave": row_ins["insumo_clave"] or "N/A",
                        "insumo_nombre": row_ins["insumo_nombre"] or "Insumo sin descripción",
                        "unidad": row_ins["unidad_medida"] or "PZA",
                        "cantidad": cls._to_float(row_ins["cantidad"]),
                        "precio": cls._to_float(row_ins["precio"]),
                        "importe": cls._to_float(row_ins["importe"]),
                        "capturo": row_ins["capturo"]
                    })

                # Deducciones / Anticipos
                if contrato_id:
                    cur.execute("""
                        SELECT 
                            id, concepto, conceptonombre, tipoconcepto, importe, porcentaje,
                            estatusretencion, estatusantret, observaciones, fechamovimiento
                        FROM contrato_anticipos_retenciones
                        WHERE idcontratacion = ?
                        ORDER BY fechamovimiento DESC
                    """, (contrato_id,))
                    cols_ded = [d[0] for d in cur.description]
                    for r_ded in cur.fetchall():
                        row_ded = dict(zip(cols_ded, r_ded))
                        deducciones.append({
                            "id": row_ded["id"],
                            "concepto": row_ded["concepto"] or row_ded["tipoconcepto"],
                            "nombre": row_ded["conceptonombre"] or row_ded["concepto"],
                            "importe": cls._to_float(row_ded["importe"]),
                            "porcentaje": cls._to_float(row_ded["porcentaje"]),
                            "estatus": row_ded["estatusretencion"] or row_ded["estatusantret"],
                            "observaciones": row_ded["observaciones"],
                            "fecha": str(row_ded["fechamovimiento"])[:10] if row_ded["fechamovimiento"] else None
                        })

            elif oc_principal["oc_origen"] == "Requisición":
                cur.execute("""
                    SELECT 
                        d.id as detalle_id, d.cantidad, d.precio, d.importe,
                        i.clave as insumo_clave, i.nombre as insumo_nombre,
                        u.descripcion as unidad_medida
                    FROM ordenes_compra_det_ek10 d
                    LEFT JOIN insumos i ON d.IdInsumo = i.id
                    LEFT JOIN unidadMedida u ON i.idunidadmedida = u.id
                    WHERE d.IdOrdenDeCompra = ?
                    ORDER BY d.id ASC
                """, (oc_principal["oc_id"],))
                cols_ins = [d[0] for d in cur.description]
                for r_ins in cur.fetchall():
                    row_ins = dict(zip(cols_ins, r_ins))
                    insumos.append({
                        "id": row_ins["detalle_id"],
                        "insumo_clave": row_ins["insumo_clave"] or "N/A",
                        "insumo_nombre": row_ins["insumo_nombre"] or "Insumo sin descripción",
                        "unidad": row_ins["unidad_medida"] or "PZA",
                        "cantidad": cls._to_float(row_ins["cantidad"]),
                        "precio": cls._to_float(row_ins["precio"]),
                        "importe": cls._to_float(row_ins["importe"]),
                        "capturo": oc_principal["comprador"]
                    })

            conn.close()

            otras_coincidencias = []
            if len(rows) > 1:
                for r in rows:
                    if r["oc_id"] != oc_principal["oc_id"]:
                        otras_coincidencias.append({
                            "id": r["oc_id"],
                            "folio": r["oc_folio"],
                            "obra": r["obra_clave"] or r["cc_clave"],
                            "fecha": str(r["oc_fecha"])[:10] if r["oc_fecha"] else None,
                            "contrato_clave": r["contrato_clave"] or "N/A",
                            "contrato_ref": r["contrato_id"],
                            "contrato_nombre": r["contrato_nombre"],
                            "contratista": r["contratista_nombre"],
                            "total": cls._to_float(r["oc_total"])
                        })

            return {
                "ok": True,
                "es_estimacion": es_estimacion,
                "origen_datos": "Snapshot Local (Aryve2)",
                "oc": oc_data,
                "contrato": contrato_data,
                "estimacion": estimacion_data,
                "insumos": insumos,
                "deducciones": deducciones,
                "otras_coincidencias": otras_coincidencias
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @classmethod
    def _consultar_live_cloud(cls, folio, clave, obra, compania) -> Dict[str, Any]:
        """Consulta en vivo al servidor Enkontrol Cloud [10.11.0.5,1433] para OCs recién creadas."""
        try:
            conn = cls._get_connection()
            cur = conn.cursor()

            # Normalizar folio
            folio_term = (folio or "").strip().upper()
            if folio_term and folio_term.replace("#", "").isdigit():
                num = int(folio_term.replace("#", ""))
                where_remoto = f"oc.folio LIKE ''%-{num:08d}''"
            elif folio_term:
                where_remoto = f"oc.folio = ''{folio_term}'' OR oc.folio LIKE ''%{folio_term}%''"
            elif clave:
                where_remoto = f"oc.folio LIKE ''%{clave}%''"
            else:
                conn.close()
                return {"ok": False}

            if obra:
                obra_clean = obra.strip().upper()
                where_remoto += f" AND (oc.[CentroCosto.Clave] = ''{obra_clean}'' OR oc.[Proyecto.Clave] = ''{obra_clean}'' OR oc.folio LIKE ''{obra_clean}-%'')"

            if compania:
                where_remoto += f" AND (oc.IdCompania = {compania} OR oc.[Compania.Clave] = ''{compania}'')"

            sql_remoto = f"""
                SELECT * FROM OPENQUERY([10.11.0.5,1433], '
                    SELECT TOP 10
                        oc.ID as oc_id,
                        oc.Folio as oc_folio,
                        oc.Fecha as oc_fecha,
                        oc.[TipoOrigen.Nombre] as oc_origen,
                        oc.Importe as oc_importe,
                        oc.RetencionesAmortizaciones as oc_amortizaciones,
                        oc.SubTotal as oc_subtotal,
                        oc.ImpuestosTrasladados as oc_iva,
                        oc.ImpuestosRetenidos as oc_retenciones,
                        oc.Total as oc_total,
                        oc.[Solicitante.NombreCompleto] as solicitante,
                        oc.[CreadoPor.NombreCompleto] as comprador,
                        oc.[EstatusSurtido.Nombre] as estatussurtido,
                        oc.[EstatusAutorizacion.Nombre] as autorizacion,
                        oc.IdCompania as idcompania,
                        oc.[Compania.Nombre] as compania_nombre,
                        oc.[Compania.Clave] as compania_clave,
                        oc.[CentroCosto.Clave] as cc_clave,
                        oc.[CentroCosto.Nombre] as cc_nombre,
                        oc.IdProyecto as obra_id,
                        oc.[Proyecto.Clave] as obra_clave,
                        oc.[Proyecto.Nombre] as obra_nombre,
                        oc.IdProveedor as contratista_id,
                        oc.[Proveedor.Clave] as contratista_clave,
                        oc.[Proveedor.NombreCompleto] as contratista_nombre,
                        oc.[Proveedor.RFC] as contratista_rfc,
                        oc.IdOrigen as idorigen,
                        oc.ID_EK9 as id_ek9
                    FROM EKCloudARYVE.dbo.uvw_soc_OrdenDeCompra oc
                    WHERE {where_remoto}
                    ORDER BY oc.Fecha DESC
                ')
            """

            cur.execute(sql_remoto)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

            if not rows:
                conn.close()
                return {"ok": False}

            oc_principal = rows[0]
            if folio_term:
                for r in rows:
                    if r["oc_folio"].strip().upper() == folio_term:
                        oc_principal = r
                        break

            oc_data = {
                "id": oc_principal["oc_id"],
                "folio": oc_principal["oc_folio"],
                "fecha": str(oc_principal["oc_fecha"])[:19] if oc_principal["oc_fecha"] else None,
                "origen": oc_principal["oc_origen"] or "Desconocido",
                "importe": cls._to_float(oc_principal["oc_importe"]),
                "amortizaciones": cls._to_float(oc_principal["oc_amortizaciones"]),
                "subtotal": cls._to_float(oc_principal["oc_subtotal"]),
                "iva": cls._to_float(oc_principal["oc_iva"]),
                "retenciones": cls._to_float(oc_principal["oc_retenciones"]),
                "total": cls._to_float(oc_principal["oc_total"]),
                "solicitante": oc_principal["solicitante"] or "N/D",
                "comprador": oc_principal["comprador"] or "N/D",
                "autorizador": "Enkontrol Cloud WF",
                "fecha_autorizacion": str(oc_principal["oc_fecha"])[:19] if oc_principal["oc_fecha"] else None,
                "estatus_surtido": oc_principal["estatussurtido"] or "En Proceso",
                "estatus_autorizacion": oc_principal["autorizacion"] or "Autorizada",
                "compania": {
                    "id": oc_principal["idcompania"],
                    "clave": oc_principal["compania_clave"],
                    "nombre": oc_principal["compania_nombre"] or f"Compañía {oc_principal['idcompania']}"
                },
                "centro_costo": {
                    "clave": oc_principal["cc_clave"],
                    "nombre": oc_principal["cc_nombre"]
                },
                "obra": {
                    "id": oc_principal["obra_id"],
                    "clave": oc_principal["obra_clave"],
                    "nombre": oc_principal["obra_nombre"] or oc_principal["cc_nombre"]
                },
                "contratista": {
                    "id": oc_principal["contratista_id"],
                    "clave": oc_principal["contratista_clave"],
                    "nombre": oc_principal["contratista_nombre"] or "N/D",
                    "rfc": oc_principal["contratista_rfc"]
                }
            }

            es_estimacion = (oc_principal["oc_origen"] == "Estimación") and (oc_principal["idorigen"] is not None)

            contrato_data = None
            estimacion_data = None
            insumos = []
            deducciones = []

            oc_id = oc_principal["oc_id"]

            # Consultar insumos live desde soc_OrdenDeCompra_Detalle en 10.11.0.5
            sql_insumos_live = f"""
                SELECT * FROM OPENQUERY([10.11.0.5,1433], '
                    SELECT 
                        d.id as detalle_id,
                        d.cantidad,
                        d.precio,
                        d.importe,
                        i.clave as insumo_clave,
                        i.nombre as insumo_nombre,
                        u.clave as unidad
                    FROM EKCloudARYVE.dbo.soc_OrdenDeCompra_Detalle d
                    LEFT JOIN EKCloudARYVE.dbo.scco_Insumo i ON d.idinsumo = i.id
                    LEFT JOIN EKCloudARYVE.dbo.UnidadMedida u ON i.idunidadmedida = u.id
                    WHERE d.idordendecompra = {oc_id}
                    ORDER BY d.id ASC
                ')
            """
            cur.execute(sql_insumos_live)
            cols_ins = [d[0] for d in cur.description]
            for r_ins in cur.fetchall():
                row_ins = dict(zip(cols_ins, r_ins))
                insumos.append({
                    "id": row_ins["detalle_id"],
                    "insumo_clave": row_ins["insumo_clave"] or "N/A",
                    "insumo_nombre": row_ins["insumo_nombre"] or "Insumo sin descripción",
                    "unidad": row_ins["unidad"] or "PZA",
                    "cantidad": cls._to_float(row_ins["cantidad"]),
                    "precio": cls._to_float(row_ins["precio"]),
                    "importe": cls._to_float(row_ins["importe"]),
                    "capturo": oc_principal["comprador"]
                })

            conn.close()

            otras_coincidencias = []
            if len(rows) > 1:
                for r in rows:
                    if r["oc_id"] != oc_principal["oc_id"]:
                        otras_coincidencias.append({
                            "id": r["oc_id"],
                            "folio": r["oc_folio"],
                            "obra": r["obra_clave"] or r["cc_clave"],
                            "fecha": str(r["oc_fecha"])[:10] if r["oc_fecha"] else None,
                            "contrato_clave": "N/D",
                            "contrato_ref": None,
                            "contrato_nombre": None,
                            "contratista": r["contratista_nombre"],
                            "total": cls._to_float(r["oc_total"])
                        })

            return {
                "ok": True,
                "es_estimacion": es_estimacion,
                "origen_datos": "Enkontrol Cloud En Vivo (10.11.0.5)",
                "oc": oc_data,
                "contrato": contrato_data,
                "estimacion": estimacion_data,
                "insumos": insumos,
                "deducciones": deducciones,
                "otras_coincidencias": otras_coincidencias
            }

        except Exception as e:
            return {"ok": False, "error": str(e)}
