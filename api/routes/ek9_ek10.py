"""
API Route: Vista Unificada EK9 - EK10
Permite cargar un archivo XLSX dinámicamente, adaptarlo al formato de órdenes y detalle
(similar a EK9 - Órdenes EY0), editar/marcar partidas en sesión y limpiar para cargar otro XLSX.
"""

import io
import json
import os
import re
import threading
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.insumos_service import InsumosService
from core.oc_contrato_service import OcContratoService
from core.proveedores_ek10_service import ProveedoresEk10Service
from core.puffy_service import PuffyService

router = APIRouter(prefix="/api/ek9-ek10", tags=["EK9 - EK10"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "ek9_ek10_session.json")
_lock = threading.Lock()


def _estado_vacio() -> Dict[str, Any]:
    return {
        "cargado": False,
        "archivo_nombre": "",
        "hojas": [],
        "ordenes": [],
        "detalle": [],
    }


def _cargar_sesion() -> Dict[str, Any]:
    if not os.path.exists(DATA_PATH):
        return _estado_vacio()
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return _estado_vacio()
            return {
                "cargado": bool(data.get("cargado", False)),
                "archivo_nombre": data.get("archivo_nombre", ""),
                "hojas": data.get("hojas", []),
                "ordenes": data.get("ordenes", []),
                "detalle": data.get("detalle", []),
            }
    except Exception:
        return _estado_vacio()


def _guardar_sesion(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_PATH)


def _normalizar_clave(texto: Any) -> str:
    if texto is None:
        return ""
    s = str(texto).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()
    return s


def _a_numero(val: Any, default: Optional[float] = 0.0) -> Optional[float]:
    if val is None or val == "":
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("$", "").replace(",", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _a_entero(val: Any, default: int = 0) -> int:
    num = _a_numero(val, None)
    if num is None:
        return default
    return int(round(num))


def _a_texto(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    s = str(val).strip()
    if re.fullmatch(r"\d+\.0+", s):
        return s.split(".", 1)[0]
    return s


def _a_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    return str(val).strip().upper() in ("1", "TRUE", "SI", "SÍ", "YES", "X", "YA")


def _leer_hoja_como_dicts(ws) -> List[Dict[str, Any]]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # Buscar la fila de encabezados (primera fila con al menos 2 celdas no vacías)
    header_idx = 0
    for idx, row in enumerate(rows[:15]):
        non_empty = sum(1 for c in row if c is not None and str(c).strip() != "")
        if non_empty >= 2:
            header_idx = idx
            break

    raw_headers = rows[header_idx]
    headers = [_normalizar_clave(h) for h in raw_headers]
    if not any(headers):
        return []

    registros: List[Dict[str, Any]] = []
    for row in rows[header_idx + 1:]:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        item: Dict[str, Any] = {}
        for col_idx, key in enumerate(headers):
            if not key:
                continue
            val = row[col_idx] if col_idx < len(row) else None
            item[key] = val
        if item:
            registros.append(item)
    return registros


def _mapear_orden(raw: Dict[str, Any], idx: int) -> Dict[str, Any]:
    numero = _a_entero(
        raw.get("NUMERO") or raw.get("NO_ORDEN") or raw.get("ORDEN") or raw.get("NUM"),
        idx + 1,
    )
    estado = _a_texto(raw.get("ESTADO") or raw.get("ESTATUS")).upper() or "SIN REQUISICION"
    return {
        "CC": _a_texto(raw.get("CC") or raw.get("CENTRO_COSTOS") or raw.get("OBRA") or "EY0"),
        "NUMERO": numero,
        "NOMBRE": _a_texto(raw.get("NOMBRE") or raw.get("PROVEEDOR") or raw.get("RAZON_SOCIAL") or f"Orden #{numero}"),
        "CLAVE_PROVEEDOR": _a_texto(raw.get("CLAVE_PROVEEDOR") or raw.get("CLAVE_PROV") or raw.get("ID_PROVEEDOR")),
        "SUB_TOTAL": _a_numero(raw.get("SUB_TOTAL") if "SUB_TOTAL" in raw else raw.get("SUBTOTAL"), 0.0) or 0.0,
        "IVA": _a_numero(raw.get("IVA"), 0.0) or 0.0,
        "TOTAL": _a_numero(raw.get("TOTAL") if "TOTAL" in raw else raw.get("IMPORTE_TOTAL"), 0.0) or 0.0,
        "REQUISICION_EK10": _a_texto(raw.get("REQUISICION_EK10") or raw.get("REQUISICION")),
        "COMPLEMENTO": _a_texto(raw.get("COMPLEMENTO") or raw.get("SEGUNDA_REQUI")),
        "ORDEN_COMPRA_EK10": _a_texto(raw.get("ORDEN_COMPRA_EK10") or raw.get("ORDEN_DE_COMPRA_EK10") or raw.get("OC_EK10")),
        "ESTADO": estado,
        "VERIFICADO_ARYVE": _a_texto(raw.get("VERIFICADO_ARYVE")),
        "ORIGEN_REQUISICION": _a_texto(raw.get("ORIGEN_REQUISICION") or "XLSX"),
        "marcado_listo": _a_bool(raw.get("MARCADO_LISTO")),
        "notas_usuario": _a_texto(raw.get("NOTAS_USUARIO")),
    }


def _mapear_detalle(raw: Dict[str, Any], idx: int) -> Dict[str, Any]:
    numero = _a_entero(
        raw.get("NUMERO") or raw.get("NO_ORDEN") or raw.get("ORDEN") or raw.get("NUM"),
        0,
    )
    precio_ek10_raw = raw.get("PRECIO_EK10")
    precio_ek10 = _a_numero(precio_ek10_raw, None) if precio_ek10_raw not in (None, "") else None
    return {
        "id": _a_entero(raw.get("ID"), idx + 1) or (idx + 1),
        "CC": _a_texto(raw.get("CC") or raw.get("CENTRO_COSTOS") or "EY0"),
        "NUMERO": numero,
        "INSUMO": _a_texto(raw.get("INSUMO") or raw.get("CLAVE") or raw.get("CODIGO")),
        "DESCRIPCION": _a_texto(raw.get("DESCRIPCION") or raw.get("CONCEPTO") or raw.get("MATERIAL")),
        "FECHA_ENTREGA": _a_texto(raw.get("FECHA_ENTREGA")),
        "CANTIDAD": _a_numero(raw.get("CANTIDAD"), 0.0) or 0.0,
        "DISPONIBLE_NIVELES": _a_numero(raw.get("DISPONIBLE_NIVELES"), 0.0) or 0.0,
        "ADITIVA": _a_numero(raw.get("ADITIVA"), 0.0) or 0.0,
        "PRECIO_EK9": _a_numero(raw.get("PRECIO_EK9") if "PRECIO_EK9" in raw else raw.get("PRECIO"), 0.0) or 0.0,
        "PRECIO_EK10": precio_ek10,
        "IMPORTE": _a_numero(raw.get("IMPORTE") if "IMPORTE" in raw else raw.get("TOTAL"), 0.0) or 0.0,
        "REQUISICION_EK10": _a_texto(raw.get("REQUISICION_EK10") or raw.get("REQUISICION")),
        "COMPLEMENTO": _a_texto(raw.get("COMPLEMENTO")),
        "ORDEN_COMPRA_EK10": _a_texto(raw.get("ORDEN_COMPRA_EK10") or raw.get("ORDEN_DE_COMPRA_EK10") or raw.get("OC_EK10")),
        "ESTADO": _a_texto(raw.get("ESTADO") or raw.get("ESTATUS")).upper() or "SIN REQUISICION",
        "VERIFICADO_ARYVE": _a_texto(raw.get("VERIFICADO_ARYVE")),
        "ORIGEN_REQUISICION": _a_texto(raw.get("ORIGEN_REQUISICION") or "XLSX"),
        "EN_ARYVE": _a_numero(raw.get("EN_ARYVE"), 0.0) or 0.0,
        "FALTA_EN_ARYVE": _a_numero(raw.get("FALTA_EN_ARYVE"), 0.0) or 0.0,
        "ESTATUS_FALTANTE": _a_texto(raw.get("ESTATUS_FALTANTE")),
        "marcado_listo": _a_bool(raw.get("MARCADO_LISTO")),
        "notas_usuario": _a_texto(raw.get("NOTAS_USUARIO")),
    }


class OrdenUpdate(BaseModel):
    ESTADO: Optional[str] = None
    CLAVE_PROVEEDOR: Optional[str] = None
    REQUISICION_EK10: Optional[str] = None
    COMPLEMENTO: Optional[str] = None
    ORDEN_COMPRA_EK10: Optional[str] = None
    VERIFICADO_ARYVE: Optional[str] = None
    marcado_listo: Optional[bool] = None
    notas_usuario: Optional[str] = None


class DetalleUpdate(BaseModel):
    ESTATUS_FALTANTE: Optional[str] = None
    DISPONIBLE_NIVELES: Optional[float] = None
    ADITIVA: Optional[float] = None
    EN_ARYVE: Optional[float] = None
    FALTA_EN_ARYVE: Optional[float] = None
    REQUISICION_EK10: Optional[str] = None
    COMPLEMENTO: Optional[str] = None
    ORDEN_COMPRA_EK10: Optional[str] = None
    ESTADO: Optional[str] = None
    marcado_listo: Optional[bool] = None
    notas_usuario: Optional[str] = None
    partida_seleccionada: Optional[str] = None
    partida_seleccionada_nombre: Optional[str] = None
    partida_seleccionada_por_req: Optional[float] = None


def _recalcular_estado_orden(o: Dict[str, Any]) -> bool:
    """
    Si una orden ya tiene tanto REQUISICION_EK10 como ORDEN_COMPRA_EK10,
    actualiza su ESTADO a COMPLETA. Si solo tiene REQUISICION_EK10 y estaba en
    SIN REQUISICION, lo promueve a SIN ORDEN DE COMPRA.
    """
    req = str(o.get("REQUISICION_EK10") or "").strip()
    oc = str(o.get("ORDEN_COMPRA_EK10") or "").strip()
    estado_actual = str(o.get("ESTADO") or "").strip().upper()
    nuevo_estado = estado_actual

    if req and oc:
        nuevo_estado = "COMPLETA"
    elif req and not oc and estado_actual in ("", "SIN REQUISICION"):
        nuevo_estado = "SIN ORDEN DE COMPRA"

    if nuevo_estado != estado_actual:
        o["ESTADO"] = nuevo_estado
        if nuevo_estado == "COMPLETA" and not str(o.get("VERIFICADO_ARYVE") or "").startswith("COMPLETA"):
            o["VERIFICADO_ARYVE"] = "COMPLETA · COMPRADA"
        return True
    return False


def _asegurar_claves_proveedor(ordenes: List[Dict[str, Any]], detalle: Optional[List[Dict[str, Any]]] = None) -> int:
    """Asegura catálogo local, restaura folios fijos (Requi/OC) y normaliza ESTADO."""
    if not ordenes:
        return 0
    if ProveedoresEk10Service.estado().get("total", 0) == 0:
        ProveedoresEk10Service.sincronizar_desde_enkontrol()

    folios_fijos = PuffyService.cargar_folios_fijos()
    actualizadas = 0
    mapa_ordenes: Dict[int, Dict[str, Any]] = {}

    for o in ordenes:
        if not o.get("CLAVE_PROVEEDOR") and o.get("NOMBRE"):
            match = ProveedoresEk10Service.buscar(o["NOMBRE"], limit=1).get("mejor")
            if match and match.get("clave"):
                o["CLAVE_PROVEEDOR"] = match["clave"]
                actualizadas += 1

        key_folio = f"{str(o.get('CC') or 'EY0').strip().upper()}_{int(o.get('NUMERO', 0))}"
        fijo = folios_fijos.get(key_folio)
        if fijo:
            if fijo.get("folio") and o.get("REQUISICION_EK10") != fijo["folio"]:
                o["REQUISICION_EK10"] = fijo["folio"]
                actualizadas += 1
            if fijo.get("requi_fija") and not o.get("requi_fija_puffy"):
                o["requi_fija_puffy"] = True
                actualizadas += 1
            if fijo.get("oc") and o.get("ORDEN_COMPRA_EK10") != fijo["oc"]:
                o["ORDEN_COMPRA_EK10"] = fijo["oc"]
                actualizadas += 1

        if _recalcular_estado_orden(o):
            actualizadas += 1

        mapa_ordenes[int(o.get("NUMERO", -1))] = o

    if detalle:
        for d in detalle:
            o = mapa_ordenes.get(int(d.get("NUMERO", -1)))
            if o:
                for k in ("ESTADO", "REQUISICION_EK10", "ORDEN_COMPRA_EK10", "VERIFICADO_ARYVE"):
                    if o.get(k) is not None and d.get(k) != o.get(k):
                        d[k] = o[k]
                        actualizadas += 1

    return actualizadas


@router.get("/estado")
def obtener_estado():
    """Retorna el estado actual del archivo XLSX cargado en EK9 - EK10."""
    with _lock:
        data = _cargar_sesion()
        if data.get("cargado") and data.get("ordenes"):
            if _asegurar_claves_proveedor(data["ordenes"], data.get("detalle")) > 0:
                _guardar_sesion(data)
    return {"ok": True, **data}


@router.post("/cargar-xlsx")
async def cargar_xlsx(archivo: UploadFile = File(...)):
    """Procesa un archivo XLSX y lo adapta al formato interactivo de órdenes y detalle."""
    nombre = archivo.filename or "archivo.xlsx"
    if not nombre.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Sube un archivo .xlsx o .xlsm",
        )

    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el Excel: {exc}")

    hojas = wb.sheetnames
    if not hojas:
        raise HTTPException(status_code=400, detail="El archivo Excel no contiene hojas")

    hoja_ordenes = None
    hoja_detalle = None

    for h in hojas:
        norm = _normalizar_clave(h)
        if hoja_ordenes is None and any(k in norm for k in ("ORDEN", "EY0", "RESUMEN", "CABECERA")):
            hoja_ordenes = h
        elif hoja_detalle is None and any(k in norm for k in ("DETALLE", "PARTIDA", "INSUMO", "MATERIAL")):
            hoja_detalle = h

    if hoja_ordenes is None:
        hoja_ordenes = hojas[0]
    if hoja_detalle is None and len(hojas) > 1:
        hoja_detalle = next((h for h in hojas if h != hoja_ordenes), None)

    raw_ordenes = _leer_hoja_como_dicts(wb[hoja_ordenes]) if hoja_ordenes else []
    raw_detalle = _leer_hoja_como_dicts(wb[hoja_detalle]) if hoja_detalle else []

    # Si solo había 1 hoja y parece ser de detalle (tiene INSUMO), sintetizar órdenes por NUMERO
    if not raw_detalle and raw_ordenes and any("INSUMO" in r for r in raw_ordenes[:5]):
        raw_detalle = raw_ordenes
        agrupadas: Dict[int, Dict[str, Any]] = {}
        for idx, r in enumerate(raw_detalle):
            num = _a_entero(r.get("NUMERO") or r.get("ORDEN"), idx + 1)
            if num not in agrupadas:
                agrupadas[num] = {
                    "CC": r.get("CC") or "EY0",
                    "NUMERO": num,
                    "NOMBRE": r.get("NOMBRE") or r.get("PROVEEDOR") or f"Orden #{num}",
                    "SUB_TOTAL": 0.0,
                    "IVA": 0.0,
                    "TOTAL": 0.0,
                    "REQUISICION_EK10": r.get("REQUISICION_EK10"),
                    "COMPLEMENTO": r.get("COMPLEMENTO"),
                    "ORDEN_COMPRA_EK10": r.get("ORDEN_COMPRA_EK10"),
                    "ESTADO": r.get("ESTADO") or "SIN REQUISICION",
                }
            imp = _a_numero(r.get("IMPORTE"), 0.0) or 0.0
            agrupadas[num]["SUB_TOTAL"] += imp
            agrupadas[num]["TOTAL"] += imp
        raw_ordenes = list(agrupadas.values())

    ordenes = [_mapear_orden(r, i) for i, r in enumerate(raw_ordenes)]
    detalle = [_mapear_detalle(r, i) for i, r in enumerate(raw_detalle)]

    # Deduplicar por NUMERO en ordenes si hubiera repetidos accidentales manteniendo el primero
    vistas_num = set()
    ordenes_unicas = []
    for o in ordenes:
        if o["NUMERO"] not in vistas_num:
            vistas_num.add(o["NUMERO"])
            ordenes_unicas.append(o)

    _asegurar_claves_proveedor(ordenes_unicas, detalle)

    sesion = {
        "cargado": True,
        "archivo_nombre": nombre,
        "hojas": hojas,
        "ordenes": ordenes_unicas,
        "detalle": detalle,
    }

    with _lock:
        _guardar_sesion(sesion)

    return {"ok": True, **sesion}


@router.post("/limpiar")
def limpiar_sesion():
    """Limpia los datos cargados del XLSX y deja la vista lista para cargar otro."""
    vacio = _estado_vacio()
    with _lock:
        _guardar_sesion(vacio)
    return {"ok": True, **vacio}


@router.put("/ordenes/{numero}")
def actualizar_orden(numero: int, payload: OrdenUpdate):
    """Actualiza una orden de la sesión EK9 - EK10 y sincroniza campos en sus partidas."""
    with _lock:
        data = _cargar_sesion()
        ordenes = data.get("ordenes", [])
        target = next((o for o in ordenes if int(o.get("NUMERO", -1)) == numero), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"Orden #{numero} no encontrada")

        cambios = payload.model_dump(exclude_unset=True)
        for k, v in cambios.items():
            target[k] = v

        _recalcular_estado_orden(target)

        if "REQUISICION_EK10" in cambios or "ORDEN_COMPRA_EK10" in cambios:
            PuffyService.guardar_folio_fijo(
                cc=target.get("CC") or "EY0",
                numero=numero,
                folio=target.get("REQUISICION_EK10") if "REQUISICION_EK10" in cambios else None,
                oc=target.get("ORDEN_COMPRA_EK10") if "ORDEN_COMPRA_EK10" in cambios else None,
            )

        campos_sync = ("ESTADO", "REQUISICION_EK10", "COMPLEMENTO", "ORDEN_COMPRA_EK10", "VERIFICADO_ARYVE")
        if any(k in cambios for k in campos_sync) or "REQUISICION_EK10" in cambios or "ORDEN_COMPRA_EK10" in cambios:
            for d in data.get("detalle", []):
                if int(d.get("NUMERO", -1)) == numero:
                    for k in campos_sync:
                        if target.get(k) is not None:
                            d[k] = target.get(k)

        _guardar_sesion(data)
        return {"ok": True, "orden": target}


@router.put("/detalle/{item_id}")
def actualizar_detalle(item_id: int, payload: DetalleUpdate):
    """Actualiza una partida específica del detalle en la sesión EK9 - EK10."""
    with _lock:
        data = _cargar_sesion()
        detalle = data.get("detalle", [])
        target = next((d for d in detalle if int(d.get("id", -1)) == item_id), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"Partida #{item_id} no encontrada")

        cambios = payload.model_dump(exclude_unset=True)
        for k, v in cambios.items():
            target[k] = v

        _guardar_sesion(data)
        return {"ok": True, "detalle": target}


@router.get("/consultar-presupuesto")
def consultar_presupuesto_insumo(
    obra: str = Query(..., description="Clave de la obra, ej. EY0"),
    insumo: str = Query(..., description="Clave del insumo, ej. 1170001"),
    cantidad: float = Query(0.0, description="Cantidad solicitada para comparar disponibilidad"),
    forzar: bool = Query(False, description="Forzar recarga en vivo desde Aryve"),
):
    """
    Consulta un insumo en el Centro de Presupuestos, Insumos & OCs (InsumosService)
    y devuelve en qué niveles/partidas aparece, ordenados para identificar el más cercano
    que cubre o sobrepasa la cantidad solicitada.
    """
    obra_clean = str(obra or "").strip().upper()
    insumo_clean = _a_texto(insumo).upper()
    if not obra_clean or not insumo_clean:
        raise HTTPException(status_code=400, detail="Se requiere obra e insumo para consultar.")

    try:
        reporte = InsumosService.consultar_reporte(
            obra=obra_clean,
            insumo=insumo_clean,
            forzar_recarga=forzar,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al consultar presupuesto: {exc}")

    partidas_raw = reporte.get("partidas", []) or []
    coincidencias: List[Dict[str, Any]] = []

    for p in partidas_raw:
        fr = p.get("frente") or {}
        p_codigo = _a_texto(p.get("codigo"))
        p_nombre = _a_texto(p.get("nombre"))
        p_nivel = _a_texto(p.get("nivel"))
        f_codigo = _a_texto(fr.get("codigo"))
        f_nombre = _a_texto(fr.get("nombre"))

        for ins in p.get("insumos", []) or []:
            clave = _a_texto(ins.get("clave")).upper()
            if clave != insumo_clean:
                continue

            ppto_real = float(ins.get("presupuesto_real") or 0.0)
            requisitado = float(ins.get("requisitado") or 0.0)
            comprado = float(ins.get("comprado") or 0.0)
            por_req = float(ins.get("por_requisitar") or 0.0)
            por_comp = float(ins.get("por_comprar") or 0.0)
            cubre = por_req >= cantidad if cantidad > 0 else por_req > 0

            coincidencias.append({
                "frente_codigo": f_codigo,
                "frente_nombre": f_nombre,
                "partida_codigo": p_codigo,
                "partida_nombre": p_nombre,
                "nivel": p_nivel,
                "insumo_clave": clave,
                "insumo_nombre": _a_texto(ins.get("nombre")),
                "unidad": _a_texto(ins.get("unidad")),
                "presupuesto_real": round(ppto_real, 4),
                "requisitado": round(requisitado, 4),
                "comprado": round(comprado, 4),
                "por_requisitar": round(por_req, 4),
                "por_comprar": round(por_comp, 4),
                "situacion": _a_texto(ins.get("situacion")),
                "cubre": cubre,
                "diferencia": round(por_req - cantidad, 4),
                "es_recomendado": False,
            })

    # Ordenar:
    # 1) Los que cubren (>= cantidad), del más cercano (menor exceso) al mayor
    # 2) Los que tienen > 0 pero no cubren, del más cercano (mayor por_requisitar) al menor
    # 3) Los que tienen <= 0
    def _orden_clave(item: Dict[str, Any]):
        por_req = item["por_requisitar"]
        if item["cubre"]:
            return (0, round(por_req - cantidad, 6), -por_req)
        if por_req > 0:
            return (1, round(cantidad - por_req, 6), -por_req)
        return (2, -por_req, 0)

    coincidencias.sort(key=_orden_clave)
    if coincidencias:
        coincidencias[0]["es_recomendado"] = True

    return {
        "ok": True,
        "obra": obra_clean,
        "insumo": insumo_clean,
        "cantidad": cantidad,
        "total_encontrados": len(coincidencias),
        "recomendado": coincidencias[0] if coincidencias else None,
        "partidas": coincidencias,
    }


@router.get("/proveedores/estado")
def estado_proveedores_ek10():
    """Devuelve el estado del catálogo local de proveedores EK10."""
    return {"ok": True, **ProveedoresEk10Service.estado()}


@router.post("/proveedores/sincronizar")
def sincronizar_proveedores_ek10():
    """
    Sincroniza el catálogo de proveedores desde Enkontrol 10 Cloud (EK-PROV-...),
    lo guarda localmente y autocompleta CLAVE_PROVEEDOR en las órdenes cargadas.
    """
    res = ProveedoresEk10Service.sincronizar_desde_enkontrol()
    if not res.get("ok"):
        raise HTTPException(status_code=502, detail=res.get("mensaje", "Error sincronizando proveedores EK10"))

    actualizadas = 0
    with _lock:
        data = _cargar_sesion()
        if data.get("cargado") and data.get("ordenes"):
            for o in data["ordenes"]:
                if not o.get("CLAVE_PROVEEDOR") and o.get("NOMBRE"):
                    match = ProveedoresEk10Service.buscar(o["NOMBRE"], limit=1).get("mejor")
                    if match and match.get("clave"):
                        o["CLAVE_PROVEEDOR"] = match["clave"]
                        actualizadas += 1
            if actualizadas > 0:
                _guardar_sesion(data)

    return {
        "ok": True,
        "total": res["total"],
        "actualizado": res["actualizado"],
        "ordenes_actualizadas": actualizadas,
    }


@router.get("/proveedores/buscar")
def buscar_proveedores_ek10(q: str = Query(..., min_length=1)):
    """Busca claves de proveedor EK-PROV-... en el catálogo local por nombre, clave o RFC."""
    res = ProveedoresEk10Service.buscar(q, limit=15)
    est = ProveedoresEk10Service.estado()
    return {
        "ok": True,
        "total_catalogo": est["total"],
        "actualizado": est["actualizado"],
        **res,
    }


class PuffyPrepararItem(BaseModel):
    insumo: str
    cantidad: float
    partida: Optional[str] = ""


class PuffyPrepararRequest(BaseModel):
    numero: int
    obra: str = "EY0"
    items: List[PuffyPrepararItem]
    contratacion: str = "MARY EK9_1"
    solicitante: str = "Yeudiel Esteban Richard Pérez"


class PuffyConfirmarRequest(BaseModel):
    numero: int
    cc: str = "EY0"
    accion_id: Any
    folio_tentativo: Optional[str] = ""


@router.post("/puffy/preparar-requisicion")
def puffy_preparar_requisicion(payload: PuffyPrepararRequest):
    """Envía los insumos checkeados (con su partida y faltante) a Puffy para preparar la requisición."""
    try:
        items = [it.model_dump() for it in payload.items]
        res = PuffyService.preparar_requisicion(
            obra=payload.obra,
            items=items,
            contratacion=payload.contratacion,
            solicitante=payload.solicitante,
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/puffy/confirmar-requisicion")
def puffy_confirmar_requisicion(payload: PuffyConfirmarRequest):
    """
    Confirma la requisición pendiente en Puffy (botón Like / Confirmar),
    fija el folio definitivo en REQUISICION_EK10 y lo guarda permanentemente.
    """
    try:
        res = PuffyService.confirmar_requisicion(accion_id=payload.accion_id, obra=payload.cc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    folio_final = (res.get("folio") or payload.folio_tentativo or "").strip().upper()
    orden_actualizada = None

    if folio_final:
        PuffyService.guardar_folio_fijo(payload.cc, payload.numero, folio=folio_final, requi_fija=True)
        with _lock:
            data = _cargar_sesion()
            target = next((o for o in data.get("ordenes", []) if int(o.get("NUMERO", -1)) == payload.numero), None)
            if target:
                target["REQUISICION_EK10"] = folio_final
                target["requi_fija_puffy"] = True
                _recalcular_estado_orden(target)
                for d in data.get("detalle", []):
                    if int(d.get("NUMERO", -1)) == payload.numero:
                        for k in ("ESTADO", "REQUISICION_EK10", "VERIFICADO_ARYVE"):
                            if target.get(k) is not None:
                                d[k] = target.get(k)
                _guardar_sesion(data)
                orden_actualizada = target

    return {
        "ok": True,
        "folio": folio_final,
        "respuesta": res.get("respuesta", ""),
        "orden": orden_actualizada,
    }


@router.get("/exportar-xlsx")
def exportar_xlsx_ek9_ek10():
    """
    Genera y descarga un archivo XLSX con las hojas 'Ordenes <CC>' y 'Detalle',
    reflejando todos los folios, estados actualizados (COMPLETA en verde, etc.)
    y partidas seleccionadas.
    """
    with _lock:
        data = _cargar_sesion()
        if not data.get("cargado") or not data.get("ordenes"):
            raise HTTPException(status_code=400, detail="No hay ningún archivo XLSX cargado para exportar.")
        _asegurar_claves_proveedor(data["ordenes"], data.get("detalle"))
        ordenes = data.get("ordenes", [])
        detalle = data.get("detalle", [])
        nombre_orig = data.get("archivo_nombre") or "EK9_EK10.xlsx"

    cc_principal = str(ordenes[0].get("CC") or "EY0").strip().upper() if ordenes else "EY0"

    wb = openpyxl.Workbook()
    ws_ord = wb.active
    ws_ord.title = f"Ordenes {cc_principal}"[:31]
    ws_det = wb.create_sheet("Detalle")

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    fill_completa = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    font_completa = Font(bold=True, color="006100", size=10)
    fill_sin_req = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    font_sin_req = Font(bold=True, color="9C0006", size=10)
    fill_pendiente = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    font_pendiente = Font(bold=True, color="9C6500", size=10)
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    def _estilar_estado(cell, estado_val: str):
        est = str(estado_val or "").strip().upper()
        if est == "COMPLETA":
            cell.fill = fill_completa
            cell.font = font_completa
        elif est == "SIN REQUISICION":
            cell.fill = fill_sin_req
            cell.font = font_sin_req
        else:
            cell.fill = fill_pendiente
            cell.font = font_pendiente

    # Hoja 1: Ordenes
    cols_ord = [
        "CC", "NUMERO", "NOMBRE", "CLAVE_PROVEEDOR", "SUB_TOTAL", "IVA", "TOTAL",
        "REQUISICION_EK10", "COMPLEMENTO", "ORDEN_COMPRA_EK10", "ESTADO",
        "VERIFICADO_ARYVE", "ORIGEN_REQUISICION", "NOTAS_USUARIO"
    ]
    ws_ord.append(cols_ord)
    for col_idx in range(1, len(cols_ord) + 1):
        c = ws_ord.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx, o in enumerate(ordenes, start=2):
        fila = [
            o.get("CC", ""),
            o.get("NUMERO", ""),
            o.get("NOMBRE", ""),
            o.get("CLAVE_PROVEEDOR", ""),
            float(o.get("SUB_TOTAL") or 0),
            float(o.get("IVA") or 0),
            float(o.get("TOTAL") or 0),
            o.get("REQUISICION_EK10", ""),
            o.get("COMPLEMENTO", ""),
            o.get("ORDEN_COMPRA_EK10", ""),
            o.get("ESTADO", ""),
            o.get("VERIFICADO_ARYVE", ""),
            o.get("ORIGEN_REQUISICION", ""),
            o.get("notas_usuario", ""),
        ]
        ws_ord.append(fila)
        for c_idx in range(1, len(cols_ord) + 1):
            cell = ws_ord.cell(row=r_idx, column=c_idx)
            cell.border = thin_border
            if c_idx in (5, 6, 7):
                cell.number_format = "#,##0.00"
        _estilar_estado(ws_ord.cell(row=r_idx, column=11), o.get("ESTADO", ""))

    ws_ord.freeze_panes = "A2"
    ws_ord.auto_filter.ref = f"A1:N{max(1, len(ordenes) + 1)}"

    # Hoja 2: Detalle
    cols_det = [
        "CC", "NUMERO", "INSUMO", "DESCRIPCION", "FECHA_ENTREGA", "CANTIDAD",
        "DISPONIBLE_NIVELES", "ADITIVA", "PRECIO_EK9", "PRECIO_EK10", "IMPORTE",
        "REQUISICION_EK10", "COMPLEMENTO", "ORDEN_COMPRA_EK10", "ESTADO",
        "VERIFICADO_ARYVE", "ORIGEN_REQUISICION", "EN_ARYVE", "FALTA_EN_ARYVE",
        "ESTATUS_FALTANTE", "PARTIDA_SELECCIONADA"
    ]
    ws_det.append(cols_det)
    for col_idx in range(1, len(cols_det) + 1):
        c = ws_det.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    for r_idx, d in enumerate(detalle, start=2):
        fila = [
            d.get("CC", ""),
            d.get("NUMERO", ""),
            _a_texto(d.get("INSUMO")),
            d.get("DESCRIPCION", ""),
            d.get("FECHA_ENTREGA", ""),
            float(d.get("CANTIDAD") or 0),
            float(d.get("DISPONIBLE_NIVELES") or 0),
            float(d.get("ADITIVA") or 0),
            float(d.get("PRECIO_EK9") or 0),
            d.get("PRECIO_EK10") if d.get("PRECIO_EK10") not in (None, "") else "",
            float(d.get("IMPORTE") or 0),
            d.get("REQUISICION_EK10", ""),
            d.get("COMPLEMENTO", ""),
            d.get("ORDEN_COMPRA_EK10", ""),
            d.get("ESTADO", ""),
            d.get("VERIFICADO_ARYVE", ""),
            d.get("ORIGEN_REQUISICION", ""),
            float(d.get("EN_ARYVE") or 0),
            float(d.get("FALTA_EN_ARYVE") or 0),
            d.get("ESTATUS_FALTANTE", ""),
            d.get("partida_seleccionada", ""),
        ]
        ws_det.append(fila)
        for c_idx in range(1, len(cols_det) + 1):
            cell = ws_det.cell(row=r_idx, column=c_idx)
            cell.border = thin_border
            if c_idx in (9, 10, 11) and cell.value != "":
                cell.number_format = "#,##0.00"
        _estilar_estado(ws_det.cell(row=r_idx, column=15), d.get("ESTADO", ""))

    ws_det.freeze_panes = "A2"
    ws_det.auto_filter.ref = f"A1:U{max(1, len(detalle) + 1)}"

    for ws in (ws_ord, ws_det):
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col[:200]:
                val_len = len(str(cell.value or ""))
                if val_len > max_len:
                    max_len = val_len
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 42)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    base_name = os.path.splitext(nombre_orig)[0]
    out_name = f"{base_name}_Actualizado.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


def _validar_requisicion_enkontrol(folio_req: str) -> Dict[str, Any]:
    """Consulta en Aryve2 / EKCloudARYVE si el folio de Requisición EK10 existe y su estatus."""
    folio_clean = str(folio_req or "").strip().upper()
    if not folio_clean:
        return {"consultada": False, "encontrada": False, "folio": "", "estatus": "", "mensaje": "Sin folio de requisición"}

    try:
        conn = OcContratoService._get_connection()
        cur = conn.cursor()
        # Intentar en snapshot local requisiciones_ek10
        for sql in (
            "SELECT TOP 1 folio, estatusautorizacion, estatus, fecha, solicitante FROM requisiciones_ek10 WHERE UPPER(LTRIM(RTRIM(folio))) = ?",
            "SELECT TOP 1 Folio as folio, [EstatusAutorizacion.Nombre] as estatusautorizacion, [Estatus.Nombre] as estatus, Fecha as fecha, [Solicitante.NombreCompleto] as solicitante FROM OPENQUERY([EK10_PROD], 'SELECT TOP 1 Folio, [EstatusAutorizacion.Nombre], [Estatus.Nombre], Fecha, [Solicitante.NombreCompleto] FROM EKCloudARYVE.dbo.uvw_soc_Requisicion WHERE Folio = ''" + folio_clean.replace("'", "''") + "''')",
        ):
            try:
                if "?" in sql:
                    cur.execute(sql, (folio_clean,))
                else:
                    cur.execute(sql)
                row = cur.fetchone()
                if row:
                    cols = [d[0].lower() for d in cur.description]
                    info = dict(zip(cols, row))
                    conn.close()
                    est_auth = str(info.get("estatusautorizacion") or info.get("estatus") or "Registrada")
                    vigente = "cancel" not in est_auth.lower()
                    return {
                        "consultada": True,
                        "encontrada": True,
                        "folio": str(info.get("folio") or folio_clean),
                        "vigente": vigente,
                        "estatus": est_auth,
                        "fecha": str(info.get("fecha") or "")[:10],
                        "solicitante": str(info.get("solicitante") or ""),
                    }
            except Exception:
                continue
        conn.close()
        return {
            "consultada": True,
            "encontrada": False,
            "folio": folio_clean,
            "vigente": False,
            "estatus": "No encontrada",
            "mensaje": f"No se encontró la requisición {folio_clean} en Enkontrol.",
        }
    except Exception as exc:
        return {
            "consultada": False,
            "encontrada": False,
            "folio": folio_clean,
            "vigente": False,
            "estatus": "Sin conexión",
            "mensaje": f"No se pudo consultar la requisición: {exc}",
        }


@router.get("/validar-oc/{numero}")
def validar_oc_enkontrol(numero: int):
    """
    Valida en Enkontrol (OcContratoService) si la ORDEN_COMPRA_EK10 de la orden #numero
    existe, está autorizada/vigente y si sus insumos y cantidades coinciden con el Detalle.
    """
    with _lock:
        data = _cargar_sesion()
        orden = next((o for o in data.get("ordenes", []) if int(o.get("NUMERO", -1)) == numero), None)
        if not orden:
            raise HTTPException(status_code=404, detail=f"Orden #{numero} no encontrada")
        folio_oc = str(orden.get("ORDEN_COMPRA_EK10") or "").strip().upper()
        if not folio_oc:
            raise HTTPException(status_code=400, detail="Esta orden aún no tiene folio de Orden Compra EK10.")
        detalle_orden = [d for d in data.get("detalle", []) if int(d.get("NUMERO", -1)) == numero]

    try:
        consulta = OcContratoService.consultar(folio=folio_oc)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error consultando Enkontrol: {exc}")

    if not consulta or not consulta.get("ok"):
        return {
            "ok": True,
            "encontrada": False,
            "folio": folio_oc,
            "mensaje": consulta.get("mensaje") if isinstance(consulta, dict) else f"No se encontró la OC {folio_oc} en Enkontrol.",
            "todos_correctos": False,
            "comparativa": [],
            "extras_en_oc": [],
        }

    oc_info = consulta.get("oc") or consulta.get("orden_compra") or {}
    insumos_oc = consulta.get("insumos") or []

    # Agrupar insumos de la OC en EK10 por clave normalizada
    mapa_oc: Dict[str, Dict[str, Any]] = {}
    for ins in insumos_oc:
        clave = _a_texto(ins.get("insumo_clave")).upper()
        if not clave:
            continue
        if clave not in mapa_oc:
            mapa_oc[clave] = {
                "clave": clave,
                "nombre": _a_texto(ins.get("insumo_nombre")),
                "cantidad": 0.0,
                "precio": float(ins.get("precio") or 0.0),
                "importe": 0.0,
            }
        mapa_oc[clave]["cantidad"] += float(ins.get("cantidad") or 0.0)
        mapa_oc[clave]["importe"] += float(ins.get("importe") or 0.0)

    comparativa: List[Dict[str, Any]] = []
    claves_esperadas = set()
    ok_count = 0
    diff_count = 0
    faltan_count = 0

    for d in detalle_orden:
        cant_esp = float(d.get("CANTIDAD") or 0.0)
        if cant_esp <= 0:
            continue
        clave = _a_texto(d.get("INSUMO")).upper()
        claves_esperadas.add(clave)
        oc_item = mapa_oc.get(clave)

        if not oc_item:
            faltan_count += 1
            comparativa.append({
                "insumo": clave,
                "descripcion": _a_texto(d.get("DESCRIPCION")),
                "cantidad_esperada": round(cant_esp, 4),
                "cantidad_oc": 0.0,
                "estatus": "FALTA_EN_OC",
            })
        else:
            cant_oc = round(oc_item["cantidad"], 4)
            if abs(cant_oc - cant_esp) <= 0.05:
                ok_count += 1
                est_ins = "OK"
            else:
                diff_count += 1
                est_ins = "DIFERENCIA_CANTIDAD"
            comparativa.append({
                "insumo": clave,
                "descripcion": _a_texto(d.get("DESCRIPCION")) or oc_item["nombre"],
                "cantidad_esperada": round(cant_esp, 4),
                "cantidad_oc": cant_oc,
                "estatus": est_ins,
            })

    extras_en_oc = [
        {"insumo": k, "descripcion": v["nombre"], "cantidad_oc": round(v["cantidad"], 4)}
        for k, v in mapa_oc.items()
        if k not in claves_esperadas
    ]

    est_auth = str(oc_info.get("estatus_autorizacion") or "Sin Autorizar")
    est_surt = str(oc_info.get("estatus_surtido") or "")
    vigente = "cancel" not in est_auth.lower() and "cancel" not in est_surt.lower()
    todos_correctos = vigente and len(comparativa) > 0 and diff_count == 0 and faltan_count == 0

    return {
        "ok": True,
        "encontrada": True,
        "folio": oc_info.get("folio") or folio_oc,
        "vigente": vigente,
        "estatus_autorizacion": est_auth,
        "estatus_surtido": est_surt,
        "total_oc": float(oc_info.get("total") or 0.0),
        "proveedor_oc": (oc_info.get("contratista") or {}).get("nombre") or "",
        "todos_correctos": todos_correctos,
        "resumen": {
            "total_esperados": len(comparativa),
            "ok": ok_count,
            "diferencias": diff_count,
            "faltantes": faltan_count,
            "extras": len(extras_en_oc),
        },
        "comparativa": comparativa,
        "extras_en_oc": extras_en_oc,
    }
