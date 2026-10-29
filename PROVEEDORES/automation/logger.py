"""
Gestor centralizado de bitácora compatible con el streaming en tiempo real
de `BotRunnerService` (stdout unbuffered), el callback en vivo de `ProveedoresService`
y el archivo histórico `log_proveedores.txt`.
"""
import time
from typing import Callable, Optional

from config.settings import RUTA_LOG


class ProveedorLogger:
    def __init__(
        self,
        ruta_log: str = RUTA_LOG,
        callback_log: Optional[Callable[[str], None]] = None,
    ):
        self.ruta_log = ruta_log
        self.callback_log = callback_log

    def iniciar_sesion_log(self) -> None:
        encabezado = (
            f"\n{'=' * 55}\n"
            f"EJECUCIÓN PROVEEDORES: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'=' * 55}\n"
        )
        self._escribir_archivo(encabezado, agregar_salto=False)

    def info(self, mensaje: str) -> None:
        self._emitir(str(mensaje))

    def aviso(self, mensaje: str) -> None:
        self._emitir(f"[AVISO]: {mensaje}")

    def error(self, mensaje: str) -> None:
        self._emitir(f"[ERROR]: {mensaje}")

    def _emitir(self, texto: str) -> None:
        try:
            print(texto, flush=True)
        except Exception:
            try:
                print(texto.encode("ascii", "replace").decode("ascii"), flush=True)
            except Exception:
                pass

        self._escribir_archivo(texto, agregar_salto=True)

        if self.callback_log:
            try:
                self.callback_log(texto)
            except Exception:
                pass

    def _escribir_archivo(self, texto: str, agregar_salto: bool = True) -> None:
        if not self.ruta_log:
            return
        try:
            with open(self.ruta_log, "a", encoding="utf-8") as f_log:
                f_log.write(texto + ("\n" if agregar_salto else ""))
        except Exception:
            pass

