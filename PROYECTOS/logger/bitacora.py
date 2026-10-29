"""
Módulo de Bitácora y Auditoría para el flujo de Permisos en Proyectos.
Compatible con el streaming en tiempo real de BotRunnerService y el historial
de depuración de permisos (log_depuracion.txt).
"""
import time
from pathlib import Path
from typing import Callable, Optional

from PROYECTOS.selectores import RUTA_LOG


class ProjectLogger:
    def __init__(
        self,
        ruta_log: Optional[str | Path] = None,
        callback_log: Optional[Callable[[str], None]] = None,
    ):
        self.ruta_log = Path(ruta_log) if ruta_log is not None else RUTA_LOG
        self.callback_log = callback_log

    def iniciar_sesion_log(self) -> None:
        encabezado = (
            f"\n{'=' * 50}\n"
            f"EJECUCIÓN: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'=' * 50}\n"
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

