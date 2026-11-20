"""
Punto de entrada para el Bot de Desasignación de Usuarios en Proyectos (Aryve).
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

from PROYECTOS.automation.desasignar_bot import ejecutar_desasignacion_automatica


def main():
    exito, mensaje = ejecutar_desasignacion_automatica()
    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    main()
