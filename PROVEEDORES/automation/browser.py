"""
Factory centralizada de navegadores Chrome y clase base Page Object Model (BasePage).
Optimiza tiempos de respuesta cacheando el binario de ChromeDriver y usando
sondeo reactivo rápido (POLL_INTERVAL_RAPIDO = 0.1s) en lugar de esperas fijas.
"""
import time
from typing import Optional, Sequence, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from automation.logger import ProveedorLogger
from config.selectors import LoaderSelectors
from config.settings import (
    CHROME_ARGUMENTS,
    PAUSA_ESTABILIZACION,
    PAUSA_MICRO,
    POLL_INTERVAL_RAPIDO,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
)

_CACHED_CHROMEDRIVER_PATH: Optional[str] = None


def obtener_ruta_chromedriver() -> str:
    """Obtiene e instala (solo la primera vez por proceso) el ejecutable de ChromeDriver."""
    global _CACHED_CHROMEDRIVER_PATH
    if not _CACHED_CHROMEDRIVER_PATH:
        _CACHED_CHROMEDRIVER_PATH = ChromeDriverManager().install()
    return _CACHED_CHROMEDRIVER_PATH


def crear_driver(headless: bool = False) -> WebDriver:
    """Crea y configura una instancia optimizada de Chrome WebDriver."""
    opciones = webdriver.ChromeOptions()
    for arg in CHROME_ARGUMENTS:
        opciones.add_argument(arg)

    if headless:
        opciones.add_argument("--headless=new")

    servicio = Service(obtener_ruta_chromedriver())
    driver = webdriver.Chrome(service=servicio, options=opciones)
    try:
        driver.maximize_window()
    except Exception:
        pass
    return driver


class BasePage:
    """
    Clase base para el patrón Page Object Model (POM) en Aryve.
    Utiliza POLL_INTERVAL_RAPIDO (100ms) para reaccionar de inmediato a cambios en el DOM
    y centraliza la escritura reactiva en inputs de React/Select2.
    """

    def __init__(self, driver: WebDriver, logger: Optional[ProveedorLogger] = None):
        self.driver = driver
        self.logger = logger or ProveedorLogger(ruta_log="")

    def _wait(self, timeout: float = TIMEOUT_LARGO) -> WebDriverWait:
        return WebDriverWait(self.driver, timeout, poll_frequency=POLL_INTERVAL_RAPIDO)

    def esperar_presente(
        self, locator: Tuple[str, str], timeout: float = TIMEOUT_LARGO
    ) -> WebElement:
        return self._wait(timeout).until(EC.presence_of_element_located(locator))

    def esperar_clicable(
        self, locator: Tuple[str, str], timeout: float = TIMEOUT_LARGO
    ) -> WebElement:
        return self._wait(timeout).until(EC.element_to_be_clickable(locator))

    def esperar_visible(
        self, locator: Tuple[str, str], timeout: float = TIMEOUT_LARGO
    ) -> WebElement:
        return self._wait(timeout).until(EC.visibility_of_element_located(locator))

    def esperar_fin_carga(
        self,
        timeout: float = TIMEOUT_MEDIO,
        pausa_extra: float = PAUSA_MICRO,
    ) -> None:
        """Espera reactivamente a que desaparezcan los indicadores de carga."""
        try:
            self._wait(timeout).until(
                EC.invisibility_of_element_located(LoaderSelectors.LOAD_PANEL)
            )
        except Exception:
            pass
        if pausa_extra > 0:
            time.sleep(pausa_extra)

    def scroll_al_centro(self, elemento: WebElement) -> None:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", elemento
        )

    def click_js(self, elemento: WebElement) -> None:
        self.driver.execute_script("arguments[0].click();", elemento)

    def click_seguro(self, elemento: WebElement) -> None:
        self.scroll_al_centro(elemento)
        time.sleep(PAUSA_MICRO)
        try:
            elemento.click()
        except Exception:
            try:
                ActionChains(self.driver).move_to_element(elemento).click().perform()
            except Exception:
                self.click_js(elemento)

    def disparar_eventos_react(self, elemento: WebElement) -> None:
        """Dispara los eventos nativos 'input' y 'change' para sincronizar el estado de React en Aryve."""
        self.driver.execute_script(
            """
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            elemento,
        )

    def escribir_campo_reactivo(
        self,
        locator: Tuple[str, str],
        texto: str,
        etiqueta: str,
        timeout: float = TIMEOUT_LARGO,
    ) -> bool:
        """
        Localiza un campo de texto de forma reactiva, hace scroll al centro, limpia su contenido,
        escribe el valor y dispara los eventos `input` y `change` de React.
        """
        self.logger.info(f"Escribiendo {etiqueta}: '{texto}'...")
        try:
            campo = self.esperar_clicable(locator, timeout=timeout)
            self.scroll_al_centro(campo)
            time.sleep(PAUSA_MICRO)
            try:
                campo.click()
            except Exception:
                self.click_js(campo)
            campo.clear()
            campo.send_keys(texto)
            self.disparar_eventos_react(campo)
            time.sleep(PAUSA_MICRO)
            self.logger.info(f"¡{etiqueta} '{texto}' ingresado exitosamente!")
            return True
        except Exception as e:
            self.logger.error(f"No se pudo escribir {etiqueta}: {e}")
            return False

    def escribir_campo_con_candidatos(
        self,
        ids_candidatos: Sequence[str],
        fallback_locator: Tuple[str, str],
        texto: str,
        etiqueta: str,
        timeout: float = TIMEOUT_MEDIO,
    ) -> bool:
        """
        Busca un input probando primero una lista de IDs candidatos y, si ninguno está visible,
        recurre al locator XPath de respaldo.
        """
        if not texto:
            return True

        self.logger.info(f"Escribiendo {etiqueta}: '{texto}'...")
        try:
            campo: Optional[WebElement] = None
            for id_cand in ids_candidatos:
                try:
                    el = self.driver.find_element(By.ID, id_cand)
                    if el and el.is_displayed():
                        campo = el
                        break
                except Exception:
                    continue

            if not campo:
                campo = self.esperar_clicable(fallback_locator, timeout=timeout)

            self.scroll_al_centro(campo)
            time.sleep(PAUSA_MICRO)
            try:
                campo.click()
            except Exception:
                self.click_js(campo)
            campo.clear()
            campo.send_keys(texto)
            self.disparar_eventos_react(campo)
            time.sleep(PAUSA_MICRO)
            self.logger.info(f"¡{etiqueta} '{texto}' ingresado exitosamente!")
            return True
        except Exception as e:
            self.logger.error(f"No se pudo escribir {etiqueta}: {e}")
            return False

    def marcar_checkbox_reactivo(
        self,
        checkbox_id: str,
        etiqueta: str,
        timeout: float = TIMEOUT_LARGO,
    ) -> bool:
        """
        Verifica si la casilla de verificación React (`checkbox_id`) ya está activa y,
        en caso contrario, hace clic en su `<label>` o `<span>` asociado.
        """
        self.logger.info(f"Marcando casilla '{etiqueta}'...")
        try:
            input_chk = self.esperar_presente((By.ID, checkbox_id), timeout=timeout)
            val_attr = (input_chk.get_attribute("value") or "").lower()
            esta_marcado = input_chk.is_selected() or val_attr == "true"

            if esta_marcado:
                self.logger.info(f"[INFO] '{etiqueta}' ya se encuentra marcado.")
                return True

            self.scroll_al_centro(input_chk)
            time.sleep(PAUSA_MICRO)

            try:
                label_chk = self.driver.find_element(
                    By.XPATH, f"//label[@for='{checkbox_id}']"
                )
                label_chk.click()
            except Exception:
                try:
                    span_box = self.driver.find_element(
                        By.XPATH,
                        f"//label[@for='{checkbox_id}']//span[contains(@class, 'box') or contains(@class, 'check')]",
                    )
                    span_box.click()
                except Exception:
                    self.click_js(input_chk)

            time.sleep(PAUSA_ESTABILIZACION)
            self.logger.info(f"¡Casilla '{etiqueta}' marcada exitosamente!")
            return True
        except Exception as e:
            self.logger.error(f"No se pudo marcar la casilla '{etiqueta}': {e}")
            return False

