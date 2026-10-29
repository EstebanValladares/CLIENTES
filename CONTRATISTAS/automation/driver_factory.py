"""
Módulo de Gestión y Creación del WebDriver de Selenium.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

try:
    from ..config.settings import CHROME_ARGUMENTS
except (ImportError, ValueError):
    from config.settings import CHROME_ARGUMENTS


def build_chrome_driver(headless: bool = False, detach: bool = True) -> webdriver.Chrome:
    """Crea una instancia configurada de Google Chrome."""
    options = webdriver.ChromeOptions()
    for arg in CHROME_ARGUMENTS:
        options.add_argument(arg)

    if headless:
        options.add_argument("--headless=new")

    if detach:
        options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.maximize_window()
    except Exception:
        pass

    return driver
