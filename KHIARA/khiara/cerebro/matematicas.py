"""
Motor Matemático y Analítico Seguro de KHIARA.
Ejecuta cálculos, porcentajes, variaciones, estadísticas y fórmulas
usando NumPy y Python seguro para evitar alucinaciones numéricas.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List


class MotorMatematico:
    @staticmethod
    def calcular_variacion_porcentual(original: float, nuevo: float) -> Dict[str, Any]:
        """Calcula el cambio y porcentaje entre un valor base y uno ajustado."""
        diferencia = nuevo - original
        pct = (diferencia / original * 100.0) if original != 0 else 0.0
        return {
            "original": original,
            "nuevo": nuevo,
            "diferencia": round(diferencia, 4),
            "porcentaje_cambio": round(pct, 2),
            "direccion": "incremento" if diferencia > 0 else ("decremento" if diferencia < 0 else "sin cambio")
        }

    @staticmethod
    def estadisticas_serie(valores: List[float]) -> Dict[str, Any]:
        """Calcula métricas estadísticas descriptivas exactas de una lista numérica."""
        if not valores:
            return {"error": "Lista vacía"}
        arr = np.array(valores, dtype=float)
        return {
            "total_elementos": len(arr),
            "suma_total": round(float(np.sum(arr)), 4),
            "promedio": round(float(np.mean(arr)), 4),
            "mediana": round(float(np.median(arr)), 4),
            "minimo": round(float(np.min(arr)), 4),
            "maximo": round(float(np.max(arr)), 4),
            "desviacion_estandar": round(float(np.std(arr)), 4)
        }

    @staticmethod
    def evaluar_expresion_segura(expresion: str) -> Dict[str, Any]:
        """Evalúa fórmulas matemáticas de forma segura en un entorno aislado."""
        ambiente_seguro = {
            "math": math,
            "np": np,
            "abs": abs,
            "round": round,
            "sum": sum,
            "min": min,
            "max": max,
            "len": len,
            "pow": pow
        }
        try:
            resultado = eval(expresion, {"__builtins__": {}}, ambiente_seguro)
            return {"ok": True, "expresion": expresion, "resultado": resultado}
        except Exception as e:
            return {"ok": False, "expresion": expresion, "error": str(e)}
