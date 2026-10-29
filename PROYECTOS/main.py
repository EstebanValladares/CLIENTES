"""
Punto de entrada para el Bot de Depuración de Permisos en Proyectos (Aryve).
Permite ejecución CLI, subproceso desde Dashboard v2 o importación como módulo.
"""
import os
import sys

_DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
if _DIR_ACTUAL not in sys.path:
    sys.path.insert(0, _DIR_ACTUAL)

_RAIZ = os.path.dirname(_DIR_ACTUAL)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from PROYECTOS.automation.proyectos_bot import (
    PermisosWorkflowService,
    ejecutar_depuracion_permisos,
)


def ejecutar_proceso_permisos(
    lista_obras=None,
    lista_usuarios_protegidos=None,
    callback_log=None,
):
    """
    Ejecuta el flujo automatizado de depuración de permisos en obras.
    Invocable desde el Dashboard Web, subprocesos o CLI.
    """
    return ejecutar_depuracion_permisos(
        lista_obras=lista_obras,
        lista_usuarios_protegidos=lista_usuarios_protegidos,
        callback_log=callback_log,
    )


if __name__ == "__main__":
    exito, mensaje = ejecutar_proceso_permisos()
    sys.exit(0 if exito else 1)
