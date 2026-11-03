# -*- coding: utf-8 -*-
"""
explorar_formulario.py
----------------------
Reconocimiento del formulario de alta de proveedores (NO guarda nada):
  1. Login en suite.ekloud.
  2. Abre una pestana con el dashboard de proveedores y da click en "Agregar (Alt+A)".
  3. Guarda el HTML/captura del formulario recien abierto.
  4. Selecciona en el DDL "Tipo de Persona" cada opcion (FISICA y MORAL) y por cada una
     guarda HTML + captura + JSON con todos los campos del formulario, marcando los obligatorios.
  5. Escribe campos_obligatorios.txt con la comparacion FISICA vs MORAL.

Salida en CARPETA_SALIDA.

Credenciales: variables de entorno EKLOUD_USUARIO y EKLOUD_PASSWORD; si no existen se
toman de USUARIO/PASSWORD en la Config de SectoresCrear/crear_sectores.py.
Requisitos: pip install selenium
"""

import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Proyecto anterior del que se toman las credenciales si no vienen en variables de entorno
ARCHIVO_CREDENCIALES = r"C:\GV\Proyectos\SectoresCrear\crear_sectores.py"


def credencial(nombre_env, nombre_config):
    """Valor de la variable de entorno o de las configuradas en el ecosistema."""
    valor = os.environ.get(nombre_env)
    if valor:
        return valor
    if "USUARIO" in nombre_env.upper():
        val = os.environ.get("EK10_USER") or os.environ.get("EK9_USER")
        if val:
            return val
    if "PASSWORD" in nombre_env.upper():
        val = os.environ.get("EK10_PASS") or os.environ.get("EK9_PASS")
        if val:
            return val
    try:
        with open(ARCHIVO_CREDENCIALES, encoding="utf-8") as f:
            m = re.search(rf'^\s*{nombre_config}\s*=\s*"([^"]*)"', f.read(), re.M)
        return m.group(1) if m else ""
    except OSError:
        return ""


class Config:
    URL_LOGIN = "https://suite.ekloud.net:1445/Aryve/Kontrol/Login?ReturnUrl=%2FAryve%2F"
    URL_PROVEEDORES = "https://suite.ekloud.net:1445/Aryve/#/scp/proveedores"
    URL_SIGNOUT = "https://suite.ekloud.net:1445/Aryve/Kontrol/SignOut"

    USUARIO = credencial("EKLOUD_USUARIO", "USUARIO")
    PASSWORD = credencial("EKLOUD_PASSWORD", "PASSWORD")

    CARPETA_SALIDA = os.path.join(os.path.dirname(os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__)), "Html")
    TIPOS_PERSONA = ("FISICA", "MORAL")

    TIEMPO_ESPERA = 30
    NAVEGADOR_HEADLESS = False


log = logging.getLogger("explorar_proveedores")


def configurar_log():
    os.makedirs(Config.CARPETA_SALIDA, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
    log.setLevel(logging.INFO)
    for h in (logging.FileHandler(os.path.join(Config.CARPETA_SALIDA, "log_explorar.txt"), encoding="utf-8"),
              logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)


def js_click(driver, elemento):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", elemento)


def visible(driver, xpath, espera=None):
    def _buscar(d):
        return next((e for e in d.find_elements(By.XPATH, xpath) if e.is_displayed()), False)
    return WebDriverWait(driver, espera or Config.TIEMPO_ESPERA).until(_buscar)


def guardar(driver, nombre):
    base = os.path.join(Config.CARPETA_SALIDA, f"{nombre}_{datetime.now():%Y%m%d_%H%M%S}")
    try:
        driver.save_screenshot(base + ".png")
        with open(base + ".html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        log.info("Guardado %s.html/.png", base)
    except WebDriverException as e:
        log.warning("No se pudo guardar %s: %s", nombre, e)
    return base


def crear_driver():
    opciones = webdriver.ChromeOptions()
    if Config.NAVEGADOR_HEADLESS:
        opciones.add_argument("--headless=new")
    opciones.add_argument("--start-maximized")
    opciones.add_argument("--ignore-certificate-errors")
    return webdriver.Chrome(options=opciones)


def iniciar_sesion(driver, intentos=6, espera_login=10):
    """Entra al sistema. Si la pagina de login no reacciona (no carga o no aparece el campo de
    usuario) en `espera_login` segundos, la recarga y reintenta, hasta `intentos` veces."""
    try:
        driver.set_page_load_timeout(espera_login)  # que driver.get no se cuelgue mas de 10 s
        for intento in range(1, intentos + 1):
            try:
                driver.get(Config.URL_LOGIN)
            except TimeoutException:
                # La pagina no termino de cargar en el tiempo dado; se corta y se recarga.
                log.warning("La pagina de login no cargo en %d s; se recarga (intento %d/%d).",
                            espera_login, intento, intentos)
                try:
                    driver.execute_script("window.stop();")
                except WebDriverException:
                    pass
            try:
                campo = WebDriverWait(driver, espera_login).until(
                    EC.presence_of_element_located((By.ID, "username")))
            except TimeoutException:
                log.warning("El login no reacciono en %d s; se recarga (intento %d/%d).",
                            espera_login, intento, intentos)
                continue
            campo.clear()
            campo.send_keys(Config.USUARIO)
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys(Config.PASSWORD)
            driver.find_element(By.ID, "btnSubmit").click()
            try:
                # El dashboard tarda bastante en cargar tras el login
                WebDriverWait(driver, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.dropdown.dropdown-user")))
            except TimeoutException:
                log.warning("El dashboard no cargo tras enviar las credenciales; se reintenta "
                            "(intento %d/%d).", intento, intentos)
                continue
            log.info("Login correcto como %s", Config.USUARIO)
            return
        raise RuntimeError("No se pudo iniciar sesion.")
    finally:
        try:
            driver.set_page_load_timeout(300)  # se restaura para el resto de la navegacion
        except WebDriverException:
            pass


def abrir_pestana(driver, url):
    previas = set(driver.window_handles)
    driver.execute_script("window.open(arguments[0], '_blank');", url)
    WebDriverWait(driver, Config.TIEMPO_ESPERA).until(lambda d: set(d.window_handles) - previas)
    driver.switch_to.window((set(driver.window_handles) - previas).pop())


# Recorre todos los controles del formulario y los describe. Un campo se considera
# obligatorio si tiene required/aria-required, clase "required" en el control o su
# contenedor, o su etiqueta lleva "*".
JS_CAMPOS = r"""
const campos = [];
const etiquetaDe = (el) => {
  if (el.id) {
    const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (l) return l;
  }
  const grupo = el.closest('.form-group, .dx-field, .dx-field-item, .col, [class*="col-"]');
  return grupo ? grupo.querySelector('label, .dx-field-item-label-text, .control-label') : null;
};
document.querySelectorAll('input, select, textarea').forEach(el => {
  const tipo = (el.type || el.tagName).toLowerCase();
  if (['hidden', 'button', 'submit', 'search'].includes(tipo) && el.tagName !== 'SELECT') return;
  if (el.closest('.dx-datagrid-search-panel, .select2-search')) return;
  const lab = etiquetaDe(el);
  const textoLab = lab ? lab.textContent.replace(/\s+/g, ' ').trim() : '';
  const grupo = el.closest('.form-group, .dx-field-item');
  const clases = [el.className, grupo ? grupo.className : '', lab ? lab.className : ''].join(' ');
  const rect = el.getBoundingClientRect();
  // select2 oculta el <select>; su visibilidad real es la del contenedor select2
  const s2 = el.tagName === 'SELECT' ? el.nextElementSibling : null;
  const esVisible = (rect.width > 0 && rect.height > 0) ||
                    !!(s2 && s2.classList.contains('select2') && s2.getBoundingClientRect().width > 0);
  const pestana = el.closest('.tab-pane');
  campos.push({
    id: el.id || '', name: el.name || '', tag: el.tagName.toLowerCase(), tipo: tipo,
    etiqueta: textoLab,
    // EK marca los obligatorios con <i class="fa fa-asterisk"> dentro del label
    obligatorio: !!(lab && lab.querySelector('.fa-asterisk')) ||
                 el.required || el.getAttribute('aria-required') === 'true' ||
                 /\brequired\b|\bobligatorio\b/i.test(clases) || /\*/.test(textoLab),
    visible: esVisible, deshabilitado: el.disabled || el.readOnly,
    maxlength: el.maxLength > 0 ? el.maxLength : null,
    valor: el.tagName === 'SELECT' ? (el.selectedOptions[0] ? el.selectedOptions[0].text : '') : el.value,
    opciones: el.tagName === 'SELECT' ? Array.from(el.options).map(o => o.text.trim()).slice(0, 60) : null,
    select2: !!(s2 && s2.classList.contains('select2')),
    pestana: pestana ? (pestana.id || '') : ''
  });
});
return campos;
"""


def sin_acentos(texto):
    return unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().upper().strip()


def seleccionar_tipo_persona(driver, texto):
    """Abre el select2 de Tipo de Persona y da click en la opcion `texto` (FISICA/MORAL)."""
    # select2 abre con mousedown: se necesita click real, no element.click() por JS
    caja = driver.find_element(By.XPATH, "//span[@id='select2-formControl_TipoPersona-container']"
                                         "/ancestor::span[contains(@class,'select2-selection')][1]")
    ActionChains(driver).move_to_element(caja).click().perform()
    log.info("DDL Tipo de Persona abierto")
    opciones = WebDriverWait(driver, Config.TIEMPO_ESPERA).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, ".select2-container--open li.select2-results__option"))
    opcion = next((o for o in opciones if sin_acentos(o.text) == texto), None)
    if opcion is None:
        raise RuntimeError(f"El DDL Tipo de Persona no tiene la opcion {texto}")
    opcion.click()
    WebDriverWait(driver, Config.TIEMPO_ESPERA).until(lambda d: sin_acentos(
        d.find_element(By.ID, "select2-formControl_TipoPersona-container").get_attribute("textContent")) == texto)
    log.info("Tipo de Persona = %s", texto)


def continuar_tipo_persona(driver):
    """Click en la flecha (->) del panel Tipo de Persona y espera a que se carguen mas campos."""
    flecha = visible(driver, "//div[contains(@class,'panel')][.//span[contains(@class,'caption-subject')]"
                             "[normalize-space()='Tipo de Persona']]//button[i[contains(@class,'fa-arrow-right')]]")
    ActionChains(driver).move_to_element(flecha).click().perform()
    log.info("Click en la flecha de Tipo de Persona")
    WebDriverWait(driver, Config.TIEMPO_ESPERA).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "input, select, textarea")) > 5)
    time.sleep(3)


def abrir_formulario_nuevo(driver, principal):
    """Cierra pestanas extra, abre una pestana con el dashboard y da 'Agregar (Alt+A)'."""
    for handle in driver.window_handles:
        if handle != principal:
            driver.switch_to.window(handle)
            driver.close()
    driver.switch_to.window(principal)
    abrir_pestana(driver, Config.URL_PROVEEDORES)
    agregar = visible(driver, "//button[@title='Agregar (Alt+A)']", 60)
    js_click(driver, agregar)
    WebDriverWait(driver, Config.TIEMPO_ESPERA).until(lambda d: "nuevo" in d.current_url)
    WebDriverWait(driver, Config.TIEMPO_ESPERA).until(
        EC.presence_of_element_located((By.ID, "select2-formControl_TipoPersona-container")))
    time.sleep(2)
    log.info("Formulario abierto: %s", driver.current_url)


def main():
    configurar_log()
    if not (Config.USUARIO and Config.PASSWORD):
        sys.exit("Sin credenciales: defina EKLOUD_USUARIO/EKLOUD_PASSWORD o revise " + ARCHIVO_CREDENCIALES)
    driver = crear_driver()
    resultado = {}
    try:
        iniciar_sesion(driver)
        principal = driver.current_window_handle
        for n, tipo in enumerate(Config.TIPOS_PERSONA, 1):
            # Cada tipo en un formulario nuevo: tras la flecha el tipo ya no se puede cambiar
            abrir_formulario_nuevo(driver, principal)
            seleccionar_tipo_persona(driver, tipo)
            continuar_tipo_persona(driver)
            base = guardar(driver, f"0{n}_persona_{tipo.lower()}")
            campos = driver.execute_script(JS_CAMPOS)
            resultado[tipo] = campos
            with open(base + "_campos.json", "w", encoding="utf-8") as f:
                json.dump(campos, f, ensure_ascii=False, indent=2)
            log.info("%s: %d campos, %d obligatorios", tipo, len(campos),
                     sum(1 for c in campos if c["obligatorio"]))
    except (TimeoutException, WebDriverException, RuntimeError) as e:
        log.error("Fallo: %s", getattr(e, "msg", None) or e)
        guardar(driver, "99_error")
    finally:
        if resultado:
            escribir_resumen(resultado)
        try:
            driver.get(Config.URL_SIGNOUT)
        except WebDriverException:
            pass
        driver.quit()


def escribir_resumen(resultado):
    ruta = os.path.join(Config.CARPETA_SALIDA, "campos_obligatorios.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        for tipo, campos in resultado.items():
            f.write(f"===== {tipo} =====\n")
            for c in campos:
                if c["visible"]:
                    marca = "*" if c["obligatorio"] else " "
                    f.write(f" {marca} {c['etiqueta'] or '(sin etiqueta)':40} id={c['id']:45} "
                            f"tipo={c['tipo']:12} pestana={c['pestana']}\n")
            f.write("\n")
        if len(resultado) == 2:
            a, b = (resultado[t] for t in Config.TIPOS_PERSONA)
            ids = lambda cs, cond: {c["id"] or c["name"] for c in cs if cond(c)}
            vis_a, vis_b = ids(a, lambda c: c["visible"]), ids(b, lambda c: c["visible"])
            obl_a = ids(a, lambda c: c["obligatorio"] and c["visible"])
            obl_b = ids(b, lambda c: c["obligatorio"] and c["visible"])
            f.write("===== DIFERENCIAS =====\n")
            f.write(f"Visibles solo en FISICA: {sorted(vis_a - vis_b)}\n")
            f.write(f"Visibles solo en MORAL:  {sorted(vis_b - vis_a)}\n")
            f.write(f"Obligatorios solo en FISICA: {sorted(obl_a - obl_b)}\n")
            f.write(f"Obligatorios solo en MORAL:  {sorted(obl_b - obl_a)}\n")
    log.info("Resumen: %s", ruta)


if __name__ == "__main__":
    main()
