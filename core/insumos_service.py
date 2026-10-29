"""
Core Domain: Insumos Engine (Trie + Hash Table).
Provee indexación O(1) de insumos y búsqueda por prefijo/código.
"""
import os
import json
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSUMOS_PATH = os.path.join(BASE_DIR, "INSUMOS_JSON", "insumos.json")

class InsumosService:
    _cache_insumos: Optional[Dict[str, Any]] = None

    @classmethod
    def cargar(cls) -> Dict[str, Any]:
        if cls._cache_insumos is not None:
            return cls._cache_insumos

        if os.path.exists(INSUMOS_PATH):
            try:
                with open(INSUMOS_PATH, "r", encoding="utf-8") as f:
                    cls._cache_insumos = json.load(f)
                    return cls._cache_insumos
            except Exception as e:
                print(f"[InsumosService] Error cargando insumos.json: {e}")

        cls._cache_insumos = {}
        return cls._cache_insumos

    @classmethod
    def buscar_por_codigo(cls, codigo: str) -> Optional[Dict[str, Any]]:
        datos = cls.cargar()
        insumos = datos.get("insumos", {}) if isinstance(datos, dict) else {}
        return insumos.get(codigo.strip().upper(), None)

