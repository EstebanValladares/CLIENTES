"""
Bot RPA Selenium para Carga de Fotos de Contratistas en Aryve (EK10).

Flujo de Operación:
1. Iniciar sesión en Aryve Suite usando credenciales oficiales EK10.
2. Para cada ID en el rango solicitado:
   a. Navegar a '#/scco/Contratistas/{id}' y esperar carga de formulario.
   b. Verificar si ya cuenta con imagen (KontrolFiles):
      - Si ya tiene foto: OMITIR sin realizar ninguna modificación.
      - Si NO tiene foto:
        1. Clic en 'Editar (Alt+E)'.
        2. Inyectar imagen local '{id}.png' en <input type="file">.
        3. Clic en icono de subida (<i class="fa fa-upload"></i>).
        4. Clic en 'Guardar (Alt+G)'.
        5. Avanzar al siguiente contratista.
"""

import os
import time
from typing import Tuple, Dict, Any, Optional, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from ..config.settings import (
        URL_LOGIN_ARYVE,
        URL_CONTRATISTAS_BASE,
        OUTPUT_DIR,
        resolver_credenciales,
    )
    from .driver_factory import build_chrome_driver
except (ImportError, ValueError):
    from config.settings import (
        URL_LOGIN_ARYVE,
        URL_CONTRATISTAS_BASE,
        OUTPUT_DIR,
        resolver_credenciales,
    )
    from automation.driver_factory import build_chrome_driver


class ContractorBot:
    def __init__(
        self,
        usuario: Optional[str] = None,
        password: Optional[str] = None,
        driver: Optional[webdriver.Chrome] = None,
        headless: bool = False,
        images_dir: str = OUTPUT_DIR
    ):
        self.usuario, self.password = resolver_credenciales(usuario, password)
        self.images_dir = images_dir
        self.headless = headless
        self.driver = driver or build_chrome_driver(headless=headless, detach=True)
        self.owns_driver = driver is None

    def login(self, timeout: int = 25) -> bool:
        """Autenticación en el portal de Aryve."""
        print("=" * 80)
        print(f"1. Accediendo al portal Aryve: {URL_LOGIN_ARYVE}")
        print(f"   Usuario: {self.usuario}")
        print("=" * 80)

        self.driver.get(URL_LOGIN_ARYVE)
        wait = WebDriverWait(self.driver, timeout)

        user_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
        user_input.clear()
        user_input.send_keys(self.usuario)

        pass_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
        pass_input.clear()
        pass_input.send_keys(self.password)

        btn_submit = wait.until(EC.element_to_be_clickable((By.ID, "btnSubmit")))
        btn_submit.click()
        print("   Enviando credenciales de acceso...")

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        if "login" in self.driver.current_url.lower():
            self.driver.refresh()
            time.sleep(2)

        print("   [OK] Sesión iniciada correctamente.")
        return True

    def navigate_to_contractor(self, contractor_id: int, timeout: int = 25):
        """Navega a la pantalla del contratista: #/scco/Contratistas/{id}."""
        target_url = f"{URL_CONTRATISTAS_BASE}{contractor_id}"
        print(f"\n[ID {contractor_id}] Navegando a: {target_url}")

        self.driver.get(target_url)
        wait = WebDriverWait(self.driver, timeout)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

    def has_existing_photo(self) -> Tuple[bool, str]:
        """
        Verifica si el contratista ya cuenta con una imagen asignada en Aryve.
        Retorna (True, motivo) si existe imagen, o (False, '') si está vacío.
        """
        try:
            time.sleep(1)
            # 1. Comprobar etiqueta <img id="fileinput-img">
            img_els = self.driver.find_elements(By.ID, "fileinput-img")
            if img_els:
                src = (img_els[0].get_attribute("src") or "").strip()
                if "KontrolFiles" in src:
                    return True, f"Tiene foto en KontrolFiles: {src.split('/')[-1]}"
                if "thumbnail.png" not in src and src and ("http" in src or "data:image" in src or "blob:" in src):
                    return True, "Tiene imagen previa asignada (no predeterminada)"

            # 2. Comprobar preview contenedor
            preview_imgs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'fileinput-preview')]//img")
            for pimg in preview_imgs:
                psrc = (pimg.get_attribute("src") or "").strip()
                if "KontrolFiles" in psrc:
                    return True, "Foto existente en vista previa"

            return False, ""
        except Exception as e:
            return False, f"Error al verificar foto: {e}"

    def click_edit_button(self, timeout: int = 12) -> bool:
        """Presiona el botón 'Editar (Alt+E)'."""
        wait = WebDriverWait(self.driver, timeout)
        xpaths = [
            "//button[contains(@class, 'btn-editar')]",
            "//button[@aria-label='Editar (Alt+E)']",
            "//button[@data-tip='Editar (Alt+E)']",
            "//button[@title='Editar (Alt+E)']",
            "//button[.//i[contains(@class, 'fa-edit')]]",
        ]

        btn_editar = None
        for xpath in xpaths:
            try:
                for el in self.driver.find_elements(By.XPATH, xpath):
                    if el.is_displayed():
                        btn_editar = el
                        break
                if btn_editar:
                    break
            except Exception:
                continue

        if not btn_editar:
            try:
                btn_editar = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-editar')]"))
                )
            except Exception:
                pass

        if btn_editar:
            try:
                btn_editar.click()
                print("   -> Clic en 'Editar (Alt+E)' ejecutado.")
            except Exception:
                self.driver.execute_script("arguments[0].click();", btn_editar)
                print("   -> Clic en 'Editar (Alt+E)' forzado con JavaScript.")
            time.sleep(1.5)
            return True
        return False

    def inject_image_file(self, contractor_id: int) -> bool:
        """Inyecta la imagen local {id}.png al input file del formulario."""
        img_path = os.path.join(self.images_dir, f"{contractor_id}.png")
        if not os.path.exists(img_path):
            print(f"   [!] No existe el archivo de imagen: {img_path}")
            return False

        ruta_absoluta = os.path.abspath(img_path)

        try:
            inputs = self.driver.find_elements(By.XPATH, "//input[@type='file' and contains(@accept, 'image')]")
            if not inputs:
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")

            if not inputs:
                print("   [!] No se encontró el elemento <input type='file'> en el formulario.")
                return False

            file_input = inputs[0]
            self.driver.execute_script("""
                var input = arguments[0];
                input.style.display = 'block';
                input.style.visibility = 'visible';
                input.style.opacity = '1';
                if (input.parentElement) {
                    input.parentElement.style.display = 'block';
                    if (input.parentElement.parentElement) {
                        input.parentElement.parentElement.style.display = 'block';
                    }
                }
            """, file_input)
            time.sleep(0.3)

            file_input.send_keys(ruta_absoluta)

            # Disparar eventos nativos y jQuery
            self.driver.execute_script("""
                var input = arguments[0];
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('input', { bubbles: true }));
                if (window.jQuery) {
                    try { window.jQuery(input).trigger('change'); } catch(e) {}
                }
            """, file_input)

            time.sleep(1.5)
            print(f"   -> Imagen '{os.path.basename(ruta_absoluta)}' cargada en el fileinput.")
            return True
        except Exception as e:
            print(f"   [!] Error al inyectar archivo: {e}")
            return False

    def click_upload_icon(self, timeout: int = 10) -> bool:
        """Presiona el botón con el icono de subida: <i class="fa fa-upload"></i>."""
        print("   -> Buscando icono de carga (<i class='fa fa-upload'>)...")
        wait = WebDriverWait(self.driver, timeout)

        xpaths = [
            "//button[.//i[contains(@class, 'fa-upload')]]",
            "//div[contains(@class, 'panel-sub4')]//button[.//i[contains(@class, 'fa-upload')]]",
            "//div[contains(@class, 'actions')]//button[.//i[contains(@class, 'fa-upload')]]",
        ]

        btn_upload = None
        for xpath in xpaths:
            try:
                for el in self.driver.find_elements(By.XPATH, xpath):
                    if el.is_displayed():
                        btn_upload = el
                        break
                if btn_upload:
                    break
            except Exception:
                continue

        if not btn_upload:
            try:
                btn_upload = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//i[contains(@class, 'fa-upload')]]"))
                )
            except Exception:
                pass

        if btn_upload:
            try:
                btn_upload.click()
                print("   -> ¡Clic en icono fa-upload realizado!")
            except Exception:
                self.driver.execute_script("arguments[0].click();", btn_upload)
                print("   -> ¡Clic en icono fa-upload forzado con JavaScript!")
            time.sleep(2)
            return True
        else:
            print("   [AVISO] No apareció el icono fa-upload (posiblemente se procesó automáticamente).")
            return False

    def click_save_button(self, timeout: int = 15) -> bool:
        """Presiona el botón 'Guardar (Alt+G)'."""
        print("   -> Presionando botón 'Guardar (Alt+G)'...")
        wait = WebDriverWait(self.driver, timeout)

        xpaths = [
            "//button[contains(@class, 'btn-editing') and contains(@aria-label, 'Guardar')]",
            "//button[@aria-label='Guardar (Alt+G)']",
            "//button[@data-tip='Guardar (Alt+G)']",
            "//button[@title='Guardar (Alt+G)']",
            "//button[contains(@class, 'btn') and .//i[contains(@class, 'icon-cloud-upload')]]",
            "//button[contains(@class, 'btn-default-ek') and contains(@aria-label, 'Guardar')]",
        ]

        btn_guardar = None
        for xpath in xpaths:
            try:
                for el in self.driver.find_elements(By.XPATH, xpath):
                    if el.is_displayed():
                        btn_guardar = el
                        break
                if btn_guardar:
                    break
            except Exception:
                continue

        if not btn_guardar:
            try:
                btn_guardar = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-tip, 'Guardar')]"))
                )
            except Exception:
                pass

        if btn_guardar:
            try:
                btn_guardar.click()
                print("   [OK] Guardado ejecutado con clic.")
            except Exception:
                self.driver.execute_script("arguments[0].click();", btn_guardar)
                print("   [OK] Guardado ejecutado con JavaScript.")

            time.sleep(3.5)
            return True
        else:
            try:
                print("   -> Intentando atajo de teclado Alt+G...")
                action = webdriver.ActionChains(self.driver)
                action.key_down(Keys.ALT).send_keys("g").key_up(Keys.ALT).perform()
                time.sleep(3)
                return True
            except Exception:
                print("   [!] No se pudo localizar el botón Guardar.")
                return False

    def process_contractor(self, contractor_id: int) -> Dict[str, Any]:
        """Procesa un solo contratista según la regla de no modificar fotos existentes."""
        self.navigate_to_contractor(contractor_id)

        tiene_foto, motivo = self.has_existing_photo()
        if tiene_foto:
            print(f"   [OMITIDO] El contratista ID {contractor_id} ya tiene imagen asignada.")
            print(f"             Motivo: {motivo}")
            print(f"             -> NO se modifica nada.")
            return {"id": contractor_id, "status": "OMITIDO", "motivo": motivo}

        print(f"   -> Contratista ID {contractor_id} NO tiene foto. Procediendo a cargar...")
        self.click_edit_button()

        if not self.inject_image_file(contractor_id):
            return {"id": contractor_id, "status": "ERROR", "motivo": "Falta archivo de imagen"}

        self.click_upload_icon()
        ok_guardar = self.click_save_button()

        if ok_guardar:
            print(f"   [ÉXITO] Foto asignada y guardada para Contratista ID {contractor_id}.")
            return {"id": contractor_id, "status": "GUARDADO", "motivo": "Foto cargada y guardada"}
        else:
            return {"id": contractor_id, "status": "PENDIENTE_GUARDAR", "motivo": "No se pudo confirmar guardado"}

    def run_batch(self, start_id: int, end_id: int, pause_at_end: bool = True) -> List[Dict[str, Any]]:
        """Ejecuta la automatización secuencialmente en el rango de IDs indicado."""
        print("=" * 80)
        print("INICIO DE AUTOMATIZACIÓN POR LOTE DE CONTRATISTAS EN ARYVE")
        print(f"Rango de IDs a procesar: {start_id} hasta {end_id}")
        print("Regla: Si ya tiene imagen -> Omitir sin modificar. Si no -> Cargar, fa-upload y Guardar.")
        print("=" * 80)

        resumen: List[Dict[str, Any]] = []

        try:
            self.login()
            for current_id in range(start_id, end_id + 1):
                resultado = self.process_contractor(current_id)
                resumen.append(resultado)

            # Resumen en consola
            print("\n" + "=" * 80)
            print("RESUMEN DE EJECUCIÓN POR LOTE:")
            print("=" * 80)
            guardados = sum(1 for r in resumen if r["status"] == "GUARDADO")
            omitidos = sum(1 for r in resumen if r["status"] == "OMITIDO")
            errores = sum(1 for r in resumen if r["status"] in ("ERROR", "PENDIENTE_GUARDAR"))

            print(f"  Total procesados:     {len(resumen)}")
            print(f"  Guardados con foto:   {guardados}")
            print(f"  Omitidos (ya tenían): {omitidos}")
            print(f"  Errores / Pendientes: {errores}")

            print("\nDetalle por ID:")
            for r in resumen:
                print(f"  - ID {r['id']:<4}: [{r['status']:<15}] {r['motivo']}")
            print("=" * 80)

            if pause_at_end and not self.headless:
                print("\nEl navegador se mantiene abierto para inspección.")
                try:
                    input("Presione ENTER en esta consola cuando desee cerrar el navegador...")
                except (KeyboardInterrupt, EOFError):
                    pass

            return resumen

        finally:
            if (not pause_at_end or self.headless) and self.owns_driver:
                self.close()

    def close(self):
        """Cierra la sesión del navegador."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
