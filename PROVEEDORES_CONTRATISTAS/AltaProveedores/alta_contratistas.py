# -*- coding: utf-8 -*-
"""
alta_contratistas.py
--------------------
Da de alta como contratista (#/scco/Contratistas) a un proveedor que ya esta en EK10,
usando su CSV (debe traer el renglon "ID EK10" que escribe alta_proveedores.py).

Por cada CSV:
  1. Abre una pestana con Contratistas y da "Agregar (Alt+A)".
  1b. Abre el proveedor (#/scp/Proveedores/<ID EK10>) y revisa su seccion "Contratistas": si ya
      tiene uno vinculado no crea otro (con --guardar anota su ID en el CSV).
  2. Llena:
       Clave              = renglon Proveedor (entero)
       Nombre             = MORAL: Nombre; FISICA: nombre y apellidos separados por espacio
       Vincular Proveedor = si, Activo = si
       Registro del IMSS  = 999999
       Proveedor          = lupa -> busca el ID EK10 -> selecciona la fila de ese ID -> Aceptar
                            (si el modal sigue abierto, click fuera de el)
  3. Sin --guardar solo guarda captura + HTML del formulario lleno (prueba).
     Con --guardar da "Guardar (Alt+G)" y, si el sistema confirma, agrega al CSV el
     renglon "ID Contratista EK10,<id>". Un CSV que ya lo tiene se omite.

Uso:
  python alta_contratistas.py archivo.csv [...]            -> prueba, no guarda
  python alta_contratistas.py --guardar archivo.csv [...]  -> da de alta
"""

import logging
import os
import re
import sys
import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import alta_proveedores as ap
import explorar_formulario as ek
from proveedor_csv import leer_archivo

URL_CONTRATISTAS = "https://suite.ekloud.net:1445/Aryve/#/scco/Contratistas"
REGISTRO_IMSS = "999999"
CAMPO_ID_CONTRATISTA = "ID Contratista EK10"
# Orden de los apellidos en el Nombre de persona fisica
ORDEN_NOMBRE_FISICA = ("nombre", "a paterno", "a materno")

log = ap.log  # mismo log que el alta de proveedores


def nombre_contratista(p):
    c = p["campos"]
    if p["tipo_persona"] == "MORAL":
        return c.get("nombre", "").strip()
    return " ".join(c.get(k, "").strip() for k in ORDEN_NOMBRE_FISICA if c.get(k, "").strip())


URL_PROVEEDOR = "https://suite.ekloud.net:1445/Aryve/#/scp/Proveedores/{}"
# Panel completo (clase exacta "panel"; "panel-heading" tambien contiene la palabra)
XP_PANEL_CONTRATISTAS = ("//span[contains(@class,'caption-subject')][normalize-space()='Contratistas']"
                         "/ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' panel ')][1]")


def contratistas_del_proveedor(driver, principal, id_ek10):
    """
    Abre el proveedor en EK10 (#/scp/Proveedores/<id>) y lee su seccion "Contratistas".
    Devuelve [(id_contratista, nombre)] de los contratistas ya vinculados a ese proveedor.
    """
    for handle in driver.window_handles:
        if handle != principal:
            driver.switch_to.window(handle)
            driver.close()
    driver.switch_to.window(principal)
    ek.abrir_pestana(driver, URL_PROVEEDOR.format(id_ek10))
    panel = ek.visible(driver, XP_PANEL_CONTRATISTAS, 90)
    # La tabla del panel termina de cargar cuando aparecen sus filas (con o sin datos)
    WebDriverWait(driver, ap.TIEMPO_ESPERA).until(
        lambda d: panel.find_elements(By.CSS_SELECTOR, ".dteRow, .dteNoData, .dteResultsCount"))
    time.sleep(2)
    vinculados = []
    for enlace in panel.find_elements(By.CSS_SELECTOR, "a[href*='/scco/Contratistas/']"):
        m = re.search(r"/Contratistas/(\d+)", enlace.get_attribute("href") or "")
        fila = enlace.find_element(By.XPATH, "./ancestor::div[contains(@class,'dteRow')][1]")
        celdas = [ap.texto_de(c) for c in fila.find_elements(By.CSS_SELECTOR, ".dteCell")]
        if m:
            vinculados.append((m.group(1), next((c for c in celdas if c), "")))
    log.info("  Proveedor ID EK10 %s: %d contratista(s) vinculado(s) %s", id_ek10, len(vinculados), vinculados)
    return vinculados


def click_agregar(driver, principal):
    for handle in driver.window_handles:
        if handle != principal:
            driver.switch_to.window(handle)
            driver.close()
    driver.switch_to.window(principal)
    ek.abrir_pestana(driver, URL_CONTRATISTAS)
    ek.js_click(driver, ek.visible(driver, "//button[@title='Agregar (Alt+A)']", 90))
    WebDriverWait(driver, ap.TIEMPO_ESPERA).until(lambda d: "nuevo" in d.current_url.lower())
    WebDriverWait(driver, ap.TIEMPO_ESPERA).until(lambda d: d.find_elements(By.ID, "formControl_Clave"))
    time.sleep(2)
    log.info("Formulario contratista abierto: %s", driver.current_url)


XP_MODAL = "//div[contains(@class,'modal') and contains(@class,'in')]"


def seleccionar_proveedor(driver, id_ek10):
    """Lupa -> busca el ID EK10 -> click en la fila cuyo enlace es #/scp/Proveedores/<id> -> Aceptar."""
    lupa = driver.find_element(By.XPATH, "//label[@for='formControl_Proveedor']/ancestor::div[contains(@class,"
                                         "'form-group')][1]//button[i[contains(@class,'fa-search')]]")
    ek.js_click(driver, lupa)
    buscar = ek.visible(driver, XP_MODAL + "//input[contains(@id,'__search')]")
    buscar.click()
    buscar.send_keys(id_ek10)
    sufijo = f"/Proveedores/{id_ek10}"
    xp_fila = (XP_MODAL + "//div[contains(@class,'dteRow')][.//a[substring(@href, string-length(@href)"
               f" - string-length('{sufijo}') + 1) = '{sufijo}']]")
    try:
        fila = ek.visible(driver, xp_fila, 20)
    except TimeoutException:
        raise RuntimeError(f"El proveedor con ID EK10 {id_ek10} no aparece en la busqueda")
    # Click en la celda del nombre (la primera celda es el enlace "Ver", que abre otra pestana)
    ActionChains(driver).move_to_element(fila.find_elements(By.CSS_SELECTOR, ".dteCell")[1]).click().perform()
    WebDriverWait(driver, 10).until(lambda d: "dteSelected" in (fila.get_attribute("class") or ""))
    ek.js_click(driver, ek.visible(driver, XP_MODAL + "//button[@title='Aceptar']"))
    time.sleep(2)
    # Normalmente el modal se cierra solo; si no, click fuera de el
    fondos = [f for f in driver.find_elements(By.CSS_SELECTOR, ".modal-scrollable") if f.is_displayed()]
    if driver.find_elements(By.XPATH, XP_MODAL) and fondos:
        ActionChains(driver).move_to_element_with_offset(
            fondos[-1], -fondos[-1].size["width"] // 2 + 20, 0).click().perform()
        time.sleep(1)
    texto = ap.texto_de(driver.find_element(By.ID, "select2-single-prepend-text-container"))
    if not texto:
        raise RuntimeError("El campo Proveedor quedo vacio tras Aceptar")
    log.info("  Proveedor = %s", texto)
    return texto


class ClaveDuplicada(RuntimeError):
    """El sistema marca la Clave con 'El campo CLAVE debe ser único'."""


def validar_clave(driver, clave):
    """Tras escribir la clave, EK valida en linea que sea unica (form-group has-error + popover)."""
    time.sleep(2)
    grupo = driver.find_element(By.XPATH, "//label[@for='formControl_Clave']/ancestor::div[contains(@class,"
                                          "'form-group')][1]")
    if "has-error" not in (grupo.get_attribute("class") or ""):
        return
    icono = grupo.find_element(By.CSS_SELECTOR, "i.fa-exclamation")
    mensaje = ""
    for _ in range(5):  # el popover a veces tarda en aparecer
        ActionChains(driver).move_to_element(icono).click().perform()
        time.sleep(1)
        mensaje = " ".join(ap.texto_de(e) for e in driver.find_elements(By.CSS_SELECTOR, ".popover")
                           if e.is_displayed())
        if mensaje:
            break
    # Con la clave capturada, la unica otra validacion de EK es "debe ser unico"
    if "unico" in ek.sin_acentos(mensaje).lower() or not mensaje:
        raise ClaveDuplicada(f"Ya existe un contratista con la clave {clave}")
    raise RuntimeError(f"La clave {clave} no es valida: {mensaje}")


def llenar_formulario(driver, clave, nombre, id_ek10):
    ap.escribir(driver, "formControl_Clave", clave)
    validar_clave(driver, clave)
    ap.escribir(driver, "formControl_Nombre", nombre)
    ap.marcar(driver, "formControl_Contratistas_VinculoProveedor", True)
    ap.marcar(driver, "formControl_Contratistas_Estatus", True)
    ap.escribir(driver, "formControl_NSS", REGISTRO_IMSS)
    seleccionar_proveedor(driver, id_ek10)


XP_EXITO = "//div[contains(@class,'toast-success')]"


def guardar_contratista(driver, clave):
    try:
        boton = ek.visible(driver, "//button[@title='Guardar (Alt+G)']", 10)
    except TimeoutException:
        raise RuntimeError("No aparecio el boton 'Guardar (Alt+G)'")
    ek.js_click(driver, boton)

    def _resultado(d):
        error = next((e for e in d.find_elements(By.XPATH, ap.XP_MENSAJE_ERROR) if e.is_displayed()), None)
        if error is not None:
            return "ERROR: " + ap.texto_de(error)
        exito = next((e for e in d.find_elements(By.XPATH, XP_EXITO) if e.is_displayed()), None)
        return "OK: " + ap.texto_de(exito) if exito is not None else False
    try:
        resultado = WebDriverWait(driver, 60).until(_resultado)
    except TimeoutException:
        raise RuntimeError("No aparecio mensaje de confirmacion del guardado")
    if resultado.startswith("ERROR"):
        raise RuntimeError("El sistema rechazo el guardado: " + resultado[7:])
    log.info("[%s] Respuesta del sistema: %s", clave, resultado[4:])
    try:
        id_contratista = WebDriverWait(driver, 15).until(
            lambda d: (re.search(r"/Contratistas/(\d+)", d.current_url, re.I) or [None, None])[1])
    except TimeoutException:
        raise RuntimeError("Contratista guardado, pero no se obtuvo el ID de la URL " + driver.current_url)
    log.info("[%s] Contratista registrado con ID EK10 %s.", clave, id_contratista)
    return id_contratista


def procesar(driver, principal, ruta, guardar):
    nombre_archivo = os.path.basename(ruta)
    etapa = "lectura"
    try:
        p = leer_archivo(ruta)
        c = p["campos"]
        clave = c.get("proveedor", "").strip()
        id_ek10 = c.get("id ek10", "").strip()
        nombre = nombre_contratista(p)
        log.info("===== CONTRATISTA %s | clave %s | ID EK10 %s | %s | %s",
                 nombre_archivo, clave, id_ek10, p["tipo_persona"], nombre)
        if c.get("id contratista ek10"):
            return clave, f"YA ES CONTRATISTA (ID {c['id contratista ek10']})"
        if not id_ek10:
            return clave or nombre_archivo, "SIN ID EK10 (primero dar de alta el proveedor)"
        if not clave.isdigit():
            return clave or nombre_archivo, f"CLAVE INVALIDA: renglon Proveedor = '{clave}'"
        if not nombre:
            return clave, "SIN NOMBRE"
        # Evita duplicados: si el proveedor ya tiene un contratista vinculado, no se crea otro
        etapa = "revision"
        vinculados = contratistas_del_proveedor(driver, principal, id_ek10)
        if vinculados:
            id_contratista, nombre_existente = vinculados[0]
            if guardar:
                ap.registrar_id_csv(ruta, id_contratista, CAMPO_ID_CONTRATISTA)
            log.warning("[%s] El proveedor ID EK10 %s ya tiene contratista (ID %s, %s); no se crea otro.",
                        clave, id_ek10, id_contratista, nombre_existente)
            return clave, f"YA TIENE CONTRATISTA (ID {id_contratista}, {nombre_existente})"
        etapa = "formulario"
        click_agregar(driver, principal)
        etapa = "llenado"
        llenar_formulario(driver, clave, nombre, id_ek10)
        time.sleep(1)
        ek.guardar(driver, f"contratista_{clave}_lleno")
        if not guardar:
            return clave, "PRUEBA OK (no se guardo)"
        etapa = "guardado"
        id_contratista = guardar_contratista(driver, clave)
        ek.guardar(driver, f"contratista_{clave}_guardado")
        ap.registrar_id_csv(ruta, id_contratista, CAMPO_ID_CONTRATISTA)
        return clave, f"OK (ID Contratista {id_contratista})"
    except ClaveDuplicada as e:
        log.warning("[%s] %s; no se da de alta.", nombre_archivo, e)
        return clave, "CLAVE DE CONTRATISTA YA EXISTE"
    except (TimeoutException, WebDriverException, RuntimeError, ValueError) as e:
        mensaje = (getattr(e, "msg", None) or str(e) or type(e).__name__).strip().splitlines()[0]
        log.error("[%s] Error en etapa '%s': %s", nombre_archivo, etapa, mensaje)
        ek.guardar(driver, f"contratista_{os.path.splitext(nombre_archivo)[0]}_error_{etapa}")
        return nombre_archivo, f"ERROR ({etapa}): {mensaje}"


def ejecutar(rutas, guardar=False):
    if not (ek.Config.USUARIO and ek.Config.PASSWORD):
        raise RuntimeError("Sin credenciales de ekloud")
    log.info("CONTRATISTAS | Modo: %s | %d archivo(s)", "GUARDAR" if guardar else "PRUEBA (no guarda)", len(rutas))
    driver = ek.crear_driver()
    resumen = []
    try:
        ek.iniciar_sesion(driver)
        principal = driver.current_window_handle
        for ruta in rutas:
            resumen.append(procesar(driver, principal, ruta, guardar))
    finally:
        log.info("===== RESUMEN CONTRATISTAS =====")
        for clave, estatus in resumen:
            log.info("  %-15s %s", clave, estatus)
        try:
            driver.get(ek.Config.URL_SIGNOUT)
        except WebDriverException:
            pass
        driver.quit()
    return resumen


def main():
    ap.configurar_log()
    argumentos = sys.argv[1:]
    guardar = "--guardar" in argumentos
    rutas = ap.expandir_rutas([a for a in argumentos if a != "--guardar"])
    if not rutas:
        sys.exit(__doc__)
    ejecutar(rutas, guardar)


if __name__ == "__main__":
    main()
