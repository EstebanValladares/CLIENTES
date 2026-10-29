"""Telemetría estructurada: convierte la ejecución de un bot en un reporte verificable.

Idea central: el veredicto NO sale de lo que imprime la consola, sale de
VERIFICACIONES DE NEGOCIO (¿el dato quedó realmente en pantalla/sistema?).

Uso típico dentro de un proyecto:

    from NUCLEO import telemetria as tel
    rep = tel.iniciar("CREACION_USUARIOS")
    tel.registrar_driver(driver)

    rep.paso("Asignar grupo", ok=exito, componente="select2-formControl_Grupo-container")
    rep.verificar("Casilla Activo", esperado=True, obtenido=checkbox.is_selected(),
                  componente="formControl_usuarios_Estatus")
    rep.finalizar()          # opcional; si no se llama, se finaliza al salir

Veredictos:
    OK                 todo verificado y sin incidencias
    ADVERTENCIA        hubo pasos fallidos/avisos pero ninguna verificación crítica falló
    FALLO_SILENCIOSO   exit code 0 PERO una verificación crítica falló (la consola "mentía")
    FALLO              excepción no controlada o exit code distinto de 0
"""
import atexit
import datetime
import json
import os
import platform
import re
import sys
import time
import traceback
import unicodedata

from NUCLEO import config

NUCLEO_DIR = config.NUCLEO_DIR
DIR_REPORTES = os.path.join(NUCLEO_DIR, "reportes")
DIR_CAPTURAS = os.path.join(NUCLEO_DIR, "capturas")

# Líneas de consola que delatan un problema aunque el proceso termine "bien".
PATRONES_ANOMALIA = [
    r"\[ERROR", r"\[AVISO", r"Traceback \(most recent", r"\bError al\b",
    r"No se pudo", r"No se encontr[óo] ", r"Abortando", r"\bExcepci[óo]n\b",
]
_RX_ANOMALIA = re.compile("|".join(PATRONES_ANOMALIA), re.IGNORECASE)

_reporte_actual = None
_driver_actual = None


def _imprimir_seguro(texto):
    """print() que NUNCA lanza excepción (consolas cp1252 no soportan ✔/✘/emojis)."""
    try:
        print(texto)
    except Exception:
        try:
            print(str(texto).encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass


def _norm(texto):
    """Minúsculas, sin acentos y sin espacios sobrantes (comparaciones tolerantes)."""
    texto = unicodedata.normalize("NFKD", str(texto if texto is not None else ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().casefold()


class Reporte:
    def __init__(self, proyecto, ruta=None):
        self.proyecto = proyecto
        self.inicio = time.time()
        self.fin = None
        self.pasos = []
        self.verificaciones = []
        self.capturas = []
        self.consola_anomalias = []
        self.excepcion = None
        self.exit_code = None
        self.veredicto = None
        self.analisis_vision = None
        self.impacto = []
        self.gestionado_por_lanzador = False
        self._finalizado = False
        self._marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.ruta = ruta or os.environ.get("VELAS_REPORTE_PATH") or os.path.join(
            DIR_REPORTES, f"{proyecto}_{self._marca}.json")

    # ------------------------------------------------------------------ registro
    def paso(self, nombre, ok=True, componente=None, detalle=""):
        """Registra una acción del bot. `ok=False` NO detiene nada; solo deja evidencia."""
        self.pasos.append({
            "nombre": nombre, "estado": "ok" if ok else "fallo",
            "componente": componente, "detalle": str(detalle)[:500],
            "t": round(time.time() - self.inicio, 2),
        })
        return ok

    def verificar(self, nombre, esperado, obtenido, ok=None, critica=True,
                  componente=None, modo="igual"):
        """Compara lo ESPERADO con lo REALMENTE observado en el sistema.

        modo: "igual" | "contiene" (esperado dentro de obtenido) | "numero" (igualdad numérica)
        """
        if ok is None:
            if modo == "contiene":
                ok = _norm(esperado) in _norm(obtenido)
            elif modo == "numero":
                try:
                    ok = int(esperado) == int(obtenido)
                except (TypeError, ValueError):
                    ok = False
            else:
                ok = _norm(esperado) == _norm(obtenido)
        self.verificaciones.append({
            "nombre": nombre, "esperado": str(esperado), "obtenido": str(obtenido),
            "ok": bool(ok), "critica": bool(critica), "componente": componente,
            "t": round(time.time() - self.inicio, 2),
        })
        icono = "✔" if ok else "✘"
        _imprimir_seguro(f"    [VERIFICACIÓN {icono}] {nombre}: esperado='{esperado}' | obtenido='{obtenido}'")
        return bool(ok)

    def anomalia_consola(self, linea):
        if len(self.consola_anomalias) < 60:
            self.consola_anomalias.append(linea.strip()[:300])

    def registrar_excepcion(self, exc_type=None, exc=None, tb=None):
        if exc is None:
            exc_type, exc, tb = sys.exc_info()
        if exc is None:
            return
        self.excepcion = "".join(traceback.format_exception(exc_type, exc, tb))[-4000:]

    def capturar(self, driver=None, motivo=""):
        """Guarda captura de pantalla + HTML de la página. Nunca lanza excepciones."""
        driver = driver or _driver_actual
        if driver is None:
            return None
        try:
            os.makedirs(DIR_CAPTURAS, exist_ok=True)
            base = os.path.join(DIR_CAPTURAS, f"{self.proyecto}_{self._marca}_{len(self.capturas) + 1}")
            png = base + ".png"
            driver.save_screenshot(png)
            registro = {"png": png, "motivo": motivo}
            try:
                registro["url"] = driver.current_url
                registro["titulo"] = driver.title
                with open(base + ".html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                registro["html"] = base + ".html"
            except Exception:
                pass
            self.capturas.append(registro)
            return png
        except Exception as e:
            print(f"[NUCLEO] No se pudo tomar captura: {e}")
            return None

    # ------------------------------------------------------------------ veredicto
    def _calcular_veredicto(self):
        crit_falla = [v for v in self.verificaciones if v["critica"] and not v["ok"]]
        pasos_falla = [p for p in self.pasos if p["estado"] == "fallo"]
        if self.excepcion or (self.exit_code not in (None, 0)):
            return "FALLO"
        if crit_falla:
            return "FALLO_SILENCIOSO"
        if pasos_falla or self.consola_anomalias or any(not v["ok"] for v in self.verificaciones):
            return "ADVERTENCIA"
        return "OK"

    def componentes_fallidos(self):
        comps = []
        for p in self.pasos:
            if p["estado"] == "fallo" and p["componente"]:
                comps.append(p["componente"])
        for v in self.verificaciones:
            if not v["ok"] and v["componente"]:
                comps.append(v["componente"])
        return sorted(set(comps))

    def a_dict(self):
        return {
            "proyecto": self.proyecto,
            "veredicto": self.veredicto,
            "cobertura": "instrumentado" if (self.pasos or self.verificaciones) else "solo_consola",
            "inicio": datetime.datetime.fromtimestamp(self.inicio).isoformat(timespec="seconds"),
            "duracion_s": round((self.fin or time.time()) - self.inicio, 1),
            "exit_code": self.exit_code,
            "excepcion": self.excepcion,
            "pasos": self.pasos,
            "verificaciones": self.verificaciones,
            "consola_anomalias": self.consola_anomalias,
            "capturas": self.capturas,
            "componentes_fallidos": self.componentes_fallidos(),
            "impacto": self.impacto,
            "analisis_vision": self.analisis_vision,
            "entorno": {"python": platform.python_version(), "so": platform.platform()},
        }

    # ------------------------------------------------------------------ cierre
    def finalizar(self, exit_code=None):
        """Idempotente. Calcula el veredicto, guarda el JSON y dispara las alertas."""
        if self._finalizado:
            return self.veredicto
        self._finalizado = True
        self.fin = time.time()
        if exit_code is not None:
            self.exit_code = exit_code
        elif self.exit_code is None:
            self.exit_code = 1 if self.excepcion else 0

        self.veredicto = self._calcular_veredicto()

        # Evidencia visual automática cuando algo salió mal y aún hay navegador.
        if self.veredicto != "OK" and not self.capturas:
            self.capturar(motivo=f"Veredicto {self.veredicto}")

        # Memoria de fallos + análisis de impacto en el grafo (no debe romper nada).
        try:
            from NUCLEO import grafo
            comps = self.componentes_fallidos()
            if comps:
                grafo.registrar_fallos(self.proyecto, comps)
                self.impacto = grafo.impacto_de_componentes(comps, excluir=self.proyecto)
        except Exception as e:
            print(f"[NUCLEO] Grafo no disponible: {e}")

        # Ojos de IA sobre la captura (opcional, requiere API key).
        if self.veredicto != "OK" and self.capturas:
            try:
                from NUCLEO import vision
                self.analisis_vision = vision.analizar_captura(self.capturas[-1]["png"], self.a_dict())
            except Exception as e:
                print(f"[NUCLEO] Visión no disponible: {e}")

        self._guardar()

        try:
            from NUCLEO import notificador
            notificador.procesar(self.a_dict(), self.ruta)
        except Exception as e:
            print(f"[NUCLEO] No se pudo notificar: {e}")
        return self.veredicto

    def _guardar(self):
        try:
            os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
            datos = self.a_dict()
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            os.makedirs(DIR_REPORTES, exist_ok=True)
            resumen = {k: datos[k] for k in ("proyecto", "veredicto", "inicio", "duracion_s", "cobertura")}
            resumen["componentes_fallidos"] = datos["componentes_fallidos"]
            resumen["reporte"] = self.ruta
            with open(os.path.join(DIR_REPORTES, "historial.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(resumen, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[NUCLEO] No se pudo guardar el reporte: {e}")


# ---------------------------------------------------------------------- singleton
def _limpiar_capturas_viejas():
    dias = config.cargar().get("dias_retencion_capturas", 30)
    if not os.path.isdir(DIR_CAPTURAS):
        return
    limite = time.time() - dias * 86400
    for nombre in os.listdir(DIR_CAPTURAS):
        ruta = os.path.join(DIR_CAPTURAS, nombre)
        try:
            if os.path.getmtime(ruta) < limite:
                os.remove(ruta)
        except OSError:
            pass


def iniciar(proyecto, ruta=None):
    """Crea (o devuelve) el reporte de la ejecución actual. Idempotente."""
    global _reporte_actual
    if _reporte_actual is not None:
        return _reporte_actual

    _reporte_actual = Reporte(proyecto, ruta)
    _limpiar_capturas_viejas()

    hook_previo = sys.excepthook

    def _hook(tipo, exc, tb):
        if _reporte_actual and not _reporte_actual.gestionado_por_lanzador:
            _reporte_actual.registrar_excepcion(tipo, exc, tb)
        hook_previo(tipo, exc, tb)

    sys.excepthook = _hook
    # Si nadie llama finalizar() (ejecución directa sin lanzador), se hace al salir.
    atexit.register(lambda: _reporte_actual and not _reporte_actual.gestionado_por_lanzador
                    and _reporte_actual.finalizar())
    return _reporte_actual


def actual():
    """Reporte en curso. Si no hay uno, crea uno 'ANONIMO' para no romper llamadas."""
    return _reporte_actual or iniciar(os.path.basename(os.getcwd()) or "ANONIMO")


def registrar_driver(driver):
    global _driver_actual
    _driver_actual = driver


def driver_actual():
    return _driver_actual
