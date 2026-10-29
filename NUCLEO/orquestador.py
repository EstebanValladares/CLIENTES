"""Orquestador maestro del ecosistema VELAS.

    python NUCLEO/orquestador.py ejecutar <PROYECTO> [script.py]   # pre-flight + ejecución vigilada
    python NUCLEO/orquestador.py salud                             # estado de todos los proyectos
    python NUCLEO/orquestador.py historial [N]                     # últimas N ejecuciones
    python NUCLEO/orquestador.py grafo                             # reconstruye el grafo del ecosistema

Ciclo de cada ejecución:
    1. PRE-FLIGHT : archivos de entrada presentes + portal Aryve accesible
    2. EJECUCIÓN  : lanzador.py (consola vigilada, excepciones, captura de pantalla)
    3. POST-FLIGHT: lee el reporte, decide el veredicto REAL y alerta si no es OK
"""
import datetime
import json
import os
import socket
import subprocess
import sys
import urllib.parse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from NUCLEO import config, telemetria as tel  # noqa: E402

LANZADOR = os.path.join(config.NUCLEO_DIR, "lanzador.py")
CATALOGO = os.path.join(config.NUCLEO_DIR, "proyectos.json")


def _p(t=""):
    try:
        print(t)
    except UnicodeEncodeError:
        print(t.encode("ascii", "replace").decode("ascii"))


def catalogo():
    try:
        with open(CATALOGO, "r", encoding="utf-8") as f:
            return json.load(f).get("proyectos", {})
    except Exception:
        return {}


def python_de(proyecto):
    base = os.path.join(RAIZ, proyecto)
    for rel in (".venv/Scripts/python.exe", ".venv/bin/python.exe", ".venv/bin/python",
                "venv/Scripts/python.exe", "venv/bin/python.exe", "venv/bin/python"):
        ruta = os.path.join(base, *rel.split("/"))
        if os.path.exists(ruta):
            return ruta
    return sys.executable


# ----------------------------------------------------------------------- pre-flight
def portal_accesible(timeout=5):
    """Prueba TCP al host:puerto del portal (robusto ante certificados autofirmados)."""
    url = urllib.parse.urlparse(config.cargar()["url_portal"])
    puerto = url.port or (443 if url.scheme == "https" else 80)
    try:
        with socket.create_connection((url.hostname, puerto), timeout=timeout):
            return True, f"{url.hostname}:{puerto}"
    except OSError as e:
        return False, f"{url.hostname}:{puerto} ({e})"


def preflight(proyecto, verbose=True):
    """Devuelve (ok, problemas[], avisos[])."""
    meta = catalogo().get(proyecto, {})
    problemas, avisos = [], []
    dir_p = os.path.join(RAIZ, proyecto)

    if not os.path.isdir(dir_p):
        return False, [f"La carpeta del proyecto '{proyecto}' no existe"], avisos

    script = meta.get("script", "main.py")
    if not os.path.exists(os.path.join(dir_p, script)):
        problemas.append(f"Falta el script principal {script}")

    def evaluar(arch):
        """Devuelve (problema, aviso) para UN archivo concreto."""
        ruta = os.path.join(dir_p, arch)
        if not os.path.exists(ruta):
            return f"Falta el archivo de entrada: {arch}", None
        if os.path.getsize(ruta) == 0:
            return f"El archivo de entrada está vacío: {arch}", None
        if arch.lower().endswith(".csv"):
            with open(ruta, "r", encoding="utf-8-sig", errors="replace") as f:
                filas = [l for l in f if l.strip()]
            if len(filas) < 2:
                return None, f"{arch} solo tiene encabezado, no hay registros que procesar"
        elif arch.lower().endswith(".json"):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                return f"{arch} no es un JSON válido: {e}", None
        return None, None

    for requisito in meta.get("requiere_archivos", []):
        # "a.json|b.json" = basta con que UNO sea válido (ej. obras_pendientes.json o obras.json)
        alternativas = [a.strip() for a in requisito.split("|")]
        resultados = [(a,) + evaluar(a) for a in alternativas]
        if any(p is None for _, p, _ in resultados):
            for a, p, av in resultados:
                if av:
                    avisos.append(av)
            for a, p, _ in resultados:
                if p and not p.startswith("Falta"):  # existe pero está mal: avisar sin bloquear
                    avisos.append(f"{p} (no bloquea: existe otra alternativa válida)")
        else:
            problemas.extend(p for _, p, _ in resultados if p)

    if meta.get("usa_portal", True):
        ok, det = portal_accesible()
        if not ok:
            problemas.append(f"El portal Aryve no responde ({det})")

    if verbose:
        for a in avisos:
            _p(f"  ⚠️  {a}")
    return not problemas, problemas, avisos


# ----------------------------------------------------------------------- ejecución
def ejecutar(proyecto, script=None, saltar_preflight=False):
    meta = catalogo().get(proyecto, {})
    script = script or meta.get("script", "main.py")
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_rep = proyecto if script == meta.get("script", "main.py") else f"{proyecto}.{os.path.splitext(script)[0]}"
    ruta_reporte = os.path.join(tel.DIR_REPORTES, f"{nombre_rep}_{marca}.json")

    if not saltar_preflight:
        _p(f"\n🔎 PRE-FLIGHT [{proyecto}]")
        ok, problemas, _ = preflight(proyecto)
        if not ok:
            # Aborta ANTES de abrir el navegador y deja evidencia/alerta como cualquier fallo.
            rep = tel.Reporte(nombre_rep, ruta_reporte)
            for pr in problemas:
                rep.verificar("Pre-flight", "sin problemas", pr, ok=False, critica=True)
            rep.excepcion = "Ejecución abortada en pre-flight:\n- " + "\n- ".join(problemas)
            rep.finalizar(exit_code=2)
            return {"veredicto": "FALLO", "reporte": ruta_reporte, "motivo": "preflight"}
        _p("  ✔ Todo en orden, lanzando el bot.\n")

    env = dict(os.environ, VELAS_REPORTE_PATH=ruta_reporte)
    subprocess.run([python_de(proyecto), LANZADOR, proyecto, script], cwd=RAIZ, env=env)

    veredicto = "DESCONOCIDO"
    if os.path.exists(ruta_reporte):
        try:
            with open(ruta_reporte, "r", encoding="utf-8") as f:
                veredicto = json.load(f).get("veredicto", "DESCONOCIDO")
        except Exception:
            pass
    else:
        # El proceso murió sin dejar reporte (crash duro): también es un fallo.
        rep = tel.Reporte(nombre_rep, ruta_reporte)
        rep.excepcion = "El proceso terminó sin generar reporte (cierre abrupto o crash del intérprete)."
        rep.finalizar(exit_code=1)
        veredicto = "FALLO"
    return {"veredicto": veredicto, "reporte": ruta_reporte}


# ----------------------------------------------------------------------- salud / historial
def salud():
    _p("\n" + "=" * 70 + "\n  🩺 SALUD DEL ECOSISTEMA VELAS\n" + "=" * 70)
    ok_portal, det = portal_accesible()
    _p(f"  {'✅' if ok_portal else '❌'} Portal Aryve: {det}")
    for nombre in catalogo():
        ok, problemas, avisos = preflight(nombre, verbose=False)
        estado = "✅ listo" if ok else "❌ " + "; ".join(problemas)
        extra = ("  ⚠️ " + "; ".join(avisos)) if avisos else ""
        _p(f"  {nombre:<26} {estado}{extra}")

    from NUCLEO import grafo
    g = grafo.construir()
    _p(f"\n  🕸️  Grafo: {len(g['nodos'])} nodos · {len(g['aristas'])} aristas")
    for id_, ps in grafo.compartidos(g)[:8]:
        _p(f"     compartido por {len(ps)}: {id_[:60]}  ->  {', '.join(ps)}")
    for id_, n in g["nodos"].items():
        if n["tipo"] == "referencia_rota":
            _p(f"     ⚠️ referencia a recurso inexistente: {id_.split(':', 1)[1]}")
    calientes = grafo.calientes(5)
    if calientes:
        _p("\n  🔥 Componentes que más fallan:")
        for comp, d in calientes:
            _p(f"     {d['fallos']:>3}× {comp}  {d['proyectos']}")
    historial(5)


def historial(n=10):
    ruta = os.path.join(tel.DIR_REPORTES, "historial.jsonl")
    if not os.path.exists(ruta):
        _p("\n  (Sin ejecuciones registradas todavía)")
        return
    with open(ruta, "r", encoding="utf-8") as f:
        filas = [json.loads(l) for l in f if l.strip()][-n:]
    icono = {"OK": "✅", "ADVERTENCIA": "⚠️", "FALLO_SILENCIOSO": "🕵️", "FALLO": "❌"}
    _p(f"\n  📜 Últimas {len(filas)} ejecuciones:")
    for r in filas:
        comp = f" · fallaron: {', '.join(r['componentes_fallidos'])}" if r.get("componentes_fallidos") else ""
        _p(f"   {icono.get(r['veredicto'], '?')} {r['inicio']} {r['proyecto']:<28} {r['veredicto']}{comp}")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "ejecutar" and len(argv) > 2:
        r = ejecutar(argv[2], argv[3] if len(argv) > 3 else None)
        return 0 if r["veredicto"] in ("OK", "ADVERTENCIA") else 3
    if cmd == "salud":
        salud()
    elif cmd == "historial":
        historial(int(argv[2]) if len(argv) > 2 else 10)
    elif cmd == "grafo":
        from NUCLEO import grafo
        grafo._cli(["grafo", "construir"])
    else:
        _p(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
