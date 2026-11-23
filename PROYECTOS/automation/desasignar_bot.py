"""
Orquestador de Automatización para la Desasignación de Usuarios por Proyecto (Aryve / Enkontrol 10).
Abre cada proyecto (usando su ID directo de URL), activa la edición, localiza en la tabla de 'Posiciones'
a los usuarios indicados y hace clic en el ícono de eliminar (fa fa-trash), confirmando y guardando.
"""
import os
import sys
import json
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from PROYECTOS.automation.browser import (
    cerrar_driver_activo,
    click_eventos_mouse,
    click_js,
    crear_driver,
    registrar_driver_activo,
)
from PROYECTOS.automation.telemetry import (
    finalizar_telemetria,
    registrar_navegador,
    rep,
)
from PROYECTOS.automation.ui_helpers import (
    click_editar_proyecto,
    click_seguro,
    esperar_fin_carga,
    guardar_proyecto_general,
    iniciar_sesion,
    normalizar_texto,
    scroll_al_centro,
    wait_driver,
)
from PROYECTOS.logger.bitacora import ProjectLogger
from PROYECTOS.selectores import (
    ECOSYSTEM_DIR,
    ProyectoDetalleSelectors,
    RUTA_CONFIG_DESASIGNACION,
    RUTA_DESASIGNACION_JSON,
    RUTA_LOG_DESASIGNACION,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
    URL_BASE_ARYVE,
)


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


def confirmar_modal_si_existe(driver: WebDriver, timeout: float = 1.0) -> bool:
    """Detecta y confirma diálogos de confirmación de DevExtreme, SweetAlert o Bootbox."""
    selectores = [
        "//div[contains(@class, 'dx-dialog')]//div[contains(@class, 'dx-button') and (.//span[contains(text(), 'Sí') or contains(text(), 'Si') or contains(text(), 'Aceptar')])]",
        "//div[contains(@class, 'modal-dialog')]//button[contains(text(), 'Sí') or contains(text(), 'Si') or contains(text(), 'Aceptar') or contains(text(), 'Confirmar')]",
        "//button[contains(@class, 'swal2-confirm')]",
        "//div[contains(@class, 'bootbox')]//button[contains(text(), 'OK') or contains(text(), 'Aceptar') or contains(text(), 'Sí')]",
    ]
    for sel in selectores:
        try:
            elementos = driver.find_elements(By.XPATH, sel)
            for el in elementos:
                if el.is_displayed():
                    el.click()
                    time.sleep(0.4)
                    return True
        except Exception:
            pass
    return False


def esta_en_modo_edicion(driver: WebDriver) -> bool:
    """Verifica si la pantalla de la obra ya se encuentra en modo edición."""
    selectores_indicadores = [
        "//button[contains(@class, 'btn-editing')]",
        "//button[contains(@class, 'yellow-casablanca')]",
        "//button[@aria-label='Guardar (Alt+G)' or @title='Guardar (Alt+G)' or @data-tip='Guardar (Alt+G)']",
        "//button[.//i[contains(@class, 'icon-cloud-upload')]]",
        "//*[@id='datagrid_SOCProyectos_Posiciones']//td[contains(@class, 'dx-command-edit')]//span[contains(@class, 'fa-trash')]",
    ]
    for sel in selectores_indicadores:
        try:
            elems = driver.find_elements(By.XPATH, sel)
            for el in elems:
                if el.is_displayed():
                    return True
        except Exception:
            pass
    return False


def salir_modo_edicion(driver: WebDriver) -> None:
    """Sale del modo edición de forma segura (presionando Regresar/Cancelar)."""
    selectores_cancelar = [
        "//button[contains(@class, 'btn-cancelar')]",
        "//button[@title='Regresar' or @aria-label='Regresar']",
        "//button[.//i[contains(@class, 'fa-arrow-left')]]",
    ]
    for sel in selectores_cancelar:
        try:
            btns = driver.find_elements(By.XPATH, sel)
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(0.6)
                    confirmar_modal_si_existe(driver)
                    return
        except Exception:
            pass


def procesar_desasignacion_obra(
    driver: WebDriver,
    clave_obra: str,
    info_obra: Dict[str, Any],
    logger: ProjectLogger,
    modo_prueba: bool = False,
) -> Tuple[int, str]:
    """
    Navega directamente a una obra, edita y analiza los usuarios uno por uno
    dentro de la tabla de Posiciones (id='datagrid_SOCProyectos_Posiciones').
    """
    id_proyecto = info_obra.get("id_proyecto")
    usuarios_objetivo: List[str] = info_obra.get("usuarios", [])
    if not usuarios_objetivo:
        return 0, "Sin usuarios asignados para remover."

    # Normalizar usuarios objetivo
    set_usuarios_remover = {normalizar_texto(u) for u in usuarios_objetivo}
    logger.info(f"   Usuarios objetivo en esta obra ({len(set_usuarios_remover)}): {', '.join(usuarios_objetivo)}")

    # Navegación a la obra garantizada
    cargada_ok = False
    if id_proyecto:
        url_obra = f"{URL_BASE_ARYVE.rstrip('/')}/#/scco/Proyectos/{id_proyecto}"
        logger.info(f"\n[{clave_obra}] Navegando a obra ID {id_proyecto}: {url_obra}")
        
        driver.get(url_obra)
        time.sleep(0.8)
        # Si la URL anterior ya era un proyecto, refrescamos para forzar a AngularJS a inicializar el nuevo ID
        if "/Proyectos/" in driver.current_url:
            driver.refresh()
            time.sleep(1.5)
            esperar_fin_carga(driver, timeout=12.0)
        else:
            esperar_fin_carga(driver, timeout=12.0)

        try:
            wait_driver(driver, 8.0).until(
                EC.presence_of_element_located((By.ID, "datagrid_SOCProyectos_Posiciones"))
            )
            cargada_ok = True
        except Exception:
            logger.aviso(f"[{clave_obra}] URL directa no estabilizó la pantalla. Recurriendo a búsqueda por catálogo...")

    if not cargada_ok:
        logger.info(f"[{clave_obra}] Abriendo proyecto mediante catálogo de obras...")
        navegar_a_proyectos(driver, logger=logger)
        buscar_obra_en_tabla(driver, clave_obra, logger=logger)
        abrir_primer_resultado(driver, logger=logger)
        time.sleep(1.5)
        esperar_fin_carga(driver)

    time.sleep(1.0)
    esperar_fin_carga(driver)

    # Activar modo edición si no está ya activo
    modo_edicion_ok = esta_en_modo_edicion(driver)
    if modo_edicion_ok:
        logger.info("   [MODO EDICIÓN]: La obra ya se encuentra en modo edición.")
    else:
        selectores_editar = [
            "//button[contains(@class, 'btn-editar')]",
            "//button[@title='Editar (Alt+E)' or @aria-label='Editar (Alt+E)' or @data-tip='Editar (Alt+E)']",
            "//button[.//i[contains(@class, 'fa-edit') or contains(@class, 'icon-pencil')]]",
            "//div[contains(@class, 'btn-group')]//button[2]",
        ]
        for int_edit in range(1, 4):
            btn_editar = None
            for sel in selectores_editar:
                try:
                    candidatos = driver.find_elements(By.XPATH, sel)
                    for c in candidatos:
                        if c.is_displayed() or c.is_enabled():
                            btn_editar = c
                            break
                    if btn_editar:
                        break
                except Exception:
                    pass

            if btn_editar:
                try:
                    scroll_al_centro(driver, btn_editar)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", btn_editar)
                    time.sleep(1.2)
                    esperar_fin_carga(driver)
                except Exception:
                    try:
                        btn_editar.click()
                        time.sleep(1.2)
                        esperar_fin_carga(driver)
                    except Exception:
                        pass

            if esta_en_modo_edicion(driver):
                logger.info("   [MODO EDICIÓN]: Botón Editar activado con éxito.")
                modo_edicion_ok = True
                break

            logger.info(f"   [Cargando]: Esperando que los controles de la obra estén listos (intento {int_edit}/3)...")
            time.sleep(1.5)
            esperar_fin_carga(driver)

    if not modo_edicion_ok:
        logger.error(f"[{clave_obra}] No se pudo activar el modo edición.")
        return 0, "No se pudo activar el modo edición."

    # Recorrido uno por uno en la tabla de Posiciones (#datagrid_SOCProyectos_Posiciones)
    eliminados_en_esta_obra = []
    indice_fila = 1
    max_filas_revisar = 60
    filas_vacias = 0

    while indice_fila <= max_filas_revisar and filas_vacias < 3:
        xpath_fila = f"//*[@id='datagrid_SOCProyectos_Posiciones']//div[contains(@class, 'dx-datagrid-rowsview')]//tbody/tr[contains(@class, 'dx-data-row')][{indice_fila}]"
        filas = driver.find_elements(By.XPATH, xpath_fila)

        if not filas:
            filas_vacias += 1
            indice_fila += 1
            continue

        fila = filas[0]
        nombre_en_fila = ""
        try:
            badges = fila.find_elements(By.XPATH, ".//td[@aria-colindex='2']//div[contains(@class, 'badge')] | .//span[contains(@class, 'badge')]")
            if badges and badges[0].text:
                nombre_en_fila = normalizar_texto(badges[0].text)
            else:
                celdas = fila.find_elements(By.XPATH, ".//td[@aria-colindex='2']")
                if celdas and celdas[0].text:
                    nombre_en_fila = normalizar_texto(celdas[0].text)
        except Exception:
            pass

        if not nombre_en_fila:
            filas_vacias += 1
            indice_fila += 1
            continue

        filas_vacias = 0
        logger.info(f"   [Fila {indice_fila}] Usuario: '{nombre_en_fila}'")
        time.sleep(0.35)  # Ritmo visual para seguimiento en vivo

        # Comprobar coincidencia con la lista objetivo
        coincide = False
        for u_rem in set_usuarios_remover:
            if u_rem in nombre_en_fila or nombre_en_fila in u_rem:
                coincide = True
                break

        if coincide:
            logger.info(f"   >>> ¡COINCIDENCIA ENCONTRADA! Eliminando: '{nombre_en_fila}'")
            iconos_trash = fila.find_elements(
                By.XPATH,
                ".//td[contains(@class, 'dx-command-edit')]//span[contains(@class, 'fa-trash')]"
            )
            if iconos_trash:
                btn_trash = iconos_trash[0]
                scroll_al_centro(driver, btn_trash)
                time.sleep(0.4)
                try:
                    click_eventos_mouse(driver, btn_trash)
                except Exception:
                    click_js(driver, btn_trash)

                time.sleep(0.8)
                confirmar_modal_si_existe(driver)
                time.sleep(0.8)
                esperar_fin_carga(driver)

                logger.info(f"   [-] Eliminado con éxito de la tabla: '{nombre_en_fila}'")
                eliminados_en_esta_obra.append(nombre_en_fila)
                time.sleep(1.2)  # Pausa para que el usuario compruebe la eliminación
                # Al eliminarse la fila, la siguiente fila toma su lugar (no incrementar indice_fila)
                continue
            else:
                logger.aviso(f"   No se encontró el ícono de basurero para '{nombre_en_fila}' en fila {indice_fila}.")
                indice_fila += 1
        else:
            indice_fila += 1

    # Si se eliminó al menos uno, guardar cambios del proyecto (o simular en modo prueba)
    if eliminados_en_esta_obra:
        if modo_prueba:
            logger.info(f"   [MODO PRUEBA ACTIVO]: Se eliminaron {len(eliminados_en_esta_obra)} usuarios de la vista.")
            logger.info(f"   [MODO PRUEBA]: Pausando 4 segundos para inspección visual en pantalla...")
            time.sleep(4.0)
            logger.info(f"   [MODO PRUEBA]: Se OMITE clic en Guardar (Alt+G). La obra '{clave_obra}' permanece INTACTA en Aryve.")
            salir_modo_edicion(driver)
            return len(eliminados_en_esta_obra), f"Prueba completada: {len(eliminados_en_esta_obra)} usuarios removidos visualmente (SIN GUARDAR)."
        else:
            logger.info(f"   Guardando cambios en obra '{clave_obra}'...")
            guardar_proyecto_general(driver, logger=logger)
            time.sleep(1.2)
            esperar_fin_carga(driver)

            # Quitar la obra de la lista pendiente en el Dashboard
            try:
                from core.permisos_service import PermisosService
                PermisosService.remover_obra_cumplida(clave_obra)
                logger.info(f"   [LISTA DASHBOARD]: Obra '{clave_obra}' removida exitosamente de las obras pendientes.")
            except Exception as e_rem:
                logger.aviso(f"No se pudo actualizar lista JSON: {e_rem}")

            return len(eliminados_en_esta_obra), f"Se eliminaron {len(eliminados_en_esta_obra)} usuarios y se guardó."
    else:
        logger.info(f"   [INFO] Ninguno de los {len(usuarios_objetivo)} usuarios objetivo estaba asignado en esta obra.")
        salir_modo_edicion(driver)
        return 0, "No se requirió eliminar usuarios."


def ejecutar_desasignacion_automatica(
    obras_especificas: Optional[List[str]] = None,
    callback_log: Optional[Callable[[str], None]] = None,
    ruta_log: Optional[str | Path] = None,
) -> Tuple[bool, str]:
    """
    Ejecuta el bot de desasignación recorriendo el archivo JSON de obras.
    """
    logger = ProjectLogger(ruta_log=ruta_log or RUTA_LOG_DESASIGNACION, callback_log=callback_log)
    logger.iniciar_sesion_log()

    # Leer configuración (modo prueba y límite)
    config = {}
    if RUTA_CONFIG_DESASIGNACION.exists():
        try:
            with open(RUTA_CONFIG_DESASIGNACION, "r", encoding="utf-8") as f_cfg:
                config = json.load(f_cfg)
        except Exception:
            pass

    modo_prueba = bool(config.get("modo_prueba", True))
    limite_obras = int(config.get("limite_obras", 1))

    if not RUTA_DESASIGNACION_JSON.exists():
        msg = f"No existe el archivo de desasignación: {RUTA_DESASIGNACION_JSON}"
        logger.error(msg)
        return False, msg

    try:
        with open(RUTA_DESASIGNACION_JSON, "r", encoding="utf-8") as f:
            data_desasig = json.load(f)
    except Exception as e:
        msg = f"Error leyendo {RUTA_DESASIGNACION_JSON}: {e}"
        logger.error(msg)
        return False, msg

    por_obra: Dict[str, Any] = data_desasig.get("por_obra", {})
    if not por_obra:
        msg = "No hay obras pendientes en el archivo de desasignación."
        logger.aviso(msg)
        return False, msg

    # Filtrar si se especificaron obras particulares
    if obras_especificas:
        claves_filtradas = [c.upper() for c in obras_especificas]
        obras_a_procesar = {k: v for k, v in por_obra.items() if k.upper() in claves_filtradas}
    else:
        obras_a_procesar = por_obra

    # Aplicar límite de obras si está configurado (> 0)
    if limite_obras > 0 and not obras_especificas:
        claves_recortadas = list(obras_a_procesar.keys())[:limite_obras]
        obras_a_procesar = {k: obras_a_procesar[k] for k in claves_recortadas}

    total_obras = len(obras_a_procesar)
    logger.info("=" * 60)
    logger.info("   INICIANDO DESASIGNACIÓN DE USUARIOS POR PROYECTO")
    logger.info(f"   MODO PRUEBA (Sin Guardar): {'SÍ (ACTIVADO)' if modo_prueba else 'NO (MODO REAL CON GUARDADO)'}")
    logger.info(f"   Total de Obras a procesar en esta tanda: {total_obras}")
    logger.info("=" * 60)

    exito_cred, res_cred = _resolver_credenciales()
    if not exito_cred:
        logger.error(str(res_cred))
        return False, str(res_cred)
    usuario_aryve, password_aryve = res_cred  # type: ignore

    driver = crear_driver()
    registrar_navegador(driver, "DESASIGNACION_PROYECTOS")

    total_removidos_global = 0
    obras_modificadas = 0

    try:
        iniciar_sesion(driver, usuario_aryve, password_aryve, logger=logger)

        for idx, (cve, info) in enumerate(obras_a_procesar.items(), start=1):
            logger.info(f"\n--- [{idx}/{total_obras}] Procesando Obra: {cve} - {info.get('nombre', '')} ---")
            try:
                removidos, detalle = procesar_desasignacion_obra(
                    driver=driver,
                    clave_obra=cve,
                    info_obra=info,
                    logger=logger,
                    modo_prueba=modo_prueba,
                )
                if removidos > 0:
                    total_removidos_global += removidos
                    obras_modificadas += 1
            except Exception as err_obra:
                msg_limpio = str(err_obra).splitlines()[0] if str(err_obra) else "Error desconocido"
                logger.error(f"Fallo al procesar obra {cve}: {msg_limpio}")

        logger.info("\n" + "=" * 60)
        resumen = (
            f"PROCESO DE DESASIGNACIÓN FINALIZADO:\n"
            f"- Obras revisadas: {total_obras}\n"
            f"- Obras modificadas y guardadas: {obras_modificadas}\n"
            f"- Total de asignaciones removidas: {total_removidos_global}"
        )
        logger.info(resumen)
        logger.info("=" * 60)
        return True, "Desasignación completada exitosamente."

    except Exception as e_global:
        msg_err = f"[ERROR GENERAL EN DESASIGNACIÓN]: {e_global}"
        logger.error(msg_err)
        traceback.print_exc()
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
