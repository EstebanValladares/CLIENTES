"""
Catálogo centralizado de selectores DOM, URLs y parámetros de configuración
para el módulo PROYECTOS (Depuración de Permisos en Aryve / Enkontrol 10).
"""
import os
import sys
from pathlib import Path
from selenium.webdriver.common.by import By

# Garantizar salida UTF-8 segura en Windows y subprocesos
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# --- RUTAS DEL PROYECTO Y ECOSISTEMA ---
BASE_DIR: Path = Path(__file__).resolve().parent
ECOSYSTEM_DIR: Path = BASE_DIR.parent

RUTA_OBRAS_JSON: Path = BASE_DIR / "obras_permisos.json"
RUTA_USUARIOS_TXT: Path = BASE_DIR / "ENKONTROL.TXT"
RUTA_LOG: Path = BASE_DIR / "log_depuracion.txt"

# --- URLS DE ARYVE ---
URL_BASE_ARYVE: str = os.getenv("ARYVE_BASE_URL", "")
URL_PROYECTOS: str = f"{URL_BASE_ARYVE.rstrip('/')}/#/scco/Proyectos"

# --- TIMEOUTS Y POLLING REACTIVO (SEGUNDOS) ---
TIMEOUT_CORTO: float = 5.0
TIMEOUT_MEDIO: float = 10.0
TIMEOUT_LARGO: float = 15.0
TIMEOUT_GUARDADO: float = 20.0
POLL_INTERVAL_RAPIDO: float = 0.1  # Sondeo cada 100ms

PAUSA_ESTABILIZACION: float = 0.35
PAUSA_ANIMACION: float = 0.9

# --- ARGUMENTOS DE CHROME ---
CHROME_ARGUMENTS: list[str] = [
    "--start-maximized",
    "--ignore-certificate-errors",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-notifications",
    "--log-level=3",
]

# --- USUARIOS PROTEGIDOS BASE ---
USUARIOS_PROTEGIDOS_BASE: list[str] = [
    "CLAUDIA SARAI PADILLA RAMIREZ",
    "LUIS SOTERO CRUZ GOMEZ",
    "ARTURO VILLANUEVA GUERRERO",
    "PEDRO PEREZ GUZMAN",
    "YEUDIEL ESTEBAN RICHARD PEREZ",
    "SANTOS PEREZ TOLENTINO",
    "IRMA MIREYA MOLINA CAZARES",
]

# --- CLASES DE SELECTORES (COMPATIBILIDAD DIRECTA) ---
class LoginSelectors:
    """Selectores de la pantalla de inicio de sesión."""
    INPUT_USERNAME = (By.ID, "username")
    INPUT_PASSWORD = (By.ID, "password")
    BTN_SUBMIT = (By.ID, "btnSubmit")
    BODY = (By.TAG_NAME, "body")


class LoaderSelectors:
    """Selectores de paneles de carga de DevExtreme / Aryve."""
    LOAD_PANEL = (
        By.XPATH,
        "//div[contains(@class, 'dx-loadpanel-content') and not(contains(@style, 'display: none'))] | "
        "//div[contains(@class, 'loading') or contains(text(), 'Cargando')]",
    )


class ProyectosTableSelectors:
    """Selectores del listado principal de Proyectos / Obras."""
    INPUT_BUSCADOR = (By.XPATH, "//input[@aria-label='Buscar en la tabla de datos']")
    PRIMERA_FILA = (
        By.XPATH,
        "//div[contains(@class, 'dx-datagrid-rowsview')]"
        "//table[contains(@class, 'dx-datagrid-table')]"
        "//tbody/tr[contains(@class, 'dx-data-row')][1]",
    )


class ProyectoDetalleSelectors:
    """Selectores dentro de la vista detalle/edición de una Obra."""
    BTN_EDITAR = (
        By.XPATH,
        "//button[contains(@class, 'btn-editar') or @title='Editar (Alt+E)']",
    )
    BTN_GUARDAR_GENERAL = (
        By.XPATH,
        "//div[contains(@class, 'page-bar-buttons')]"
        "//button[contains(@class, 'btn-editing') or contains(@class, 'yellow-casablanca') or @title='Guardar (Alt+G)']",
    )
    BTN_REGRESAR = (
        By.XPATH,
        "//button[contains(@class, 'btn-cancelar') or @title='Regresar' or .//i[contains(@class, 'fa-arrow-left')]]",
    )

    @staticmethod
    def fila_usuario(indice: int):
        return (By.XPATH, f"//tr[contains(@class, 'dx-data-row')][{indice}]")

    @staticmethod
    def badge_nombre_usuario(indice: int):
        return (
            By.XPATH,
            f"//tr[contains(@class, 'dx-data-row')][{indice}]"
            f"//div[contains(@class, 'badge-info') or contains(@class, 'badge')]",
        )

    @staticmethod
    def celda_nombre_usuario(indice: int):
        return (
            By.XPATH,
            f"//tr[contains(@class, 'dx-data-row')][{indice}]//td[@aria-colindex='2']",
        )

    @staticmethod
    def icono_permisos_usuario(indice: int):
        return (
            By.XPATH,
            f"//tr[contains(@class, 'dx-data-row')][{indice}]"
            f"//span[contains(@class, 'wbs-button') and @title='Permisos Documentos']",
        )


class SidebarPermisosSelectors:
    """Selectores del sidebar lateral de Permisos Documentos."""
    XPATH_SIDEBAR_STR = "//div[@id='Sidebar$PermisosDocumentos']"
    SIDEBAR = (By.XPATH, XPATH_SIDEBAR_STR)

    BTN_CHEVRON_TIPO_PROCESO = (
        By.XPATH,
        f"{XPATH_SIDEBAR_STR}//div[contains(@class, 'col-lg-4')][1]"
        f"//button[contains(@class, 'btn-ico-ek')]",
    )

    BTN_OPCION_NO = (
        By.XPATH,
        f"{XPATH_SIDEBAR_STR}//div[contains(@class, 'col-lg-4')][1]"
        f"//span[contains(@class, 'badgeSquare') and normalize-space(text())='NO']",
    )

    BTN_GUARDAR_SIDEBAR = (
        By.XPATH,
        f"{XPATH_SIDEBAR_STR}//button[contains(@class, 'c-sidebar-close-button') and @title='Guardar (Alt+G)']",
    )


class SafeSelectorDict(dict):
    """Diccionario tolerante a fallos que retorna cadena vacía si no existe la clave."""
    def __missing__(self, key: str) -> str:
        return ""


SELECTORES = SafeSelectorDict({
    "login_user": "username",
    "login_pass": "password",
    "login_submit": "btnSubmit",
    "buscador_obras": "//input[@aria-label='Buscar en la tabla de datos']",
    "primera_fila": "//div[contains(@class, 'dx-datagrid-rowsview')]//table[contains(@class, 'dx-datagrid-table')]//tbody/tr[contains(@class, 'dx-data-row')][1]",
    "btn_editar": "//button[contains(@class, 'btn-editar') or @title='Editar (Alt+E)']",
    "btn_guardar_general": "//div[contains(@class, 'page-bar-buttons')]//button[contains(@class, 'btn-editing') or contains(@class, 'yellow-casablanca') or @title='Guardar (Alt+G)']",
    "btn_regresar": "//button[contains(@class, 'btn-cancelar') or @title='Regresar' or .//i[contains(@class, 'fa-arrow-left')]]",
    "sidebar_permisos": "//div[@id='Sidebar$PermisosDocumentos']",
})

