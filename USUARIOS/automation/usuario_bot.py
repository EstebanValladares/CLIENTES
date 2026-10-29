"""
Flujo de Automatización de Usuarios en Aryve (Selenium WebDriver).
Coordina:
1. Alta completa de nuevo usuario (Datos generales, niveles, grupos, clasificadores, verificación QA y guardado).
2. Asignación directa de clasificadores para usuarios existentes por ID.
"""
import re
import time
import traceback
from typing import Any, Dict, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from USUARIOS.automation.browser import cerrar_driver_activo, crear_driver_chrome
from USUARIOS.automation.ui_helpers import (
    abrir_panel,
    buscar_y_marcar_clasificador_hijo,
    cancelar_y_cerrar_panel,
    guardar_y_cerrar_panel,
    iniciar_sesion,
    leer_contador_panel,
    obtener_panel_seccion,
    seleccionar_opcion_menu,
)
from USUARIOS.logger.bitacora import (
    limpiar_fallos_resueltos,
    registrar_fallo_clasificador,
    registrar_log_usuario,
)
from USUARIOS.puestos_service import (
    es_clasificador_omitido,
    extraer_padres_e_hijos,
    obtener_campo,
    obtener_configuracion_puesto,
)
from USUARIOS.selectores import (
    ARYVE_BASE_URL,
    ARYVE_NUEVO_USUARIO_URL,
    ID_SIMULADO_PRUEBA,
    POLL_INTERVAL_RAPIDO,
    SELECTORES,
    TIMEOUT_CORTO,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
    obtener_url_perfil_usuario,
)


# ==============================================================================
# SUB-FLUJOS ESPECÍFICOS DE PANELES
# ==============================================================================

def asignar_niveles(driver: Any, compania_texto: str, nivel_texto: str) -> bool:
    """Abre panel NIVELES ASIGNADOS, selecciona compañía y nivel y guarda."""
    if not abrir_panel(driver, "NIVELES ASIGNADOS"):
        return False
    time.sleep(0.2)
    exito_comp = seleccionar_opcion_menu(driver, SELECTORES["caja_compania"], compania_texto, "NIVELES")
    exito_niv = seleccionar_opcion_menu(driver, SELECTORES["caja_nivel"], nivel_texto, "NIVELES")
    if exito_comp and exito_niv:
        return guardar_y_cerrar_panel(driver, "NIVELES ASIGNADOS", SELECTORES["btn_guardar_niveles"])
    cancelar_y_cerrar_panel(driver, "NIVELES ASIGNADOS")
    return False


def asignar_grupos(driver: Any, nombre_grupo: str) -> bool:
    """Abre panel GRUPOS, selecciona el grupo y guarda."""
    if not abrir_panel(driver, "GRUPOS"):
        return False
    time.sleep(0.2)
    exito = seleccionar_opcion_menu(driver, SELECTORES["caja_grupo"], nombre_grupo, "GRUPOS")
    if exito:
        return guardar_y_cerrar_panel(driver, "GRUPOS", SELECTORES["btn_guardar_grupos"])
    cancelar_y_cerrar_panel(driver, "GRUPOS")
    return False


def asignar_clasificadores(
    driver: Any,
    clasificadores_dict: dict[str, Any],
    puesto_nombre: str = "",
) -> None:
    """Asigna todos los bloques padre/hijos en el panel CLASIFICADORES."""
    if not clasificadores_dict:
        return

    pares = extraer_padres_e_hijos(clasificadores_dict)
    if not pares:
        return

    print(f"\n--- Asignando {len(pares)} bloque(s) de clasificadores ---")
    for idx, (nombre_padre, lista_hijos) in enumerate(pares, start=1):
        if es_clasificador_omitido(nombre_padre):
            print(f" -> Omitiendo clasificador protegido: '{nombre_padre}'")
            continue

        print(f"\n  -> Bloque [{idx}/{len(pares)}]: Padre='{nombre_padre}' ({len(lista_hijos)} hijo(s))")

        try:
            if not abrir_panel(driver, "CLASIFICADORES"):
                print("[ERROR]: No se pudo desplegar el panel CLASIFICADORES.")
                continue

            time.sleep(0.4)

            # Seleccionar tipo padre
            caja_tipo = SELECTORES.get("caja_tipo_clasificador", "select2-formControl_TipoClasificador-container")
            exito_tipo = seleccionar_opcion_menu(driver, caja_tipo, nombre_padre, "CLASIFICADORES")
            if not exito_tipo:
                p = obtener_panel_seccion(driver, "CLASIFICADORES")
                if p:
                    try:
                        caja_sp = p.find_element(By.XPATH, ".//span[contains(@class, 'select2-selection')]")
                        exito_tipo = seleccionar_opcion_menu(driver, caja_sp, nombre_padre, "CLASIFICADORES")
                    except Exception:
                        pass

            if not exito_tipo:
                print(f"[ALERTA]: No se pudo seleccionar '{nombre_padre}'. Cancelando panel...")
                registrar_fallo_clasificador(
                    puesto_nombre, nombre_padre, "TODOS", "No se pudo seleccionar en el desplegable"
                )
                cancelar_y_cerrar_panel(driver, "CLASIFICADORES")
                continue

            # Esperar tabla DevExtreme
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'dx-datagrid')]"))
                )
                time.sleep(0.3)
            except Exception:
                time.sleep(0.8)

            # Marcar hijos
            for hijo in lista_hijos:
                hijo_limpio = str(hijo).strip()
                if not hijo_limpio:
                    continue
                ok_hijo = buscar_y_marcar_clasificador_hijo(driver, hijo_limpio)
                if not ok_hijo:
                    registrar_fallo_clasificador(
                        puesto_nombre, nombre_padre, hijo_limpio, "Hijo no encontrado en la tabla"
                    )

            # Guardar panel
            guardar_y_cerrar_panel(
                driver, "CLASIFICADORES", SELECTORES.get("btn_guardar_clasificadores", "Clasificadores_saveButtonKey")
            )
            time.sleep(0.3)
        except Exception as err:
            print(f"[ERROR CLASIFICADORES]: {err}")
            cancelar_y_cerrar_panel(driver, "CLASIFICADORES")


def guardar_usuario_general(driver: Any) -> tuple[bool, str]:
    """Presiona el botón global de guardar usuario y extrae el nuevo ID numérico generado."""
    print("Guardando usuario en producción...")
    try:
        btn_guardar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@id='btnSubmit' or @type='submit' or contains(text(), 'Guardar') or contains(@class, 'btn-guardar')]")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_guardar)
        time.sleep(0.2)
        try:
            btn_guardar.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_guardar)

        for _ in range(30):
            time.sleep(0.5)
            url_actual = driver.current_url
            m = re.search(r"/usuarios/(\d+)", url_actual)
            if m:
                id_nuevo = m.group(1)
                print(f"¡Usuario guardado con ÉXITO en Aryve! ID: {id_nuevo}")
                return True, id_nuevo
        return False, ""
    except Exception as e:
        print(f"[ERROR GUARDAR GLOBAL]: {e}")
        return False, ""


# ==============================================================================
# FLUJO 1: ALTA COMPLETA DE NUEVO USUARIO
# ==============================================================================

def llenar_formulario_usuario(
    driver: Any,
    datos: dict[str, Any],
    guardar_en_produccion: bool = False,
) -> bool:
    """Llena todos los campos del formulario de usuario, niveles, grupos y clasificadores."""
    puesto_nom = obtener_campo(datos, "Posicion", "posicion", "puesto")
    puesto_cfg = obtener_configuracion_puesto(puesto_nom)

    # 1. Campos de texto básicos
    campos = [
        (SELECTORES["nombre"], obtener_campo(datos, "Nombre", "nombre"), "Nombre"),
        (SELECTORES["apellidos"], obtener_campo(datos, "Apellidos", "apellidos"), "Apellidos"),
        (SELECTORES["clave"], obtener_campo(datos, "Clave", "clave"), "Clave"),
        (SELECTORES["correo"], obtener_campo(datos, "Correo", "correo", "Email", "email"), "Correo"),
        (SELECTORES["telefono"], obtener_campo(datos, "Telefono", "telefono"), "Teléfono"),
        (SELECTORES["inicio"], obtener_campo(datos, "Inicio", "inicio"), "Inicio"),
        (SELECTORES["fin"], obtener_campo(datos, "Fin", "fin"), "Fin"),
    ]

    for id_campo, val, etiqueta in campos:
        if val:
            try:
                el = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.ID, id_campo)))
                el.clear()
                el.send_keys(val)
            except Exception as e:
                print(f"Error escribiendo '{etiqueta}': {e}")

    # 2. Casilla Activo
    try:
        chk = driver.find_element(By.ID, SELECTORES["estatus_activo"])
        if not chk.is_selected():
            driver.execute_script("arguments[0].click();", chk)
    except Exception:
        pass

    # 3. Posición
    if puesto_cfg.nombre_puesto:
        seleccionar_opcion_menu(driver, SELECTORES["caja_posicion"], puesto_cfg.nombre_puesto, "POSICION")

    # 4. Regional
    tz = obtener_campo(datos, "ZonaHoraria", "zonahoraria")
    lang = obtener_campo(datos, "Idioma", "idioma")
    if tz:
        seleccionar_opcion_menu(driver, SELECTORES["caja_timezone"], tz, "ZONA HORARIA")
    if lang:
        seleccionar_opcion_menu(driver, SELECTORES["caja_idioma"], lang, "IDIOMA")

    # 5. Niveles
    for n in puesto_cfg.niveles_asignados:
        cia = n.get("compania", "")
        niv = n.get("nivel", "")
        if cia and niv:
            asignar_niveles(driver, cia, niv)

    # 6. Grupos
    for g in puesto_cfg.grupos:
        if g:
            asignar_grupos(driver, g)

    # 7. Clasificadores
    if puesto_cfg.clasificadores:
        asignar_clasificadores(driver, puesto_cfg.clasificadores, puesto_nombre=puesto_cfg.nombre_puesto)

    # 8. Guardado y Bitácora
    if guardar_en_produccion:
        ok_save, id_gen = guardar_usuario_general(driver)
        if ok_save:
            registrar_log_usuario(
                driver,
                datos,
                id_forzado=id_gen,
                url_forzada=obtener_url_perfil_usuario(id_gen),
            )
            return True
        return False
    else:
        registrar_log_usuario(
            driver,
            datos,
            id_forzado=ID_SIMULADO_PRUEBA,
            url_forzada=obtener_url_perfil_usuario(ID_SIMULADO_PRUEBA),
        )
        return True


def ejecutar_alta_usuario(
    datos_empleado: dict[str, Any],
    guardar_en_produccion: bool = False,
    usuario: str | None = None,
    password: str | None = None,
    on_driver_created: Any = None,
) -> tuple[bool, str]:
    """Orquesta la apertura de Chrome, login, llenado completo y guardado."""
    nom = f"{datos_empleado.get('Nombre', '')} {datos_empleado.get('Apellidos', '')}".strip()
    driver = None
    try:
        driver, _ = crear_driver_chrome(detach=True, maximizar=True, on_driver_created=on_driver_created)
        driver.get(ARYVE_BASE_URL)
        iniciar_sesion(driver, usuario, password)

        # Navegar al formulario de nuevo usuario
        driver.get(ARYVE_NUEVO_USUARIO_URL)
        try:
            WebDriverWait(driver, 10, poll_frequency=POLL_INTERVAL_RAPIDO).until(
                EC.element_to_be_clickable((By.ID, SELECTORES["nombre"]))
            )
        except Exception:
            time.sleep(2.0)

        ok = llenar_formulario_usuario(driver, datos_empleado, guardar_en_produccion=guardar_en_produccion)
        if ok:
            msg = f"Alta de '{nom}' completada exitosamente. (Modo producción: {guardar_en_produccion})"
            return True, msg
        return False, f"El proceso de alta de '{nom}' no pudo completarse."
    except Exception as err:
        err_msg = f"Error durante el llenado de '{nom}': {err}"
        traceback.print_exc()
        return False, err_msg


# ==============================================================================
# FLUJO 2: ASIGNACIÓN DE CLASIFICADORES A USUARIO EXISTENTE
# ==============================================================================

def ejecutar_asignacion_clasificadores(
    id_usuario: str,
    clasificadores_dict: Dict[str, Any],
    puesto: str = "",
    nombre_usuario: str = "",
    usuario: Optional[str] = None,
    password: Optional[str] = None,
    on_driver_created: Optional[Any] = None,
) -> Tuple[bool, str]:
    """Abre el perfil del usuario id_usuario, entra a modo edición y asigna clasificadores."""
    if not id_usuario or str(id_usuario).strip() in ["", "0", "None"]:
        return False, "ID de usuario inválido o no especificado."

    if not clasificadores_dict:
        return False, "No se recibieron clasificadores para asignar."

    print(f"\n=== Asignando clasificadores a Usuario #{id_usuario} ({puesto}) ===")
    driver = None
    try:
        driver, _ = crear_driver_chrome(detach=True, maximizar=True, on_driver_created=on_driver_created)
        driver.get(ARYVE_BASE_URL)
        iniciar_sesion(driver, usuario, password)

        # Navegar directo al perfil del usuario
        url_destino = obtener_url_perfil_usuario(id_usuario)
        driver.get(url_destino)
        time.sleep(2.5)

        # Clic en Editar
        btn_edit = WebDriverWait(driver, 12).until(
            EC.element_to_be_clickable((By.XPATH, SELECTORES["btn_editar_usuario"]))
        )
        btn_edit.click()
        time.sleep(1.5)

        # Asignar clasificadores
        asignar_clasificadores(driver, clasificadores_dict, puesto_nombre=f"ID #{id_usuario} {puesto}")

        # Guardar cambios
        guardar_usuario_general(driver)
        time.sleep(1.0)

        if nombre_usuario:
            limpiar_fallos_resueltos(nombre_usuario)

        return True, f"Clasificadores asignados exitosamente al usuario #{id_usuario}."
    except Exception as e:
        err_msg = f"Error en asignación de clasificadores para #{id_usuario}: {e}"
        print(f"[ERROR]: {err_msg}")
        traceback.print_exc()
        return False, err_msg

