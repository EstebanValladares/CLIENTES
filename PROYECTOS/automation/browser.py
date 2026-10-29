"""
Factory centralizada y ciclo de vida de ChromeDriver para el módulo PROYECTOS.
Optimiza tiempos de arranque cacheando el binario de ChromeDriver y configurando
banderas de estabilidad para Aryve.
"""
import time
from typing import Any, Callable, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from PROYECTOS.selectores import (
    CHROME_ARGUMENTS,
    PAUSA_ESTABILIZACION,
    POLL_INTERVAL_RAPIDO,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
    LoaderSelectors,
)

_CACHED_CHROMEDRIVER_PATH: Optional[str] = None
_driver_activo: Any = None


def registrar_driver_activo(drv: Any) -> None:
    global _driver_activo
    _driver_activo = drv


def obtener_driver_activo() -> Any:
    global _driver_activo
    return _driver_activo


def cerrar_driver_activo() -> None:
    global _driver_activo
    if _driver_activo is not None:
        try:
            _driver_activo.quit()
        except Exception:
            pass
        _driver_activo = None


def obtener_ruta_chromedriver() -> str:
    """Obtiene e instala (solo la primera vez por proceso) el ejecutable de ChromeDriver."""
    global _CACHED_CHROMEDRIVER_PATH
    if not _CACHED_CHROMEDRIVER_PATH:
        _CACHED_CHROMEDRIVER_PATH = ChromeDriverManager().install()
    return _CACHED_CHROMEDRIVER_PATH


def crear_driver(
    headless: bool = False,
    detach: bool = False,
    maximizar: bool = True,
    on_driver_created: Optional[Callable[[WebDriver, Service], Any]] = None,
) -> WebDriver:
    """Crea y configura una instancia optimizada de Chrome WebDriver para Aryve."""
    opciones = webdriver.ChromeOptions()
    if detach:
        opciones.add_experimental_option("detach", True)
    for arg in CHROME_ARGUMENTS:
        opciones.add_argument(arg)

    if headless:
        opciones.add_argument("--headless=new")

    servicio = Service(obtener_ruta_chromedriver())
    driver = webdriver.Chrome(service=servicio, options=opciones)

    if on_driver_created:
        try:
            on_driver_created(driver, servicio)
        except Exception:
            pass

    if maximizar:
        try:
            driver.maximize_window()
        except Exception:
            pass

    registrar_driver_activo(driver)
    return driver


# ==============================================================================
# HELPERS DE ESPERA Y CLIC REUTILIZABLES
# ==============================================================================

def wait_driver(driver: WebDriver, timeout: float = TIMEOUT_LARGO) -> WebDriverWait:
    """Retorna un WebDriverWait con sondeo rápido (100ms)."""
    return WebDriverWait(driver, timeout, poll_frequency=POLL_INTERVAL_RAPIDO)


def esperar_fin_carga(
    driver: WebDriver,
    timeout: float = TIMEOUT_MEDIO,
    pausa_extra: float = PAUSA_ESTABILIZACION,
) -> None:
    """Espera reactivamente a que desaparezcan los indicadores de carga de DevExtreme."""
    try:
        wait_driver(driver, timeout).until(
            EC.invisibility_of_element_located(LoaderSelectors.LOAD_PANEL)
        )
    except Exception:
        pass
    if pausa_extra > 0:
        time.sleep(pausa_extra)


def click_js(driver: WebDriver, elemento: WebElement) -> None:
    """Realiza clic directo inyectado por JavaScript."""
    driver.execute_script("arguments[0].click();", elemento)


def click_seguro(driver: WebDriver, elemento: WebElement) -> None:
    """Intenta clic mediante ActionChains con fallback a JavaScript."""
    try:
        ActionChains(driver).move_to_element(elemento).click().perform()
    except Exception:
        click_js(driver, elemento)


def click_eventos_mouse(driver: WebDriver, elemento: WebElement) -> None:
    """Despacha la secuencia completa de eventos de ratón para disparar handlers complejos de UI."""
    js_dispatch = """
    var btn = arguments[0];
    var target = btn.querySelector('span') || btn;
    ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click'].forEach(function(eventType) {
        var ev = new MouseEvent(eventType, {
            bubbles: true,
            cancelable: true,
            view: window
        });
        target.dispatchEvent(ev);
    });
    """
    driver.execute_script(js_dispatch, elemento)


def scroll_al_centro(driver: WebDriver, elemento: WebElement) -> None:
    """Desplaza suavemente el elemento al centro visible del viewport."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)


# ==============================================================================
# CLASE BASE PARA COMPATIBILIDAD (BasePage)
# ==============================================================================

class BasePage:
    """Clase base Page Object Model para compatibilidad."""
    def __init__(self, driver: WebDriver, logger: Any = None):
        self.driver = driver
        self.logger = logger

    def _wait(self, timeout: float = TIMEOUT_LARGO) -> WebDriverWait:
        return wait_driver(self.driver, timeout)

    def esperar_presente(self, locator: Tuple[str, str], timeout: float = TIMEOUT_LARGO) -> WebElement:
        return self._wait(timeout).until(EC.presence_of_element_located(locator))

    def esperar_clicable(self, locator: Tuple[str, str], timeout: float = TIMEOUT_LARGO) -> WebElement:
        return self._wait(timeout).until(EC.element_to_be_clickable(locator))

    def esperar_invisible(self, locator: Tuple[str, str], timeout: float = TIMEOUT_LARGO) -> bool:
        return self._wait(timeout).until(EC.invisibility_of_element_located(locator))

    def esperar_fin_carga(self, timeout: float = TIMEOUT_MEDIO, pausa_extra: float = PAUSA_ESTABILIZACION) -> None:
        esperar_fin_carga(self.driver, timeout=timeout, pausa_extra=pausa_extra)

    def click_js(self, elemento: WebElement) -> None:
        click_js(self.driver, elemento)

    def click_seguro(self, elemento: WebElement) -> None:
        click_seguro(self.driver, elemento)

    def click_eventos_mouse(self, elemento: WebElement) -> None:
        click_eventos_mouse(self.driver, elemento)

    def scroll_al_centro(self, elemento: WebElement) -> None:
        scroll_al_centro(self.driver, elemento)
