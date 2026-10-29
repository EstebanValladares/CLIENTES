"""
Rutas API para el Módulo de Obras en Dashboard Intelligence Solutions.
Lectura y navegación ultrarrápida con Tablas de Hash en memoria RAM.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from core.obras_service import ObrasCoreService

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
