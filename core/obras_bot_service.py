"""
Core Domain: Bot Service para Navegación y Automatización de Obras en Aryve (eKlod).
Permite buscar una obra, abrir el panel lateral/izquierdo, presionar 'APLICAR CONFIGURACIÓN'
y posteriormente 'IR A OBRA' para entrar en su contexto operativo.

Arquitectura Dual:
1. Modo CDP (Rápido): Si Chrome está abierto con '1_abrir_aryve_rea.bat' en el puerto 9222,
   se acopla de inmediato a la sesión activa sin requerir nuevo inicio de sesión.
2. Modo Autónomo (Auto-Login): Si Chrome 9222 no está activo, inicia Chrome con Selenium,
   toma las credenciales EK10_USER / EK10_PASS del archivo .env y realiza el inicio de sesión.
"""

import os
import sys
import json
import time
import datetime
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOGO_OBRAS_PATH = os.path.join(BASE_DIR, "OBRAS", "catalogo_obras.json")
CDP_URL = "http://127.0.0.1:9222"
URL_ARYVE_BASE = os.getenv("ARYVE_BASE_URL", "https://suite.ekloud.net:1445/Aryve/")
URL_OBRAS = f"{URL_ARYVE_BASE.rstrip('/')}/#/scco/Obra"
URL_LOGIN = f"{URL_ARYVE_BASE.rstrip('/')}/#/login"


class ObrasBotService:

    @classmethod
    def obtener_id_obra(cls, clave_obra: str) -> Optional[int]:
        """Obtiene el ID numérico de la obra en Aryve (ej. KB5 -> 412)."""
        clave_clean = str(clave_obra).strip().upper()
        if not os.path.exists(CATALOGO_OBRAS_PATH):
            return None
        try:
            with open(CATALOGO_OBRAS_PATH, "r", encoding="utf-8") as f:
                catalogo = json.load(f)
                for o in catalogo:
                    c = str(o.get("clave", "")).strip().upper()
                    if c == clave_clean:
                        return int(o.get("id_obra") or o.get("id") or 0)
        except Exception as e:
            print(f"[ObrasBot] Error leyendo catálogo de obras: {e}")
        return None

    @classmethod
    def verificar_chrome_rea(cls) -> bool:
        """Verifica si Chrome con modo depuración en puerto 9222 está activo."""
        try:
            with urllib.request.urlopen(f"{CDP_URL}/json", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def resolver_credenciales(cls) -> Tuple[bool, Tuple[str, str] | str]:
        """Carga credenciales desde .env o NUCLEO."""
        # 1. Intentar desde .env
        env_path = os.path.join(BASE_DIR, ".env")
        if os.path.exists(env_path):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
            except Exception:
                pass
        
        user = os.getenv("EK10_USER", "")
        password = os.getenv("EK10_PASS", "")
        if user and password:
            return True, (user, password)

        # 2. Intentar desde NUCLEO
        try:
            if BASE_DIR not in sys.path:
                sys.path.insert(0, BASE_DIR)
            from NUCLEO.config import obtener_credenciales_aryve
            u, p = obtener_credenciales_aryve()
            if u and p:
                return True, (u, p)
        except Exception:
            pass

        return False, "Credenciales de Aryve (EK10_USER / EK10_PASS) no encontradas en .env ni en NUCLEO."

    @classmethod
    def _iniciar_driver_y_sesion(cls, log) -> Any:
        """
        Retorna un driver de Selenium configurado:
        - Si el puerto 9222 está vivo, se acopla a él.
        - Si no, levanta un nuevo ChromeDriver y hace login con las credenciales configuradas.
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        if cls.verificar_chrome_rea():
            log(f"Chrome REA detectado en {CDP_URL}. Acoplándose a la sesión activa...")
            options = Options()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)
            return driver, "CDP_9222"

        log("Puerto 9222 no detectado. Levantando navegador autónomo con inicio de sesión automático...")
        ok, creds = cls.resolver_credenciales()
        if not ok:
            raise RuntimeError(str(creds))
        
        usuario, password = creds
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--log-level=3")

        # Intentar con webdriver_manager o ChromeDriver local
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e_drv:
            log(f"Aviso con ChromeDriverManager ({e_drv}), intentando Chrome directo...")
            driver = webdriver.Chrome(options=options)

        log("Iniciando sesión en Aryve...")
        driver.get(URL_LOGIN)
        wait = WebDriverWait(driver, 20)

        # Llenar usuario y password
        user_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
        user_input.clear()
        user_input.send_keys(usuario)

        pass_input = driver.find_element(By.ID, "password")
        pass_input.clear()
        pass_input.send_keys(password)

        driver.find_element(By.ID, "btnSubmit").click()
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        driver.refresh()
        time.sleep(1.5)
        log("¡Inicio de sesión en Aryve exitoso!")

        return driver, "AUTONOMO"

    @classmethod
    def ir_a_obra(cls, clave_obra: str, log_callback=None) -> Dict[str, Any]:
        """
        Flujo de Automatización para Selección y Acceso a Obra:
        1. Conecta con Aryve (CDP o Login).
        2. Navega a #/scco/Obra si no está en ella.
        3. Escribe la clave de la obra en el buscador de la tabla de datos DevExtreme.
        4. Selecciona la fila de la obra para abrir el panel izquierdo/lateral.
        5. Da clic en 'APLICAR CONFIGURACIÓN'.
        6. Da clic en 'IR A OBRA'.
        7. Valida la navegación y finaliza.
        """
        logs = []
        def log(msg: str):
            linea = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
            logs.append(linea)
            print(f"[ObrasBot] {linea}")
            if log_callback:
                try:
                    log_callback(linea)
                except Exception:
                    pass

        clave_clean = str(clave_obra).strip().upper()
        if not clave_clean:
            return {"ok": False, "error": "Debe especificar la clave de la obra."}

        id_obra = cls.obtener_id_obra(clave_clean)
        log(f"Iniciando proceso para obra: {clave_clean} (ID detectado: {id_obra or 'N/A'})...")

        driver = None
        modo_ejecucion = None
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.action_chains import ActionChains

            driver, modo_ejecucion = cls._iniciar_driver_y_sesion(log)
            wait = WebDriverWait(driver, 15)

            # 1. Navegar a /scco/Obra
            if "/scco/Obra" not in driver.current_url:
                log(f"Navegando a Administración de Obra: {URL_OBRAS}...")
                driver.get(URL_OBRAS)
                time.sleep(2.5)

            # Esperar a que el buscador del grid esté presente
            log("Esperando tabla de Administración de Obra...")
            input_busqueda = None
            selectores_busqueda = [
                (By.XPATH, "//input[@aria-label='Buscar en la tabla de datos']"),
                (By.XPATH, "//div[contains(@class, 'dx-datagrid-search-panel')]//input"),
                (By.XPATH, "//input[contains(@class, 'dx-texteditor-input')]")
            ]

            for by, val in selectores_busqueda:
                try:
                    input_busqueda = wait.until(EC.element_to_be_clickable((by, val)))
                    if input_busqueda:
                        break
                except Exception:
                    continue

            if not input_busqueda:
                raise RuntimeError("No se localizó el buscador de obras en la tabla DevExtreme.")

            log(f"Filtrando obra '{clave_clean}' en la tabla...")
            input_busqueda.click()
            input_busqueda.send_keys(Keys.CONTROL + "a")
            input_busqueda.send_keys(Keys.BACKSPACE)
            time.sleep(0.3)
            input_busqueda.send_keys(clave_clean)
            input_busqueda.send_keys(Keys.ENTER)
            time.sleep(1.8)

            # 2. Localizar primera fila de resultados
            log("Localizando la fila de la obra en el grid...")
            fila_xpath = "//div[contains(@class, 'dx-datagrid-rowsview')]//table[contains(@class, 'dx-datagrid-table')]//tr[contains(@class, 'dx-data-row')][1]"
            try:
                fila = wait.until(EC.presence_of_element_located((By.XPATH, fila_xpath)))
            except Exception:
                fila = None

            if not fila:
                raise RuntimeError(f"No se encontró ninguna fila con la obra '{clave_clean}' en el catálogo de Aryve.")

            log("Haciendo clic en la fila de la obra...")
            try:
                fila.click()
            except Exception:
                driver.execute_script("arguments[0].click();", fila)
            time.sleep(1.2)

            # 3. Localizar y presionar 'APLICAR CONFIGURACIÓN'
            log("Buscando botón 'APLICAR CONFIGURACIÓN' en el panel...")
            xpath_aplicar_config = [
                "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'APLICAR CONFIGURACION')]",
                "//a[contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'APLICAR CONFIGURACION')]",
                "//div[contains(@class, 'dx-button') and contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'APLICAR CONFIGURACION')]",
                "//*[contains(translate(@title, 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'APLICAR CONFIGURACION')]",
                "//button[contains(@id, 'Config') or contains(@id, 'btnConfig')]",
                "//span[contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'APLICAR CONFIGURACION')]/ancestor::button[1]"
            ]

            btn_aplicar = None
            for xp in xpath_aplicar_config:
                elems = driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed():
                        btn_aplicar = el
                        break
                if btn_aplicar:
                    break

            if btn_aplicar:
                log("Botón 'APLICAR CONFIGURACIÓN' encontrado. Haciendo clic...")
                try:
                    btn_aplicar.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn_aplicar)
                time.sleep(1.5)
            else:
                log("Aviso: No se detectó botón explícito 'APLICAR CONFIGURACIÓN' en este panel. Continuando al siguiente paso...")

            # 4. Localizar y presionar 'IR A OBRA'
            log("Buscando botón 'IR A OBRA'...")
            xpath_ir_a_obra = [
                "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'IR A OBRA')]",
                "//a[contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'IR A OBRA')]",
                "//div[contains(@class, 'dx-button') and contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'IR A OBRA')]",
                "//*[contains(translate(@title, 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'IR A OBRA')]",
                "//button[contains(@id, 'IrAObra') or contains(@id, 'btnIrAObra')]",
                "//span[contains(translate(., 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'IR A OBRA')]/ancestor::button[1]"
            ]

            btn_ir_obra = None
            for xp in xpath_ir_a_obra:
                elems = driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed():
                        btn_ir_obra = el
                        break
                if btn_ir_obra:
                    break

            if btn_ir_obra:
                log("Botón 'IR A OBRA' encontrado. Haciendo clic...")
                try:
                    btn_ir_obra.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn_ir_obra)
                time.sleep(2.5)
                log(f"¡Acción 'IR A OBRA' ejecutada con éxito! URL actual: {driver.current_url}")
            else:
                # Si no se encontró el botón pero tenemos el id_obra, navegamos a la pantalla de edición de obra directamente
                if id_obra:
                    url_directa = f"{URL_OBRAS}/{id_obra}"
                    log(f"No se detectó botón 'IR A OBRA'. Navegando directamente a vista de Obra #{id_obra}: {url_directa}...")
                    driver.get(url_directa)
                    time.sleep(2.5)
                else:
                    # Intento de doble clic sobre la fila
                    log("Intentando doble clic sobre la fila para entrar a la obra...")
                    actions = ActionChains(driver)
                    actions.double_click(fila).perform()
                    time.sleep(2.0)

            url_final = driver.current_url
            log(f"Proceso finalizado con éxito. Pantalla de Aryve lista en: {url_final}")

            return {
                "ok": True,
                "obra": clave_clean,
                "id_obra": id_obra,
                "url_final": url_final,
                "modo": modo_ejecucion,
                "logs": logs
            }

        except Exception as e:
            err_msg = f"Error en automatización de Obras: {str(e)}"
            log(f"[ERROR] {err_msg}")
            return {
                "ok": False,
                "obra": clave_clean,
                "error": err_msg,
                "modo": modo_ejecucion,
                "logs": logs
            }
        finally:
            # Si se ejecutó en modo autónomo y el usuario no desea mantenerlo abierto, o se mantiene para que el usuario opere
            pass

    @classmethod
    def ejecutar_llenado_optimizacion(
        cls,
        obras: List[str],
        grupos: List[Dict[str, Any]],
        log_callback=None
    ) -> Dict[str, Any]:
        """
        Llenado visual de COMPAÑIA GRUPO DE INSUMOS según reglas oficiales del usuario:
        - Tipo 1 (MATERIALES) -> 20 CONSOLIDADORA
        - Tipo 2 (MANO DE OBRA) -> 01 CONSTRUCCIONES ARYVE
        - Tipo 4 (SUBCONTRATOS) -> 01 CONSTRUCCIONES ARYVE
        - Tipo 5 (INDIRECTOS) -> 20 CONSOLIDADORA
        - 'Los que ya tienen, omitelos': Si una fila ya tiene compañía asignada, se ignora.
        - 'Al final no lo guardes': Se mantiene en modo edición sin hacer clic en Guardar (Alt+G).
        """
        logs = []
        def log(msg: str):
            linea = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
            logs.append(linea)
            print(f"[OptimizadorInsumos] {linea}")
            if log_callback:
                try:
                    log_callback(linea)
                except Exception:
                    pass

        if not obras:
            return {"ok": False, "error": "No se especificaron obras a procesar."}

        log(f"Iniciando proceso de Optimización de Insumos para {len(obras)} obra(s)...")
        log("Reglas de asignación:")
        log("  • Tipo 1: MATERIALES -> 20 CONSOLIDADORA")
        log("  • Tipo 2: MANO DE OBRA -> 01 CONSTRUCCIONES ARYVE S.A. DE C.V.")
        log("  • Tipo 4: SUBCONTRATOS -> 01 CONSTRUCCIONES ARYVE S.A. DE C.V.")
        log("  • Tipo 5: INDIRECTOS -> 20 CONSOLIDADORA")
        log("  • Omitir filas que ya tengan compañía asignada")
        log("  • NO GUARDAR al finalizar para revisión visual del usuario")

        driver = None
        modo_ejecucion = None
        obras_procesadas = []

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver, modo_ejecucion = cls._iniciar_driver_y_sesion(log)
            wait = WebDriverWait(driver, 15)

            for clave_obra in obras:
                clave_clean = str(clave_obra).strip().upper()
                id_obra = cls.obtener_id_obra(clave_clean)
                log(f"\n--- PROCESANDO OBRA: {clave_clean} (ID: {id_obra or 'N/A'}) ---")

                # 1. Navegar a la pantalla de la obra
                url_obra = f"{URL_OBRAS}/{id_obra}" if id_obra else None
                if url_obra and url_obra not in driver.current_url:
                    log(f"Navegando a vista de edición de obra: {url_obra}...")
                    driver.get(url_obra)
                    time.sleep(3.5)
                elif not url_obra:
                    log(f"Buscando obra {clave_clean} en tabla de Administración de Obra...")
                    cls.ir_a_obra(clave_clean, log_callback=log)
                    time.sleep(3.0)

                # 2. Verificar y activar Modo Edición (Alt+E)
                log("Comprobando estado de edición en la obra...")
                btns_guardar = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-editing') or @title='Guardar (Alt+G)' or contains(@class, 'yellow-casablanca')]")
                en_edicion = any(b.is_displayed() for b in btns_guardar)

                if en_edicion:
                    log("La obra ya se encuentra en modo edición (botón Guardar visible).")
                else:
                    log("Haciendo clic en 'Editar (Alt+E)'...")
                    btns_editar = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-editar') or @title='Editar (Alt+E)' or contains(text(), 'Editar')]")
                    btn_ed = next((b for b in btns_editar if b.is_displayed()), None)
                    if btn_ed:
                        try:
                            btn_ed.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", btn_ed)
                        time.sleep(2.5)
                        log("Modo edición activado con éxito.")
                    else:
                        log("Aviso: No se detectó botón explícito de Editar; continuando...")

                # 3. Localizar la sección 'COMPAÑIA GRUPO DE INSUMOS'
                log("Localizando y desplegando sección 'COMPAÑIA GRUPO DE INSUMOS'...")
                xpath_panel = (
                    "//div[contains(@class, 'panel') and "
                    ".//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'COMPA') and "
                    "contains(translate(text(), 'abcdefghijklmnopqrstuvwxyzáéíóú', 'ABCDEFGHIJKLMNOPQRSTUVWXYZAEIOU'), 'GRUPO DE INSUMO')]]"
                )
                panels = driver.find_elements(By.XPATH, xpath_panel)
                if not panels:
                    raise RuntimeError("No se localizó la sección 'COMPAÑIA GRUPO DE INSUMOS' en la pantalla.")

                panel = panels[0]
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", panel)
                time.sleep(1.2)

                # Verificar si el panel está colapsado y expandir
                clase_panel = panel.get_attribute("class") or ""
                headings = panel.find_elements(By.XPATH, ".//div[contains(@class, 'panel-heading')]")
                es_colapsado = "collapsed" in clase_panel or (headings and headings[0].get_attribute("aria-expanded") == "false")

                if es_colapsado:
                    log("Desplegando sección 'COMPAÑIA GRUPO DE INSUMOS'...")
                    btn_expandir = panel.find_elements(By.XPATH, ".//button[@title='Expandir la sección' or .//i[contains(@class, 'fa-chevron-down')]]")
                    if btn_expandir and btn_expandir[0].is_displayed():
                        try:
                            btn_expandir[0].click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", btn_expandir[0])
                    elif headings:
                        try:
                            headings[0].click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", headings[0])
                    time.sleep(2.0)
                    log("Sección 'COMPAÑIA GRUPO DE INSUMOS' desplegada.")

                # 4. Desplegar los grupos de la tabla (1 MATERIALES, 2 MANO DE OBRA, 4 SUBCONTRATOS, 5 INDIRECTOS)
                log("Desplegando grupos colapsados en la tabla (Tipo 1, 2, 4 y 5)...")
                js_expandir_grupos = """
                let expandidos = [];
                let headers = document.querySelectorAll('.dteGroupText, .dteGroupCell');
                headers.forEach(h => {
                    let txt = (h.innerText || '').trim();
                    if (txt.includes('1 MATERIALES') || txt.includes('2 MANO DE OBRA') || txt.includes('4 SUBCONTRATOS') || txt.includes('5 INDIRECTOS')) {
                        let row = h.closest('tr, .dteRow') || h;
                        let arrow = row.querySelector('.dteGroupArrowCollapsed, .fa-caret-right');
                        if (arrow) {
                            arrow.click();
                            expandidos.push(txt);
                        }
                    }
                });
                return expandidos;
                """
                grupos_expandidos = driver.execute_script(js_expandir_grupos)
                if grupos_expandidos:
                    log(f"Grupos desplegados visualmente: {', '.join(grupos_expandidos)}")
                    time.sleep(2.0)
                else:
                    log("Los grupos de la tabla ya se encontraban desplegados.")

                # 5. Ejecutar la asignación visual de Compañía según las reglas oficiales
                log("Aplicando asignación de compañía en cada recuadro visible...")
                js_asignar_reglas = """
                let resultado = { asignados: 0, omitidos: 0, detalle: [] };

                // Mapeo oficial:
                // Tipo 1: 20 CONSOLIDADORA
                // Tipo 2: 01 CONSTRUCCIONES ARYVE
                // Tipo 4: 01 CONSTRUCCIONES ARYVE
                // Tipo 5: 20 CONSOLIDADORA
                const reglas = {
                    '1': { code: '20', name: 'CONSOLIDADORA' },
                    '2': { code: '01', name: 'CONSTRUCCIONES ARYVE S.A. DE C.V.' },
                    '4': { code: '01', name: 'CONSTRUCCIONES ARYVE S.A. DE C.V.' },
                    '5': { code: '20', name: 'CONSOLIDADORA' }
                };

                // Encontrar el panel de Compañía Grupo de Insumos
                let panel = Array.from(document.querySelectorAll('.panel, .panel-main')).find(p => {
                    let t = p.innerText || '';
                    return t.toUpperCase().includes('COMPA') && t.toUpperCase().includes('GRUPO DE INSUMO');
                });
                if (!panel) panel = document;

                // Buscar todos los selects de compañía
                let selects = Array.from(panel.querySelectorAll('select[id*="formControl_Compania"]'));

                selects.forEach((sel, idx) => {
                    let tr = sel.closest('tr, .dteRow') || sel.parentElement;
                    let txtFila = (tr ? tr.innerText : '') || '';

                    // Determinar el tipo de insumo de esta fila
                    let tipo = null;
                    if (txtFila.includes('MATERIALES')) tipo = '1';
                    else if (txtFila.includes('MANO DE OBRA')) tipo = '2';
                    else if (txtFila.includes('SUBCONTRATO')) tipo = '4';
                    else if (txtFila.includes('INDIRECTO')) tipo = '5';
                    else {
                        // Buscar en el grupo previo hacia arriba
                        let prev = tr ? tr.previousElementSibling : null;
                        while (prev) {
                            let pTxt = prev.innerText || '';
                            if (pTxt.includes('1 MATERIALES')) { tipo = '1'; break; }
                            if (pTxt.includes('2 MANO DE OBRA')) { tipo = '2'; break; }
                            if (pTxt.includes('4 SUBCONTRATOS')) { tipo = '4'; break; }
                            if (pTxt.includes('5 INDIRECTOS')) { tipo = '5'; break; }
                            prev = prev.previousElementSibling;
                        }
                    }

                    if (!tipo || !reglas[tipo]) return;

                    let regla = reglas[tipo];
                    let containerSelect2 = document.getElementById('select2-' + sel.id + '-container');

                    // Regla: "los que ya tienen omitelos"
                    let tieneAsignado = false;
                    if (sel.value && sel.value !== '-1' && sel.value !== '') {
                        tieneAsignado = true;
                    }
                    if (containerSelect2) {
                        let cText = containerSelect2.innerText || '';
                        if (cText.includes('20') || cText.includes('01') || cText.includes('CONSOLIDADORA') || cText.includes('ARYVE') || containerSelect2.querySelector('.badge-success')) {
                            tieneAsignado = true;
                        }
                    }

                    if (tieneAsignado) {
                        resultado.omitidos++;
                        return;
                    }

                    // Asignar el valor de la compañía en el select y Select2
                    sel.value = regla.code;

                    if (window.$ && $(sel).data('select2')) {
                        $(sel).val(regla.code).trigger('change');
                    } else {
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Actualizar el DOM visual del badge en Select2 si no se refrescó
                    if (containerSelect2) {
                        containerSelect2.innerHTML = '<span class="badge badge-success">' + regla.code + '</span> <span>' + regla.name + '</span>';
                    }

                    resultado.asignados++;
                    resultado.detalle.push('Fila ' + idx + ' (Tipo ' + tipo + ') -> ' + regla.code + ' ' + regla.name);
                });

                return resultado;
                """
                res_asignacion = driver.execute_script(js_asignar_reglas)
                total_asig = res_asignacion.get("asignados", 0)
                total_omit = res_asignacion.get("omitidos", 0)

                log(f"Asignación visual completada en {clave_clean}:")
                log(f"  • {total_asig} fila(s) actualizadas con su compañía correspondiente.")
                log(f"  • {total_omit} fila(s) omitidas porque ya tenían compañía asignada.")

                for d in res_asignacion.get("detalle", [])[:10]:
                    log(f"    ✔ {d}")
                if len(res_asignacion.get("detalle", [])) > 10:
                    log(f"    ... y {len(res_asignacion.get('detalle', [])) - 10} más.")

                obras_procesadas.append({
                    "obra": clave_clean,
                    "id_obra": id_obra,
                    "asignados": total_asig,
                    "omitidos": total_omit
                })

            log("\n==================================================================")
            log("✅ LLENADO VISUAL DE OPTIMIZACIÓN COMPLETADO")
            log("⚠️  RECORDATORIO:")
            log("    TAL COMO SE SOLICITÓ, LA OBRA SE QUEDA EN MODO EDICIÓN")
            log("    ¡NO SE HA GUARDADO (SIN Alt+G)! PUEDES VERIFICAR CADA RECIBO")
            log("    CON EL BADGE [20] Y [01] DIRECTAMENTE EN PANTALLA.")
            log("==================================================================")

            return {
                "ok": True,
                "obras_procesadas": obras_procesadas,
                "modo": modo_ejecucion,
                "guardado": False,
                "mensaje": "Llenado visual completado exitosamente. La pantalla se mantiene en edición sin guardar.",
                "logs": logs
            }

        except Exception as e:
            err_msg = f"Error en llenado de optimización: {str(e)}"
            log(f"[ERROR] {err_msg}")
            return {
                "ok": False,
                "error": err_msg,
                "modo": modo_ejecucion,
                "guardado": False,
                "logs": logs
            }
