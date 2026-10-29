"""
Factory centralizada y ciclo de vida de ChromeDriver (Selenium WebDriver).
"""
from typing import Any, Callable
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

_CACHED_CHROMEDRIVER_PATH: str | None = None
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


def construir_opciones_chrome(detach: bool = False) -> webdriver.ChromeOptions:
    """Construye ChromeOptions con banderas de estabilidad y velocidad para Aryve."""
    opciones = webdriver.ChromeOptions()
    if detach:
        opciones.add_experimental_option("detach", True)
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--disable-extensions")
    opciones.add_argument("--log-level=3")
    return opciones


def crear_driver_chrome(
    detach: bool = True,
    maximizar: bool = True,
    on_driver_created: Callable[[webdriver.Chrome, Service], Any] | None = None,
) -> tuple[webdriver.Chrome, Service]:
    """Crea y configura una instancia de webdriver.Chrome lista para operar en Aryve."""
    opciones = construir_opciones_chrome(detach=detach)
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
    return driver, servicio
