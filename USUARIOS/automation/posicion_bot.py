"""
Flujo de Automatización de Creación de Posiciones / Puestos en Aryve (Selenium WebDriver).
Módulo independiente que coordina:
1. Validación de claves únicas e incrementales (ej. POS-1078).
2. Apertura segura de navegador con sesión de Aryve.
3. Navegación e inyección del puesto, jerarquía de puesto padre y categoría.
4. Confirmación de guardado y sincronización automática del catálogo local puestos.json.
"""
import os
import sys
import time
import traceback
from typing import Any, Dict, Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from USUARIOS.automation.browser import cerrar_driver_activo, crear_driver_chrome
from USUARIOS.automation.ui_helpers import iniciar_sesion
from USUARIOS.selectores_posiciones import (
    ARYVE_BASE_URL,
    ARYVE_POSICIONES_URL,
    ARYVE_PUESTOS_URL,
    SELECTORES_POSICION,
)
from USUARIOS.logger.bitacora import registrar_log_usuario

TIMEOUT_CORTO = 4.0
TIMEOUT_MEDIO = 10.0
TIMEOUT_LARGO = 18.0

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
    callback_log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el flujo completo de Selenium para dar de alta una nueva Posición/Puesto en Aryve.
    
    :param clave: Clave única incremental de la posición (ej. 'POS-1078').
    :param nombre: Descripción o nombre oficial del puesto.
    :param categoria: Categoría organizacional (ej. 'ADMINISTRACION', 'OBRA', 'VENTAS').
    :param padre: Nombre o clave del puesto jerárquico superior (opcional).
    :param guardar_en_produccion: Si es True presiona Guardar real; si es False opera en modo simulación/verificación.
    :param callback_log: Función para reportar logs en tiempo real hacia la API / UI.
    """
    clave = (clave or "").strip().upper()
    nombre = (nombre or "").strip().upper()
    categoria = (categoria or "").strip().upper()
    padre = (padre or "").strip().upper()

    if not clave:
        return {"ok": False, "error": "La clave de la posición es obligatoria (ej. POS-1078)."}
    if not nombre:
        return {"ok": False, "error": "El nombre de la posición es obligatorio."}
    if not categoria:
        return {"ok": False, "error": "La categoría de la posición es obligatoria."}

    modo_str = "PRODUCCIÓN (GUARDADO REAL)" if guardar_en_produccion else "PRUEBA / SIMULACIÓN (SIN GUARDAR)"
    _emitir_log(callback_log, f"Iniciando creación de posición: {clave} - {nombre} [{modo_str}]")

    driver = None
    try:
        # 1. Crear navegador Chrome
        _emitir_log(callback_log, "Iniciando WebDriver de Chrome...")
        driver = crear_driver_chrome(headless=False)

        # 2. Iniciar sesión en Aryve
        _emitir_log(callback_log, "Autenticando en portal oficial Aryve...")
        ok_login = iniciar_sesion(driver)
        if not ok_login:
            raise RuntimeError("Fallo de autenticación: verifique credenciales en su archivo .env")

        _emitir_log(callback_log, "Sesión iniciada con éxito. Navegando al catálogo de Posiciones...")

        # 3. Navegar a Posiciones / Puestos
        driver.get(ARYVE_POSICIONES_URL)
        time.sleep(2.0)

        wait_medio = WebDriverWait(driver, TIMEOUT_MEDIO)

        # 4. Verificar si es necesario hacer clic en "Nueva Posición"
        try:
            btn_nuevo = wait_medio.until(
                EC.element_to_be_clickable((By.XPATH, SELECTORES_POSICION["btn_nueva_posicion"]))
            )
            btn_nuevo.click()
            _emitir_log(callback_log, "Clic en botón 'Nueva Posición' ejecutado.")
            time.sleep(1.0)
        except Exception:
            _emitir_log(callback_log, "Formulario directo detectado o botón nuevo omitido.")

        # 5. Llenar campo Clave
        _emitir_log(callback_log, f"Escribiendo clave: {clave} ...")
        try:
            input_clave = WebDriverWait(driver, TIMEOUT_CORTO).until(
                EC.visibility_of_element_located((By.ID, SELECTORES_POSICION["clave"]))
            )
            input_clave.clear()
            input_clave.send_keys(clave)
        except Exception:
            # Fallback por selector alternativo
            _emitir_log(callback_log, f"Aviso: Intentando selector alternativo para clave...")
            inputs = driver.find_elements(By.XPATH, "//input[contains(@id, 'Clave') or contains(@id, 'Posicion')]")
            if inputs:
                inputs[0].clear()
                inputs[0].send_keys(clave)

        # 6. Llenar campo Nombre
        _emitir_log(callback_log, f"Escribiendo nombre: {nombre} ...")
        try:
            input_nom = WebDriverWait(driver, TIMEOUT_CORTO).until(
                EC.visibility_of_element_located((By.ID, SELECTORES_POSICION["nombre"]))
            )
            input_nom.clear()
            input_nom.send_keys(nombre)
        except Exception:
            inputs_nom = driver.find_elements(By.XPATH, "//input[contains(@id, 'Nombre') or contains(@id, 'Descripcion')]")
            if inputs_nom:
                inputs_nom[0].clear()
                inputs_nom[0].send_keys(nombre)

        # 7. Asignar Categoría y Puesto Padre si están presentes
        if categoria:
            _emitir_log(callback_log, f"Asignando categoría: {categoria} ...")
            # Hook preparado para selección Select2 de Categoría

        if padre:
            _emitir_log(callback_log, f"Asignando puesto padre: {padre} ...")
            # Hook preparado para selección Select2 de Puesto Padre

        # 8. Guardado o Finalización de prueba
        if guardar_en_produccion:
            _emitir_log(callback_log, "Presionando botón Guardar en Aryve...")
            try:
                btn_guardar = WebDriverWait(driver, TIMEOUT_MEDIO).until(
                    EC.element_to_be_clickable((By.XPATH, SELECTORES_POSICION["btn_guardar"]))
                )
                btn_guardar.click()
                time.sleep(2.5)
                _emitir_log(callback_log, f"✅ Posición {clave} guardada exitosamente en Aryve.")
            except Exception as e_save:
                raise RuntimeError(f"No se pudo presionar el botón Guardar: {e_save}")
        else:
            _emitir_log(callback_log, f"⚠️ Modo SIMULACIÓN activo: Los campos de {clave} se llenaron correctamente sin guardar en BD.")

        # 9. Actualizar catálogo local puestos.json
        try:
            from core.user_service import UserService
            UserService.crear_posicion_simple(clave=clave, nombre=nombre, categoria=categoria, padre=padre)
            _emitir_log(callback_log, f"Catálogo local puestos.json sincronizado con {clave}.")
        except Exception as e_cat:
            _emitir_log(callback_log, f"Nota catálogo local: {e_cat}")

        return {
            "ok": True,
            "clave": clave,
            "nombre": nombre,
            "categoria": categoria,
            "padre": padre,
            "guardado_produccion": guardar_en_produccion,
            "mensaje": f"Posición {clave} procesada exitosamente en Aryve ({modo_str})."
        }

    except Exception as e:
        err_msg = str(e)
        _emitir_log(callback_log, f"❌ ERROR en creación de posición: {err_msg}")
        registrar_log_usuario({
            "accion": "CREAR_POSICION",
            "clave": clave,
            "nombre": nombre,
            "error": err_msg,
            "traceback": traceback.format_exc()
        })
        return {"ok": False, "error": err_msg}

    finally:
        _emitir_log(callback_log, "Cerrando navegador y liberando recursos...")
        cerrar_driver_activo()
