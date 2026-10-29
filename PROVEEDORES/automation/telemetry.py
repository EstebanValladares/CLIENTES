"""
Adaptador de Telemetría hacia NUCLEO para `iniciar_dashboard_v2`.
Alimenta las métricas globales (/api/metricas -> NUCLEO/reportes/historial.jsonl)
y permite operar de forma autónoma si NUCLEO no está presente.
"""
import sys
from typing import Any

from config.settings import ECOSYSTEM_DIR

try:
    if str(ECOSYSTEM_DIR) not in sys.path:
        sys.path.append(str(ECOSYSTEM_DIR))
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


def registrar_navegador(driver: Any, proyecto: str = "PROVEEDORES") -> None:
    """Inicia el reporte del proyecto en NUCLEO y registra el navegador."""
    try:
        if _tel:
            _tel.iniciar(proyecto)
            _tel.registrar_driver(driver)
    except Exception:
        pass


def finalizar_telemetria() -> Any:
    """Cierra el reporte en NUCLEO: calcula el veredicto y actualiza historial.jsonl."""
    try:
        return rep().finalizar()
    except Exception:
        return None

