"""
Adaptador de Telemetría hacia NUCLEO para PROYECTOS.
Implementa el patrón Null Object (_ReporteNulo) para funcionar de forma autónoma
si NUCLEO no está disponible en el entorno.
"""
import sys
from typing import Any
from PROYECTOS.selectores import ECOSYSTEM_DIR

try:
    if str(ECOSYSTEM_DIR) not in sys.path:
        sys.path.insert(0, str(ECOSYSTEM_DIR))
    from NUCLEO import telemetria as _tel
except Exception:
    _tel = None


class _ReporteNulo:
    """Objeto nulo que absorbe llamadas de telemetría cuando NUCLEO no está activo."""
    verificaciones: list[dict[str, Any]] = []

    def __getattr__(self, _nombre: str) -> Any:
        return lambda *a, **k: True


def rep() -> Any:
    """Devuelve el reporte de telemetría de la ejecución actual (o un shim nulo)."""
    try:
        return _tel.actual() if _tel else _ReporteNulo()
    except Exception:
        return _ReporteNulo()


def registrar_navegador(driver: Any, proyecto: str = "PROYECTOS") -> None:
    """Inicia el reporte del proyecto y registra el navegador para capturas automáticas."""
    try:
        if _tel:
            _tel.iniciar(proyecto)
            _tel.registrar_driver(driver)
    except Exception:
        pass


def finalizar_telemetria() -> Any:
    """Cierra el reporte: calcula el veredicto real, guarda el JSON y dispara alertas."""
    try:
        return rep().finalizar()
    except Exception:
        return None
