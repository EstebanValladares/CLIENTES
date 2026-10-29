from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import unicodedata


def iniciar_sesion(driver, usuario, password):
    """Inicia sesión en la plataforma Aryve."""
    print("Iniciando sesión en Aryve...")
    driver.get("")

    wait = WebDriverWait(driver, 20)

    # Campo de usuario
    user_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
    user_input.clear()
    user_input.send_keys(usuario)

    # Campo de contraseña
    pass_input = driver.find_element(By.ID, "password")
    pass_input.clear()
    pass_input.send_keys(password)

    # Botón submit
    driver.find_element(By.ID, "btnSubmit").click()

    # Esperar carga y refresco estándar
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)
    driver.refresh()
    time.sleep(2)
    print("¡Logeo exitoso!")


def _norm_str(texto):
    """Normaliza cadenas eliminando acentos, espacios extra y en mayúsculas."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8')
    texto_norm = re.sub(r'[^A-Z0-9]', ' ', texto_norm.upper())
    return " ".join(texto_norm.split())


def seleccionar_tipo_persona(driver, tipo="MORAL"):
    """
    Selecciona directamente 'MORAL' (o 'FÍSICA') en el campo TIPO DE PERSONA
    utilizando el elemento Select2 exacto sin tocar las flechas de colapsar/expandir paneles.
    """
    print(f"Seleccionando Tipo de Persona: '{tipo}'...")
    wait = WebDriverWait(driver, 15)

    # 1. Localizar el span rendered del Select2 por su ID exacto
    caja_rendered = wait.until(
        EC.presence_of_element_located((By.ID, "select2-formControl_TipoPersona-container"))
    )

    # Si ya tiene el valor seleccionado, no hace falta volver a seleccionarlo
    texto_actual = _norm_str(caja_rendered.text or caja_rendered.get_attribute("textContent"))
    if texto_actual == _norm_str(tipo):
        print(f"Tipo de Persona ya se encuentra en '{tipo}'.")
        return True

    # 2. Hacer clic en el contenedor para abrir el desplegable
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caja_rendered)
    time.sleep(0.3)
    try:
        caja_rendered.click()
    except Exception:
        driver.execute_script("arguments[0].click();", caja_rendered)

    time.sleep(0.5)

    # 3. Buscar y seleccionar la opción en la lista desplegada
    xpath_opcion = f"//li[contains(@class, 'select2-results__option') and contains(translate(text(), 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), '{tipo.upper()}')]"

    try:
        opcion = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_opcion)))
        opcion.click()
    except Exception:
        # Fallback con JavaScript si está cubierto por overlay
        opcion = driver.find_element(By.XPATH, xpath_opcion)
        driver.execute_script("arguments[0].click();", opcion)

    time.sleep(0.5)
    print(f"¡'{tipo}' seleccionado exitosamente en TIPO DE PERSONA!")
    return True


def avanzar_siguiente_panel(driver):
    """
    Presiona la flecha '->' del panel actual para confirmar y avanzar al siguiente panel de captura.
    """
    print("Avanzando al siguiente panel con la flecha...")
    try:
        # La flecha a la derecha suele ser un enlace o botón con icono dentro del panel-heading
        btn_flecha = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class, 'panel-heading') and .//*[contains(text(), 'TIPO DE PERSONA')]]//a | "
                "//div[contains(@class, 'panel-heading') and .//*[contains(text(), 'TIPO DE PERSONA')]]//i[contains(@class, 'arrow') or contains(@class, 'right') or contains(@class, 'next')]/.. | "
                "//div[contains(@class, 'panel-heading')]//*[contains(@class, 'fa-arrow-right') or contains(@class, 'fa-chevron-right') or contains(@class, 'icon-arrow-right')]"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_flecha)
        time.sleep(0.3)
        try:
            btn_flecha.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_flecha)
        
        time.sleep(1)
        print("Avanzado con éxito.")
        return True
    except Exception as e:
        print(f"[AVISO]: No se pudo hacer clic en la flecha de avance: {e}")
        return False


def escribir_clave(driver, clave_texto):
    """
    Escribe de forma segura y limpia la clave en el input #formControl_Clave.
    Lanza los eventos 'input' y 'change' para que Aryve detecte el cambio en el contador 0/50.
    """
    print(f"Escribiendo Clave: '{clave_texto}'...")
    try:
        wait = WebDriverWait(driver, 15)
        campo = wait.until(EC.element_to_be_clickable((By.ID, "formControl_Clave")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        
        campo.click()
        campo.clear()
        
        # Enviar teclas de forma estándar
        campo.send_keys(clave_texto)
        
        # Disparar eventos nativos para asegurar que el framework de Aryve actualice su estado
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        
        time.sleep(0.3)
        print(f"¡Clave '{clave_texto}' ingresada exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir la clave: {e}")
        return False


def escribir_nombre(driver, nombre_texto):
    """
    Escribe de forma segura y limpia el nombre completo en el input #formControl_Nombre.
    Lanza los eventos 'input' y 'change' para actualizar el contador 0/150.
    """
    print(f"Escribiendo Nombre completo: '{nombre_texto}'...")
    try:
        wait = WebDriverWait(driver, 15)
        campo = wait.until(EC.element_to_be_clickable((By.ID, "formControl_Nombre")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        
        campo.click()
        campo.clear()
        
        campo.send_keys(nombre_texto)
        
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        
        time.sleep(0.3)
        print(f"¡Nombre '{nombre_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el nombre completo: {e}")
        return False


def escribir_rfc(driver, rfc_texto):
    """
    Escribe de forma segura y limpia el RFC en el input #formControl_RFC.
    Lanza los eventos 'input' y 'change' para que Aryve valide el formato y quite el error.
    """
    print(f"Escribiendo RFC: '{rfc_texto}'...")
    try:
        wait = WebDriverWait(driver, 15)
        campo = wait.until(EC.element_to_be_clickable((By.ID, "formControl_RFC")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        
        campo.click()
        campo.clear()
        
        campo.send_keys(rfc_texto)
        
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        
        time.sleep(0.3)
        print(f"¡RFC '{rfc_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el RFC: {e}")
        return False


def escribir_nombre_corto(driver, nombre_corto_texto):
    """
    Escribe el nombre corto en el input #formControl_NombreCorto.
    Dispara los eventos 'input' y 'change' para sincronizar el contador 0/25.
    """
    print(f"Escribiendo Nombre Corto: '{nombre_corto_texto}'...")
    try:
        wait = WebDriverWait(driver, 15)
        campo = wait.until(EC.element_to_be_clickable((By.ID, "formControl_NombreCorto")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        
        campo.click()
        campo.clear()
        
        campo.send_keys(nombre_corto_texto)
        
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        
        time.sleep(0.3)
        print(f"¡Nombre Corto '{nombre_corto_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el Nombre Corto: {e}")
        return False


def marcar_obliga_cfdi(driver):
    """
    Marca la casilla de verificación 'Obliga CFDI'.
    Verifica si ya está marcada (value='true' o checkbox seleccionado) para evitar desmarcarla.
    Hace clic en el label o span interactivo de React.
    """
    print("Marcando casilla 'Obliga CFDI'...")
    try:
        wait = WebDriverWait(driver, 15)
        
        # Localizar el input checkbox oculto o reactivo
        input_chk = wait.until(EC.presence_of_element_located((By.ID, "formControl_Proveedores_obliga_cfd")))
        
        # Verificar si ya está activo
        val_attr = (input_chk.get_attribute("value") or "").lower()
        esta_marcado = input_chk.is_selected() or val_attr == "true"
        
        if esta_marcado:
            print("[INFO] 'Obliga CFDI' ya se encuentra marcado.")
            return True

        # Localizar el label correspondiente para hacer clic visual y disparar React
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_chk)
        time.sleep(0.2)

        try:
            label_chk = driver.find_element(By.XPATH, "//label[@for='formControl_Proveedores_obliga_cfd']")
            label_chk.click()
        except Exception:
            try:
                span_box = driver.find_element(By.XPATH, "//label[@for='formControl_Proveedores_obliga_cfd']//span[contains(@class, 'box') or contains(@class, 'check')]")
                span_box.click()
            except Exception:
                driver.execute_script("arguments[0].click();", input_chk)

        time.sleep(0.4)
        print("¡Casilla 'Obliga CFDI' marcada exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo marcar la casilla 'Obliga CFDI': {e}")
        return False


def marcar_factoraje(driver):
    """
    Marca la casilla de verificación 'Factoraje'.
    Verifica si ya está marcada (value='true' o checkbox seleccionado) para evitar desmarcarla.
    Hace clic en el label interactivo de React.
    """
    print("Marcando casilla 'Factoraje'...")
    try:
        wait = WebDriverWait(driver, 15)
        input_chk = wait.until(EC.presence_of_element_located((By.ID, "formControl_Proveedores_factoraje")))
        
        val_attr = (input_chk.get_attribute("value") or "").lower()
        esta_marcado = input_chk.is_selected() or val_attr == "true"
        
        if esta_marcado:
            print("[INFO] 'Factoraje' ya se encuentra marcado.")
            return True

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_chk)
        time.sleep(0.2)

        try:
            label_chk = driver.find_element(By.XPATH, "//label[@for='formControl_Proveedores_factoraje']")
            label_chk.click()
        except Exception:
            try:
                span_box = driver.find_element(By.XPATH, "//label[@for='formControl_Proveedores_factoraje']//span[contains(@class, 'box') or contains(@class, 'check')]")
                span_box.click()
            except Exception:
                driver.execute_script("arguments[0].click();", input_chk)

        time.sleep(0.4)
        print("¡Casilla 'Factoraje' marcada exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo marcar la casilla 'Factoraje': {e}")
        return False


def escribir_domicilio(driver, calle_texto):
    """
    Escribe la calle/domicilio en el input #formControl_Domicilio.
    Dispara los eventos 'input' y 'change' para sincronizar con React.
    """
    print(f"Escribiendo Domicilio / Calle: '{calle_texto}'...")
    try:
        wait = WebDriverWait(driver, 15)
        campo = wait.until(EC.element_to_be_clickable((By.ID, "formControl_Domicilio")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        
        campo.click()
        campo.clear()
        
        campo.send_keys(calle_texto)
        
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        
        time.sleep(0.3)
        print(f"¡Domicilio '{calle_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el Domicilio: {e}")
        return False


def escribir_num_exterior(driver, num_ext_texto):
    """
    Escribe el número exterior en el input #formControl_NumExterior.
    Dispara los eventos 'input' y 'change' para sincronizar con React.
    """
    print(f"Escribiendo Número Exterior: '{num_ext_texto}'...")
    try:
        wait = WebDriverWait(driver, 15)
        campo = wait.until(EC.element_to_be_clickable((By.ID, "formControl_NumExterior")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        
        campo.click()
        campo.clear()
        
        campo.send_keys(num_ext_texto)
        
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        
        time.sleep(0.3)
        print(f"¡Número Exterior '{num_ext_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el Número Exterior: {e}")
        return False


def seleccionar_asentamiento_cp(driver, cp_texto, colonia_texto=""):
    """
    Despliega el Select2 remoto de C.P. / COLONIA / MUNICIPIO (#formControl_Asentamiento),
    escribe el Código Postal en la caja de búsqueda para disparar la carga remota,
    espera los resultados y selecciona la opción que mejor coincida con la COLONIA.
    Si no hay colonia o no coincide exactamente, selecciona la opción correspondiente al CP.
    """
    print(f"Buscando C.P. '{cp_texto}' (Colonia: '{colonia_texto}')...")
    try:
        wait = WebDriverWait(driver, 15)

        # 1. Localizar y hacer clic en el contenedor Select2 del Asentamiento
        caja = wait.until(EC.element_to_be_clickable((By.ID, "select2-formControl_Asentamiento-container")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caja)
        time.sleep(0.2)

        try:
            caja.click()
        except Exception:
            driver.execute_script("arguments[0].click();", caja)

        time.sleep(0.4)

        # 2. Localizar el input de búsqueda Select2
        input_busqueda = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[contains(@class, 'select2-search__field')]"))
        )
        input_busqueda.clear()
        # Escribir el CP para que el servidor devuelva las colonias correspondientes
        input_busqueda.send_keys(cp_texto)
        time.sleep(1.2)  # Dar tiempo a la petición remota (data-source-remote="true")

        # 3. Esperar que aparezcan las opciones que no sean el mensaje de carga o error
        xpath_opciones = "//li[contains(@class, 'select2-results__option') and not(@aria-disabled='true') and not(contains(@class, 'select2-results__message'))]"
        
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, xpath_opciones)))
        except Exception:
            time.sleep(1.0)

        opciones = driver.find_elements(By.XPATH, xpath_opciones)
        if not opciones:
            print(f"[AVISO]: No se encontraron opciones para el CP '{cp_texto}'. Intentando seleccionar con Enter...")
            input_busqueda.send_keys(Keys.ENTER)
            time.sleep(0.5)
            return True

        colonia_norm = _norm_str(colonia_texto)
        opcion_elegida = None

        # 4. Comparar cada opción con el nombre de la COLONIA proporcionada
        if colonia_norm:
            # Coincidencia directa o parcial de colonia
            for op in opciones:
                txt_op = _norm_str(op.text or op.get_attribute("textContent"))
                if colonia_norm in txt_op or any(palabra in txt_op for palabra in colonia_norm.split() if len(palabra) > 3):
                    opcion_elegida = op
                    print(f"  -> Coincidencia encontrada con Colonia '{colonia_texto}': {op.text}")
                    break

        # Si no hubo coincidencia o no se especificó colonia, elegir la primera opción que traiga el CP
        if not opcion_elegida:
            opcion_elegida = opciones[0]
            print(f"  -> Seleccionando opción por defecto para el CP: {opcion_elegida.text}")

        # 5. Hacer clic en la opción elegida
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcion_elegida)
        time.sleep(0.2)
        try:
            opcion_elegida.click()
        except Exception:
            driver.execute_script("arguments[0].click();", opcion_elegida)

        time.sleep(0.5)
        print("¡Asentamiento / C.P. seleccionado con éxito!")
        return True

    except Exception as e:
        print(f"[ERROR]: Fallo al seleccionar Asentamiento/CP: {e}")
        return False


def escribir_apellido_paterno(driver, paterno_texto):
    """
    Escribe el Apellido Paterno en el input correspondiente.
    Intenta por los IDs más comunes (formControl_ApellidoPaterno, formControl_Paterno, etc.)
    o por búsqueda de input adyacente a la etiqueta APELLIDO PATERNO.
    """
    print(f"Escribiendo Apellido Paterno: '{paterno_texto}'...")
    try:
        wait = WebDriverWait(driver, 10)
        campo = None
        posibles_ids = [
            "formControl_ApellidoPaterno",
            "formControl_Paterno",
            "formControl_PrimerApellido",
            "ApellidoPaterno"
        ]
        for id_cand in posibles_ids:
            try:
                campo = driver.find_element(By.ID, id_cand)
                if campo and campo.is_displayed():
                    break
            except Exception:
                continue

        if not campo:
            # Buscar por XPath relativo a la etiqueta 'APELLIDO PATERNO'
            campo = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PATERNO')]/following-sibling::*//input | "
                "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PATERNO')]/..//input"
            )))

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        campo.click()
        campo.clear()
        campo.send_keys(paterno_texto)
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        time.sleep(0.3)
        print(f"¡Apellido Paterno '{paterno_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el Apellido Paterno: {e}")
        return False


def escribir_apellido_materno(driver, materno_texto):
    """
    Escribe el Apellido Materno en el input correspondiente.
    """
    if not materno_texto:
        return True

    print(f"Escribiendo Apellido Materno: '{materno_texto}'...")
    try:
        wait = WebDriverWait(driver, 10)
        campo = None
        posibles_ids = [
            "formControl_ApellidoMaterno",
            "formControl_Materno",
            "formControl_SegundoApellido",
            "ApellidoMaterno"
        ]
        for id_cand in posibles_ids:
            try:
                campo = driver.find_element(By.ID, id_cand)
                if campo and campo.is_displayed():
                    break
            except Exception:
                continue

        if not campo:
            campo = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'MATERNO')]/following-sibling::*//input | "
                "//label[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'MATERNO')]/..//input"
            )))

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.2)
        campo.click()
        campo.clear()
        campo.send_keys(materno_texto)
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)
        time.sleep(0.3)
        print(f"¡Apellido Materno '{materno_texto}' ingresado exitosamente!")
        return True
    except Exception as e:
        print(f"[ERROR]: No se pudo escribir el Apellido Materno: {e}")
        return False


def guardar_proveedor_general(driver):
    """
    Presiona el botón de guardar global (icono icon-cloud-upload / Guardar (Alt+G))
    en la barra superior. Espera a que la URL cambie para capturar el ID real generado
    al final de la URL (ej: /Proveedores/id?1052 o /Proveedores/1052).
    Devuelve (id_proveedor, url_final).
    """
    print("\nGuardando Proveedor en Aryve...")
    try:
        wait = WebDriverWait(driver, 15)
        xpaths_guardar = [
            "//button[contains(@class, 'btn-editing') and .//i[contains(@class, 'icon-cloud-upload')]]",
            "//button[contains(@class, 'page-bar-button') and .//i[contains(@class, 'icon-cloud-upload')]]",
            "//div[contains(@class, 'page-bar-buttons')]//button[contains(@class, 'btn-editing') or contains(@data-tip, 'Guardar') or contains(@title, 'Guardar')]",
            "//button[@data-tip='Guardar (Alt+G)' or @title='Guardar (Alt+G)' or contains(@title, 'Guardar')]"
        ]

        btn_guardar = None
        for xp in xpaths_guardar:
            try:
                elems = driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed():
                        btn_guardar = el
                        break
                if btn_guardar:
                    break
            except Exception:
                continue

        if not btn_guardar:
            print("[ERROR]: No se encontró el botón de guardar en la barra superior.")
            return None, driver.current_url

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_guardar)
        time.sleep(0.3)
        try:
            btn_guardar.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_guardar)

        print("Botón 'Guardar' presionado. Esperando respuesta y captura del ID en la URL...")

        id_proveedor = None
        url_final = driver.current_url

        # Esperar hasta 25 segundos a que la URL cambie tras guardar
        for _ in range(50):
            time.sleep(0.5)
            url_act = driver.current_url
            url_final = url_act

            # Buscar patrones comunes de ID al final de la URL en Aryve
            # Ejemplos: .../Proveedores/id?12345, .../Proveedores/12345, .../id=12345
            m = (
                re.search(r'/Proveedores/id[?=](\d+)', url_act) or
                re.search(r'/Proveedores/(\d+)(?:[?#]|$)', url_act) or
                re.search(r'id[?=](\d+)', url_act)
            )
            if m and "id?nuevo" not in url_act:
                id_proveedor = m.group(1)
                break

        if id_proveedor:
            print(f"[EXITO] ¡Proveedor guardado con éxito! ID generado: {id_proveedor}")
            print(f"URL: {url_final}")
        else:
            # Si no capturó número en la URL, intentar extraer el último segmento que no sea 'nuevo'
            partes = [p for p in url_final.replace("?", "/").replace("=", "/").split("/") if p and p != "nuevo"]
            if partes and partes[-1].isdigit():
                id_proveedor = partes[-1]
                print(f"ID capturado por segmento final: {id_proveedor}")
            else:
                print(f"[AVISO]: Se guardó pero la URL aún no expuso un ID numérico ({url_final}).")

        return id_proveedor, url_final

    except Exception as e:
        print(f"[ERROR]: Fallo al intentar guardar proveedor: {e}")
        return None, driver.current_url








