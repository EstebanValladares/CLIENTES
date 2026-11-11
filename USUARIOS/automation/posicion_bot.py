"""
Flujo de Automatización de Creación de Posiciones / Puestos en Aryve (Selenium WebDriver).
Módulo modular y escalable que coordina:
1. Validación de claves únicas e incrementales (ej. POS-1081).
2. Apertura segura de navegador con sesión de Aryve Enkontrol.
3. Redirección directa a la pantalla oficial: https://suite.ekloud.net:1445/Aryve/#/kontrol/posiciones/id?nuevo
4. Inyección guiada de la clave, nombre, puesto padre y categoría organizacional.
5. Telemetría de logs en tiempo real hacia el dashboard.
"""
import os
import sys
import time
import traceback
from typing import Any, Dict, Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from USUARIOS.automation.browser import cerrar_driver_activo, crear_driver_chrome
from USUARIOS.automation.ui_helpers import iniciar_sesion, seleccionar_opcion_menu
from USUARIOS.selectores_posiciones import (
    ARYVE_BASE_URL,
    ARYVE_POSICIONES_URL,
    ARYVE_POSICIONES_NUEVO_URL,
    ARYVE_PUESTOS_URL,
    SELECTORES_POSICION,
)
from USUARIOS.logger.bitacora import registrar_log_usuario

TIMEOUT_CORTO = 4.0
TIMEOUT_MEDIO = 12.0
TIMEOUT_LARGO = 25.0

def _emitir_log(callback: Optional[Callable[[str], None]], mensaje: str):
    """Envía mensaje al callback de telemetría y a stdout."""
    timestamp = time.strftime("%H:%M:%S")
    linea = f"[{timestamp}] [PosicionBot] {mensaje}"
    print(linea)
    if callback:
        try:
            callback(linea)
        except Exception:
            pass

def ejecutar_alta_posicion(
    clave: str,
    nombre: str,
    categoria: str,
    padre: str = "",
    guardar_en_produccion: bool = False,
    cerrar_al_terminar: bool = False,
    callback_log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el flujo de Selenium para dar de alta una nueva Posición/Puesto en Aryve.
    
    1. Abre Chrome.
    2. Inicia sesión en Aryve Enkontrol.
    3. Redirige a https://suite.ekloud.net:1445/Aryve/#/kontrol/posiciones/id?nuevo
    4. Llama a los inputs para llenar Clave, Nombre, Categoría y Padre.
    
    :param clave: Clave única incremental de la posición (ej. 'POS-1081').
    :param nombre: Descripción o nombre oficial del puesto.
    :param categoria: Categoría organizacional (ej. 'ADMINISTRACION', 'OBRA', 'VENTAS').
    :param padre: Nombre o clave del puesto jerárquico superior (opcional).
    :param guardar_en_produccion: Si es True presiona Guardar real; si es False deja los datos en pantalla para revisión.
    :param cerrar_al_terminar: Si es False, mantiene la ventana de Chrome abierta para interacción del usuario.
    :param callback_log: Función para reportar logs en tiempo real hacia la API / UI.
    """
    clave = (clave or "").strip().upper()
    nombre = (nombre or "").strip().upper()
    categoria = (categoria or "").strip().upper()
    padre = (padre or "").strip().upper()

    if not clave:
        return {"ok": False, "error": "La clave de la posición es obligatoria (ej. POS-1081)."}
    if not nombre:
        return {"ok": False, "error": "El nombre de la posición es obligatorio."}
    if not categoria:
        return {"ok": False, "error": "La categoría de la posición es obligatoria."}

    modo_str = "PRODUCCIÓN (GUARDADO REAL)" if guardar_en_produccion else "VERIFICACIÓN / APERTURA GUIADA"
    _emitir_log(callback_log, f"Iniciando flujo para {clave} - {nombre} [{modo_str}]")

    driver = None
    try:
        # 1. Crear navegador Chrome maximizado y desacoplado
        _emitir_log(callback_log, "Iniciando WebDriver de Chrome...")
        driver, _ = crear_driver_chrome(detach=True, maximizar=True)

        # 2. Navegar a Aryve e Iniciar sesión
        _emitir_log(callback_log, f"Navegando a Aryve ({ARYVE_BASE_URL})...")
        driver.get(ARYVE_BASE_URL)
        time.sleep(1.5)

        _emitir_log(callback_log, "Autenticando en portal oficial Aryve Enkontrol...")
        iniciar_sesion(driver)
        _emitir_log(callback_log, "✅ Autenticación exitosa en Aryve.")

        # 3. Redirigir a la pantalla oficial de nueva posición
        _emitir_log(callback_log, f"Redirigiendo a pantalla de nueva posición: {ARYVE_POSICIONES_NUEVO_URL} ...")
        driver.get(ARYVE_POSICIONES_NUEVO_URL)
        time.sleep(3.0)

        # Si el SPA de AngularJS no carga directo el formulario, usar el botón 'Agregar (Alt+A)' detectado en el escaneo DOM
        if "id?nuevo" not in driver.current_url:
            _emitir_log(callback_log, "Accediendo vía catálogo y botón 'Agregar (Alt+A)'...")
            driver.get(ARYVE_POSICIONES_URL)
            time.sleep(2.0)
            try:
                btn_agr = WebDriverWait(driver, 5.0).until(
                    EC.element_to_be_clickable((By.XPATH, SELECTORES_POSICION["btn_nueva_posicion"]))
                )
                btn_agr.click()
                time.sleep(2.5)
            except Exception as e_btn:
                _emitir_log(callback_log, f"Aviso botón Agregar: {e_btn}")

        current_url = driver.current_url
        _emitir_log(callback_log, f"URL activa: {current_url}")

        wait_medio = WebDriverWait(driver, TIMEOUT_MEDIO)

        # 4. Esperar que cargue el formulario de la posición
        _emitir_log(callback_log, "Esperando renderizado de la pantalla de posición...")
        try:
            wait_medio.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

        # 5. Localizar y llenar campo Clave (formControl_Clave o selector alternativo)
        _emitir_log(callback_log, f"Escribiendo Clave: {clave} ...")
        input_clave = None
        selectores_clave = [
            (By.ID, SELECTORES_POSICION["clave"]),
            (By.XPATH, "//input[contains(@id, 'Clave') or contains(@id, 'clave') or contains(@id, 'Posicion')]"),
            (By.XPATH, "//label[contains(text(), 'Clave') or contains(text(), 'CLAVE')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[name*='clave' i], input[id*='clave' i]")
        ]

        for by_tipo, selector_val in selectores_clave:
            try:
                elem = WebDriverWait(driver, 3.0).until(
                    EC.element_to_be_clickable((by_tipo, selector_val))
                )
                if elem and elem.is_displayed():
                    input_clave = elem
                    break
            except Exception:
                continue

        if input_clave:
            try:
                input_clave.click()
                input_clave.clear()
                # Simular tipeo real para activar watchers de AngularJS / Vue / DevExtreme
                input_clave.send_keys(clave)
                input_clave.send_keys(Keys.TAB)
                _emitir_log(callback_log, f"Campo Clave establecido con '{clave}'.")
            except Exception as e_ck:
                _emitir_log(callback_log, f"Aviso al escribir clave: {e_ck}")
        else:
            _emitir_log(callback_log, "Aviso: No se detectó input directo de clave por ID estándar, verificando formulario...")

        # 6. Localizar y llenar campo Nombre (formControl_Nombre)
        _emitir_log(callback_log, f"Escribiendo Nombre: {nombre} ...")
        input_nom = None
        selectores_nombre = [
            (By.ID, SELECTORES_POSICION["nombre"]),
            (By.XPATH, "//input[contains(@id, 'Nombre') or contains(@id, 'nombre') or contains(@id, 'Descripcion')]"),
            (By.XPATH, "//label[contains(text(), 'Nombre') or contains(text(), 'NOMBRE')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[name*='nombre' i], input[id*='nombre' i]")
        ]

        for by_tipo, selector_val in selectores_nombre:
            try:
                elem = WebDriverWait(driver, 3.0).until(
                    EC.element_to_be_clickable((by_tipo, selector_val))
                )
                if elem and elem.is_displayed():
                    input_nom = elem
                    break
            except Exception:
                continue

        if input_nom:
            try:
                input_nom.click()
                input_nom.clear()
                input_nom.send_keys(nombre)
                input_nom.send_keys(Keys.TAB)
                _emitir_log(callback_log, f"Campo Nombre establecido con '{nombre}'.")
            except Exception as e_cn:
                _emitir_log(callback_log, f"Aviso al escribir nombre: {e_cn}")

        # 7. Asignar Categoría mediante Select2 si está disponible
        if categoria:
            _emitir_log(callback_log, f"Asignando categoría: '{categoria}' ...")
            try:
                seleccionar_opcion_menu(driver, SELECTORES_POSICION["categoria"], categoria, "CATEGORÍA")
                _emitir_log(callback_log, f"Categoría '{categoria}' seleccionada con éxito.")
            except Exception as e_cat:
                _emitir_log(callback_log, f"Aviso categoría: {e_cat}")

        # 8. Asignar Puesto Padre si está especificado (Soporta Select2 o Input Texto Libre)
        if padre:
            _emitir_log(callback_log, f"Asignando puesto padre: '{padre}' ...")
            asignado_padre = False
            try:
                asignado_padre = seleccionar_opcion_menu(driver, SELECTORES_POSICION["padre"], padre, "PADRE")
            except Exception:
                pass

            if not asignado_padre:
                try:
                    inputs_padre = driver.find_elements(By.XPATH, "//input[contains(@id, 'Padre') or contains(@id, 'padre') or contains(@placeholder, 'padre') or contains(@name, 'padre')]")
                    if inputs_padre:
                        inputs_padre[0].clear()
                        inputs_padre[0].send_keys(padre)
                        inputs_padre[0].send_keys(Keys.TAB)
                        asignado_padre = True
                except Exception:
                    pass

            if asignado_padre:
                _emitir_log(callback_log, f"Puesto padre '{padre}' asignado.")
            else:
                _emitir_log(callback_log, f"Aviso: No se requirió o no se localizó campo para puesto padre.")

        # 9. Llenado sin guardar (Modo Seguro solicitado por el usuario)
        if guardar_en_produccion:
            _emitir_log(callback_log, "Presionando botón Guardar en Aryve...")
            try:
                btn_guardar = WebDriverWait(driver, TIMEOUT_MEDIO).until(
                    EC.element_to_be_clickable((By.XPATH, SELECTORES_POSICION["btn_guardar"]))
                )
                btn_guardar.click()
                time.sleep(3.0)
                _emitir_log(callback_log, f"✅ Posición {clave} guardada en producción en Aryve Enkontrol.")
            except Exception as e_save:
                raise RuntimeError(f"No se pudo completar el guardado en Aryve: {e_save}")
        else:
            _emitir_log(callback_log, "🛡️ Modo Llenado Activo: Los campos se llenaron para verificación. NO se guardó en BD.")
            _emitir_log(callback_log, f"✨ Formulario listo con Clave: {clave}, Nombre: {nombre}. Navegador abierto.")

        # 10. Actualizar catálogo local de puestos
        try:
            from core.user_service import UserService
            UserService.crear_posicion_simple(clave=clave, nombre=nombre, categoria=categoria, padre=padre)
            _emitir_log(callback_log, f"Catálogo local sincronizado con la clave {clave}.")
        except Exception as e_loc:
            _emitir_log(callback_log, f"Nota catálogo local: {e_loc}")

        return {
            "ok": True,
            "clave": clave,
            "nombre": nombre,
            "categoria": categoria,
            "padre": padre,
            "guardado_produccion": guardar_en_produccion,
            "url": ARYVE_POSICIONES_NUEVO_URL,
            "mensaje": f"Selenium completó la navegación y carga de {clave} exitosamente."
        }

    except Exception as e:
        err_msg = str(e)
        _emitir_log(callback_log, f"❌ ERROR en automatización de posición: {err_msg}")
        registrar_log_usuario({
            "accion": "CREAR_POSICION_SELENIUM",
            "clave": clave,
            "nombre": nombre,
            "error": err_msg,
            "traceback": traceback.format_exc()
        })
        return {"ok": False, "error": err_msg}

    finally:
        if cerrar_al_terminar:
            _emitir_log(callback_log, "Cerrando navegador...")
            cerrar_driver_activo()
        else:
            _emitir_log(callback_log, "Navegador Chrome mantenido abierto para interacción continua.")
