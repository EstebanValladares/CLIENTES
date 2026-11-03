# -*- coding: utf-8 -*-
"""
explorar_contratistas.py
------------------------
Reconocimiento del formulario de alta de contratistas (NO guarda nada):
  1. Login, pestana con #/scco/Contratistas y click en "Agregar (Alt+A)".
  2. Guarda HTML/captura/JSON de campos del formulario.
  3. Da click en la lupa del campo Proveedor y guarda HTML/captura del modal de busqueda.
Salida en Html/contratistas.
"""

import json
import sys
import os
import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import explorar_formulario as ek

URL_CONTRATISTAS = "https://suite.ekloud.net:1445/Aryve/#/scco/Contratistas"


def main():
    ek.Config.CARPETA_SALIDA = os.path.join(os.path.dirname(ek.Config.CARPETA_SALIDA), "Html", "contratistas") \
        if not ek.Config.CARPETA_SALIDA.endswith("Html") else os.path.join(ek.Config.CARPETA_SALIDA, "contratistas")
    ek.configurar_log()
    driver = ek.crear_driver()
    try:
        ek.iniciar_sesion(driver)
        ek.abrir_pestana(driver, URL_CONTRATISTAS)
        agregar = ek.visible(driver, "//button[@title='Agregar (Alt+A)']", 90)
        time.sleep(2)
        ek.guardar(driver, "01_dashboard_contratistas")
        ek.js_click(driver, agregar)
        WebDriverWait(driver, 30).until(lambda d: "nuevo" in d.current_url.lower()
                                        or len(d.find_elements(By.CSS_SELECTOR, "input, select")) > 5)
        time.sleep(4)
        ek.log.info("Formulario: %s", driver.current_url)
        base = ek.guardar(driver, "02_formulario_contratista")
        campos = driver.execute_script(ek.JS_CAMPOS)
        with open(base + "_campos.json", "w", encoding="utf-8") as f:
            json.dump(campos, f, ensure_ascii=False, indent=2)
        for c in campos:
            if c["visible"]:
                ek.log.info("  %s %-30s id=%s tipo=%s", "*" if c["obligatorio"] else " ",
                            c["etiqueta"], c["id"], c["tipo"])

        # Lupa del campo Proveedor
        lupas = driver.execute_script(r"""
          const r = [];
          document.querySelectorAll('i.fa-search, i.fa-search-plus, .fa-magnifying-glass').forEach(i => {
            const b = i.closest('button, span, a, div');
            const g = i.closest('.form-group');
            const lab = g ? (g.querySelector('label') || {}).textContent : '';
            r.push([b, (lab || '').trim(), b ? b.outerHTML.slice(0, 200) : '']);
          });
          return r;
        """)
        for _, lab, html in lupas:
            ek.log.info("  Lupa: label=%r html=%s", lab, html)
        lupa = next((b for b, lab, _ in lupas if b is not None and "proveedor" in (lab or "").lower()), None)
        if lupa is None:
            ek.log.warning("No se encontro la lupa del campo Proveedor")
            return
        ek.js_click(driver, lupa)
        time.sleep(4)
        ek.guardar(driver, "03_modal_buscar_proveedor")

        # Secuencia: escribir el ID EK10 -> Aceptar -> click fuera del modal
        id_prueba = sys.argv[1] if len(sys.argv) > 1 else "1060"
        buscar = ek.visible(driver, "//input[contains(@id,'__search')]")
        buscar.click()
        buscar.send_keys(id_prueba)
        time.sleep(3)
        ek.guardar(driver, "04_modal_id_escrito")
        filas = [t.text for t in driver.find_elements(By.CSS_SELECTOR, ".modal.in .dteRow")]
        ek.log.info("Filas tras escribir %s: %s", id_prueba, filas[:5])
        # Fila cuyo enlace "Ver" apunta exactamente al ID; se da click en la celda del nombre
        fila = ek.visible(driver, f"//div[contains(@class,'modal') and contains(@class,'in')]"
                                  f"//div[contains(@class,'dteRow')][.//a[substring(@href, string-length(@href)"
                                  f" - string-length('/Proveedores/{id_prueba}') + 1) = '/Proveedores/{id_prueba}']]")
        celda = fila.find_elements(By.CSS_SELECTOR, ".dteCell")[1]
        ActionChains(driver).move_to_element(celda).click().perform()
        time.sleep(1)
        ek.log.info("Clases de la fila tras click: %s", fila.get_attribute("class"))
        ek.guardar(driver, "04b_fila_seleccionada")
        ek.js_click(driver, ek.visible(driver, "//div[contains(@class,'modal') and contains(@class,'in')]"
                                               "//button[@title='Aceptar']"))
        time.sleep(3)
        ek.guardar(driver, "05_modal_tras_aceptar")
        filas = [t.text for t in driver.find_elements(By.CSS_SELECTOR, ".modal.in tr.dx-data-row")]
        ek.log.info("Filas tras Aceptar: %s", filas[:5])
        ek.log.info("Proveedor (hidden) = %r | texto = %r",
                    driver.find_element(By.ID, "formControl_Proveedor").get_attribute("value"),
                    driver.find_element(By.ID, "select2-single-prepend-text-container").get_attribute("textContent"))
        # Click fuera del modal (en el fondo .modal-scrollable)
        fondo = driver.find_elements(By.CSS_SELECTOR, ".modal-scrollable")
        if fondo:
            ActionChains(driver).move_to_element_with_offset(fondo[-1], -fondo[-1].size["width"] // 2 + 20, 0).click().perform()
        time.sleep(3)
        ek.guardar(driver, "06_tras_click_fuera")
        ek.log.info("Modal abierto: %s", bool(driver.find_elements(By.CSS_SELECTOR, ".modal.in")))
        ek.log.info("Proveedor (hidden) = %r | texto = %r",
                    driver.find_element(By.ID, "formControl_Proveedor").get_attribute("value"),
                    driver.find_element(By.ID, "select2-single-prepend-text-container").get_attribute("textContent"))
        for c in driver.execute_script(ek.JS_CAMPOS):
            if c["visible"] and c["valor"]:
                ek.log.info("  %s = %r", c["etiqueta"], c["valor"])
    except (TimeoutException, WebDriverException, RuntimeError) as e:
        ek.log.error("Fallo: %s", getattr(e, "msg", None) or e)
        ek.guardar(driver, "99_error")
    finally:
        try:
            driver.get(ek.Config.URL_SIGNOUT)
        except WebDriverException:
            pass
        driver.quit()


if __name__ == "__main__":
    main()
