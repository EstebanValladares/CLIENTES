"""
Módulo Principal de USUARIOS (Clean & Modular Architecture).
"""
from USUARIOS.selectores import SELECTORES
from USUARIOS.puestos_service import (
    ConfiguracionPuesto,
    es_clasificador_omitido,
    expandir_rangos,
    extraer_padres_e_hijos,
    leer_puestos_json,
    obtener_configuracion_puesto,
)
from USUARIOS.automation import (
    asignar_clasificadores,
    cerrar_driver_activo,
    crear_driver_chrome,
    ejecutar_alta_usuario,
    ejecutar_asignacion_clasificadores,
    iniciar_sesion,
    obtener_driver_activo,
)
from USUARIOS.logger import (
    limpiar_fallos_resueltos,
    registrar_fallo_clasificador,
    registrar_log_usuario,
)
