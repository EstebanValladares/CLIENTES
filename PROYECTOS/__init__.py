"""
Módulo Principal de PROYECTOS (Clean & Modular Architecture).
"""
from PROYECTOS.selectores import (
    RUTA_LOG,
    RUTA_OBRAS_JSON,
    RUTA_USUARIOS_TXT,
    SELECTORES,
    URL_BASE_ARYVE,
    URL_PROYECTOS,
)
from PROYECTOS.permisos_service import (
    cargar_obras,
    cargar_usuarios_protegidos,
    es_usuario_protegido,
    normalizar_texto,
)
from PROYECTOS.automation import (
    BasePage,
    LoginPage,
    PermisosSidebarPage,
    PermisosWorkflowService,
    ProyectosPage,
    cerrar_driver_activo,
    crear_driver,
    ejecutar_depuracion_permisos,
    iniciar_sesion,
    navegar_a_proyectos,
    obtener_driver_activo,
    procesar_obra,
)
from PROYECTOS.logger import ProjectLogger
from PROYECTOS.main import ejecutar_proceso_permisos

__all__ = [
    "SELECTORES",
    "RUTA_OBRAS_JSON",
    "RUTA_USUARIOS_TXT",
    "RUTA_LOG",
    "URL_BASE_ARYVE",
    "URL_PROYECTOS",
    "cargar_obras",
    "cargar_usuarios_protegidos",
    "es_usuario_protegido",
    "normalizar_texto",
    "BasePage",
    "crear_driver",
    "cerrar_driver_activo",
    "obtener_driver_activo",
    "iniciar_sesion",
    "navegar_a_proyectos",
    "procesar_obra",
    "ejecutar_depuracion_permisos",
    "ejecutar_proceso_permisos",
    "PermisosWorkflowService",
    "ProjectLogger",
    "LoginPage",
    "ProyectosPage",
    "PermisosSidebarPage",
]

