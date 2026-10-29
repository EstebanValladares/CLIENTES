"""Lanzador: ejecuta un script de proyecto con telemetría automática, SIN modificarlo.

    python NUCLEO/lanzador.py <PROYECTO> [script.py]

Qué añade a cualquier bot (incluso los que no están instrumentados):
  * Vigila la consola en vivo (tee transparente) y detecta líneas de error/aviso aunque
    el proceso termine con exit code 0.
  * Captura excepciones no controladas y exit codes != 0.
  * Registra automáticamente el WebDriver de Selenium para poder tomar captura al fallar.
  * Genera el reporte JSON + alertas mediante NUCLEO.telemetria.

Es transparente: input() sigue funcionando, el navegador se queda abierto, etc.
"""
import os
import runpy
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from NUCLEO import telemetria as tel  # noqa: E402


class _Tee:
    """Duplica stdout/stderr hacia el reporte sin alterar nada de lo que ve el usuario."""

    def __init__(self, destino, rep):
        self._destino = destino
        self._rep = rep
        self._buffer = ""

    def write(self, texto):
        n = self._destino.write(texto)
        try:
            self._buffer += texto
            while "\n" in self._buffer:
                linea, self._buffer = self._buffer.split("\n", 1)
                if tel._RX_ANOMALIA.search(linea):
                    self._rep.anomalia_consola(linea)
        except Exception:
            pass
        return n

    def flush(self):
        return self._destino.flush()

    def __getattr__(self, nombre):  # encoding, isatty, fileno, reconfigure...
        return getattr(self._destino, nombre)


def _enganchar_selenium():
    """Registra cada WebDriver creado para poder capturar pantalla ante un fallo."""
    try:
        from selenium.webdriver.remote.webdriver import WebDriver
    except Exception:
        return
    original = WebDriver.__init__

    def init(self, *a, **kw):
        original(self, *a, **kw)
        tel.registrar_driver(self)

    WebDriver.__init__ = init


def ejecutar(proyecto, script="main.py"):
    dir_proyecto = os.path.join(RAIZ, proyecto)
    ruta_script = os.path.join(dir_proyecto, script)
    if not os.path.exists(ruta_script):
        print(f"[NUCLEO] No existe {ruta_script}")
        return 2

    rep = tel.iniciar(f"{proyecto}" if script == "main.py" else f"{proyecto}.{os.path.splitext(script)[0]}")
    rep.gestionado_por_lanzador = True

    os.chdir(dir_proyecto)
    sys.path.insert(0, dir_proyecto)
    sys.argv = [ruta_script]

    sys.stdout = _Tee(sys.stdout, rep)
    sys.stderr = _Tee(sys.stderr, rep)
    # Selenium se importa desde el venv del proyecto: el gancho se instala al primer import.
    _enganchar_selenium()

    codigo = 0
    try:
        runpy.run_path(ruta_script, run_name="__main__")
    except SystemExit as e:
        codigo = e.code if isinstance(e.code, int) else (0 if e.code in (None, 0) else 1)
    except KeyboardInterrupt:
        rep.registrar_excepcion()
        codigo = 130
    except BaseException:
        rep.registrar_excepcion()
        codigo = 1
    finally:
        # Restaura streams para que el banner final no pase por el tee.
        sys.stdout = getattr(sys.stdout, "_destino", sys.stdout)
        sys.stderr = getattr(sys.stderr, "_destino", sys.stderr)

    if rep.excepcion:
        rep.capturar(motivo="Excepción no controlada")
    rep.finalizar(exit_code=codigo)
    return codigo if codigo else (3 if rep.veredicto in ("FALLO", "FALLO_SILENCIOSO") else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(ejecutar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "main.py"))

