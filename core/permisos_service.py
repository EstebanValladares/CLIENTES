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
RUTA_DESASIGNACION_JSON = os.path.join(DIR_PERMISOS, "desasignacion_usuarios_obras.json")
RUTA_CONFIG_DESASIGNACION = os.path.join(DIR_PERMISOS, "desasignacion_config.json")

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

    @classmethod
    def obtener_desasignacion(cls) -> Dict[str, Any]:
        if os.path.exists(RUTA_DESASIGNACION_JSON):
            try:
                with open(RUTA_DESASIGNACION_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[PermisosService] Error leyendo {RUTA_DESASIGNACION_JSON}: {e}")
        return {
            "metadata": {},
            "usuarios": [],
            "lista_obras": [],
            "por_obra": {},
            "por_usuario": {}
        }

    @classmethod
    def guardar_desasignacion(cls, data: Dict[str, Any]) -> bool:
        try:
            with open(RUTA_DESASIGNACION_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PermisosService] Error guardando desasignacion: {e}")
            return False

    @classmethod
    def obtener_config_desasignacion(cls) -> Dict[str, Any]:
        if os.path.exists(RUTA_CONFIG_DESASIGNACION):
            try:
                with open(RUTA_CONFIG_DESASIGNACION, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"modo_prueba": True, "limite_obras": 1}

    @classmethod
    def guardar_config_desasignacion(cls, config: Dict[str, Any]) -> bool:
        try:
            with open(RUTA_CONFIG_DESASIGNACION, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PermisosService] Error guardando config desasignacion: {e}")
            return False

    @classmethod
    def remover_obra_cumplida(cls, clave_obra: str) -> bool:
        """Remueve una obra procesada y guardada del archivo de desasignación."""
        clave = str(clave_obra).strip().upper()
        data = cls.obtener_desasignacion()
        lista_obras = data.get("lista_obras", [])
        por_obra = data.get("por_obra", {})
        por_usuario = data.get("por_usuario", {})

        modificado = False
        if clave in por_obra:
            del por_obra[clave]
            modificado = True

        if clave in lista_obras:
            data["lista_obras"] = [o for o in lista_obras if o != clave]
            modificado = True

        for usr, obras_usr in por_usuario.items():
            antes = len(obras_usr)
            filtradas = [o for o in obras_usr if (o.get("proyecto") or "").upper() != clave]
            if len(filtradas) != antes:
                por_usuario[usr] = filtradas
                modificado = True

        if modificado:
            return cls.guardar_desasignacion(data)
        return True
