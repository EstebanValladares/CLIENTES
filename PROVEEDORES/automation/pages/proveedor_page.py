"""
Page Object del formulario de Alta / Creación de Proveedores en Aryve.
Reemplaza esperas fijas prolongadas por esperas reactivas sobre los selectores reales del DOM.
"""
import re
import time
from typing import Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from automation.browser import BasePage
from config.selectors import ProveedorFormSelectors
from config.settings import (
    PAUSA_ESTABILIZACION,
    PAUSA_MICRO,
    PAUSA_PANEL,
    PAUSA_REMOTA_SELECT2,
    POLL_INTERVAL_RAPIDO,
    TIMEOUT_CORTO,
    TIMEOUT_GUARDADO,
    TIMEOUT_LARGO,
    TIMEOUT_MEDIO,
    URL_NUEVO_PROVEEDOR,
)
from domain.generador_claves import normalizar_alfanumerico
from domain.models import ProveedorData


class ProveedorPage(BasePage):
    """Encapsula todas las interacciones del formulario de Nuevo Proveedor en Aryve."""

    def abrir_formulario_nuevo(self, url: str = URL_NUEVO_PROVEEDOR) -> None:
        """Navega a la URL de nuevo proveedor y espera reactivamente al selector de Tipo de Persona."""
        self.logger.info(f"Navegando a: {url}")
        self.driver.get(url)
        self.esperar_presente(ProveedorFormSelectors.BODY, timeout=TIMEOUT_GUARDADO)
        self.esperar_fin_carga(timeout=TIMEOUT_MEDIO, pausa_extra=PAUSA_ESTABILIZACION)
        try:
            self.esperar_presente(
                ProveedorFormSelectors.CAJA_TIPO_PERSONA,
                timeout=TIMEOUT_GUARDADO,
            )
            time.sleep(PAUSA_ESTABILIZACION)
        except Exception:
            # Respaldo en caso de que el contenedor tarde en montarse en React
            time.sleep(1.5)

    def seleccionar_tipo_persona(self, tipo: str = "MORAL") -> bool:
        """
        Selecciona 'MORAL' o 'FÍSICA' en el campo Select2 de TIPO DE PERSONA.
        Si ya tiene el valor seleccionado, omite abrir el desplegable.
        """
        self.logger.info(f"Seleccionando Tipo de Persona: '{tipo}'...")
        caja_rendered = self.esperar_presente(
            ProveedorFormSelectors.CAJA_TIPO_PERSONA,
            timeout=TIMEOUT_LARGO,
        )

        texto_actual = normalizar_alfanumerico(
            caja_rendered.text or caja_rendered.get_attribute("textContent") or ""
        )
        if texto_actual == normalizar_alfanumerico(tipo):
            self.logger.info(f"Tipo de Persona ya se encuentra en '{tipo}'.")
            return True

        self.click_seguro(caja_rendered)
        time.sleep(PAUSA_ESTABILIZACION)

        locator_opcion = ProveedorFormSelectors.opcion_select2_por_texto(tipo)
        try:
            opcion = self.esperar_clicable(locator_opcion, timeout=TIMEOUT_MEDIO)
            opcion.click()
        except Exception:
            opcion = self.driver.find_element(*locator_opcion)
            self.click_js(opcion)

        time.sleep(PAUSA_ESTABILIZACION)
        self.logger.info(f"¡'{tipo}' seleccionado exitosamente en TIPO DE PERSONA!")
        return True

    def avanzar_siguiente_panel(self) -> bool:
        """
        Presiona la flecha '->' del panel TIPO DE PERSONA para confirmar y desplegar
        los campos generales del proveedor, esperando reactivamente a `#formControl_Clave`.
        """
        self.logger.info("Avanzando al siguiente panel con la flecha...")
        try:
            btn_flecha = self.esperar_clicable(
                ProveedorFormSelectors.BTN_AVANZAR_PANEL,
                timeout=TIMEOUT_MEDIO,
            )
            self.click_seguro(btn_flecha)

            # Esperar reactivamente a que el campo Clave sea interactuable en lugar de dormir fijo
            try:
                self.esperar_clicable(
                    ProveedorFormSelectors.INPUT_CLAVE,
                    timeout=TIMEOUT_CORTO,
                )
            except Exception:
                time.sleep(PAUSA_PANEL)

            self.logger.info("Avanzado con éxito.")
            return True
        except Exception as e:
            self.logger.aviso(f"No se pudo hacer clic en la flecha de avance: {e}")
            return False

    def escribir_clave(self, clave_texto: str) -> bool:
        return self.escribir_campo_reactivo(
            ProveedorFormSelectors.INPUT_CLAVE,
            clave_texto,
            etiqueta="Clave",
        )

    def escribir_nombre(self, nombre_texto: str) -> bool:
        return self.escribir_campo_reactivo(
            ProveedorFormSelectors.INPUT_NOMBRE,
            nombre_texto,
            etiqueta="Nombre completo",
        )

    def escribir_apellido_paterno(self, paterno_texto: str) -> bool:
        return self.escribir_campo_con_candidatos(
            ProveedorFormSelectors.IDS_APELLIDO_PATERNO,
            ProveedorFormSelectors.XPATH_APELLIDO_PATERNO_FALLBACK,
            paterno_texto,
            etiqueta="Apellido Paterno",
        )

    def escribir_apellido_materno(self, materno_texto: str) -> bool:
        return self.escribir_campo_con_candidatos(
            ProveedorFormSelectors.IDS_APELLIDO_MATERNO,
            ProveedorFormSelectors.XPATH_APELLIDO_MATERNO_FALLBACK,
            materno_texto,
            etiqueta="Apellido Materno",
        )

    def escribir_rfc(self, rfc_texto: str) -> bool:
        return self.escribir_campo_reactivo(
            ProveedorFormSelectors.INPUT_RFC,
            rfc_texto,
            etiqueta="RFC",
        )

    def escribir_nombre_corto(self, nombre_corto_texto: str) -> bool:
        return self.escribir_campo_reactivo(
            ProveedorFormSelectors.INPUT_NOMBRE_CORTO,
            nombre_corto_texto,
            etiqueta="Nombre Corto",
        )

    def marcar_obliga_cfdi(self) -> bool:
        return self.marcar_checkbox_reactivo(
            ProveedorFormSelectors.ID_OBLIGA_CFDI,
            etiqueta="Obliga CFDI",
        )

    def marcar_factoraje(self) -> bool:
        return self.marcar_checkbox_reactivo(
            ProveedorFormSelectors.ID_FACTORAJE,
            etiqueta="Factoraje",
        )

    def escribir_domicilio(self, calle_texto: str) -> bool:
        return self.escribir_campo_reactivo(
            ProveedorFormSelectors.INPUT_DOMICILIO,
            calle_texto,
            etiqueta="Domicilio / Calle",
        )

    def escribir_num_exterior(self, num_ext_texto: str) -> bool:
        return self.escribir_campo_reactivo(
            ProveedorFormSelectors.INPUT_NUM_EXTERIOR,
            num_ext_texto,
            etiqueta="Número Exterior",
        )

    def seleccionar_asentamiento_cp(self, cp_texto: str, colonia_texto: str = "") -> bool:
        """
        Despliega el Select2 remoto de C.P. / COLONIA / MUNICIPIO (#formControl_Asentamiento),
        escribe el Código Postal, espera reactivamente las opciones remotas y selecciona la
        que mejor coincida con la colonia indicada (o la primera del CP por defecto).
        """
        self.logger.info(f"Buscando C.P. '{cp_texto}' (Colonia: '{colonia_texto}')...")
        try:
            caja = self.esperar_clicable(
                ProveedorFormSelectors.CAJA_ASENTAMIENTO,
                timeout=TIMEOUT_LARGO,
            )
            self.click_seguro(caja)
            time.sleep(PAUSA_ESTABILIZACION)

            input_busqueda = self.esperar_visible(
                ProveedorFormSelectors.INPUT_BUSQUEDA_SELECT2,
                timeout=TIMEOUT_MEDIO,
            )
            input_busqueda.clear()
            input_busqueda.send_keys(cp_texto)

            # Pausa breve para disparo del debounce remoto y espera reactiva de resultados
            time.sleep(PAUSA_REMOTA_SELECT2)
            try:
                self.esperar_presente(
                    ProveedorFormSelectors.OPCIONES_SELECT2,
                    timeout=TIMEOUT_MEDIO,
                )
            except Exception:
                time.sleep(PAUSA_PANEL)

            opciones = self.driver.find_elements(*ProveedorFormSelectors.OPCIONES_SELECT2)
            if not opciones:
                self.logger.aviso(
                    f"No se encontraron opciones para el CP '{cp_texto}'. Intentando seleccionar con Enter..."
                )
                input_busqueda.send_keys(Keys.ENTER)
                time.sleep(PAUSA_ESTABILIZACION)
                return True

            colonia_norm = normalizar_alfanumerico(colonia_texto)
            opcion_elegida: Optional[WebElement] = None

            if colonia_norm:
                palabras_clave = [p for p in colonia_norm.split() if len(p) > 3]
                for op in opciones:
                    txt_op = normalizar_alfanumerico(
                        op.text or op.get_attribute("textContent") or ""
                    )
                    if colonia_norm in txt_op or any(p in txt_op for p in palabras_clave):
                        opcion_elegida = op
                        self.logger.info(
                            f"  -> Coincidencia encontrada con Colonia '{colonia_texto}': {op.text}"
                        )
                        break

            if not opcion_elegida:
                opcion_elegida = opciones[0]
                self.logger.info(
                    f"  -> Seleccionando opción por defecto para el CP: {opcion_elegida.text}"
                )

            self.click_seguro(opcion_elegida)
            time.sleep(PAUSA_ESTABILIZACION)
            self.logger.info("¡Asentamiento / C.P. seleccionado con éxito!")
            return True

        except Exception as e:
            self.logger.error(f"Fallo al seleccionar Asentamiento/CP: {e}")
            return False

    def guardar_proveedor_general(self) -> Tuple[Optional[str], str]:
        """
        Presiona el botón global 'Guardar (Alt+G)' en la barra superior y monitorea
        reactivamente el cambio de URL para extraer el ID real asignado por Aryve.
        Devuelve `(id_proveedor, url_final)`.
        """
        self.logger.info("\nGuardando Proveedor en Aryve...")
        try:
            btn_guardar: Optional[WebElement] = None
            for xp in ProveedorFormSelectors.XPATHS_BTN_GUARDAR:
                try:
                    elems = self.driver.find_elements(By.XPATH, xp)
                    for el in elems:
                        if el.is_displayed():
                            btn_guardar = el
                            break
                    if btn_guardar:
                        break
                except Exception:
                    continue

            if not btn_guardar:
                self.logger.error("No se encontró el botón de guardar en la barra superior.")
                return None, self.driver.current_url

            self.click_seguro(btn_guardar)
            self.logger.info(
                "Botón 'Guardar' presionado. Esperando respuesta y captura del ID en la URL..."
            )

            id_proveedor: Optional[str] = None
            url_final = self.driver.current_url
            max_intentos = int(TIMEOUT_GUARDADO / POLL_INTERVAL_RAPIDO)

            for _ in range(max_intentos):
                time.sleep(POLL_INTERVAL_RAPIDO)
                url_act = self.driver.current_url
                url_final = url_act

                m = (
                    re.search(r"/Proveedores/id[?=](\d+)", url_act)
                    or re.search(r"/Proveedores/(\d+)(?:[?#]|$)", url_act)
                    or re.search(r"id[?=](\d+)", url_act)
                )
                if m and "id?nuevo" not in url_act:
                    id_proveedor = m.group(1)
                    break

            if id_proveedor:
                self.logger.info(
                    f"[EXITO] ¡Proveedor guardado con éxito! ID generado: {id_proveedor}"
                )
                self.logger.info(f"URL: {url_final}")
            else:
                partes = [
                    p
                    for p in url_final.replace("?", "/").replace("=", "/").split("/")
                    if p and p != "nuevo"
                ]
                if partes and partes[-1].isdigit():
                    id_proveedor = partes[-1]
                    self.logger.info(f"ID capturado por segmento final: {id_proveedor}")
                else:
                    self.logger.aviso(
                        f"Se guardó pero la URL aún no expuso un ID numérico ({url_final})."
                    )

            return id_proveedor, url_final

        except Exception as e:
            self.logger.error(f"Fallo al intentar guardar proveedor: {e}")
            return None, self.driver.current_url

    def llenar_y_guardar_proveedor(
        self,
        proveedor: ProveedorData,
    ) -> Tuple[Optional[str], str]:
        """
        Ejecuta la secuencia completa de llenado y guardado de un proveedor en Aryve.
        """
        self.abrir_formulario_nuevo()

        self.logger.info(f"Seleccionando tipo de persona: {proveedor.tipo_persona}")
        self.seleccionar_tipo_persona(tipo=proveedor.tipo_persona)
        time.sleep(PAUSA_ESTABILIZACION)

        self.avanzar_siguiente_panel()
        time.sleep(PAUSA_ESTABILIZACION)

        if proveedor.clave:
            self.escribir_clave(proveedor.clave)

        if proveedor.nombre:
            self.escribir_nombre(proveedor.nombre)

        if proveedor.es_persona_fisica:
            if proveedor.paterno:
                self.escribir_apellido_paterno(proveedor.paterno)
            if proveedor.materno:
                self.escribir_apellido_materno(proveedor.materno)

        if proveedor.rfc:
            self.escribir_rfc(proveedor.rfc)

        if proveedor.nombre_corto:
            self.escribir_nombre_corto(proveedor.nombre_corto)

        if proveedor.es_persona_moral:
            self.logger.info("Marcando Obliga CFDI y Factoraje...")
            self.marcar_obliga_cfdi()
            self.marcar_factoraje()
        else:
            self.logger.info("[INFO] Modo Persona FÍSICA: se omiten Obliga CFDI y Factoraje.")

        if proveedor.calle:
            self.escribir_domicilio(proveedor.calle)

        if proveedor.ext:
            self.escribir_num_exterior(proveedor.ext)

        if proveedor.cp:
            self.seleccionar_asentamiento_cp(proveedor.cp, proveedor.colonia)
            time.sleep(PAUSA_MICRO)

        self.logger.info("Presionando botón Guardar en Aryve...")
        return self.guardar_proveedor_general()

