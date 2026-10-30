"""
Rutas API para el Módulo de Obras en Dashboard Intelligence Solutions.
Lectura y navegación ultrarrápida con Tablas de Hash en memoria RAM.
Integración con Microservicios de Insumos, Requisiciones y Órdenes de Compra (OCs).
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from core.obras_service import ObrasCoreService
from core.insumos_service import InsumosService
from core.ordenes_compra_service import OrdenesCompraService

router = APIRouter(prefix="/api/obras", tags=["Obras"])

@router.get("/metricas")
def obtener_metricas():
    """Devuelve las métricas globales del módulo Obras."""
    return ObrasCoreService.obtener_metricas()

@router.get("/catalogo")
def obtener_catalogo(q: Optional[str] = Query(None)):
    """
    Obtiene el listado ligero de todas las obras con totales de frentes, partidas y tarjetas.
    Tiempo de respuesta estimado: < 1ms.
    """
    return ObrasCoreService.obtener_catalogo(busqueda=q)

@router.get("/reporte-insumos")
def obtener_reporte_insumos(
    obra: str = Query(..., description="Clave de la obra, ej. AT1"),
    insumo: Optional[str] = Query(None, description="Clave específica de insumo"),
    nombre: Optional[str] = Query(None, description="Filtro de nombre de insumo"),
    forzar: bool = Query(False, description="Forzar descarga en vivo desde el servidor")
):
    """
    Consulta en vivo el árbol WBS de insumos por partida, frentes,
    presupuesto real, requisitado, comprado (OC) y pendientes.
    """
    try:
        reporte = InsumosService.consultar_reporte(
            obra=obra, 
            insumo=insumo, 
            nombre=nombre, 
            forzar_recarga=forzar
        )
        return reporte
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/movimientos")
def obtener_movimientos(
    obra: str = Query(..., description="Clave de la obra"),
    partida: str = Query(..., description="Código de la partida, ej. 1.7.1"),
    insumo: str = Query(..., description="Clave del insumo, ej. 1080003")
):
    """
    Devuelve el desglose detallado de Requisiciones y Órdenes de Compra en firme.
    """
    try:
        movs = InsumosService.consultar_movimientos(obra=obra, partida=partida, insumo=insumo)
        return movs
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ordenes-compra")
def buscar_ordenes_compra(
    obra: str = Query(..., description="Clave de obra/centro de costos, ej. GA4"),
    folio: str = Query(..., min_length=1, description="Folio OC, ej. GA4-00000794")
):
    """Busca órdenes por folio dentro de la obra seleccionada en la copia local."""
    try:
        return OrdenesCompraService.buscar_por_folio(obra=obra, folio=folio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/suministrar")
def ejecutar_suministro(payload: Dict[str, Any] = Body(...)):
    """
    Ejecuta el marcado de suministro en vivo para la obra especificada
    usando el token de autorización detectado en REA.
    """
    obra = payload.get("obra", "")
    if not obra:
        raise HTTPException(status_code=400, detail="Debe especificar la obra a suministrar.")
    try:
        res = InsumosService.actualizar_suministro_obra(obra=obra)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sincronizar-firestore-obra")
def sincronizar_firestore_obra(payload: Dict[str, Any] = Body(...)):
    """
    Guarda el reporte de la obra en Firebase Firestore para que CLIENTES lo use.
    """
    obra = payload.get("obra", "")
    if not obra:
        raise HTTPException(status_code=400, detail="Debe especificar la obra.")
    try:
        reporte = InsumosService.consultar_reporte(obra=obra)
        ok = InsumosService.sincronizar_firestore(obra=obra, datos_reporte=reporte)
        return {"ok": ok, "obra": obra, "mensaje": "Sincronizado en Firestore con éxito"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{clave_o_id}/arbol")
def obtener_arbol(clave_o_id: str):
    """
    Obtiene la jerarquía completa (Frentes -> Partidas -> Tarjetas) de una obra.
    Recuperación instantánea O(1) desde memoria RAM.
    """
    arbol = ObrasCoreService.obtener_arbol(clave_o_id)
    if not arbol:
        raise HTTPException(status_code=404, detail=f"No se encontró la obra '{clave_o_id}'.")
    return arbol

@router.post("/recargar")
def recargar_cache():
    """Fuerza la recarga del archivo obras.json en la memoria RAM."""
    return ObrasCoreService.recargar()

@router.post("/sincronizar-aryve")
def sincronizar_obras_aryve():
    """
    Conecta en vivo a la API de Aryve con la Llave Maestra, extrae los árboles
    de todas las obras, actualiza obras.json local y sincroniza automáticamente
    en la colección 'OBRAS' de Firebase Firestore.
    """
    # Versión cliente - lectura directa de Firebase
    try:
        resultado = {"obras": ObrasCoreService.obtener_catalogo()}
        ObrasCoreService.recargar()
        return {
            "ok": True,
            "total_obras": len(resultado.get("obras", [])),
            "total_frentes": resultado.get("metadata", {}).get("total_frentes", 0),
            "firebase_sync": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización: {e}")
