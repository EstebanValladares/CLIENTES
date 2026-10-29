"""
Componente de interacción UI con Aryve (Selenium).
Centraliza el manejo seguro de Select2, Paneles editables y Tablas DevExtreme.
"""
import base64
import os
import re
import sys
import time
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from USUARIOS.puestos_service import normalizar_alnum
from USUARIOS.selectores import (
    ECOSYSTEM_DIR,
    SELECTORES,
    TIMEOUT_CORTO,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
)


# ==============================================================================
# INICIO DE SESIÓN
# ==============================================================================

def _resolver_credenciales(usuario: str | None = None, password: str | None = None) -> tuple[str, str]:
    if not usuario or not password:
        if str(ECOSYSTEM_DIR) not in sys.path:
            sys.path.insert(0, str(ECOSYSTEM_DIR))
        try:
            from NUCLEO.config import obtener_credenciales_aryve
            u_env, p_env = obtener_credenciales_aryve()
            usuario = usuario or u_env
            password = password or p_env
        except Exception:
            pass

    if not usuario or not password:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ECOSYSTEM_DIR, ".env"))
        usuario = usuario or os.getenv("EK10_USER", "")
        password = password or os.getenv("EK10_PASS", "")

    return str(usuario or ""), str(password or "")


def iniciar_sesion(driver: Any, usuario: str | None = None, password: str | None = None) -> None:
    """Inicia sesión de forma segura en Aryve con manejo de sesión refrescada."""
    user_final, pass_final = _resolver_credenciales(usuario, password)
    print("Iniciando sesión en Aryve...")

    user_input = WebDriverWait(driver, TIMEOUT_MEDIO).until(
        EC.element_to_be_clickable((By.ID, SELECTORES["login_user_id"]))
    )
    user_input.clear()
    user_input.send_keys(user_final)

    pass_input = driver.find_element(By.ID, SELECTORES["login_pass_id"])
    pass_input.clear()
    pass_input.send_keys(pass_final)

    driver.find_element(By.ID, SELECTORES["login_submit_id"]).click()

    WebDriverWait(driver, TIMEOUT_MEDIO).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(2.0)
    driver.refresh()
    time.sleep(1.5)
    print("¡Logeo exitoso en Aryve!")


# ==============================================================================
# MANEJO DE DESPLEGABLES SELECT2
# ==============================================================================

def _texto_select2(driver: Any, selector: str | Any) -> str:
    try:
        el = driver.find_element(By.ID, selector) if isinstance(selector, str) else selector
        return (el.text or el.get_attribute("title") or "").strip()
    except Exception:
        return ""


def seleccionar_opcion_menu(
    driver: Any,
    selector_caja: str | Any,
    texto_a_elegir: str,
    nombre_seccion: str = "GENERAL",
) -> bool:
    """Busca y selecciona una opción en un desplegable select2 de Aryve."""
    texto_a_elegir = str(texto_a_elegir).strip()
    if not texto_a_elegir:
        return True

    print(f"  [{nombre_seccion}] Seleccionando '{texto_a_elegir}'...")
    try:
        if isinstance(selector_caja, str):
            caja = WebDriverWait(driver, TIMEOUT_CORTO).until(
                EC.element_to_be_clickable((By.ID, selector_caja))
            )
        else:
            caja = selector_caja

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caja)
        time.sleep(0.1)

        try:
            caja.click()
        except Exception:
            driver.execute_script("arguments[0].click();", caja)

        # Localizar el input de búsqueda select2
        input_busqueda = None
        for xp in ["//input[contains(@class, 'select2-search__field')]", "//input[@type='search']"]:
            try:
                elem = driver.find_element(By.XPATH, xp)
                if elem.is_displayed():
                    input_busqueda = elem
                    break
            except Exception:
                continue

        if input_busqueda:
            input_busqueda.clear()
            input_busqueda.send_keys(texto_a_elegir)
            time.sleep(0.4)

        # Localizar resultado
        texto_norm = normalizar_alnum(texto_a_elegir)
        xpath_opciones = [
            f"//li[contains(@class, 'select2-results__option') and not(contains(@class, 'loading')) and normalize-space()='{texto_a_elegir}']",
            f"//li[contains(@class, 'select2-results__option') and contains(., '{texto_a_elegir}')]",
            "//li[contains(@class, 'select2-results__option') and not(contains(@class, 'loading'))][1]",
        ]

        opcion = None
        for xp in xpath_opciones:
            try:
                opcion = WebDriverWait(driver, 2.5).until(EC.element_to_be_clickable((By.XPATH, xp)))
                if opcion:
                    break
            except Exception:
                continue

        if not opcion:
            print(f"  [AVISO]: No se encontró opción para '{texto_a_elegir}'. Cerrando select2...")
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            return False

        try:
            opcion.click()
        except Exception:
            driver.execute_script("arguments[0].click();", opcion)

        time.sleep(0.2)
        return True
    except Exception as e:
        print(f"  [ERROR SELECT2] Error al seleccionar '{texto_a_elegir}': {e}")
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return False


# ==============================================================================
# MANEJO DE PANELES (NIVELES, GRUPOS, CLASIFICADORES)
# ==============================================================================

def obtener_panel_seccion(driver: Any, nombre_seccion: str) -> Any | None:
    """Localiza el contenedor del panel dado su encabezado."""
    nombre_upper = nombre_seccion.upper()
    xpaths = [
        f"//div[contains(@class, 'panel-heading') and contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{nombre_upper}')]/ancestor::div[contains(@class, 'panel')][1]",
        f"//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{nombre_upper}')]/ancestor::div[contains(@class, 'panel')][1]",
    ]
    for xpath in xpaths:
        try:
            p = driver.find_element(By.XPATH, xpath)
            if p:
                return p
        except Exception:
            continue
    return None


def abrir_panel(driver: Any, nombre_seccion: str) -> bool:
    """Abre un panel en modo edición haciendo clic en su botón '+'."""
    panel = obtener_panel_seccion(driver, nombre_seccion)
    if not panel:
        return False

    clases = panel.get_attribute("class") or ""
    if "panel-edit" in clases:
        return True

    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", panel)
        btn_agregar = panel.find_element(
            By.XPATH,
            ".//div[contains(@class, 'actions')]//button[@title='Agregar' or contains(@class, 'btn-ico-ek')]",
        )
        try:
            btn_agregar.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_agregar)

        for _ in range(25):
            time.sleep(0.1)
            p_act = obtener_panel_seccion(driver, nombre_seccion)
            if p_act and "panel-edit" in (p_act.get_attribute("class") or ""):
                return True
        return True
    except Exception as e:
        print(f"[ERROR ABRIR PANEL {nombre_seccion}]: {e}")
        return False


def cancelar_y_cerrar_panel(driver: Any, nombre_seccion: str) -> bool:
    """Fuerza el cierre (cancelar) de un panel para descongelar pantalla."""
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass

    panel = obtener_panel_seccion(driver, nombre_seccion)
    if panel and "panel-edit" in (panel.get_attribute("class") or ""):
        try:
            btn_cancelar = panel.find_element(
                By.XPATH,
                ".//button[contains(@title, 'Regresar') or contains(@title, 'Cancelar') or (contains(@class, 'btn-ico-ek') and not(contains(@title, 'Guardar')))]",
            )
            driver.execute_script("arguments[0].click();", btn_cancelar)
        except Exception:
            pass
        time.sleep(0.3)
    return True


def guardar_y_cerrar_panel(driver: Any, nombre_seccion: str, id_btn_guardar: str) -> bool:
    """Presiona la palomita de guardar del panel y espera a que pase a modo vista."""
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass
    time.sleep(0.2)

    btn_guardar = None
    try:
        btn_guardar = WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.ID, id_btn_guardar)))
    except Exception:
        panel = obtener_panel_seccion(driver, nombre_seccion)
        if panel:
            try:
                btn_guardar = panel.find_element(By.XPATH, ".//button[contains(@title, 'Guardar') or contains(@id, 'saveButtonKey')]")
            except Exception:
                pass

    if btn_guardar:
        try:
            btn_guardar.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_guardar)

        for _ in range(25):
            time.sleep(0.1)
            p_act = obtener_panel_seccion(driver, nombre_seccion)
            if p_act:
                clases = p_act.get_attribute("class") or ""
                if "panel-view" in clases and "panel-edit" not in clases:
                    return True

    cancelar_y_cerrar_panel(driver, nombre_seccion)
    return False


def leer_contador_panel(driver: Any, nombre_seccion: str) -> int | None:
    """Lee el número en el encabezado del panel (ej. 'CLASIFICADORES [9]')."""
    panel = obtener_panel_seccion(driver, nombre_seccion)
    if not panel:
        return None
    try:
        encabezado = panel.find_element(By.XPATH, ".//div[contains(@class, 'panel-heading')]")
        m = re.search(r"\d+", encabezado.text or encabezado.get_attribute("textContent") or "")
        return int(m.group()) if m else None
    except Exception:
        return None


# ==============================================================================
# TABLA DE CLASIFICADORES HIJOS (DevExtreme DataGrid)
# ==============================================================================

def buscar_y_marcar_clasificador_hijo(driver: Any, clave_hijo: str) -> bool:
    """Busca un hijo en la tabla DevExtreme y marca su checkbox."""
    clave_hijo = str(clave_hijo).strip()
    if not clave_hijo:
        return True

    try:
        # 1. Input de búsqueda en la tabla
        for xp in [
            "(//input[@aria-label='Buscar en la tabla de datos'])[last()]",
            "//div[contains(@class, 'panel-body')]//input[contains(@class, 'dx-texteditor-input')]",
            "//input[contains(@placeholder, 'Buscar')]",
        ]:
            try:
                inputs = driver.find_elements(By.XPATH, xp)
                for inp in inputs:
                    if inp.is_displayed():
                        driver.execute_script("arguments[0].value = '';", inp)
                        inp.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                        inp.send_keys(clave_hijo)
                        break
            except Exception:
                continue

        # 2. Localizar fila
        clave_upper = clave_hijo.upper()
        fila = None
        for _ in range(12):
            try:
                filas = driver.find_elements(By.XPATH, "//tr[contains(@class, 'dx-row') and not(contains(@class, 'dx-header-row'))]")
                for f in filas:
                    if not f.is_displayed():
                        continue
                    if clave_upper in [c.text.strip().upper() for c in f.find_elements(By.TAG_NAME, "td") if c.text]:
                        fila = f
                        break
                if fila:
                    break
            except Exception:
                time.sleep(0.1)
            time.sleep(0.1)

        if not fila:
            print(f"    [AVISO]: No se encontró fila para '{clave_hijo}'.")
            return False

        # 3. Marcar checkbox
        icono = None
        for xp_i in [".//i[contains(@onclick, 'dgOnClickSelect')]", ".//i[contains(@class, 'fa-square') or contains(@class, 'fa-check')]", ".//td[1]//i"]:
            try:
                elems = fila.find_elements(By.XPATH, xp_i)
                for el in elems:
                    if el.is_displayed() or el.get_attribute("onclick"):
                        icono = el
                        break
                if icono:
                    break
            except Exception:
                continue

        if not icono:
            return False

        title_attr = (icono.get_attribute("title") or "").strip()
        class_attr = (icono.get_attribute("class") or "").strip()
        if ("Seleccionado" in title_attr and "No Seleccionado" not in title_attr) or ("fa-check" in class_attr and "fa-square-o" not in class_attr):
            return True

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icono)
        try:
            icono.click()
        except Exception:
            driver.execute_script("arguments[0].click();", icono)

        onclick = icono.get_attribute("onclick")
        if onclick:
            try:
                driver.execute_script(onclick)
            except Exception:
                pass

        time.sleep(0.2)
        print(f"    [✔] Casilla marcada para '{clave_hijo}'.")
        return True
    except Exception as e:
        print(f"    [ERROR HIJO]: {e}")
        return False

