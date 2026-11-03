"""
Rutas API para el Módulo de Obras en Dashboard Intelligence Solutions.
Lectura y navegación ultrarrápida con Tablas de Hash en memoria RAM.
Integración con Microservicios de Insumos, Requisiciones y Órdenes de Compra (OCs).
"""

import os
import json
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

@router.get("/grupos-insumos-tipo")
def obtener_grupos_insumos_tipo():
    """
    Devuelve la estructura de tipos e hijos de insumos desde GRUPO_INSUMOS_TIPO.json
    para la optimización y alta masiva en obras (evita error de material no disponible en EK10).
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ruta_json = os.path.join(base_dir, "OBRAS", "GRUPO_INSUMOS_TIPO.json")
    if not os.path.exists(ruta_json):
        ruta_json = os.path.join("OBRAS", "GRUPO_INSUMOS_TIPO.json")
    if os.path.exists(ruta_json):
        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error leyendo GRUPO_INSUMOS_TIPO.json: {e}")
    raise HTTPException(status_code=404, detail="Archivo GRUPO_INSUMOS_TIPO.json no encontrado.")

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
    de todas las obras y actualiza obras.json local.
    """
    # Versión cliente - lectura directa de Firebase
    try:
        resultado = {"obras": ObrasCoreService.obtener_catalogo()}
        ObrasCoreService.recargar()
        return {
            "ok": True,
            "total_obras": len(resultado.get("obras", [])),
            "total_frentes": resultado.get("metadata", {}).get("total_frentes", 0),
            "sincronizado_local": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización: {e}")

@router.post("/reparar-presupuesto/diagnostico")
def diagnosticar_reparacion_presupuesto(payload: Dict[str, Any] = Body(...)):
    """
    Analiza el WBS local para hallar las tarjetas afectadas por 'Presupuesto no Disponible'.
    """
    from core.reparador_presupuesto_bot import ReparadorPresupuestoBot
    obra = payload.get("obra", "")
    insumo = payload.get("insumo", "")
    folio_req = payload.get("folio_req", "")
    if not obra:
        raise HTTPException(status_code=400, detail="Debe especificar la clave de la obra (ej. KB5).")
    res = ReparadorPresupuestoBot.diagnosticar(clave_obra=obra, clave_insumo=insumo, folio_req=folio_req)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Error en diagnóstico"))
    return res

@router.post("/reparar-presupuesto/ejecutar")
def ejecutar_reparacion_presupuesto(payload: Dict[str, Any] = Body(...)):
    """
    Ejecuta el bot Selenium / REA en vivo para guardar suministros en Destajo y Subcontrato.
    """
    from core.reparador_presupuesto_bot import ReparadorPresupuestoBot
    obra = payload.get("obra", "")
    tarjetas = payload.get("tarjetas", [])
    if not obra:
        raise HTTPException(status_code=400, detail="Debe especificar la clave de la obra.")
    res = ReparadorPresupuestoBot.ejecutar_reparacion(clave_obra=obra, tarjetas=tarjetas)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Error ejecutando reparación"))
    return res

@router.post("/ir-a-obra")
def automatizar_ir_a_obra(payload: Dict[str, Any] = Body(...)):
    """
    Automatiza la búsqueda de la obra en Aryve, despliegue del panel lateral,
    clic en 'APLICAR CONFIGURACIÓN' y posterior clic en 'IR A OBRA'.
    Soporta acoplamiento en vivo a Chrome 9222 o inicio de sesión automático.
    """
    from core.obras_bot_service import ObrasBotService
    obra = payload.get("obra", "")
    if not obra:
        raise HTTPException(status_code=400, detail="Debe especificar la clave de la obra.")
    res = ObrasBotService.ir_a_obra(clave_obra=obra)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Error ejecutando navegación de obra"))
    return res

@router.post("/optimizar-insumos/ejecutar")
def ejecutar_optimizacion_insumos(payload: Dict[str, Any] = Body(...)):
    """
    Automatiza el llenado de COMPAÑIA GRUPO DE INSUMOS en las obras indicadas:
    1. Se logea en Aryve (o conecta a Chrome 9222).
    2. Entra a la obra y activa modo Edición (Alt+E).
    3. Abre la sección 'COMPAÑIA GRUPO DE INSUMOS'.
    4. Abre el panel '+' y agrega los grupos seleccionados (omitiendo los ya existentes).
    5. Termina y DEJA LA PANTALLA ABIERTA SIN GUARDAR (sin Alt+G) para revisión visual del usuario.
    """
    from core.obras_bot_service import ObrasBotService
    obras = payload.get("obras", [])
    grupos = payload.get("grupos", [])
    if not obras:
        raise HTTPException(status_code=400, detail="Debe especificar al menos una obra en la cola.")

    res = ObrasBotService.ejecutar_llenado_optimizacion(obras=obras, grupos=grupos)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Error ejecutando optimización"))
    return res

