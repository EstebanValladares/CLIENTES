"""
Servicio para Asignación Automatizada de Clasificadores en Aryve vía Selenium.
Lee las matrices de puestos.json y ejecuta asignador_clasificadores de forma asíncrona,
reportando logs y estado en tiempo real para el Dashboard.
"""
import os
import sys
import json
import time
import threading
import datetime
from typing import Dict, Any, Tuple, Optional, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUTA_USR = os.path.join(BASE_DIR, "USUARIOS")
PUESTOS_PATH = os.path.join(RUTA_USR, "data", "puestos.json") if os.path.exists(os.path.join(RUTA_USR, "data", "puestos.json")) else os.path.join(RUTA_USR, "puestos.json")

if RUTA_USR not in sys.path:
    sys.path.insert(0, RUTA_USR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class UserClassifierService:
    _estado_actual: Dict[str, Any] = {
        "ejecutando": False,
        "ok": None,
        "mensaje": "",
        "id_usuario": None,
        "puesto": None,
        "logs": []
    }
    _id_ejecucion = 0
    _lock = threading.Lock()

    @classmethod
    def obtener_estado(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._estado_actual)

    @classmethod
    def obtener_puestos_clasificadores(cls) -> Dict[str, Any]:
        """Devuelve el diccionario completo de puestos desde Firebase Firestore en la nube (con fallback local)."""
        if os.getenv("USE_FIREBASE", "0").lower() in ("1", "true", "yes"):
            try:
                from core.firebase_client import FirebaseClient
                puestos_cloud = FirebaseClient.obtener_puestos()
                if puestos_cloud:
                    return puestos_cloud
            except Exception as e:
                pass

        if not os.path.exists(PUESTOS_PATH):
            return {}
        try:
            with open(PUESTOS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("puestos", {})
        except Exception as e:
            print(f"[UserClassifierService] Error leyendo puestos.json local: {e}")
            return {}

    @classmethod
    def obtener_clasificadores_de_puesto(cls, nombre_puesto: str) -> Dict[str, Any]:
        """Busca un puesto por coincidencia exacta o normalizada y retorna su configuración."""
        puestos = cls.obtener_puestos_clasificadores()
        if not nombre_puesto:
            return {}

        puesto_limpio = nombre_puesto.strip().upper()
        if puesto_limpio in puestos:
            return puestos[puesto_limpio]

        for k, v in puestos.items():
            if k.strip().upper() == puesto_limpio:
                return v

        return {}

    @classmethod
    def iniciar_asignacion_asincrona(cls, id_usuario: str, puesto: str, nombre_usuario: str = "") -> Tuple[bool, str]:
        """Lanza la ejecución de asignador_clasificadores en un hilo en segundo plano."""
        with cls._lock:
            if cls._estado_actual["ejecutando"]:
                return False, "Ya hay un proceso de asignación de clasificadores en ejecución."

            if not id_usuario or str(id_usuario).strip() in ["", "0", "None"]:
                return False, "ID de usuario inválido o no especificado."

            puesto_info = cls.obtener_clasificadores_de_puesto(puesto)
            if not puesto_info:
                return False, f"El puesto '{puesto}' no existe en puestos.json."

            clasificadores = puesto_info.get("clasificadores", {})
            if not clasificadores:
                return False, f"El puesto '{puesto}' no tiene clasificadores definidos en puestos.json."

            cls._id_ejecucion += 1
            id_local = cls._id_ejecucion

            hora_inicio = datetime.datetime.now().strftime("%H:%M:%S")
            cls._estado_actual = {
                "ejecutando": True,
                "ok": None,
                "mensaje": f"Iniciando asignación para ID #{id_usuario} ({puesto})...",
                "id_usuario": id_usuario,
                "puesto": puesto,
                "logs": [
                    f"[{hora_inicio}] Tarea enviada al navegador Chrome...",
                    f"[{hora_inicio}] Usuario ID: {id_usuario} | Puesto: {puesto}"
                ]
            }

            hilo = threading.Thread(
                target=cls._worker,
                args=(id_usuario, clasificadores, puesto, nombre_usuario, id_local),
                daemon=True
            )
            hilo.start()
            return True, f"Asignación de clasificadores iniciada en segundo plano para usuario #{id_usuario}."

    @classmethod
    def _worker(cls, id_usuario: str, clasificadores: dict, puesto: str, nombre_usuario: str, id_local: int):
        try:
            # Asegurar importación limpia de asignador_clasificadores
            if RUTA_USR not in sys.path:
                sys.path.insert(0, RUTA_USR)

            from USUARIOS.automation import ejecutar_asignacion_clasificadores
            from USUARIOS.logger import limpiar_fallos_resueltos

            def registrar_log(msg: str):
                with cls._lock:
                    if cls._id_ejecucion == id_local:
                        h = datetime.datetime.now().strftime("%H:%M:%S")
                        cls._estado_actual["logs"].append(f"[{h}] {msg}")

            registrar_log("Abriendo navegador Chrome y conectando a Portal Aryve...")

            ok, msg = ejecutar_asignacion_clasificadores(id_usuario, clasificadores)

            with cls._lock:
                if cls._id_ejecucion == id_local:
                    cls._estado_actual["ok"] = ok
                    cls._estado_actual["mensaje"] = msg
                    h = datetime.datetime.now().strftime("%H:%M:%S")
                    cls._estado_actual["logs"].append(f"[{h}] Resultado final: {msg}")

            if ok and nombre_usuario:
                try:
                    limpiar_fallos_resueltos(nombre_usuario)
                except Exception:
                    pass

        except Exception as e:
            with cls._lock:
                if cls._id_ejecucion == id_local:
                    cls._estado_actual["ok"] = False
                    cls._estado_actual["mensaje"] = f"Excepción en Selenium: {str(e)}"
                    h = datetime.datetime.now().strftime("%H:%M:%S")
                    cls._estado_actual["logs"].append(f"[{h}] [ERROR]: {str(e)}")
        finally:
            with cls._lock:
                if cls._id_ejecucion == id_local:
                    cls._estado_actual["ejecutando"] = False

