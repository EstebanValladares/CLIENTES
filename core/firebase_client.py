"""
Core Domain: Gestor Centralizado de Datos Locales para Dashboard EK10.
Mantiene compatibilidad con módulos existentes operando 100% de manera autónoma
y en memoria RAM, sin requerir dependencias ni conexiones externas a Firebase.
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIR_USUARIOS_DATA = os.path.join(BASE_DIR, "USUARIOS", "data")
PUESTOS_LOCAL_PATH = (
    os.path.join(DIR_USUARIOS_DATA, "puestos.json")
    if os.path.exists(os.path.join(DIR_USUARIOS_DATA, "puestos.json"))
    else os.path.join(BASE_DIR, "USUARIOS", "puestos.json")
)


class FirebaseClient:
    """Cliente unificado para compatibilidad retrocompatible de catálogos locales."""
    _lock = threading.Lock()
    _cache_puestos: Dict[str, Any] = {}
    _ultimo_fetch_puestos: float = 0

    @classmethod
    def get_db(cls):
        """Retorna None ya que el sistema opera 100% de forma autónoma en local."""
        return None

    # =========================================================================
    # MÓDULO USUARIOS: PUESTOS Y CLASIFICADORES (100% LOCAL)
    # =========================================================================
    @classmethod
    def obtener_puestos(cls, forzar: bool = False) -> Dict[str, Any]:
        """Obtiene el catálogo completo de puestos desde puestos.json local."""
        with cls._lock:
            if not forzar and cls._cache_puestos:
                return dict(cls._cache_puestos)

            if os.path.exists(PUESTOS_LOCAL_PATH):
                try:
                    with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        puestos = data.get("puestos", {})
                        cls._cache_puestos = puestos
                        cls._ultimo_fetch_puestos = time.time()
                        return dict(puestos)
                except Exception as e:
                    print(f"[FirebaseClient] Error leyendo puestos.json local: {e}")
            return {}

    @classmethod
    def obtener_puesto_por_nombre(cls, nombre: str) -> Optional[Dict[str, Any]]:
        """Busca la configuración de un puesto específico en puestos.json local."""
        puestos = cls.obtener_puestos()
        nombre_clean = str(nombre).strip().upper()
        if nombre_clean in puestos:
            return puestos[nombre_clean]

        for k, v in puestos.items():
            if k.upper() == nombre_clean:
                return v
        return None

    @classmethod
    def guardar_puesto(
        cls,
        nombre: str,
        area: str,
        niveles: list,
        grupos: list,
        clasificadores: dict
    ) -> Dict[str, Any]:
        """Guarda un nuevo puesto o actualiza uno existente en puestos.json local."""
        nombre_limpio = nombre.strip().upper()
        if not nombre_limpio:
            return {"ok": False, "error": "El nombre del puesto no puede estar vacío."}

        conteo_abuelos = {}
        conteo_total = 0
        for k, v in clasificadores.items():
            sub = len(v) if isinstance(v, list) else 0
            conteo_abuelos[k] = sub
            conteo_total += sub

        nuevo_puesto_data = {
            "nombre": nombre_limpio,
            "area_organizacional": area.strip().upper(),
            "total_clasificadores": conteo_total,
            "resumen_clasificadores_por_abuelo": conteo_abuelos,
            "niveles_asignados": niveles,
            "grupos": grupos,
            "clasificadores": clasificadores,
            "actualizado_en": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            os.makedirs(os.path.dirname(PUESTOS_LOCAL_PATH), exist_ok=True)
            datos_loc = {"_comentario": "Catálogo oficial local de puestos", "puestos": {}}
            if os.path.exists(PUESTOS_LOCAL_PATH):
                try:
                    with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                        datos_loc = json.load(f)
                except Exception:
                    pass

            if "puestos" not in datos_loc:
                datos_loc["puestos"] = {}

            datos_loc["puestos"][nombre_limpio] = nuevo_puesto_data
            datos_loc["ultima_actualizacion"] = time.strftime("%Y-%m-%d %H:%M:%S")

            with open(PUESTOS_LOCAL_PATH, "w", encoding="utf-8") as f:
                json.dump(datos_loc, f, indent=2, ensure_ascii=False)

            with cls._lock:
                cls._cache_puestos[nombre_limpio] = nuevo_puesto_data

            return {
                "ok": True,
                "offline": True,
                "mensaje": f"Puesto '{nombre_limpio}' guardado exitosamente en el catálogo local."
            }
        except Exception as e_loc:
            print(f"[FirebaseClient] Error guardando puesto local: {e_loc}")
            return {"ok": False, "error": str(e_loc)}

    @classmethod
    def sincronizar_puestos(cls) -> Dict[str, Any]:
        """Recarga el catálogo local de puestos."""
        puestos = cls.obtener_puestos(forzar=True)
        return {
            "ok": True,
            "total": len(puestos),
            "mensaje": f"Catálogo local recargado con {len(puestos)} puestos."
        }

    @classmethod
    def obtener_estado_sincronizacion_puestos(cls) -> Dict[str, Any]:
        """Retorna el estado operativo autónomo del catálogo local."""
        puestos = cls.obtener_puestos()
        return {
            "firebase_online": False,
            "total_puestos": len(puestos),
            "total_puestos_local": len(puestos),
            "pendientes_subir": 0,
            "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "modo": "100% Local Autónomo (Llave Maestra)"
        }

    @classmethod
    def sincronizar_usuarios_a_firestore(cls, usuarios: list) -> bool:
        """No-op: los usuarios se gestionan 100% de forma autónoma en Usuarios.json."""
        return True

    @classmethod
    def sincronizar_obras_a_firestore(cls, obras_resultado: dict) -> bool:
        """No-op: las obras se gestionan 100% de forma autónoma en obras.json."""
        return True
