"""
Catálogo centralizado de selectores DOM para el módulo PROVEEDORES en Aryve.
Separa selectores tipados para Page Objects y mantiene el diccionario `SELECTORES`
para compatibilidad con el analizador de grafo de `NUCLEO`.
"""
from selenium.webdriver.common.by import By


SELECTORES: dict[str, str] = {
    # --- LOGIN ---
    "login_username": "username",
    "login_password": "password",
    "login_submit": "btnSubmit",

    # --- TIPO DE PERSONA ---
    "caja_tipo_persona": "select2-formControl_TipoPersona-container",
    "select_tipo_persona": "formControl_TipoPersona",

    # --- DATOS GENERALES / IDENTIFICACIÓN ---
    "clave": "formControl_Clave",
    "nombre": "formControl_Nombre",
    "apellido_paterno": "formControl_ApellidoPaterno",
    "apellido_materno": "formControl_ApellidoMaterno",
    "rfc": "formControl_RFC",
    "nombre_corto": "formControl_NombreCorto",
    "check_obliga_cfdi": "formControl_Proveedores_obliga_cfd",
    "check_factoraje": "formControl_Proveedores_factoraje",

    # --- DIRECCIÓN / DOMICILIO ---
    "domicilio": "formControl_Domicilio",
    "num_exterior": "formControl_NumExterior",
    "caja_asentamiento": "select2-formControl_Asentamiento-container",
    "select_asentamiento": "formControl_Asentamiento",

    # --- PANELES Y GENERALES ---
    "panel_tipo_persona": "TIPO DE PERSONA",
    "btn_guardar_general": "//button[contains(@class, 'btn-editing') and .//i[contains(@class, 'icon-cloud-upload')]]",
    "input_busqueda_select2": "//input[contains(@class, 'select2-search__field')]",
    "opciones_select2": "//li[contains(@class, 'select2-results__option') and not(@aria-disabled='true') and not(contains(@class, 'select2-results__message'))]",
}


class LoginSelectors:
    """Selectores de la pantalla de inicio de sesión de Aryve."""
    INPUT_USERNAME = (By.ID, SELECTORES["login_username"])
    INPUT_PASSWORD = (By.ID, SELECTORES["login_password"])
    BTN_SUBMIT = (By.ID, SELECTORES["login_submit"])
    BODY = (By.TAG_NAME, "body")


class LoaderSelectors:
    """Selectores de indicadores de carga en Aryve."""
    LOAD_PANEL = (
        By.XPATH,
        "//div[contains(@class, 'dx-loadpanel-content') and not(contains(@style, 'display: none'))] | "
        "//div[contains(@class, 'loading') or contains(text(), 'Cargando')]",
    )


class ProveedorFormSelectors:
    """Selectores del formulario de Alta / Edición de Proveedores en Aryve."""
    BODY = (By.TAG_NAME, "body")

    # Panel Tipo de Persona
    CAJA_TIPO_PERSONA = (By.ID, SELECTORES["caja_tipo_persona"])
    BTN_AVANZAR_PANEL = (
        By.XPATH,
        "//div[contains(@class, 'panel-heading') and .//*[contains(text(), 'TIPO DE PERSONA')]]//a | "
        "//div[contains(@class, 'panel-heading') and .//*[contains(text(), 'TIPO DE PERSONA')]]"
        "//i[contains(@class, 'arrow') or contains(@class, 'right') or contains(@class, 'next')]/.. | "
        "//div[contains(@class, 'panel-heading')]"
        "//*[contains(@class, 'fa-arrow-right') or contains(@class, 'fa-chevron-right') or contains(@class, 'icon-arrow-right')]",
    )

    # Identificación
    INPUT_CLAVE = (By.ID, SELECTORES["clave"])
    INPUT_NOMBRE = (By.ID, SELECTORES["nombre"])
    INPUT_RFC = (By.ID, SELECTORES["rfc"])
    INPUT_NOMBRE_CORTO = (By.ID, SELECTORES["nombre_corto"])

    IDS_APELLIDO_PATERNO = (
        SELECTORES["apellido_paterno"],
        "formControl_Paterno",
        "formControl_PrimerApellido",
        "ApellidoPaterno",
    )
    XPATH_APELLIDO_PATERNO_FALLBACK = (
        By.XPATH,
        "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PATERNO')]/following-sibling::*//input | "
        "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PATERNO')]/..//input",
    )

    IDS_APELLIDO_MATERNO = (
        SELECTORES["apellido_materno"],
        "formControl_Materno",
        "formControl_SegundoApellido",
        "ApellidoMaterno",
    )
    XPATH_APELLIDO_MATERNO_FALLBACK = (
        By.XPATH,
        "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'MATERNO')]/following-sibling::*//input | "
        "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'MATERNO')]/..//input",
    )

    # Casillas de verificación (Checkboxes React)
    ID_OBLIGA_CFDI = SELECTORES["check_obliga_cfdi"]
    ID_FACTORAJE = SELECTORES["check_factoraje"]

    # Domicilio y Asentamiento
    INPUT_DOMICILIO = (By.ID, SELECTORES["domicilio"])
    INPUT_NUM_EXTERIOR = (By.ID, SELECTORES["num_exterior"])
    CAJA_ASENTAMIENTO = (By.ID, SELECTORES["caja_asentamiento"])
    INPUT_BUSQUEDA_SELECT2 = (By.XPATH, SELECTORES["input_busqueda_select2"])
    OPCIONES_SELECT2 = (By.XPATH, SELECTORES["opciones_select2"])

    # Guardado global
    XPATHS_BTN_GUARDAR = (
        SELECTORES["btn_guardar_general"],
        "//button[contains(@class, 'page-bar-button') and .//i[contains(@class, 'icon-cloud-upload')]]",
        "//div[contains(@class, 'page-bar-buttons')]//button[contains(@class, 'btn-editing') or contains(@data-tip, 'Guardar') or contains(@title, 'Guardar')]",
        "//button[@data-tip='Guardar (Alt+G)' or @title='Guardar (Alt+G)' or contains(@title, 'Guardar')]",
    )

    @staticmethod
    def opcion_select2_por_texto(texto: str):
        texto_upper = texto.strip().upper()
        return (
            By.XPATH,
            f"//li[contains(@class, 'select2-results__option') and "
            f"contains(translate(text(), 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), '{texto_upper}')]",
        )

