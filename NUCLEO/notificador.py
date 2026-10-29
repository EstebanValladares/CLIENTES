"""Notificaciones: consola, popup de Windows, Telegram (texto + captura) y bitácora.

Solo se alerta cuando el veredicto NO es OK. Siempre se imprime un banner final en
consola con el veredicto real (para que "todo bien en consola" nunca engañe).
"""
import datetime
import json
import mimetypes
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid

from NUCLEO import config

NUCLEO_DIR = config.NUCLEO_DIR
LOG_ALERTAS = os.path.join(NUCLEO_DIR, "alertas.log")
ULTIMA_ALERTA = os.path.join(NUCLEO_DIR, "ULTIMA_ALERTA.md")
ULTIMO_DIAGNOSTICO = os.path.join(NUCLEO_DIR, "ULTIMO_DIAGNOSTICO.md")

ICONOS = {"OK": "✅", "ADVERTENCIA": "⚠️", "FALLO_SILENCIOSO": "🕵️", "FALLO": "❌"}
TITULOS = {
    "OK": "Ejecución verificada correctamente",
    "ADVERTENCIA": "Terminó con advertencias",
    "FALLO_SILENCIOSO": "FALLO SILENCIOSO: la consola dijo OK pero el resultado NO es el esperado",
    "FALLO": "La ejecución FALLÓ",
}


def _p(texto=""):
    try:
        print(texto)
    except UnicodeEncodeError:
        print(texto.encode("ascii", "replace").decode("ascii"))


def formatear(rep, detallado=False):
    """Texto Markdown con todo lo necesario para entender (y arreglar) el fallo."""
    v = rep["veredicto"]
    L = [f"{ICONOS.get(v, '')} **{rep['proyecto']}** — {TITULOS.get(v, v)}",
         f"Inicio: {rep['inicio']} · Duración: {rep['duracion_s']} s · Cobertura: {rep['cobertura']}"]

    fallidas = [x for x in rep["verificaciones"] if not x["ok"]]
    if fallidas:
        L.append("\n**Verificaciones de negocio que NO coinciden:**")
        for x in fallidas:
            marca = "🔴" if x["critica"] else "🟡"
            L.append(f"- {marca} {x['nombre']}: esperado `{x['esperado']}` → obtenido `{x['obtenido']}`"
                     + (f" _(componente: {x['componente']})_" if x["componente"] else ""))

    pasos_f = [p for p in rep["pasos"] if p["estado"] == "fallo"]
    if pasos_f:
        L.append("\n**Pasos fallidos:**")
        for p in pasos_f[: (40 if detallado else 8)]:
            L.append(f"- {p['nombre']}" + (f" _(componente: {p['componente']})_" if p["componente"] else "")
                     + (f" — {p['detalle']}" if p["detalle"] else ""))

    if rep.get("excepcion"):
        cola = rep["excepcion"].strip().splitlines()
        L.append("\n**Excepción:**\n```\n" + "\n".join(cola[-(25 if detallado else 6):]) + "\n```")

    if rep["consola_anomalias"]:
        L.append("\n**Líneas sospechosas en consola:**")
        for linea in rep["consola_anomalias"][: (30 if detallado else 5)]:
            L.append(f"- `{linea}`")

    if rep.get("impacto"):
        L.append("\n**🕸️ Impacto en el ecosistema (grafo):**")
        for i in rep["impacto"]:
            L.append(f"- {i['componente']} también lo usan: {', '.join(i['proyectos'])}")

    if rep.get("analisis_vision"):
        L.append("\n**👁️ Análisis visual (Gemini):**\n" + rep["analisis_vision"])
    return "\n".join(L)


def _diagnostico_para_agente(rep, ruta_json):
    extra = [
        "# Diagnóstico para reparar", "",
        formatear(rep, detallado=True), "",
        "## Evidencia",
        f"- Reporte JSON: `{ruta_json}`",
    ]
    for c in rep["capturas"]:
        extra.append(f"- Captura: `{c['png']}` ({c.get('motivo', '')}) · URL: {c.get('url', 'n/d')}")
        if c.get("html"):
            extra.append(f"- HTML de la página: `{c['html']}`")
    extra += [
        "", "## Prompt sugerido para el agente",
        "> Analiza `NUCLEO/ULTIMO_DIAGNOSTICO.md`, abre la captura y el HTML indicados, "
        "identifica por qué el componente falló (selector cambiado, temporización, dato inválido), "
        "corrige el código del proyecto, y valida el arreglo.",
    ]
    return "\n".join(extra)


# ----------------------------------------------------------------------- canales
def _popup_windows(titulo, mensaje):
    """Ventana emergente NO bloqueante (proceso aparte para que sobreviva al bot)."""
    if os.name != "nt":
        return
    try:
        env = dict(os.environ, VELAS_T=titulo, VELAS_M=mensaje[:600])
        ps = ("Add-Type -AssemblyName PresentationFramework;"
              "[void][System.Windows.MessageBox]::Show($env:VELAS_M,$env:VELAS_T,'OK','Warning')")
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                         env=env, creationflags=0x00000008 | 0x08000000,  # DETACHED | NO_WINDOW
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        _p(f"[NUCLEO] Popup no disponible: {e}")


def _telegram(texto, foto=None):
    cfg = config.cargar()
    token, chat = cfg.get("telegram_token"), cfg.get("telegram_chat_id")
    if not token or not chat:
        return False
    base = f"https://api.telegram.org/bot{token}"
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": texto[:3900]}).encode()
        urllib.request.urlopen(urllib.request.Request(f"{base}/sendMessage", data=data), timeout=10).read()

        if foto and os.path.exists(foto):
            borde = uuid.uuid4().hex
            with open(foto, "rb") as f:
                contenido = f.read()
            tipo = mimetypes.guess_type(foto)[0] or "image/png"
            cuerpo = (
                f"--{borde}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat}\r\n"
                f"--{borde}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"captura.png\"\r\n"
                f"Content-Type: {tipo}\r\n\r\n"
            ).encode() + contenido + f"\r\n--{borde}--\r\n".encode()
            req = urllib.request.Request(f"{base}/sendPhoto", data=cuerpo,
                                         headers={"Content-Type": f"multipart/form-data; boundary={borde}"})
            urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as e:
        _p(f"[NUCLEO] Telegram falló: {e}")
        return False


# ----------------------------------------------------------------------- entrada
def procesar(rep, ruta_json):
    v = rep["veredicto"]
    linea = "=" * 70
    _p(f"\n{linea}\n {ICONOS.get(v, '')} VEREDICTO NUCLEO [{rep['proyecto']}]: {v}")
    if rep["cobertura"] == "solo_consola" and v == "OK":
        _p("  (Este proyecto aún no tiene verificaciones de negocio: solo se vigiló consola/excepciones.)")
    for x in [x for x in rep["verificaciones"] if not x["ok"]]:
        _p(f"  ✘ {x['nombre']}: esperado='{x['esperado']}' obtenido='{x['obtenido']}'")
    _p(f"{linea}\n")

    if v == "OK":
        return

    cfg = config.cargar()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    texto = formatear(rep)

    try:
        with open(LOG_ALERTAS, "a", encoding="utf-8") as f:
            f.write(f"[{ahora}] {rep['proyecto']} -> {v} | {ruta_json}\n")
        with open(ULTIMA_ALERTA, "w", encoding="utf-8") as f:
            f.write(texto)
        with open(ULTIMO_DIAGNOSTICO, "w", encoding="utf-8") as f:
            f.write(_diagnostico_para_agente(rep, ruta_json))
    except Exception as e:
        _p(f"[NUCLEO] No se pudo escribir la bitácora: {e}")

    _p(f"  📄 Diagnóstico completo: {ULTIMO_DIAGNOSTICO}")

    grave = v in ("FALLO", "FALLO_SILENCIOSO")
    if grave and cfg.get("popup_windows", True):
        resumen = f"{rep['proyecto']}: {TITULOS[v]}\n\nRevisa NUCLEO/ULTIMO_DIAGNOSTICO.md"
        _popup_windows(f"VELAS · {v}", resumen)

    if grave or cfg.get("notificar_advertencias", True):
        foto = rep["capturas"][-1]["png"] if rep["capturas"] else None
        if _telegram(texto, foto):
            _p("  📨 Alerta enviada a Telegram.")

