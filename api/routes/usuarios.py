from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from core.user_service import UserService
from core.user_creation_service import UserCreationService
from core.user_classifier_service import UserClassifierService

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

@router.get("", include_in_schema=False)
@router.get("/")
def listar_usuarios(
    q: Optional[str] = Query("", description="Búsqueda por ID, nombre, correo, puesto o área"),
    filtro_vigencia: Optional[str] = Query("TODOS", description="TODOS | ACTIVOS | VENCIDOS | ESTE_MES | PROX_MES"),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0)
):
    todos = UserService.buscar_usuarios(query=q, filtro_vigencia=filtro_vigencia)
    total = len(todos)
    paginados = todos[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "usuarios": paginados
    }

@router.post("/sincronizar-aryve")
def sincronizar_usuarios_aryve():
    """Conecta en vivo a la API de Aryve (Enkontrol 10) y actualiza la base de usuarios instantáneamente"""
    resultado = UserService.sincronizar_desde_aryve()
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("error", "Error sincronizando con Aryve"))
    return resultado

@router.get("/puestos")
def listar_puestos():
    return UserService.obtener_puestos()

@router.post("/crear")
def crear_usuario(payload: Dict[str, Any] = Body(...)):
    """Inicia el alta de usuario en segundo plano para evitar timeout HTTP"""
    guardar_prod = payload.get("guardar_en_produccion", False)
    ok, msg = UserCreationService.iniciar_alta_asincrona(payload, guardar_en_produccion=guardar_prod)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}

@router.get("/crear/estado")
def estado_creacion():
    """Consulta el progreso y logs de Selenium del alta en curso"""
    return UserCreationService.obtener_estado()

@router.post("/crear/detener")
def detener_creacion():
    """Detiene Selenium y cierra la ventana de Chrome"""
    ok, msg = UserCreationService.detener_proceso()
    return {"ok": ok, "mensaje": msg}

@router.post("/crear/reiniciar")
def reiniciar_creacion(payload: Dict[str, Any] = Body(...)):
    """Detiene cualquier proceso previo, cierra Chrome y reinicia el alta con los datos"""
    guardar_prod = payload.get("guardar_en_produccion", False)
    ok, msg = UserCreationService.reiniciar_alta(payload, guardar_en_produccion=guardar_prod)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}

@router.post("/puestos")
def guardar_puesto(payload: Dict[str, Any] = Body(...)):
    nombre = payload.get("nombre", "")
    area = payload.get("area_organizacional", "")
    niveles = payload.get("niveles", [])
    grupos = payload.get("grupos", [])
    clasificadores = payload.get("clasificadores", {})

    resultado = UserService.guardar_puesto(nombre, area, niveles, grupos, clasificadores)
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("error", "Error desconocido"))
    return resultado

@router.post("/puestos/sincronizar")
def sincronizar_puestos():
    """Fuerza la sincronización bidireccional entre puestos.json local y Firebase Firestore"""
    return UserService.sincronizar_puestos()

@router.get("/puestos/sync-status")
def estado_sincronizacion_puestos():
    """Consulta el estado de conectividad y si hay puestos locales pendientes por subir"""
    return UserService.obtener_estado_sincronizacion()

# ==============================================================================
# GESTIÓN Y ASIGNACIÓN DE CLASIFICADORES
# ==============================================================================

@router.get("/clasificadores/puesto-info")
def obtener_info_clasificadores_puesto(puesto: str = Query(..., description="Nombre del puesto")):
    """Devuelve el resumen de clasificadores del puesto según puestos.json"""
    info = UserClassifierService.obtener_clasificadores_de_puesto(puesto)
    if not info:
        return {
            "encontrado": False,
            "puesto": puesto,
            "total_clasificadores": 0,
            "categorias": [],
            "area": ""
        }

    resumen = info.get("resumen_clasificadores_por_abuelo", {})
    categorias = [{"nombre": k, "total": v} for k, v in resumen.items()]
    return {
        "encontrado": True,
        "puesto": puesto,
        "area": info.get("area_organizacional", ""),
        "total_clasificadores": info.get("total_clasificadores", 0),
        "categorias": categorias,
        "clasificadores": info.get("clasificadores", {})
    }

@router.post("/clasificadores/iniciar")
def iniciar_asignacion_clasificadores(payload: Dict[str, Any] = Body(...)):
    """Inicia la asignación de clasificadores vía Selenium en segundo plano para el usuario en Aryve"""
    id_usuario = str(payload.get("id_usuario", "")).strip()
    puesto = str(payload.get("puesto", "")).strip()
    nombre_usuario = str(payload.get("nombre_usuario", "")).strip()

    if not id_usuario:
        raise HTTPException(status_code=400, detail="Debe proporcionar el ID del usuario.")
    if not puesto:
        raise HTTPException(status_code=400, detail="Debe seleccionar un puesto de puestos.json.")

    ok, msg = UserClassifierService.iniciar_asignacion_asincrona(
        id_usuario=id_usuario,
        puesto=puesto,
        nombre_usuario=nombre_usuario
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "mensaje": msg}

@router.get("/clasificadores/estado")
def estado_asignacion_clasificadores():
    """Consulta el progreso y logs de Selenium de la asignación de clasificadores"""
    return UserClassifierService.obtener_estado()
