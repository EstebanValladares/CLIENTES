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

from capturador_csv import capturar_datos_proveedor
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
from NUCLEO.config import obtener_credenciales_aryve

load_dotenv()
USER, PASSWORD = obtener_credenciales_aryve()
TARGET_URL = "#/scp/Proveedores/id?nuevo"


def main():
    # 1. Capturar datos por consola y guardarlos en datos.csv
    datos_proveedor = capturar_datos_proveedor("datos.csv")

    # 2. Configurar navegador con Selenium
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
        # 3. Iniciar sesión en Aryve
        iniciar_sesion(driver, USER, PASSWORD)

        # 4. Navegar a la pantalla de nuevo proveedor
        print(f"Navegando a: {TARGET_URL}")
        driver.get(TARGET_URL)
        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(4)

        # 5. Seleccionar Tipo de Persona ('MORAL' o 'FÍSICA' según lo capturado)
        tipo_persona = datos_proveedor.get("TIPO PERSONA", "MORAL")
        seleccionar_tipo_persona(driver, tipo=tipo_persona)
        time.sleep(1)

        # 6. Avanzar al siguiente panel con la flecha derecha (->)
        avanzar_siguiente_panel(driver)
        time.sleep(1)

        # 7. Escribir la CLAVE generada en el campo #formControl_Clave
        clave_a_escribir = datos_proveedor.get("CLAVE", "")
        if clave_a_escribir:
            escribir_clave(driver, clave_a_escribir)
            time.sleep(0.5)

        # 8. Escribir NOMBRE (y Apellidos si es Persona Física)
        nombre_a_escribir = datos_proveedor.get("NOMBRE", "")
        if nombre_a_escribir:
            escribir_nombre(driver, nombre_a_escribir)
            time.sleep(0.5)

        if "FISICA" in tipo_persona or "FÍSICA" in tipo_persona:
            paterno_a_escribir = datos_proveedor.get("PATERNO", "")
            if paterno_a_escribir:
                escribir_apellido_paterno(driver, paterno_a_escribir)
                time.sleep(0.5)

            materno_a_escribir = datos_proveedor.get("MATERNO", "")
            if materno_a_escribir:
                escribir_apellido_materno(driver, materno_a_escribir)
                time.sleep(0.5)

        # 9. Escribir el RFC en el campo #formControl_RFC
        rfc_a_escribir = datos_proveedor.get("RFC", "")
        if rfc_a_escribir:
            escribir_rfc(driver, rfc_a_escribir)
            time.sleep(0.5)

        # 10. Escribir el NOMBRE CORTO en el campo #formControl_NombreCorto
        corto_a_escribir = datos_proveedor.get("NOMBRE CORTO", "")
        if corto_a_escribir:
            escribir_nombre_corto(driver, corto_a_escribir)
            time.sleep(0.5)

        # 11 y 12. Marcar casillas 'Obliga CFDI' y 'Factoraje' ÚNICAMENTE si es Persona MORAL
        es_persona_moral = not ("FISICA" in tipo_persona or "FÍSICA" in tipo_persona)
        if es_persona_moral:
            marcar_obliga_cfdi(driver)
            time.sleep(0.5)
            marcar_factoraje(driver)
            time.sleep(0.5)
        else:
            print("[INFO] Modo Persona FÍSICA: se omite 'Obliga CFDI' y 'Factoraje'.")

        # 13. Escribir la Calle en el campo #formControl_Domicilio
        calle_a_escribir = datos_proveedor.get("CALLE", "")
        if calle_a_escribir:
            escribir_domicilio(driver, calle_a_escribir)
            time.sleep(0.5)

        # 14. Escribir el Número Exterior en el campo #formControl_NumExterior
        ext_a_escribir = datos_proveedor.get("EXT", "")
        if ext_a_escribir:
            escribir_num_exterior(driver, ext_a_escribir)
            time.sleep(0.5)

        # 15. Seleccionar C.P. y Colonia en el desplegable remoto
        cp_a_buscar = datos_proveedor.get("CP", "")
        colonia_a_buscar = datos_proveedor.get("COLONIA", "")
        if cp_a_buscar:
            seleccionar_asentamiento_cp(driver, cp_a_buscar, colonia_a_buscar)
            time.sleep(0.5)

        # 16. Guardar en Aryve y capturar ID generado en la URL
        print("\nPresionando botón Guardar en Aryve...")
        id_obtenido, url_obtenida = guardar_proveedor_general(driver)
        
        # Guardar en registro_proveedores.json
        import json
        ruta_reg = "registro_proveedores.json"
        registros_previos = []
        if os.path.exists(ruta_reg):
            try:
                with open(ruta_reg, "r", encoding="utf-8") as fr:
                    registros_previos = json.load(fr)
            except Exception:
                pass
        
        nuevo_reg = {
            "id": str(id_obtenido or "Pendiente"),
            "clave": clave_a_escribir
        }
        # Actualizar o agregar
        actualizado = False
        for i, r in enumerate(registros_previos):
            if r.get("clave") == clave_a_escribir:
                registros_previos[i] = nuevo_reg
                actualizado = True
                break
        if not actualizado:
            registros_previos.append(nuevo_reg)

        with open(ruta_reg, "w", encoding="utf-8") as fw:
            json.dump(registros_previos, fw, indent=2, ensure_ascii=False)

        input(f"\n[COMPLETADO]: Proveedor guardado. ID: '{id_obtenido}'. Presiona Enter en la terminal cuando desees cerrar el navegador...")

    except Exception as err:
        print(f"\n[ERROR EN EJECUCIÓN]: {err}")
        traceback.print_exc()
        input("\nPresiona Enter para cerrar el navegador tras el error...")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
