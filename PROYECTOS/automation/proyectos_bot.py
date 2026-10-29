"""
Orquestador de Automatización para el Módulo PROYECTOS (Selenium WebDriver).
Coordina:
1. Conexión segura a Aryve.
2. Búsqueda y apertura de cada Obra.
3. Recorrido de usuarios y depuración de permisos (asignando 'NO' a usuarios no protegidos).
4. Guardado y telemetría de ejecución.
"""
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Set, Tuple

from PROYECTOS.automation.browser import (
    cerrar_driver_activo,
    crear_driver,
    registrar_driver_activo,
)
from PROYECTOS.automation.telemetry import (
    finalizar_telemetria,
    registrar_navegador,
    rep,
)
from PROYECTOS.automation.ui_helpers import (
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
from PROYECTOS.logger.bitacora import ProjectLogger
from PROYECTOS.permisos_service import (
    cargar_obras,
    cargar_usuarios_protegidos,
    es_usuario_protegido,
)
from PROYECTOS.selectores import ECOSYSTEM_DIR, RUTA_LOG, URL_BASE_ARYVE


def _resolver_credenciales() -> Tuple[bool, Tuple[str, str] | str]:
    """Carga credenciales desde NUCLEO o desde archivo .env."""
    if str(ECOSYSTEM_DIR) not in sys.path:
        sys.path.insert(0, str(ECOSYSTEM_DIR))
    try:
        from NUCLEO.config import obtener_credenciales_aryve
        u, p = obtener_credenciales_aryve()
        if u and p:
            return True, (u, p)
    except Exception:
        pass

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ECOSYSTEM_DIR, ".env"))
        u = os.getenv("EK10_USER", "")
        p = os.getenv("EK10_PASS", "")
        if u and p:
            return True, (u, p)
    except Exception:
        pass

    return False, "Credenciales de Aryve no encontradas en NUCLEO ni en .env"


def procesar_obra(
    driver: Any,
    obra: str,
    usuarios_protegidos: Set[str],
    logger: ProjectLogger,
) -> None:
    """Procesa una obra individualmente: recorre sus usuarios y depura permisos."""
    logger.info(f"\nObra: {obra}")

    buscar_obra_en_tabla(driver, obra, logger=logger)
    abrir_primer_resultado(driver, logger=logger)
    click_editar_proyecto(driver, logger=logger)

    indice_usuario = 1
    while True:
        nombre_usuario = obtener_nombre_usuario_fila(driver, indice_usuario, logger=logger)
        if not nombre_usuario and not existe_fila_usuario(driver, indice_usuario):
            logger.info(
                f"No hay más usuarios en la obra '{obra}' (total revisados: {indice_usuario - 1})."
            )
            break

        if es_usuario_protegido(nombre_usuario, usuarios_protegidos):
            logger.info(f"usuario {nombre_usuario}, omitido (protegido)")
            indice_usuario += 1
            continue

        try:
            abierto = click_icono_usuario_por_indice(driver, indice_usuario, logger=logger)
            if not abierto:
                logger.info(f"usuario {nombre_usuario}, fallo")
                break

            abrir_apartado_y_seleccionar_no(driver, logger=logger)
            guardar_permisos_sidebar(driver, logger=logger)
            logger.info(f"usuario {nombre_usuario}, ok")
        except Exception as err_u:
            logger.info(f"usuario {nombre_usuario}, fallo ({err_u})")

        indice_usuario += 1

    guardar_proyecto_general(driver, logger=logger)
    regresar_a_lista_proyectos(driver, logger=logger)
    logger.info(f"[OK] Obra '{obra}' completada.")


def ejecutar_depuracion_permisos(
    lista_obras: Optional[Iterable[str]] = None,
    lista_usuarios_protegidos: Optional[Iterable[str]] = None,
    callback_log: Optional[Callable[[str], None]] = None,
    ruta_log: Optional[str | Path] = None,
) -> Tuple[bool, str]:
    """
    Ejecuta el flujo completo de depuración de permisos en Aryve.
    Retorna `(exito: bool, mensaje: str)`.
    """
    logger = ProjectLogger(ruta_log=ruta_log or RUTA_LOG, callback_log=callback_log)
    logger.iniciar_sesion_log()

    obras = cargar_obras(lista_obras=lista_obras)
    if not obras:
        logger.aviso("No hay obras para procesar.")
        return False, "No hay obras para procesar."

    usuarios_protegidos = cargar_usuarios_protegidos(
        lista_personalizada=lista_usuarios_protegidos,
        imprimir_resumen=(lista_usuarios_protegidos is None),
    )

    exito_cred, res_cred = _resolver_credenciales()
    if not exito_cred:
        logger.error(str(res_cred))
        return False, str(res_cred)
    usuario_aryve, password_aryve = res_cred  # type: ignore

    driver = crear_driver()
    registrar_navegador(driver, "PROYECTOS")

    try:
        logger.info("=" * 60)
        logger.info("   INICIANDO MÓDULO DE PERMISOS PROYECTOS")
        logger.info("=" * 60)

        iniciar_sesion(driver, usuario_aryve, password_aryve, logger=logger)
        navegar_a_proyectos(driver, logger=logger)

        for obra in obras:
            procesar_obra(
                driver=driver,
                obra=obra,
                usuarios_protegidos=usuarios_protegidos,
                logger=logger,
            )

        rep().verificar("Obras procesadas", len(obras), len(obras), ok=True, critica=True)
        logger.info("\n" + "=" * 60)
        logger.info("OK")
        logger.info("=" * 60)
        return True, "Proceso completado exitosamente (OK)"

    except Exception as err:
        msg_err = f"[ERROR EN EJECUCIÓN]: {err}"
        logger.info(f"\n{msg_err}")
        traceback.print_exc()
        try:
            rep().registrar_excepcion()
            rep().capturar(motivo="Excepción durante ejecución de Permisos Proyectos")
        except Exception:
            pass
        return False, msg_err

    finally:
        try:
            finalizar_telemetria()
        except Exception:
            pass
        try:
            cerrar_driver_activo()
        except Exception:
            pass


class PermisosWorkflowService:
    """Clase de compatibilidad para código que instancie PermisosWorkflowService."""
    def __init__(
        self,
        callback_log: Optional[Callable[[str], None]] = None,
        ruta_log: Optional[str | Path] = None,
    ):
        self.callback_log = callback_log
        self.ruta_log = ruta_log

    def ejecutar(
        self,
        lista_obras: Optional[Iterable[str]] = None,
        lista_usuarios_protegidos: Optional[Iterable[str]] = None,
    ) -> Tuple[bool, str]:
        return ejecutar_depuracion_permisos(
            lista_obras=lista_obras,
            lista_usuarios_protegidos=lista_usuarios_protegidos,
            callback_log=self.callback_log,
            ruta_log=self.ruta_log,
        )
