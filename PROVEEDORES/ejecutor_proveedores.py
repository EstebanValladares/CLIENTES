import os
import time
import traceback
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from funciones_proveedores import (
    iniciar_sesion,
    seleccionar_tipo_persona,
    avanzar_siguiente_panel,
    escribir_clave,
    escribir_nombre,
    escribir_apellido_paterno,
    escribir_apellido_materno,
    escribir_rfc,
    escribir_nombre_corto,
    marcar_obliga_cfdi,
    marcar_factoraje,
    escribir_domicilio,
    escribir_num_exterior,
    seleccionar_asentamiento_cp,
    guardar_proveedor_general
)

# Cargar variables de entorno desde la raíz del proyecto o carpeta local
import sys
_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

try:
    from NUCLEO.config import obtener_credenciales_aryve
    USER, PASSWORD = obtener_credenciales_aryve()
except Exception:
    load_dotenv()
    USER = os.getenv("EK9_USER", "")
    PASSWORD = os.getenv("EK9_PASS", "")

TARGET_URL = "#/scp/Proveedores/id?nuevo"
RUTA_REGISTRO_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_proveedores.json")


def registrar_proveedor_json(clave, id_generado):
    """
    Guarda o actualiza únicamente la clave y el ID en registro_proveedores.json.
    """
    import json
    registros = []
    if os.path.exists(RUTA_REGISTRO_JSON):
        try:
            with open(RUTA_REGISTRO_JSON, "r", encoding="utf-8") as f:
                registros = json.load(f)
        except Exception:
            registros = []

    nuevo_item = {"id": str(id_generado), "clave": str(clave)}

    actualizado = False
    for i, r in enumerate(registros):
        if r.get("clave") == clave:
            registros[i] = nuevo_item
            actualizado = True
            break
    if not actualizado:
        registros.append(nuevo_item)

    try:
        with open(RUTA_REGISTRO_JSON, "w", encoding="utf-8") as f:
            json.dump(registros, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error al escribir en registro_proveedores.json: {e}")



def procesar_un_proveedor(driver, datos_proveedor, log_callback=None):
    """
    Llena un proveedor completo en Aryve usando el driver ya abierto.
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)

    log(f"Navegando a: {TARGET_URL}")
    driver.get(TARGET_URL)
    WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3.5)

    tipo_persona = datos_proveedor.get("TIPO PERSONA", "MORAL")
    log(f"Seleccionando tipo de persona: {tipo_persona}")
    seleccionar_tipo_persona(driver, tipo=tipo_persona)
    time.sleep(1)

    avanzar_siguiente_panel(driver)
    time.sleep(1.2)

    # 1. Clave
    clave_a_escribir = datos_proveedor.get("CLAVE", "")
    if clave_a_escribir:
        log(f"Escribiendo clave: {clave_a_escribir}")
        escribir_clave(driver, clave_a_escribir)
        time.sleep(0.4)

    # 2. Nombre y Apellidos
    nombre_a_escribir = datos_proveedor.get("NOMBRE", "")
    if nombre_a_escribir:
        log(f"Escribiendo nombre: {nombre_a_escribir}")
        escribir_nombre(driver, nombre_a_escribir)
        time.sleep(0.4)

    if "FISICA" in tipo_persona or "FÍSICA" in tipo_persona:
        paterno = datos_proveedor.get("PATERNO", "")
        if paterno:
            escribir_apellido_paterno(driver, paterno)
            time.sleep(0.4)
        materno = datos_proveedor.get("MATERNO", "")
        if materno:
            escribir_apellido_materno(driver, materno)
            time.sleep(0.4)

    # 3. RFC
    rfc_a_escribir = datos_proveedor.get("RFC", "")
    if rfc_a_escribir:
        log(f"Escribiendo RFC: {rfc_a_escribir}")
        escribir_rfc(driver, rfc_a_escribir)
        time.sleep(0.4)

    # 4. Nombre Corto
    corto_a_escribir = datos_proveedor.get("NOMBRE CORTO", "")
    if corto_a_escribir:
        log(f"Escribiendo nombre corto: {corto_a_escribir}")
        escribir_nombre_corto(driver, corto_a_escribir)
        time.sleep(0.4)

    # 5. Casillas CFDI y Factoraje (solo MORAL)
    es_persona_moral = not ("FISICA" in tipo_persona or "FÍSICA" in tipo_persona)
    if es_persona_moral:
        log("Marcando Obliga CFDI y Factoraje...")
        marcar_obliga_cfdi(driver)
        time.sleep(0.4)
        marcar_factoraje(driver)
        time.sleep(0.4)
    else:
        log("Persona Física: se omiten Obliga CFDI y Factoraje.")

    # 6. Domicilio / Calle
    calle_a_escribir = datos_proveedor.get("CALLE", "")
    if calle_a_escribir:
        log(f"Escribiendo calle: {calle_a_escribir}")
        escribir_domicilio(driver, calle_a_escribir)
        time.sleep(0.4)

    # 7. No. Exterior
    ext_a_escribir = datos_proveedor.get("EXT", "")
    if ext_a_escribir:
        log(f"Escribiendo num exterior: {ext_a_escribir}")
        escribir_num_exterior(driver, ext_a_escribir)
        time.sleep(0.4)

    # 8. CP y Colonia
    cp_a_buscar = datos_proveedor.get("CP", "")
    colonia_a_buscar = datos_proveedor.get("COLONIA", "")
    if cp_a_buscar:
        log(f"Seleccionando CP {cp_a_buscar} y Colonia {colonia_a_buscar}...")
        seleccionar_asentamiento_cp(driver, cp_a_buscar, colonia_a_buscar)
        time.sleep(0.5)

    # 9. GUARDAR EN PRODUCCIÓN Y CAPTURAR ID DESDE LA URL
    log("Presionando botón Guardar en Aryve...")
    id_generado, url_generada = guardar_proveedor_general(driver)
    
    id_final = id_generado if id_generado else "Pendiente"
    log(f"[ID] ID obtenido para '{clave_a_escribir}': {id_final}")

    # Guardar únicamente ID y Clave en registro_proveedores.json
    registrar_proveedor_json(clave_a_escribir, id_final)

    log(f"[OK] Proveedor '{nombre_a_escribir}' ({clave_a_escribir}) guardado con éxito. ID: {id_final}")
    return True, id_final


def procesar_cola_proveedores(lista_proveedores, log_callback=None):
    """
    Procesa secuencialmente una lista/cola de proveedores en Aryve.
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(msg)

    if not lista_proveedores:
        log("[AVISO] No hay proveedores en la lista para procesar.")
        return False, "Cola vacía"

    opciones = webdriver.ChromeOptions()
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--disable-extensions")
    opciones.add_argument("--log-level=3")

    servicio = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servicio, options=opciones)
    driver.maximize_window()

    try:
        log("Iniciando sesión en Aryve...")
        iniciar_sesion(driver, USER, PASSWORD)

        total = len(lista_proveedores)
        for i, prov in enumerate(lista_proveedores, 1):
            nom = prov.get("NOMBRE", f"Proveedor {i}")
            log(f"\n=======================================================")
            log(f" PROCESANDO [{i}/{total}]: {nom} ({prov.get('TIPO PERSONA', 'MORAL')})")
            log(f"=======================================================")
            procesar_un_proveedor(driver, prov, log_callback=log_callback)
            time.sleep(2)

        log("\n[EXITO] ¡Todos los proveedores de la lista fueron llenados con éxito!")
        return True, "Proceso completado exitosamente"

    except Exception as err:
        log(f"\n[ERROR EN EJECUCIÓN]: {err}")
        traceback.print_exc()
        return False, str(err)
    finally:
        time.sleep(2)
        driver.quit()

