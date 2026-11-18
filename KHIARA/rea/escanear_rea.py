"""
Paso 2 (REA): Detecta automáticamente la pestaña activa de Aryve en el puerto 9222,
ejecuta los escáneres de REA (inspect-web-page y analyze-web-bundle) y además
extrae la radiografía completa de selectores DOM (formControl, Select2, DevExtreme,
botones, inputs y modales) en archivos JSON listos para construir automatizaciones Selenium.
"""
import os
import sys
import json
import time
import datetime
import subprocess
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

DIR_REA = os.path.dirname(os.path.abspath(__file__))
DIR_REPORTES = os.path.join(DIR_REA, "reportes")
CDP_URL = "http://127.0.0.1:9222"


def obtener_target_aryve():
    """Consulta http://127.0.0.1:9222/json para hallar el TARGET_ID de la pestaña de Aryve."""
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json", timeout=5) as resp:
            targets = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"\n[ERROR] No se detectó Chrome en {CDP_URL}.")
        print("Asegúrate de haber ejecutado primero '1_abrir_aryve_rea.bat'.")
        print(f"Detalle: {e}")
        return None

    paginas = [t for t in targets if t.get("type") == "page"]
    for t in paginas:
        url = t.get("url", "").lower()
        if "aryve" in url or "ekloud" in url:
            return t

    # Si no dice aryve en la URL, tomar la primera página abierta que no sea devtools
    for t in paginas:
        if not t.get("url", "").startswith("devtools://"):
            return t

    return paginas[0] if paginas else None


def ejecutar_comando_rea(args_lista, archivo_salida):
    """Ejecuta npx rea-agents con los argumentos indicados y guarda el JSON."""
    cmd = ["npx", "--yes", "rea-agents@latest"] + args_lista
    print(f"[REA] Ejecutando: {' '.join(cmd)}")
    try:
        res = subprocess.run(
            cmd,
            cwd=DIR_REA,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
            timeout=90
        )
        salida = res.stdout.strip()
        if salida:
            with open(archivo_salida, "w", encoding="utf-8") as f:
                f.write(salida)
            print(f"  -> Guardado en: {archivo_salida}")
            return True
        else:
            if res.stderr:
                print(f"  [AVISO REA]: {res.stderr.strip()[:300]}")
            return False
    except Exception as e:
        print(f"  [AVISO] No se pudo completar comando REA ({e}). Continuando con radiografía DOM...")
        return False


def extraer_radiografia_aryve():
    """
    Se conecta por CDP a la sesión viva de Chrome y extrae todos los elementos interactivos,
    IDs de Aryve (formControl_*, select2-*, dx-datagrid, sidebars, botones y tablas).
    """
    print("[DOM X-RAY] Extrayendo mapa profundo de selectores y componentes de la pantalla actual...")
    opciones = Options()
    opciones.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opciones)

    script_js = """
    function getXPath(el) {
        if (el.id) return "//*[@id='" + el.id + "']";
        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let idx = 1;
            let sib = el.previousSibling;
            while (sib) {
                if (sib.nodeType === Node.ELEMENT_NODE && sib.tagName === el.tagName) idx++;
                sib = sib.previousSibling;
            }
            parts.unshift(el.tagName.toLowerCase() + "[" + idx + "]");
            el = el.parentNode;
        }
        return "/" + parts.join("/");
    }

    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    }

    function findLabel(el) {
        if (el.id) {
            const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (lbl) return lbl.innerText.trim();
        }
        const parentGroup = el.closest('.form-group, .col-md-4, .col-md-6, .col-lg-4, .col-sm-6, div');
        if (parentGroup) {
            const lbl = parentGroup.querySelector('label, .control-label, .caption');
            if (lbl) return lbl.innerText.trim();
        }
        return '';
    }

    const inputs = Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
        tag: el.tagName.toLowerCase(),
        type: el.type || '',
        id: el.id || '',
        name: el.name || '',
        className: el.className || '',
        placeholder: el.placeholder || '',
        ariaLabel: el.getAttribute('aria-label') || '',
        value: (el.value || '').slice(0, 100),
        checked: !!el.checked,
        disabled: !!el.disabled,
        visible: isVisible(el),
        label: findLabel(el),
        xpath: getXPath(el)
    }));

    const select2Containers = Array.from(document.querySelectorAll('.select2-selection, [id^="select2-"]')).map(el => ({
        id: el.id || '',
        className: el.className || '',
        text: (el.innerText || '').trim(),
        title: el.getAttribute('title') || '',
        visible: isVisible(el),
        label: findLabel(el),
        xpath: getXPath(el)
    }));

    const buttons = Array.from(document.querySelectorAll('button, a.btn, .btn-ico-ek, [role="button"], .wbs-button, .badgeSquare')).map(el => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        className: el.className || '',
        title: el.getAttribute('title') || el.getAttribute('data-tip') || '',
        text: (el.innerText || '').trim().slice(0, 80),
        visible: isVisible(el),
        xpath: getXPath(el)
    })).filter(b => b.visible || b.id || b.title);

    const panelsAndSidebars = Array.from(document.querySelectorAll('.panel, [id^="Sidebar"], .modal, .dx-datagrid')).map(el => ({
        id: el.id || '',
        className: el.className || '',
        heading: (el.querySelector('.panel-heading, .modal-header, .c-sidebar-header')?.innerText || '').trim().slice(0, 100),
        visible: isVisible(el),
        xpath: getXPath(el)
    }));

    return {
        url: window.location.href,
        title: document.title,
        timestamp: new Date().toISOString(),
        resumen: {
            total_inputs: inputs.length,
            total_select2: select2Containers.length,
            total_botones: buttons.length,
            total_paneles_grids: panelsAndSidebars.length
        },
        inputs: inputs,
        select2: select2Containers,
        botones: buttons,
        paneles_y_grids: panelsAndSidebars
    };
    """

    datos_xray = driver.execute_script(script_js)
    html_completo = driver.page_source
    return datos_xray, html_completo


def main():
    os.makedirs(DIR_REPORTES, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 65)
    print("  PASO 2: ESCANEANDO PANTALLA ACTIVA DE ARYVE CON REA + X-RAY")
    print("=" * 65)

    target = obtener_target_aryve()
    if not target:
        return 1

    target_id = target.get("id")
    url_actual = target.get("url")
    titulo = target.get("title")

    print(f"[TARGET DETECTADO]")
    print(f"  • ID   : {target_id}")
    print(f"  • URL  : {url_actual}")
    print(f"  • Title: {titulo}\n")

    # 1. Extraer radiografía DOM completa e instantánea para Selenium
    try:
        datos_xray, html_completo = extraer_radiografia_aryve()
        ruta_xray = os.path.join(DIR_REPORTES, "ultimo_escaneo_dom.json")
        ruta_xray_hist = os.path.join(DIR_REPORTES, f"escaneo_dom_{ts}.json")
        ruta_html = os.path.join(DIR_REPORTES, "ultimo_dom.html")

        with open(ruta_xray, "w", encoding="utf-8") as f:
            json.dump(datos_xray, f, indent=2, ensure_ascii=False)
        with open(ruta_xray_hist, "w", encoding="utf-8") as f:
            json.dump(datos_xray, f, indent=2, ensure_ascii=False)
        with open(ruta_html, "w", encoding="utf-8") as f:
            f.write(html_completo)

        res = datos_xray["resumen"]
        print(f"[OK] Radiografía de Selectores guardada en: {ruta_xray}")
        print(f"     Inputs: {res['total_inputs']} | Select2: {res['total_select2']} | Botones: {res['total_botones']} | Grids/Paneles: {res['total_paneles_grids']}")
    except Exception as e:
        print(f"[ERROR en Radiografía DOM]: {e}")

    # 2. Ejecutar comandos oficiales de REA (inspect-web-page y analyze-web-bundle)
    print("\n[REA] Ejecutando análisis profundo con rea-agents...")
    ruta_rea_inspect = os.path.join(DIR_REPORTES, "rea_inspect.json")
    ruta_rea_bundle = os.path.join(DIR_REPORTES, "rea_bundle.json")

    ejecutar_comando_rea(
        ["inspect-web-page", CDP_URL, target_id, "--observation-ms", "2500", "--json"],
        ruta_rea_inspect
    )
    ejecutar_comando_rea(
        ["analyze-web-bundle", CDP_URL, target_id, "--json"],
        ruta_rea_bundle
    )

    print("\n" + "=" * 65)
    print("  ¡ESCANEO COMPLETADO CON ÉXITO!")
    print("  Archivos actualizados en: REA/reportes/")
    print("  -> Ahora solo dime en el chat qué quieres automatizar de esta pantalla.")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())

