"""
Paso 1 (REA): Abre Chrome con el puerto de depuración 9222 habilitado
e inicia sesión automáticamente en Aryve usando las credenciales del proyecto.
Deja el navegador abierto para que navegues a la pantalla que deseas escanear.
"""
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    from NUCLEO.config import obtener_credenciales_aryve
except ImportError:
    def obtener_credenciales_aryve():
        # Fallback a variables de entorno o archivo .env
        user = os.getenv("ARYVE_USER", os.getenv("USUARIO_ARYVE", ""))
        pwd = os.getenv("ARYVE_PASSWORD", os.getenv("PASSWORD_ARYVE", ""))
        return user, pwd

PORT_CDP = 9222
PERFIL_CDP = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".chrome_rea_profile")
URL_ARYVE = "https://suite.ekloud.net:1445/Aryve/"


def abrir_navegador_rea():
    print("=" * 65)
    print("  PASO 1: INICIANDO CHROME EN MODO DEPURACIÓN (CDP PUERTO 9222)")
    print("=" * 65)

    os.makedirs(PERFIL_CDP, exist_ok=True)

    opciones = webdriver.ChromeOptions()
    opciones.add_experimental_option("detach", True)
    opciones.add_argument(f"--remote-debugging-port={PORT_CDP}")
    opciones.add_argument(f"--user-data-dir={PERFIL_CDP}")
    opciones.add_argument("--remote-allow-origins=*")
    opciones.add_argument("--ignore-certificate-errors")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--start-maximized")
    opciones.add_argument("--log-level=3")

    # Intentar inicializar Chrome de forma nativa con Selenium 4.
    # Si falla, recurre a webdriver_manager limpiando posibles bloqueos residuales.
    try:
        driver = webdriver.Chrome(options=opciones)
    except Exception as err_native:
        print(f"[INFO] Selenium nativo no pudo abrir el driver ({err_native}). Intentando con webdriver_manager...")
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            # Limpiar posible candado huérfano de webdriver-manager si existiera
            lock_file = os.path.expanduser(r"~\.wdm\.wdm-lock-chromedriver-win64")
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
            servicio = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=servicio, options=opciones)
        except Exception as err_wdm:
            print(f"[ERROR CRÍTICO] No se pudo inicializar ChromeDriver: {err_wdm}")
            return

    try:
        usuario, password = obtener_credenciales_aryve()
        print(f"[INFO] Navegando a {URL_ARYVE} ...")
        driver.get(URL_ARYVE)

        wait = WebDriverWait(driver, 20)
        try:
            user_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            print("[INFO] Iniciando sesión automáticamente en Aryve...")
            user_input.clear()
            user_input.send_keys(usuario)

            pass_input = driver.find_element(By.ID, "password")
            pass_input.clear()
            pass_input.send_keys(password)

            driver.find_element(By.ID, "btnSubmit").click()
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            driver.refresh()
            time.sleep(2)
            print("[OK] ¡Sesión iniciada correctamente!")
        except Exception:
            print("[INFO] La sesión ya estaba activa o la pantalla de login no fue requerida.")

        print("\n" + "=" * 65)
        print("  NAVEGADOR LISTO Y CONECTADO EN: http://127.0.0.1:9222")
        print("  1. Entra en Chrome a la pantalla o módulo que quieras analizar.")
        print("  2. Abre el modal o desplegable que te interese.")
        print("  3. Ejecuta '2_escanear_pantalla.bat' para capturar todo.")
        print("=" * 65)

    except Exception as e:
        print(f"[ERROR]: {e}")


if __name__ == "__main__":
    abrir_navegador_rea()
