"""
Módulo de Automatización de Proyectos y Permisos en Aryve (Selenium).
"""
from PROYECTOS.automation.browser import (
    BasePage,
    cerrar_driver_activo,
    crear_driver,
    obtener_driver_activo,
    registrar_driver_activo,
)
from PROYECTOS.automation.ui_helpers import (
    LoginPage,
    PermisosSidebarPage,
    ProyectosPage,
    abrir_apartado_y_seleccionar_no,
    abrir_primer_resultado,
    buscar_obra_en_tabla,
    click_editar_proyecto,
    click_icono_usuario_por_indice,
    existe_fila_usuario,
    guardar_permisos_sidebar,
    guardar_proyecto_general,
    iniciar_sesion,
    navegar_a_proyectos,
    obtener_nombre_usuario_fila,
    regresar_a_lista_proyectos,
)
from PROYECTOS.automation.proyectos_bot import (
    PermisosWorkflowService,
    ejecutar_depuracion_permisos,
    procesar_obra,
)

__all__ = [
    "BasePage",
    "crear_driver",
    "cerrar_driver_activo",
    "obtener_driver_activo",
    "registrar_driver_activo",
    "LoginPage",
    "ProyectosPage",
    "PermisosSidebarPage",
    "iniciar_sesion",
    "navegar_a_proyectos",
    "buscar_obra_en_tabla",
    "abrir_primer_resultado",
    "click_editar_proyecto",
    "existe_fila_usuario",
    "obtener_nombre_usuario_fila",
    "click_icono_usuario_por_indice",
    "abrir_apartado_y_seleccionar_no",
    "guardar_permisos_sidebar",
    "guardar_proyecto_general",
    "regresar_a_lista_proyectos",
    "PermisosWorkflowService",
    "ejecutar_depuracion_permisos",
    "procesar_obra",
]
