"""
Core Domain: Servicio de Creación de Posiciones / Puestos en Aryve.
Maneja la ejecución asíncrona de Selenium para posiciones con streaming de logs,
permitiendo que la interfaz consulte el progreso sin congelarse.
"""
import os
import sys
import time
import threading
import datetime
from typing import Dict, Any, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUTA_USR = os.path.join(BASE_DIR, "USUARIOS")

if RUTA_USR not in sys.path:
    sys.path.insert(0, RUTA_USR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

class UserPositionService:
    _estado_actual = {
        "ejecutando": False,
        "ok": None,
        "mensaje": "Listo",
        "logs": []
    }
    _id_ejecucion = 0
    _lock = threading.Lock()

    @classmethod
    def obtener_estado(cls) -> Dict[str, Any]:
        """Consulta el progreso y logs de Selenium de la posición en curso."""
        return cls._estado_actual

    @classmethod
    def iniciar_alta_asincrona(
        cls,
        clave: str,
        nombre: str,
        categoria: str,
        padre: str = "",
        guardar_en_produccion: bool = False
    ) -> Tuple[bool, str]:
        """Inicia el bot de Selenium para crear una posición en segundo plano."""
        with cls._lock:
            if cls._estado_actual["ejecutando"]:
                return False, "Ya hay un proceso de alta de posición en ejecución."

            cls._id_ejecucion += 1
            id_local = cls._id_ejecucion

            cls._estado_actual = {
                "ejecutando": True,
                "ok": None,
                "mensaje": f"Iniciando Selenium para posición {clave.upper()}...",
                "logs": [f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Tarea de posición enviada al navegador Chrome..."]
            }

            hilo = threading.Thread(
                target=cls._worker,
                args=(clave, nombre, categoria, padre, guardar_en_produccion, id_local),
                daemon=True
            )
            hilo.start()
            return True, "Creación de posición iniciada en segundo plano."

    @classmethod
    def detener_proceso(cls) -> Tuple[bool, str]:
        """Detiene la ejecución actual de Selenium y cierra Chrome."""
        with cls._lock:
            cls._id_ejecucion += 1
            cls._estado_actual["ejecutando"] = False
            cls._estado_actual["ok"] = False
            cls._estado_actual["mensaje"] = "Proceso cancelado. Cerrando navegador..."
            cls._estado_actual["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Proceso detenido por el usuario.")

            try:
                from USUARIOS.automation import cerrar_driver_activo
                cerrar_driver_activo()
            except Exception as e:
                cls._estado_actual["logs"].append(f"Aviso al cerrar navegador: {e}")

            cls._estado_actual["mensaje"] = "Navegador cerrado. Listo."
            return True, "Proceso de posición detenido y navegador cerrado."

    @classmethod
    def _worker(
        cls,
        clave: str,
        nombre: str,
        categoria: str,
        padre: str,
        guardar_en_produccion: bool,
        id_local: int
    ):
        """Hilo de fondo que corre Selenium sin bloquear la API."""
        try:
            def log_callback(msg: str):
                if id_local != cls._id_ejecucion:
                    return
                cls._estado_actual["logs"].append(msg)
                cls._estado_actual["mensaje"] = msg

            from USUARIOS.automation import ejecutar_alta_posicion
            res = ejecutar_alta_posicion(
                clave=clave,
                nombre=nombre,
                categoria=categoria,
                padre=padre,
                guardar_en_produccion=guardar_en_produccion,
                callback_log=log_callback
            )

            if id_local != cls._id_ejecucion:
                return

            if res.get("ok"):
                cls._estado_actual["ok"] = True
                cls._estado_actual["mensaje"] = res.get("mensaje", "Posición creada exitosamente.")
            else:
                cls._estado_actual["ok"] = False
                cls._estado_actual["mensaje"] = res.get("error", "Error al procesar posición.")

        except Exception as e:
            if id_local == cls._id_ejecucion:
                cls._estado_actual["ok"] = False
                cls._estado_actual["mensaje"] = f"Fallo inesperado: {str(e)}"
                cls._estado_actual["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Excepción: {e}")
        finally:
            if id_local == cls._id_ejecucion:
                cls._estado_actual["ejecutando"] = False
