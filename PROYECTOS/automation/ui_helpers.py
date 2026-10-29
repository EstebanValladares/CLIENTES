"""
Interacciones atómicas con la interfaz de usuario de Aryve (Selenium).
Centraliza la navegación, login, tabla de proyectos, panel de permisos y guardado.
"""
import time
from typing import Any, Optional
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from PROYECTOS.automation.browser import (
    click_eventos_mouse,
    click_js,
    click_seguro,
    esperar_fin_carga,
    scroll_al_centro,
    wait_driver,
)
from PROYECTOS.permisos_service import normalizar_texto
from PROYECTOS.selectores import (
    PAUSA_ANIMACION,
    PAUSA_ESTABILIZACION,
    TIMEOUT_GUARDADO,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
    URL_BASE_ARYVE,
    URL_PROYECTOS,
    LoginSelectors,
    ProyectoDetalleSelectors,
    ProyectosTableSelectors,
    SidebarPermisosSelectors,
)


def _log(logger: Any, msg: str, level: str = "info") -> None:
    if logger and hasattr(logger, level):
        getattr(logger, level)(msg)
    elif logger and hasattr(logger, "info"):
        logger.info(msg)
    else:
        print(msg)


# ==============================================================================
# 1. LOGIN Y NAVEGACIÓN
# ==============================================================================

def iniciar_sesion(
    driver: WebDriver,
    usuario: str,
    password: str,
    logger: Any = None,
    url: str = URL_BASE_ARYVE,
) -> None:
    """Inicia sesión de forma segura en Aryve con manejo de sesión refrescada."""
    _log(logger, "Iniciando sesión en el sistema...")
    driver.get(url)

    wait = wait_driver(driver, TIMEOUT_LARGO)
    user_input = wait.until(EC.element_to_be_clickable(LoginSelectors.INPUT_USERNAME))
    user_input.clear()
    user_input.send_keys(usuario)

    pass_input = driver.find_element(*LoginSelectors.INPUT_PASSWORD)
    pass_input.clear()
    pass_input.send_keys(password)

    driver.find_element(*LoginSelectors.BTN_SUBMIT).click()

    wait.until(EC.presence_of_element_located(LoginSelectors.BODY))
    time.sleep(1.5)
    driver.refresh()
    time.sleep(1.0)
    _log(logger, "¡Logeo exitoso en Aryve!")


def navegar_a_proyectos(driver: WebDriver, logger: Any = None, url: str = URL_PROYECTOS) -> None:
    """Navega directamente a la pantalla de Proyectos y espera a que cargue la tabla."""
    _log(logger, f"Redirigiendo a proyectos: {url}...")
    driver.get(url)
    wait_driver(driver, TIMEOUT_LARGO).until(
        EC.presence_of_element_located(ProyectosTableSelectors.INPUT_BUSCADOR)
    )
    esperar_fin_carga(driver)
    _log(logger, "¡Navegación al módulo de proyectos completada!")


# ==============================================================================
# 2. BÚSQUEDA Y SELECCIÓN DE OBRA
# ==============================================================================

def buscar_obra_en_tabla(driver: WebDriver, obra: str, logger: Any = None) -> None:
    """Ingresa el nombre o clave de la obra en el buscador DevExtreme."""
    _log(logger, f"Buscando obra en la tabla: {obra}...")
    try:
        input_busqueda = wait_driver(driver, TIMEOUT_LARGO).until(
            EC.element_to_be_clickable(ProyectosTableSelectors.INPUT_BUSCADOR)
        )
        input_busqueda.click()
        input_busqueda.clear()
        time.sleep(PAUSA_ESTABILIZACION)
        input_busqueda.send_keys(obra)
        _log(logger, f"¡Obra '{obra}' ingresada en el buscador!")
        time.sleep(1.2)
        esperar_fin_carga(driver)
    except Exception as e:
        _log(logger, f"Error al buscar la obra '{obra}' en la tabla: {e}", level="error")
        raise


def abrir_primer_resultado(driver: WebDriver, logger: Any = None) -> None:
    """Realiza doble clic sobre el primer registro de la tabla."""
    _log(logger, "Esperando la primera fila de resultados para hacer doble clic...")
    try:
        fila = wait_driver(driver, TIMEOUT_LARGO).until(
            EC.presence_of_element_located(ProyectosTableSelectors.PRIMERA_FILA)
        )
        time.sleep(0.5)
        ActionChains(driver).double_click(fila).perform()
        _log(logger, "¡Doble clic realizado con éxito en el primer proyecto!")
        wait_driver(driver, TIMEOUT_LARGO).until(
            EC.element_to_be_clickable(ProyectoDetalleSelectors.BTN_EDITAR)
        )
        esperar_fin_carga(driver)
    except Exception as e:
        _log(logger, f"Error al intentar dar doble clic en el primer proyecto: {e}", level="error")
        raise


def click_editar_proyecto(driver: WebDriver, logger: Any = None) -> None:
    """Activa el modo edición de la obra."""
    _log(logger, "Buscando el botón 'Editar (Alt+E)'...")
    try:
        btn_editar = wait_driver(driver, TIMEOUT_LARGO).until(
            EC.element_to_be_clickable(ProyectoDetalleSelectors.BTN_EDITAR)
        )
        click_js(driver, btn_editar)
        _log(logger, "¡Clic realizado en el botón Editar!")
        time.sleep(1.2)
        esperar_fin_carga(driver)
    except Exception as e:
        _log(logger, f"Error al hacer clic en el botón Editar: {e}", level="error")
        raise


# ==============================================================================
# 3. RECORRIDO DE USUARIOS EN EL PROYECTO
# ==============================================================================

def existe_fila_usuario(driver: WebDriver, indice: int) -> bool:
    """Verifica si existe la fila indicada en la tabla de usuarios."""
    filas = driver.find_elements(*ProyectoDetalleSelectors.fila_usuario(indice))
    return bool(filas)


def obtener_nombre_usuario_fila(driver: WebDriver, indice: int, logger: Any = None) -> str:
    """Obtiene el nombre normalizado del usuario en la fila especificada."""
    try:
        elementos = driver.find_elements(*ProyectoDetalleSelectors.badge_nombre_usuario(indice))
        if elementos and elementos[0].text:
            return normalizar_texto(elementos[0].text)

        elementos_td = driver.find_elements(*ProyectoDetalleSelectors.celda_nombre_usuario(indice))
        if elementos_td and elementos_td[0].text:
            return normalizar_texto(elementos_td[0].text)

        return ""
    except Exception as e:
        _log(logger, f"Error al leer nombre en fila {indice}: {e}", level="error")
        return ""


def click_icono_usuario_por_indice(driver: WebDriver, indice: int, logger: Any = None) -> bool:
    """Abre el panel lateral de permisos para el usuario en la fila dada."""
    try:
        icono = wait_driver(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located(ProyectoDetalleSelectors.icono_permisos_usuario(indice))
        )
        time.sleep(PAUSA_ESTABILIZACION)
        click_eventos_mouse(driver, icono)
        time.sleep(1.2)
        return True
    except Exception as e:
        _log(logger, f"No se encontró icono de permisos o error en fila {indice}: {e}", level="aviso")
        return False


# ==============================================================================
# 4. SIDEBAR LATERAL DE PERMISOS
# ==============================================================================

def esta_opcion_no_activa(btn_no: WebElement) -> bool:
    """Determina si la opción 'NO' ya se encuentra seleccionada."""
    style_attr = btn_no.get_attribute("style") or ""
    class_attr = btn_no.get_attribute("class") or ""
    return (
        ("rgba(0, 0, 0, 0.3)" not in style_attr and "rgba(0,0,0,0.3)" not in style_attr)
        or "active" in class_attr
        or "rgb(51, 122, 183)" in style_attr
    )


def abrir_apartado_y_seleccionar_no(driver: WebDriver, logger: Any = None) -> None:
    """Despliega la sección 'TIPO DE PROCESO' en el sidebar y selecciona 'NO' si procede."""
    try:
        wait = wait_driver(driver, TIMEOUT_LARGO)
        wait.until(EC.presence_of_element_located(SidebarPermisosSelectors.SIDEBAR))
        time.sleep(1.0)

        # 1. Desplegar el acordeón de "TIPO DE PROCESO"
        btn_desplegar = wait_driver(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located(SidebarPermisosSelectors.BTN_CHEVRON_TIPO_PROCESO)
        )
        scroll_al_centro(driver, btn_desplegar)
        time.sleep(PAUSA_ESTABILIZACION)
        click_seguro(driver, btn_desplegar)

        # 2. Esperar carga de opciones
        time.sleep(1.2)
        esperar_fin_carga(driver, pausa_extra=PAUSA_ESTABILIZACION)

        # 3. Localizar el botón "NO"
        btn_no = wait_driver(driver, TIMEOUT_MEDIO).until(
            EC.presence_of_element_located(SidebarPermisosSelectors.BTN_OPCION_NO)
        )

        if esta_opcion_no_activa(btn_no):
            _log(logger, "El usuario YA TIENE 'NO' asignado previamente. Se omite clic para no alternarlo.")
        else:
            click_js(driver, btn_no)
            time.sleep(PAUSA_ANIMACION)
    except Exception as e:
        _log(logger, f"Error al abrir apartado y seleccionar 'NO': {e}", level="error")
        raise


def guardar_permisos_sidebar(driver: WebDriver, logger: Any = None) -> None:
    """Presiona Guardar en el sidebar y espera el cierre completo."""
    try:
        btn_guardar = wait_driver(driver, TIMEOUT_LARGO).until(
            EC.element_to_be_clickable(SidebarPermisosSelectors.BTN_GUARDAR_SIDEBAR)
        )
        time.sleep(0.5)
        click_js(driver, btn_guardar)

        # Esperar a que el sidebar se cierre
        wait_driver(driver, TIMEOUT_GUARDADO).until(
            EC.invisibility_of_element_located(SidebarPermisosSelectors.SIDEBAR)
        )
        esperar_fin_carga(driver, timeout=TIMEOUT_LARGO, pausa_extra=1.8)
    except Exception as e:
        _log(logger, f"Aviso al guardar permisos del sidebar: {e}", level="aviso")
        time.sleep(2.5)


# ==============================================================================
# 5. GUARDADO GENERAL Y RETORNO
# ==============================================================================

def guardar_proyecto_general(driver: WebDriver, logger: Any = None) -> None:
    """Guarda los cambios globales de la obra (botón naranja)."""
    _log(logger, "Guardando el proyecto (clic en botón naranja/nube general)...")
    try:
        btn = wait_driver(driver, TIMEOUT_LARGO).until(
            EC.element_to_be_clickable(ProyectoDetalleSelectors.BTN_GUARDAR_GENERAL)
        )
        time.sleep(0.5)
        click_js(driver, btn)
        _log(logger, "¡Clic en Guardar Proyecto (naranja) realizado exitosamente!")
        time.sleep(2.5)
        esperar_fin_carga(driver, timeout=TIMEOUT_LARGO, pausa_extra=1.0)
    except Exception as e:
        _log(logger, f"Error al hacer clic en Guardar Proyecto general: {e}", level="error")


def regresar_a_lista_proyectos(driver: WebDriver, logger: Any = None) -> None:
    """Regresa a la tabla principal de proyectos."""
    _log(logger, "Haciendo clic en la flecha de Regresar...")
    try:
        btn = wait_driver(driver, TIMEOUT_LARGO).until(
            EC.element_to_be_clickable(ProyectoDetalleSelectors.BTN_REGRESAR)
        )
        time.sleep(0.5)
        click_js(driver, btn)
        _log(logger, "¡Regresando a la lista de obras!")
        wait_driver(driver, TIMEOUT_LARGO).until(
            EC.presence_of_element_located(ProyectosTableSelectors.INPUT_BUSCADOR)
        )
        esperar_fin_carga(driver, pausa_extra=1.0)
    except Exception as e:
        _log(logger, f"Error al regresar a la lista de proyectos: {e}", level="error")


# ==============================================================================
# WRAPPERS DE COMPATIBILIDAD CON PAGE OBJECTS
# ==============================================================================

class LoginPage:
    def __init__(self, driver: WebDriver, logger: Any = None):
        self.driver = driver
        self.logger = logger
    def abrir_portal(self, url: str = URL_BASE_ARYVE) -> None:
        self.driver.get(url)
    def iniciar_sesion(self, usuario: str, password: str) -> None:
        iniciar_sesion(self.driver, usuario, password, self.logger)


class ProyectosPage:
    def __init__(self, driver: WebDriver, logger: Any = None):
        self.driver = driver
        self.logger = logger
    def navegar_a_proyectos(self, url: str = URL_PROYECTOS) -> None:
        navegar_a_proyectos(self.driver, self.logger, url)
    def buscar_obra_en_tabla(self, obra: str) -> None:
        buscar_obra_en_tabla(self.driver, obra, self.logger)
    def abrir_primer_resultado(self) -> None:
        abrir_primer_resultado(self.driver, self.logger)
    def click_editar_proyecto(self) -> None:
        click_editar_proyecto(self.driver, self.logger)
    def existe_fila_usuario(self, indice: int) -> bool:
        return existe_fila_usuario(self.driver, indice)
    def obtener_nombre_usuario_fila(self, indice: int) -> str:
        return obtener_nombre_usuario_fila(self.driver, indice, self.logger)
    def click_icono_usuario_por_indice(self, indice: int) -> bool:
        return click_icono_usuario_por_indice(self.driver, indice, self.logger)
    def guardar_proyecto_general(self) -> None:
        guardar_proyecto_general(self.driver, self.logger)
    def regresar_a_lista_proyectos(self) -> None:
        regresar_a_lista_proyectos(self.driver, self.logger)


class PermisosSidebarPage:
    def __init__(self, driver: WebDriver, logger: Any = None):
        self.driver = driver
        self.logger = logger
    def abrir_apartado_y_seleccionar_no(self) -> None:
        abrir_apartado_y_seleccionar_no(self.driver, self.logger)
    def guardar_permisos_sidebar(self) -> None:
        guardar_permisos_sidebar(self.driver, self.logger)

