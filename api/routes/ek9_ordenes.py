"""
API Route: Control y Visualización de Órdenes EK9 (EY0) y Detalle
Permite consultar, filtrar, editar campos y marcar avance antes de modificar el Excel.
"""

import json
import os
import threading
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/ek9", tags=["EK9 Órdenes EY0"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "ek9_ey0.json")
_lock = threading.Lock()


def _cargar_datos():
    if not os.path.exists(DATA_PATH):
        return {"ordenes": [], "detalle": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_datos(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    tmp_path = DATA_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_PATH)


class OrdenUpdate(BaseModel):
    ESTADO: Optional[str] = None
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


@router.get("/ordenes")
def obtener_ek9_ey0():
    """Retorna todas las órdenes EY0 y su detalle completo."""
    with _lock:
        data = _cargar_datos()
    return {
        "ok": True,
        "ordenes": data.get("ordenes", []),
        "detalle": data.get("detalle", []),
    }


@router.put("/ordenes/{numero}")
def actualizar_orden(numero: int, payload: OrdenUpdate):
    """Actualiza una orden EY0 y sincroniza campos compartidos en sus partidas de Detalle."""
    with _lock:
        data = _cargar_datos()
        ordenes = data.get("ordenes", [])
        target = next((o for o in ordenes if int(o.get("NUMERO", -1)) == numero), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"Orden EY0 #{numero} no encontrada")

        cambios = payload.model_dump(exclude_unset=True)
        for k, v in cambios.items():
            target[k] = v

        # Sincronizar folios/estado en las filas de Detalle del mismo NUMERO
        campos_sync = ("ESTADO", "REQUISICION_EK10", "COMPLEMENTO", "ORDEN_COMPRA_EK10", "VERIFICADO_ARYVE")
        if any(k in cambios for k in campos_sync):
            for d in data.get("detalle", []):
                if int(d.get("NUMERO", -1)) == numero:
                    for k in campos_sync:
                        if k in cambios:
                            d[k] = cambios[k]

        _guardar_datos(data)
        return {"ok": True, "orden": target}


@router.put("/detalle/{item_id}")
def actualizar_detalle(item_id: int, payload: DetalleUpdate):
    """Actualiza una partida específica de la hoja Detalle."""
    with _lock:
        data = _cargar_datos()
        detalle = data.get("detalle", [])
        target = next((d for d in detalle if int(d.get("id", -1)) == item_id), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"Partida de detalle #{item_id} no encontrada")

        cambios = payload.model_dump(exclude_unset=True)
        for k, v in cambios.items():
            target[k] = v

        _guardar_datos(data)
        return {"ok": True, "detalle": target}
