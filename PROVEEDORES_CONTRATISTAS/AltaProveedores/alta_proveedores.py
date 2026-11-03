# -*- coding: utf-8 -*-
"""
alta_proveedores.py
-------------------
Da de alta proveedores en suite.ekloud a partir de CSV (formato vertical CAMPO,VALOR;
un proveedor por archivo, ver proveedor_csv.py).

Por cada CSV:
  1. Abre una pestana con el dashboard de proveedores y da "Agregar (Alt+A)".
  1b. Busca el RFC sin guiones en Administracion Proveedores (Buscar): si ya existe no lo da
      de alta; obtiene su ID EK10 (icono Abrir) y, con --guardar, lo anota en el CSV.
  2. Selecciona Tipo de Persona (Persona Fisica Si -> FISICA, No -> MORAL) y da la flecha.
  3. Llena el formulario:
       Clave = EK-PROV-... generada del nombre (proveedor_csv.generar_clave), Nombre, Apellidos (solo FISICA), Nombre Corto,
       RFC sin guiones ni espacios, Calle tal como viene y su numero final en Ext,
       C.P./Colonia buscando por Codigo Postal y eligiendo la colonia (si no viene, vacio),
       Tipo de Proveedor, Tipo de Tercero, Tipo de Operacion, Activo, Obliga CFDI, Factoraje.
       Filial (Tipo Movimiento Base) y Nac. o Ext. (Nacionalidad) se dejan siempre vacios.
  4. Sin --guardar solo guarda captura + HTML del formulario lleno (prueba).
     Con --guardar da click en Guardar y, al responder "Proveedor Registrado", agrega al
     CSV el renglon "ID EK10,<id>" (tomado de la URL). Un CSV que ya tiene ID EK10 se omite.
  5. Al terminar pregunta si los proveedores con ID EK10 se dan de alta tambien como
     contratistas (alta_contratistas.py), con el mismo modo prueba/guardar.

Uso:
  python alta_proveedores.py archivo.csv [archivo2.csv ...]            -> prueba, no guarda
  python alta_proveedores.py --guardar archivo.csv [archivo2.csv ...]  -> da de alta
  --contratistas / --sin-contratistas  -> responde la pregunta del paso 5 sin preguntar
  python alta_proveedores.py --verificar archivo.csv [...] -> no da de alta: busca el RFC en EK10
                                                              y anota el ID EK10 en el CSV
  (tambien acepta una carpeta: procesa todos sus .csv)
"""

import difflib
import glob
import logging
import os
import re
import sys
import time
from datetime import datetime

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

import explorar_formulario as ek
from proveedor_csv import decodificar, generar_clave, leer_archivo, es_si, normalizar

# Compilado con PyInstaller __file__ apunta a la carpeta temporal: usar la del .exe
CARPETA_BASE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
CARPETA_RESULTADOS = os.path.join(CARPETA_BASE, "Resultados")
TIEMPO_ESPERA = 30
TIEMPO_BUSQUEDA_CP = 20

log = logging.getLogger("alta_proveedores")


def configurar_log():
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    log.setLevel(logging.INFO)
    for h in (logging.FileHandler(os.path.join(CARPETA_RESULTADOS, "log_alta_proveedores.txt"), encoding="utf-8"),
              logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)
    # Los helpers de explorar_formulario escriben en este mismo log
    ek.log.handlers = log.handlers
    ek.log.setLevel(logging.INFO)
    ek.Config.CARPETA_SALIDA = CARPETA_RESULTADOS


# =============================================================================
# TRANSFORMACIONES DEL CSV
# =============================================================================
def limpiar_rfc(rfc):
    return re.sub(r"[\s-]", "", rfc or "").upper()


def numero_exterior(calle):
    """'PIPILA 310' -> '310'; 'TEPIC - PUERTO VALLARTA KM 146.2' -> '146.2'; sin numero final -> ''."""
    m = re.search(r"(?:^|\s)(\d[\w.\-/]*)\s*$", (calle or "").strip())
    return m.group(1) if m else ""


def datos_formulario(p):
    """Del proveedor leido del CSV arma los valores a capturar."""
    c = p["campos"]
    return {
        "clave": p["clave"],
        "nombre": c.get("nombre", ""),
        "paterno": c.get("a paterno", ""),
        "materno": c.get("a materno", ""),
        "nombre_corto": c.get("nombre corto", ""),
        "rfc": limpiar_rfc(c.get("rfc")),
        "calle": c.get("calle", ""),
        "exterior": numero_exterior(c.get("calle")),
        "cp": c.get("codigo postal", ""),
        "colonia": c.get("colonia", ""),
        "municipio": c.get("deleg o mpio", ""),
        "tipo_proveedor": c.get("tipo de proveedor", ""),
        "tercero": c.get("tipo de tercero", ""),
        "operacion": c.get("tipo de operacion", ""),
        "activo": normalizar(c.get("estatus general", "")) in ("vigente", "activo"),
        "obliga_cfdi": es_si(c.get("obliga cfdi", "")),
        "factoraje": es_si(c.get("factoraje", "")),
    }


# =============================================================================
# CONTROLES DEL FORMULARIO
# =============================================================================
def escribir(driver, id_campo, valor):
    campo = driver.find_element(By.ID, id_campo)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
    campo.click()
    campo.send_keys(Keys.CONTROL, "a")
    campo.send_keys(Keys.DELETE)
    if valor:
        campo.send_keys(valor)
    campo.send_keys(Keys.TAB)
    leido = campo.get_attribute("value") or ""
    if valor and leido != valor:
        log.warning("  %s: se escribio '%s' pero quedo '%s'", id_campo, valor, leido)


def marcar(driver, id_campo, activo):
    """Deja el checkbox (md-checkbox) en el estado indicado dando click en su label."""
    check = driver.find_element(By.ID, id_campo)
    if check.is_selected() != activo:
        ek.js_click(driver, driver.find_element(By.XPATH, f"//label[@for='{id_campo}']"))
        time.sleep(0.3)
    if check.is_selected() != activo:
        raise RuntimeError(f"No se pudo dejar {id_campo} en {activo}")


def abrir_select2(driver, id_campo):
    caja = driver.find_element(By.XPATH, f"//span[@id='select2-{id_campo}-container']"
                                         "/ancestor::span[contains(@class,'select2-selection')][1]")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", caja)
    ActionChains(driver).move_to_element(caja).click().perform()


def texto_de(elemento):
    """textContent: .text de Selenium sale vacio para opciones fuera del area visible del scroll."""
    return re.sub(r"\s+", " ", elemento.get_attribute("textContent") or "").strip()


def opciones_abiertas(driver):
    return [o for o in driver.find_elements(By.CSS_SELECTOR, ".select2-container--open li.select2-results__option")
            if "loading-results" not in (o.get_attribute("class") or "")]


def seleccionar_select2(driver, id_campo, texto):
    """Elige en un select2 local la opcion cuyo texto (sin acentos) es igual a `texto`."""
    if not texto:
        return
    abrir_select2(driver, id_campo)
    opciones = WebDriverWait(driver, TIEMPO_ESPERA).until(lambda d: opciones_abiertas(d))
    buscado = ek.sin_acentos(texto)

    def coincide(o):
        # Las opciones traen la clave del catalogo al inicio: "TPROV-0007 SERVICIOS"
        t = ek.sin_acentos(texto_de(o))
        return t == buscado or t.split(" ", 1)[-1] == buscado
    opcion = next((o for o in opciones if coincide(o)), None)
    if opcion is None:
        log.warning("  %s: opciones visibles %s", id_campo, [texto_de(o) for o in opciones])
        ek.guardar(driver, f"ddl_{id_campo}")
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        raise RuntimeError(f"{id_campo}: no existe la opcion '{texto}'")
    driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", opcion)
    opcion.click()
    log.info("  %s = %s", id_campo, texto)


# Digitos que el OCR confunde entre si (para probar CP alternativos)
DIGITOS_PARECIDOS = {"3": "865", "8": "3609", "6": "850", "5": "63", "0": "869", "9": "80",
                     "1": "7", "7": "1"}


def cp_alternativos(cp):
    """CP con un digito cambiado por uno parecido (33177 -> 83177, 63177, 53177, 38177...)."""
    if not re.fullmatch(r"\d{5}", cp or ""):
        return []
    return [cp[:i] + d + cp[i + 1:] for i, c in enumerate(cp) for d in DIGITOS_PARECIDOS.get(c, "")]


def parecido(buscado, texto, minimo=0.75):
    """True si `buscado` aparece en `texto` aunque tenga errores de OCR ("IRMOSLLO" ~ "Hermosillo")."""
    b, t = normalizar(buscado), normalizar(texto)
    if not b:
        return True
    if b in t:
        return True
    n = len(b)
    return any(difflib.SequenceMatcher(None, b, t[i:i + n]).ratio() >= minimo for i in range(max(1, len(t) - n + 1)))


def opciones_cp(driver, cp):
    """Busca el CP en el select2 remoto de C.P./Colonia; [(opcion, texto)] solo de ese CP exacto."""
    abrir_select2(driver, "formControl_Asentamiento")
    busqueda = WebDriverWait(driver, TIEMPO_ESPERA).until(
        lambda d: next((b for b in d.find_elements(By.CSS_SELECTOR, ".select2-container--open .select2-search__field")
                        if b.is_displayed()), False))
    busqueda.send_keys(Keys.CONTROL, "a")
    busqueda.send_keys(cp)
    # Espera resultados o el mensaje final ("No se encontraron resultados"), no el de "Buscando..."
    limite, opciones = time.time() + TIEMPO_BUSQUEDA_CP, []
    while time.time() < limite:
        time.sleep(1)
        todos = opciones_abiertas(driver)
        opciones = [o for o in todos if "select2-results__message" not in (o.get_attribute("class") or "")]
        mensajes = [texto_de(o).lower() for o in todos if o not in opciones]
        if opciones or (mensajes and not any(re.search(r"busca|search|carg|load", m) for m in mensajes)):
            break
    # La busqueda remota tambien trae otros CP parecidos (09070 -> 90700...): solo el CP exacto
    return [(o, t) for o, t in ((o, texto_de(o)) for o in opciones) if t.startswith(cp + " ")]


def seleccionar_colonia(driver, cp, colonia, municipio=""):
    """
    C.P./Colonia/Municipio es un select2 remoto: se busca por CP y se elige la opcion que
    contiene la colonia. Si la colonia no viene, queda vacio.
    El CP viene del OCR y puede traer un digito mal leido: si el CP no existe en el catalogo o
    sus colonias no son del municipio del CSV, se prueban CP con un digito parecido y se usa el
    que tenga la colonia en ese municipio.
    Retorna (texto elegido o "", CP usado).
    """
    if not colonia:
        log.info("  Sin colonia en el CSV; C.P./Colonia queda vacio")
        return "", cp
    for n, cp_prueba in enumerate([cp] + cp_alternativos(cp)):
        resultados = opciones_cp(driver, cp_prueba)
        textos = [t for _, t in resultados]
        mismo_municipio = not municipio or any(parecido(municipio, t) for t in textos)
        # Si varias colonias contienen el nombre ("Puerta Real Residencial" / "... III"), la mas corta
        coinciden = [(o, t) for o, t in resultados if parecido(colonia, t, 0.85) and mismo_municipio]
        opcion = min(coinciden, key=lambda ot: len(ot[1]))[0] if coinciden else None
        if n == 0:
            log.info("  Resultados para CP %s: %s", cp, textos[:15])
        if opcion is not None:
            texto = texto_de(opcion)
            driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", opcion)
            opcion.click()
            if cp_prueba != cp:
                log.warning("  CP corregido: el CSV dice %s pero la colonia '%s' (%s) esta en el CP %s",
                            cp, colonia, municipio, cp_prueba)
            log.info("  C.P./Colonia = %s", texto)
            return texto, cp_prueba
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        if n == 0:
            if textos and mismo_municipio:
                # El CP existe y es del municipio: la colonia simplemente no esta en el catalogo
                log.warning("  Colonia '%s' no esta en el catalogo del CP %s; C.P./Colonia queda vacio", colonia, cp)
                return "", cp
            log.warning("  El CP %s %s; se prueban CP con un digito parecido", cp,
                        "no existe en el catalogo" if not textos else f"no es del municipio '{municipio}'")
    log.warning("  No se encontro la colonia '%s' en ningun CP parecido a %s; C.P./Colonia queda vacio", colonia, cp)
    return "", cp


def llenar_formulario(driver, tipo, d):
    escribir(driver, "formControl_Clave", d["clave"])
    escribir(driver, "formControl_Nombre", d["nombre"])
    if tipo == "FISICA":
        escribir(driver, "formControl_ApellidoPaterno", d["paterno"])
        escribir(driver, "formControl_ApellidoMaterno", d["materno"])
    escribir(driver, "formControl_NombreCorto", d["nombre_corto"][:25])
    escribir(driver, "formControl_RFC", d["rfc"])
    seleccionar_select2(driver, "formControl_TipoProveedor", d["tipo_proveedor"])
    marcar(driver, "formControl_Proveedores_Estatus", d["activo"])
    marcar(driver, "formControl_Proveedores_obliga_cfd", d["obliga_cfdi"])
    marcar(driver, "formControl_Proveedores_factoraje", d["factoraje"])
    escribir(driver, "formControl_Domicilio", d["calle"])
    escribir(driver, "formControl_NumExterior", d["exterior"])
    _, d["cp_usado"] = seleccionar_colonia(driver, d["cp"], d["colonia"], d["municipio"])
    seleccionar_select2(driver, "formControl_Tercero", d["tercero"])
    seleccionar_select2(driver, "formControl_Operacion", d["operacion"])


CAMPO_ID_EK10 = "ID EK10"
XP_REGISTRADO = "//*[contains(@class,'toast')][contains(normalize-space(.),'Proveedor Registrado')]"
XP_MENSAJE_ERROR = ("//div[contains(@class,'toast-error')] | "
                    "//div[contains(@class,'sweet-alert') and contains(@class,'visible')]")


def guardar_proveedor(driver, clave):
    try:
        boton = ek.visible(driver, "//button[@title='Guardar (Alt+G)']", 10)
    except TimeoutException:
        raise RuntimeError("No aparecio el boton 'Guardar (Alt+G)'")
    ek.js_click(driver, boton)

    # Guardado correcto: el sistema muestra "Proveedor Registrado" y la URL pasa a
    # #/scp/Proveedores/<ID EK10>. El aviso dura pocos segundos y con el servidor lento puede
    # no verse: basta con que la URL ya tenga el ID. Si lo rechaza muestra un toast con el motivo.
    def _resultado(d):
        error = next((e for e in d.find_elements(By.XPATH, XP_MENSAJE_ERROR) if e.is_displayed()), None)
        if error is not None:
            return "ERROR: " + texto_de(error)
        registrado = any(e.is_displayed() for e in d.find_elements(By.XPATH, XP_REGISTRADO))
        return "OK" if registrado or re.search(r"/Proveedores/\d+", d.current_url, re.I) else False
    try:
        resultado = WebDriverWait(driver, 60).until(_resultado)
    except TimeoutException:
        raise RuntimeError("No aparecio el mensaje 'Proveedor Registrado'")
    if resultado != "OK":
        raise RuntimeError("El sistema rechazo el guardado: " + resultado[7:])
    try:
        id_ek10 = WebDriverWait(driver, 15).until(
            lambda d: (re.search(r"/Proveedores/(\d+)", d.current_url, re.I) or [None, None])[1])
    except TimeoutException:
        raise RuntimeError("Proveedor Registrado, pero no se obtuvo el ID de la URL " + driver.current_url)
    log.info("[%s] Proveedor Registrado con ID EK10 %s.", clave, id_ek10)
    return id_ek10


def corregir_campo_csv(ruta, campo, valor):
    """Cambia el VALOR del renglon `campo` del CSV en su mismo lugar (p.ej. el CP corregido)."""
    with open(ruta, "rb") as f:
        crudo = f.read()
    texto = decodificar(crudo)
    salto = "\r\n" if "\r\n" in texto else "\n"
    lineas = [f"{l.split(',', 1)[0]},{valor}" if normalizar(l.split(",", 1)[0]) == normalizar(campo) else l
              for l in texto.splitlines()]
    with open(ruta, "w", encoding="utf-8-sig" if crudo.startswith(b"\xef\xbb\xbf") else "utf-8", newline="") as f:
        f.write(salto.join(lineas) + salto)
    log.info("  CSV actualizado: %s = %s", campo, valor)


def registrar_id_csv(ruta, id_ek10, campo=CAMPO_ID_EK10):
    """Agrega (o actualiza) el renglon '<campo>,<id>' en el CSV del proveedor, conservando su formato."""
    with open(ruta, "rb") as f:
        crudo = f.read()
    bom = crudo.startswith(b"\xef\xbb\xbf")
    texto = decodificar(crudo)
    salto = "\r\n" if "\r\n" in texto else "\n"
    lineas = [l for l in texto.splitlines() if normalizar(l.split(",", 1)[0]) != normalizar(campo)]
    lineas.append(f"{campo},{id_ek10}")
    contenido = salto.join(lineas) + salto
    for intento in range(1, 6):
        try:
            with open(ruta, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
                f.write(contenido)
            log.info("  CSV actualizado: %s = %s", campo, id_ek10)
            return True
        except PermissionError:
            log.warning("  El CSV esta abierto en otro programa; cierrelo (intento %d/5).", intento)
            time.sleep(10)
    log.error("  No se pudo escribir el ID EK10 %s en %s", id_ek10, ruta)
    return False


# =============================================================================
# DASHBOARD: BUSQUEDA DE CLAVES
# =============================================================================
XP_FILAS = "//div[contains(@class,'dx-datagrid-rowsview')]//tr[contains(@class,'dx-data-row')]"
COLUMNA_CLAVE, COLUMNA_NOMBRE, COLUMNA_RFC = 2, 3, 4  # aria-colindex en Administracion Proveedores


def abrir_dashboard(driver, principal):
    """Cierra pestanas extra y abre una con el dashboard de proveedores en Estatus = Todos."""
    for handle in driver.window_handles:
        if handle != principal:
            driver.switch_to.window(handle)
            driver.close()
    driver.switch_to.window(principal)
    ek.abrir_pestana(driver, ek.Config.URL_PROVEEDORES)
    ek.js_click(driver, ek.visible(driver, "//*[normalize-space()='Todos']", 60))
    WebDriverWait(driver, 90).until(lambda d: next(
        (e for e in d.find_elements(By.CSS_SELECTOR, ".dx-datagrid-search-panel input") if e.is_displayed()), False))
    time.sleep(2)


def buscar_en_dashboard(driver, texto):
    """Escribe `texto` en Buscar de Administracion Proveedores (debe estar abierto) y devuelve las
    filas como [{columna: texto, 'indice': aria-rowindex}]."""
    campo = driver.find_element(By.CSS_SELECTOR, ".dx-datagrid-search-panel input")
    campo.send_keys(Keys.CONTROL, "a")
    campo.send_keys(texto)
    time.sleep(1)
    # Espera a que el grid termine de filtrar (sin indicador de carga)
    WebDriverWait(driver, TIEMPO_ESPERA).until(lambda d: not any(
        e.is_displayed() for e in d.find_elements(By.CSS_SELECTOR, ".dx-datagrid .dx-loadpanel-content")))
    time.sleep(2)
    filas = []
    for tr in driver.find_elements(By.XPATH, XP_FILAS):
        celdas = {int(td.get_attribute("aria-colindex") or 0): texto_de(td)
                  for td in tr.find_elements(By.XPATH, "./td[@aria-colindex]")}
        if celdas.get(COLUMNA_CLAVE) or celdas.get(COLUMNA_RFC):
            celdas["indice"] = tr.get_attribute("aria-rowindex")
            filas.append(celdas)
    return filas


def clave_existe(driver, clave):
    """Dice si alguna fila del dashboard tiene exactamente esa clave."""
    existe = any(f.get(COLUMNA_CLAVE, "").upper() == clave.upper() for f in buscar_en_dashboard(driver, clave))
    log.info("  Clave %s %s en el dashboard", clave, "YA EXISTE" if existe else "no existe")
    return existe


def proveedor_por_rfc(driver, rfc):
    """Busca el RFC sin guiones en el dashboard; devuelve la fila del proveedor existente o None."""
    rfc = limpiar_rfc(rfc)
    if not rfc:
        return None
    fila = next((f for f in buscar_en_dashboard(driver, rfc) if limpiar_rfc(f.get(COLUMNA_RFC)) == rfc), None)
    if fila:
        log.warning("  El RFC %s YA EXISTE en EK10: clave %s, %s", rfc, fila.get(COLUMNA_CLAVE), fila.get(COLUMNA_NOMBRE))
    else:
        log.info("  RFC %s no existe en el dashboard", rfc)
    return fila


def id_de_fila(driver, fila):
    """Abre el proveedor de la fila (icono Abrir) y devuelve su ID EK10 de la URL, o '' si no se pudo."""
    # El icono vive en la tabla de columnas fijas, en la fila con el mismo aria-rowindex
    iconos = driver.find_elements(By.XPATH, f"{XP_FILAS}[@aria-rowindex='{fila['indice']}']//span[@title='Abrir']")
    icono = next((i for i in iconos if i.is_displayed()), iconos[0] if iconos else None)
    if icono is None:
        return ""
    previas = set(driver.window_handles)
    ek.js_click(driver, icono)
    try:
        WebDriverWait(driver, TIEMPO_ESPERA).until(
            lambda d: set(d.window_handles) - previas or re.search(r"/Proveedores/\d+", d.current_url, re.I))
        nuevas = set(driver.window_handles) - previas
        if nuevas:
            driver.switch_to.window(nuevas.pop())
        return WebDriverWait(driver, TIEMPO_ESPERA).until(
            lambda d: (re.search(r"/Proveedores/(\d+)", d.current_url, re.I) or [None, None])[1])
    except TimeoutException:
        return ""


def resolver_clave(driver, p):
    """Clave libre para el proveedor o None si esta duplicada (FISICA reintenta con paterno completo)."""
    clave = p["clave"]
    if not clave_existe(driver, clave):
        return clave
    if p["tipo_persona"] == "FISICA":
        alterna = generar_clave("FISICA", p["campos"], paterno_completo=True)
        if alterna != clave and not clave_existe(driver, alterna):
            log.info("  Se usa la clave alterna %s", alterna)
            return alterna
    return None


def click_agregar(driver):
    ek.js_click(driver, ek.visible(driver, "//button[@title='Agregar (Alt+A)']", 60))
    WebDriverWait(driver, TIEMPO_ESPERA).until(lambda d: "nuevo" in d.current_url)
    WebDriverWait(driver, TIEMPO_ESPERA).until(
        lambda d: d.find_elements(By.ID, "select2-formControl_TipoPersona-container"))
    time.sleep(2)
    log.info("Formulario abierto: %s", driver.current_url)


# =============================================================================
# PROCESO PRINCIPAL
# =============================================================================
def procesar(driver, principal, ruta, guardar):
    nombre = os.path.basename(ruta)
    etapa = "lectura"
    try:
        p = leer_archivo(ruta)
        d = datos_formulario(p)
        clave = d["clave"] or nombre
        log.info("===== %s | %s | %s | %s", nombre, clave, p["tipo_persona"], d["nombre"])
        if p["campos"].get("id ek10"):
            log.info("[%s] El CSV ya tiene ID EK10 %s; se omite.", clave, p["campos"]["id ek10"])
            return clave, f"YA REGISTRADO (ID EK10 {p['campos']['id ek10']})"
        if p["faltantes"]:
            log.warning("[%s] Faltan campos obligatorios: %s", clave, p["faltantes"])
            return clave, "FALTAN DATOS: " + ", ".join(p["faltantes"])
        etapa = "rfc"
        abrir_dashboard(driver, principal)
        existente = proveedor_por_rfc(driver, d["rfc"])
        if existente:
            id_existente = id_de_fila(driver, existente)
            detalle = f"clave {existente.get(COLUMNA_CLAVE)}" + (f", ID EK10 {id_existente}" if id_existente else "")
            if guardar and id_existente:
                # Ya existe: se anota su ID para que el paso de contratista pueda usarlo
                registrar_id_csv(ruta, id_existente)
            return clave, f"YA EXISTE EN EK10 POR RFC ({detalle})"
        etapa = "clave"
        abrir_dashboard(driver, principal)
        clave = resolver_clave(driver, p)
        if clave is None:
            log.warning("[%s] La clave ya existe en el sistema; no se da de alta.", d["clave"])
            return d["clave"], "CLAVE DUPLICADA"
        d["clave"] = clave
        etapa = "formulario"
        click_agregar(driver)
        ek.seleccionar_tipo_persona(driver, p["tipo_persona"])
        ek.continuar_tipo_persona(driver)
        etapa = "llenado"
        llenar_formulario(driver, p["tipo_persona"], d)
        nota_cp = f"; CP corregido {d['cp']} -> {d['cp_usado']}" if d.get("cp_usado", d["cp"]) != d["cp"] else ""
        time.sleep(1)
        ek.guardar(driver, f"{clave}_lleno")
        if not guardar:
            return clave, f"PRUEBA OK (no se guardo){nota_cp}"
        if nota_cp:
            corregir_campo_csv(ruta, "Código Postal", d["cp_usado"])
        etapa = "guardado"
        try:
            id_ek10 = guardar_proveedor(driver, clave)
        except RuntimeError as e:
            if "rechazo" in str(e):
                raise
            # Sin confirmacion visible: puede haberse guardado igual. Se verifica por RFC.
            log.warning("[%s] %s; se verifica por RFC si quedo registrado.", clave, e)
            ek.guardar(driver, f"{clave}_sin_confirmacion")
            etapa = "verificacion"
            return verificar(driver, principal, ruta)
        ek.guardar(driver, f"{clave}_guardado")
        registrar_id_csv(ruta, id_ek10)
        etapa = "verificacion"
        abrir_dashboard(driver, principal)
        if not clave_existe(driver, clave):
            return clave, f"REGISTRADO ID {id_ek10} (no aparece aun en el dashboard)"
        return clave, f"OK (ID EK10 {id_ek10}){nota_cp}"
    except (TimeoutException, WebDriverException, RuntimeError, ValueError) as e:
        mensaje = (getattr(e, "msg", None) or str(e) or type(e).__name__).strip().splitlines()[0]
        log.error("[%s] Error en etapa '%s': %s", nombre, etapa, mensaje)
        ek.guardar(driver, f"{os.path.splitext(nombre)[0]}_error_{etapa}")
        return nombre, f"ERROR ({etapa}): {mensaje}"


def verificar(driver, principal, ruta):
    """
    Revisa si el proveedor del CSV ya esta en EK10 (busca su RFC sin guiones en Administracion
    Proveedores) y, si esta, anota su ID EK10 en el CSV. No crea ni modifica nada en EK10.
    """
    nombre = os.path.basename(ruta)
    try:
        p = leer_archivo(ruta)
        clave = p["clave"] or nombre
        rfc = limpiar_rfc(p["campos"].get("rfc"))
        log.info("===== VERIFICAR %s | RFC %s | %s", nombre, rfc, p["campos"].get("nombre", ""))
        if not rfc:
            return clave, "SIN RFC: no se puede verificar"
        abrir_dashboard(driver, principal)
        fila = proveedor_por_rfc(driver, rfc)
        if fila is None:
            return clave, f"NO ESTA EN EK10 (RFC {rfc})"
        clave = fila.get(COLUMNA_CLAVE) or clave
        id_ek10 = id_de_fila(driver, fila)
        if not id_ek10:
            return clave, f"ESTA EN EK10 (clave {clave}) pero no se pudo obtener su ID"
        registrar_id_csv(ruta, id_ek10)
        return clave, f"OK VERIFICADO (clave {clave}, ID EK10 {id_ek10})"
    except (TimeoutException, WebDriverException, RuntimeError, ValueError) as e:
        mensaje = (getattr(e, "msg", None) or str(e) or type(e).__name__).strip().splitlines()[0]
        log.error("[%s] Error al verificar: %s", nombre, mensaje)
        ek.guardar(driver, f"{os.path.splitext(nombre)[0]}_error_verificar")
        return nombre, f"ERROR (verificar): {mensaje}"


def expandir_rutas(argumentos):
    rutas = []
    for a in argumentos:
        rutas += sorted(glob.glob(os.path.join(a, "*.csv"))) if os.path.isdir(a) else [a]
    return rutas


def ejecutar(rutas, guardar=False, solo_verificar=False):
    """Procesa la lista de CSV; retorna [(clave, estatus)]. Usado tambien por el portal.
    solo_verificar: no da de alta, solo busca cada RFC en EK10 y anota el ID EK10."""
    if not (ek.Config.USUARIO and ek.Config.PASSWORD):
        raise RuntimeError("Sin credenciales de ekloud")
    log.info("Modo: %s | %d archivo(s)", "VERIFICAR EN EK10" if solo_verificar else
             "GUARDAR" if guardar else "PRUEBA (no guarda)", len(rutas))
    driver = ek.crear_driver()
    resumen = []
    try:
        ek.iniciar_sesion(driver)
        principal = driver.current_window_handle
        for ruta in rutas:
            resumen.append(verificar(driver, principal, ruta) if solo_verificar
                           else procesar(driver, principal, ruta, guardar))
    finally:
        log.info("===== RESUMEN =====")
        for clave, estatus in resumen:
            log.info("  %-15s %s", clave, estatus)
        try:
            driver.get(ek.Config.URL_SIGNOUT)
        except WebDriverException:
            pass
        driver.quit()
    return resumen


def preguntar_contratistas(rutas, respuesta=None):
    """
    Paso consecutivo: pregunta si los proveedores con ID EK10 se dan de alta tambien como
    contratistas. `respuesta` (True/False) evita la pregunta (--contratistas / --sin-contratistas).
    """
    con_id = []
    for ruta in rutas:
        try:
            if leer_archivo(ruta)["campos"].get("id ek10"):
                con_id.append(ruta)
        except (OSError, ValueError):
            continue
    if not con_id:
        log.info("Ningun CSV tiene ID EK10; no hay contratistas que dar de alta.")
        return False
    if respuesta is None:
        print()
        for ruta in con_id:
            print("   ", os.path.basename(ruta))
        try:
            texto = input(f"¿Dar de alta como CONTRATISTAS estos {len(con_id)} proveedor(es)? (S/N): ")
        except EOFError:
            texto = ""
        respuesta = ek.sin_acentos(texto).startswith("S")
    log.info("Alta como contratistas: %s", "SI" if respuesta else "NO")
    return con_id if respuesta else False


def main():
    configurar_log()
    banderas = {"--guardar", "--contratistas", "--sin-contratistas", "--verificar"}
    argumentos = sys.argv[1:]
    guardar = "--guardar" in argumentos
    rutas = expandir_rutas([a for a in argumentos if a not in banderas])
    if not rutas:
        sys.exit(__doc__)
    ejecutar(rutas, guardar, solo_verificar="--verificar" in argumentos)
    if "--verificar" in argumentos:
        return

    respuesta = True if "--contratistas" in argumentos else False if "--sin-contratistas" in argumentos else None
    contratistas = preguntar_contratistas(rutas, respuesta)
    if contratistas:
        import alta_contratistas  # importado aqui: alta_contratistas importa este modulo
        alta_contratistas.ejecutar(contratistas, guardar)


if __name__ == "__main__":
    main()
