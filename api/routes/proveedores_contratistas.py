"""
Rutas API para el Módulo Unificado de Proveedores y Contratistas (EK10 / Aryve).
"""

import os
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Any, List, Optional
from core.prov_contra_service import ProvContraService

router = APIRouter(prefix="/api/prov-contra", tags=["Proveedores & Contratistas Unificado"])


@router.get("/registros")
def obtener_registros():
    """Obtiene el listado completo de registros e historial enriquecido."""
    try:
        registros = ProvContraService.obtener_todos()
        en_revision = [r for r in registros if not r.get("en_historial")]
        en_historial = [r for r in registros if r.get("en_historial")]
        con_id_prov = [r for r in registros if r.get("id_ek10")]
        con_id_contra = [r for r in registros if r.get("id_contratista")]

        return {
            "registros": registros,
            "metricas": {
                "total": len(registros),
                "en_revision": len(en_revision),
                "en_historial": len(en_historial),
                "con_id_proveedor": len(con_id_prov),
                "con_id_contratista": len(con_id_contra)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo registros: {str(e)}")


@router.get("/registros/{id_registro}")
def obtener_detalle_registro(id_registro: int):
    reg = ProvContraService.obtener_por_id(id_registro, con_campos=True)
    if not reg:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return reg


@router.post("/consultar-db")
def consultar_por_numpro(payload: Dict[str, Any] = Body(...)):
    """Consulta directa a la base de datos de Enkontrol por número de proveedor."""
    numpro = payload.get("numpro", "").strip()
    if not numpro:
        raise HTTPException(status_code=400, detail="Debe ingresar un número de proveedor.")
    try:
        res = ProvContraService.consultar_base_ek10(numpro)
        return {"ok": True, "registro": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subir-captura")
def subir_captura(payload: Dict[str, Any] = Body(...)):
    """Sube una captura de Datos Generales (EK9) en Base64 y la procesa con OCR / DB."""
    try:
        import base64
        data_b64 = payload.get("imagen_base64", "")
        filename = payload.get("filename", "captura.png")
        lector = payload.get("lector", "db")

        if not data_b64:
            raise HTTPException(status_code=400, detail="No se recibió contenido de imagen.")

        if "," in data_b64:
            data_b64 = data_b64.split(",", 1)[1]

        contenido = base64.b64decode(data_b64)
        res = ProvContraService.procesar_captura(contenido, filename, lector=lector)
        return {"ok": True, "registro": res}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error procesando imagen: {str(e)}")


@router.put("/registros/{id_registro}")
def actualizar_registro(id_registro: int, payload: Dict[str, Any] = Body(...)):
    """Actualiza datos del CSV, casillas de alta o paso a historial."""
    try:
        actualizado = ProvContraService.guardar_registro(id_registro, payload)
        return {"ok": True, "registro": actualizado}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/registros/{id_registro}")
def eliminar_registro(id_registro: int):
    ok = ProvContraService.eliminar_registro(id_registro)
    if not ok:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"ok": True, "mensaje": "Registro eliminado exitosamente"}


@router.get("/imagen/{id_registro}")
def ver_imagen_registro(id_registro: int):
    reg = ProvContraService.obtener_por_id(id_registro)
    if not reg or not reg.get("imagen") or not os.path.exists(reg["imagen"]):
        raise HTTPException(status_code=404, detail="Imagen no disponible")
    return FileResponse(reg["imagen"])


@router.get("/csv/{id_registro}")
def descargar_csv_registro(id_registro: int):
    reg = ProvContraService.obtener_por_id(id_registro)
    if not reg or not reg.get("csv") or not os.path.exists(reg["csv"]):
        raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
    return FileResponse(reg["csv"], filename=reg.get("archivo_csv", "proveedor.csv"))


@router.post("/ejecutar")
def ejecutar_automatizacion(payload: Dict[str, Any] = Body(...)):
    """Inicia el bot Selenium para altas de proveedores y contratistas."""
    ids_prov = [int(i) for i in payload.get("proveedor", [])]
    ids_contra = [int(i) for i in payload.get("contratista", [])]
    ids_verif = [int(i) for i in payload.get("verificar", [])]
    guardar = bool(payload.get("guardar", False))

    if not ids_prov and not ids_contra and not ids_verif:
        raise HTTPException(status_code=400, detail="No se seleccionó ningún registro para ejecutar.")

    try:
        estado = ProvContraService.iniciar_trabajo(ids_prov, ids_contra, guardar=guardar, ids_verificar=ids_verif)
        return {"ok": True, "trabajo": estado}
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/trabajo")
def obtener_estado_trabajo(desde: int = Query(0, ge=0)):
    """Streaming de logs y estado en tiempo real del bot Selenium."""
    return ProvContraService.obtener_estado_trabajo(desde_linea=desde)


@router.post("/limpiar-terminal")
def limpiar_terminal_consola():
    ProvContraService.limpiar_terminal()
    return {"ok": True, "mensaje": "Consola terminal reiniciada."}
