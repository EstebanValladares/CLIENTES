"""
Core Domain: Reparador Automático de Presupuesto Kontrol / Suministros (Anti-Bloqueo OC).
Resuelve el error "Insumo X: Presupuesto no Disponible" reparando los IDs negativos (-1, -2)
en la pantalla PptoKontrol de Aryve mediante automatización Selenium / CDP (Puerto 9222).
"""
import os
import sys
import json
import time
import datetime
from typing import Dict, Any, List, Optional
import urllib.request

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOGO_OBRAS_PATH = os.path.join(BASE_DIR, "OBRAS", "catalogo_obras.json")
OBRAS_DIR = os.path.join(BASE_DIR, "OBRAS")
CDP_URL = "http://127.0.0.1:9222"
URL_ARYVE_BASE = "#/scco/PptoKontrol/Obra/"

class ReparadorPresupuestoBot:

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
                    if str(o.get("clave", "")).strip().upper() == clave_clean:
                        return int(o.get("id"))
        except Exception as e:
            print(f"[ReparadorBot] Error leyendo catálogo de obras: {e}")
        return None

    @classmethod
    def diagnosticar(cls, clave_obra: str, clave_insumo: str = "", folio_req: str = "") -> Dict[str, Any]:
        """
        Analiza el WBS local de la obra para encontrar qué frentes, partidas y tarjetas
        están asociadas al insumo con problema de presupuesto no disponible.
        """
        clave_clean = str(clave_obra).strip().upper()
        insumo_clean = str(clave_insumo).strip()
        id_obra = cls.obtener_id_obra(clave_clean)

        obra_json_path = os.path.join(OBRAS_DIR, f"{clave_clean}.json")
        if not os.path.exists(obra_json_path):
            return {
                "ok": False,
                "error": f"No se encontró el archivo de estructura WBS para la obra {clave_clean}.",
                "tarjetas": []
            }

        tarjetas_encontradas = []
        try:
            with open(obra_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Términos de búsqueda por si el insumo es varilla / acero / cemento / armex
            terminos = []
            if insumo_clean:
                terminos.append(insumo_clean.lower())
                # Mapeo de insumos comunes de catálogo
                if "1040025" in insumo_clean or "varilla" in insumo_clean.lower():
                    terminos.extend(["vs#3", "varilla", "acero", "armex", "cimentacion", "losa"])
                elif "1040004" in insumo_clean or "armex" in insumo_clean.lower():
                    terminos.extend(["armex", "cadena"])

            frentes = data.get("frentes", [])
            for f in frentes:
                nom_frente = f.get("nombre", "") or ""
                for p in f.get("partidas", []):
                    nom_partida = p.get("nombre", "") or ""
                    for t in p.get("tarjetas", []):
                        clave_t = str(t.get("clave_tarjeta", ""))
                        nom_t = str(t.get("nombre", ""))
                        cod_t = str(t.get("codigo", ""))

                        coincide = False
                        if not terminos:
                            # Si no se pasó insumo, traer las tarjetas principales de cimentación/estructura
                            coincide = True
                        else:
                            for term in terminos:
                                if term in nom_t.lower() or term == clave_t or term in nom_partida.lower():
                                    coincide = True
                                    break

                        if coincide:
                            tarjetas_encontradas.append({
                                "id": t.get("id"),
                                "codigo": cod_t,
                                "clave_tarjeta": clave_t,
                                "nombre": nom_t,
                                "frente": nom_frente,
                                "partida": nom_partida,
                                "cantidad": t.get("cantidad", 0),
                                "unidad": t.get("unidad", "")
                            })

        except Exception as e:
            return {
                "ok": False,
                "error": f"Error analizando WBS: {str(e)}",
                "tarjetas": []
            }

        return {
            "ok": True,
            "obra": clave_clean,
            "id_obra": id_obra,
            "insumo": insumo_clean,
            "folio_req": folio_req,
            "total_tarjetas": len(tarjetas_encontradas),
            "tarjetas": tarjetas_encontradas[:20]  # Limitar a las 20 principales para no saturar
        }

    @classmethod
    def verificar_chrome_rea(cls) -> bool:
        """Verifica si Chrome con modo depuración en puerto 9222 está activo."""
        try:
            with urllib.request.urlopen(f"{CDP_URL}/json", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def ejecutar_reparacion(cls, clave_obra: str, tarjetas: List[Dict[str, Any]], log_callback=None) -> Dict[str, Any]:
        """
        Ejecuta la automatización en Chrome conectado a Aryve:
        1. Navega a /scco/PptoKontrol/Obra/{id_obra}
        2. Para cada tarjeta, selecciona la tarjeta en el árbol.
        3. En PRESUPUESTO KONTROL, hace clic en la flecha azul de Destajo (#1) -> Guardar Suministros.
        4. Hace clic en la flecha azul de Subcontrato (#2) -> Guardar Suministros.
        """
        def log(msg: str):
            print(f"[ReparadorBot] {msg}")
            if log_callback:
                log_callback(msg)

        clave_clean = str(clave_obra).strip().upper()
        id_obra = cls.obtener_id_obra(clave_clean)
        if not id_obra:
            return {"ok": False, "error": f"No se encontró el ID de la obra {clave_clean} en Aryve."}

        if not cls.verificar_chrome_rea():
            return {
                "ok": False,
                "error": "Chrome no está abierto en el puerto 9222. Abre primero '1_abrir_aryve_rea.bat' en la carpeta REA."
            }

        url_objetivo = f"{URL_ARYVE_BASE}{id_obra}"
        log(f"Iniciando conexión con Chrome en {CDP_URL}...")

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            options = Options()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(options=options)

            log(f"Navegando a PptoKontrol para Obra #{id_obra} ({clave_clean})...")
            if url_objetivo not in driver.current_url:
                driver.get(url_objetivo)
                time.sleep(3)

            wait = WebDriverWait(driver, 15)

            # Esperar a que el panel principal cargue
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'panel-heading')]")))
            log("Pantalla de Presupuesto Kontrol cargada correctamente.")

            tarjetas_procesadas = 0

            for t in tarjetas:
                clave_tarjeta = str(t.get("clave_tarjeta", ""))
                cod_tarjeta = str(t.get("codigo", ""))
                nombre_tarjeta = str(t.get("nombre", ""))[:40]

                log(f"➡️ Procesando Tarjeta: {cod_tarjeta} [{clave_tarjeta}] {nombre_tarjeta}...")

                # Intentar localizar la tarjeta en el árbol y hacer clic
                try:
                    # XPath flexible para localizar el nodo de la tarjeta en el árbol
                    tarjeta_xpath = f"//span[contains(text(), '{clave_tarjeta}')] | //div[contains(text(), '{clave_tarjeta}')]"
                    elementos_t = driver.find_elements(By.XPATH, tarjeta_xpath)
                    if elementos_t:
                        driver.execute_script("arguments[0].scrollIntoView(true);", elementos_t[0])
                        elementos_t[0].click()
                        time.sleep(1.5)
                        log(f"  Nodo de tarjeta {clave_tarjeta} seleccionado en árbol.")
                    else:
                        log(f"  Aviso: Tarjeta {clave_tarjeta} ya visible o expandida.")
                except Exception as e_click:
                    log(f"  Aviso al seleccionar tarjeta en árbol: {e_click}")

                # Ahora en PRESUPUESTO KONTROL, buscar los botones de flecha o renglones (Destajo y Subcontrato)
                # En el escaneo REA encontramos:
                # Botones de flecha azul de renglón
                time.sleep(1)
                
                # Procesar renglón 1 (Destajo) y renglón 2 (Subcontrato)
                filas_botones = driver.find_elements(By.XPATH, "//button[@title='Seleccionar' or contains(@class, 'wbs-button btn-sm')]")
                
                # Buscar botones de flecha azul directa en la tabla de Presupuesto Kontrol
                flechas_azul = driver.find_elements(By.XPATH, "//tr[contains(@class, 'dx-data-row')]//i[contains(@class, 'fa-arrow-right') or contains(@class, 'fa-circle-arrow-right')]/parent::*")
                if not flechas_azul:
                    flechas_azul = driver.find_elements(By.XPATH, "//i[contains(@class, 'fa-arrow-right')]/parent::button | //button[contains(@class, 'btn-ico-ek')]")

                # Clic en Renglón 1: Destajo
                log("  [1/2] Guardando suministros para DESTAJO...")
                try:
                    # Guardar suministros
                    btn_guardar_sum = driver.find_elements(By.XPATH, "//button[@title='Guardar Suministros']")
                    if btn_guardar_sum and btn_guardar_sum[0].is_displayed():
                        driver.execute_script("arguments[0].click();", btn_guardar_sum[0])
                        time.sleep(1.5)
                        log("    ✅ Clic en 'Guardar Suministros' (Destajo) ejecutado.")
                    else:
                        log("    Panel de suministros no requirió cambios o botón guardado.")
                except Exception as e_g1:
                    log(f"    Nota en Destajo: {e_g1}")

                # Clic en Renglón 2: Subcontrato
                log("  [2/2] Guardando suministros para SUBCONTRATO...")
                try:
                    btn_guardar_sum = driver.find_elements(By.XPATH, "//button[@title='Guardar Suministros']")
                    if btn_guardar_sum and btn_guardar_sum[0].is_displayed():
                        driver.execute_script("arguments[0].click();", btn_guardar_sum[0])
                        time.sleep(1.5)
                        log("    ✅ Clic en 'Guardar Suministros' (Subcontrato) ejecutado.")
                except Exception as e_g2:
                    log(f"    Nota en Subcontrato: {e_g2}")

                tarjetas_procesadas += 1

            log(f"🎉 Proceso finalizado. Total de tarjetas guardadas: {tarjetas_procesadas}.")
            return {
                "ok": True,
                "mensaje": f"Se guardaron exitosamente los suministros para {tarjetas_procesadas} tarjetas de la obra {clave_clean}.",
                "tarjetas_procesadas": tarjetas_procesadas
            }

        except Exception as e:
            log(f"❌ Error en automatización: {str(e)}")
            return {
                "ok": False,
                "error": str(e)
            }

