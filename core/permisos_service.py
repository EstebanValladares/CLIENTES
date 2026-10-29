"""
Core Domain: Servicios de Permisos Proyectos (Depuración de Obras y Usuarios Protegidos).
Lee y escribe ENKONTROL.TXT y obras_permisos.json de forma segura.
"""
import os
import json
from typing import Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIR_PERMISOS = os.path.join(BASE_DIR, "PROYECTOS")
RUTA_OBRAS_JSON = os.path.join(DIR_PERMISOS, "obras_permisos.json")
RUTA_ENKONTROL_TXT = os.path.join(DIR_PERMISOS, "ENKONTROL.TXT")
RUTA_LOG_DEPURACION = os.path.join(DIR_PERMISOS, "log_depuracion.txt")

class PermisosService:
    @classmethod
    def obtener_datos(cls) -> Dict[str, Any]:
        usuarios = []
        if os.path.exists(RUTA_ENKONTROL_TXT):
            try:
                with open(RUTA_ENKONTROL_TXT, "r", encoding="utf-8") as f:
                    usuarios = [line.strip().upper() for line in f if line.strip()]
            except Exception:
                pass

        obras = []
        if os.path.exists(RUTA_OBRAS_JSON):
            try:
                with open(RUTA_OBRAS_JSON, "r", encoding="utf-8") as f:
                    obras = json.load(f)
            except Exception:
                pass

        return {
            "usuarios_protegidos": usuarios,
            "obras": obras
        }

    @classmethod
    def guardar_datos(cls, usuarios: List[str], obras: List[str]) -> bool:
        try:
            with open(RUTA_ENKONTROL_TXT, "w", encoding="utf-8") as f:
                for u in usuarios:
                    f.write(f"{u.strip().upper()}\n")
            with open(RUTA_OBRAS_JSON, "w", encoding="utf-8") as f:
                json.dump([o.strip().upper() for o in obras if o.strip()], f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PermisosService] Error guardando: {e}")
            return False

    @classmethod
    def obtener_log_historial(cls) -> str:
        if os.path.exists(RUTA_LOG_DEPURACION):
            try:
                with open(RUTA_LOG_DEPURACION, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return ""
