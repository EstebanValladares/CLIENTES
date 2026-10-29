"""
Servicio para Crear Usuarios y Posiciones conectando con los módulos de Selenium/RH.
Maneja la ejecución asíncrona no-bloqueante con streaming de logs para la UI,
incluyendo control de cancelación, reinicio y limpieza.
"""
import os
import sys
import json
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

class UserCreationService:
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
        return cls._estado_actual

    @classmethod
    def iniciar_alta_asincrona(cls, datos: Dict[str, Any], guardar_en_produccion: bool = False):
        with cls._lock:
            if cls._estado_actual["ejecutando"]:
                return False, "Ya hay un proceso de alta en ejecución."

            cls._id_ejecucion += 1
            id_local = cls._id_ejecucion

            cls._estado_actual = {
                "ejecutando": True,
                "ok": None,
                "mensaje": f"Iniciando Selenium para {datos.get('nombre', '').upper()}...",
                "logs": [f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Tarea enviada al navegador Chrome..."]
            }

            hilo = threading.Thread(target=cls._worker, args=(datos, guardar_en_produccion, id_local), daemon=True)
            hilo.start()
            return True, "Proceso iniciado en segundo plano."

    @classmethod
    def detener_proceso(cls):
        """Detiene la ejecución actual de Selenium y cierra la ventana de Chrome"""
        with cls._lock:
            cls._id_ejecucion += 1  # Invalida cualquier hilo previo
            cls._estado_actual["ejecutando"] = False
            cls._estado_actual["ok"] = False
            cls._estado_actual["mensaje"] = "Proceso cancelado por el usuario. Cerrando navegador..."
            cls._estado_actual["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Proceso detenido. Cerrando Chrome...")

            try:
                from USUARIOS.automation import cerrar_driver_activo
                cerrar_driver_activo()
            except Exception as e:
                cls._estado_actual["logs"].append(f"Aviso al cerrar navegador: {e}")

            cls._estado_actual["mensaje"] = "Navegador cerrado. Listo para reiniciar."
            return True, "Proceso detenido y navegador cerrado."

    @classmethod
    def reiniciar_alta(cls, datos: Dict[str, Any], guardar_en_produccion: bool = False):
        """Detiene cualquier proceso activo, cierra el navegador y relanza la creación con los datos dados"""
        cls.detener_proceso()
        time.sleep(1.0)
        return cls.iniciar_alta_asincrona(datos, guardar_en_produccion=guardar_en_produccion)

    @classmethod
    def _worker(cls, datos: Dict[str, Any], guardar_en_produccion: bool, id_local: int):
        try:
            # Asegurar aislamiento de módulos para USUARIOS
            if "selectores" in sys.modules:
                del sys.modules["selectores"]
            if RUTA_USR in sys.path:
                sys.path.remove(RUTA_USR)
            sys.path.insert(0, RUTA_USR)

            from USUARIOS.automation import ejecutar_alta_usuario
            
            nom_val = str(datos.get("nombre", "")).strip().upper()
            ape_val = str(datos.get("apellidos", "")).strip().upper()
            cor_val = str(datos.get("correo", "")).strip()
            cla_val = str(datos.get("clave", "") or cor_val).strip()
            pue_val = str(datos.get("puesto", "")).strip()
            ini_val = datetime.datetime.now().strftime("%d/%m/%Y")
            fin_val = (datetime.datetime.now() + datetime.timedelta(days=90)).strftime("%d/%m/%Y")
            zon_val = "(UTC-06:00) Guadalajara, Ciudad de México, Monterrey"

            payload = {
                "Nombre": nom_val,
                "nombre": nom_val,
                "Apellidos": ape_val,
                "apellidos": ape_val,
                "Clave": cla_val,
                "clave": cla_val,
                "Correo": cor_val,
                "correo": cor_val,
                "Telefono": "0101010101",
                "telefono": "0101010101",
                "Inicio": ini_val,
                "inicio": ini_val,
                "Fin": fin_val,
                "fin": fin_val,
                "ZonaHoraria": zon_val,
                "zonahoraria": zon_val,
                "Idioma": "Español (México)",
                "idioma": "Español (México)",
                "Posicion": pue_val,
                "posicion": pue_val,
                "Area": "",
                "area": ""
            }

            if cls._id_ejecucion == id_local:
                cls._estado_actual["logs"].append("Abriendo navegador y conectando a Aryve...")
            
            ok, msg = ejecutar_alta_usuario(payload, guardar_en_produccion=guardar_en_produccion)
            
            if cls._id_ejecucion == id_local:
                cls._estado_actual["ok"] = ok
                cls._estado_actual["mensaje"] = msg
                cls._estado_actual["logs"].append(f"Resultado final: {msg}")

        except Exception as e:
            if cls._id_ejecucion == id_local:
                cls._estado_actual["ok"] = False
                cls._estado_actual["mensaje"] = f"Excepción en Selenium: {str(e)}"
                cls._estado_actual["logs"].append(f"[ERROR]: {str(e)}")
        finally:
            if cls._id_ejecucion == id_local:
                cls._estado_actual["ejecutando"] = False

    @classmethod
    def crear_usuario_selenium(cls, datos: Dict[str, Any], guardar_en_produccion: bool = False) -> Tuple[bool, str]:
        """Ejecución síncrona clásica de respaldo"""
        try:
            if "selectores" in sys.modules:
                del sys.modules["selectores"]
            if RUTA_USR in sys.path:
                sys.path.remove(RUTA_USR)
            sys.path.insert(0, RUTA_USR)

            from USUARIOS.automation import ejecutar_alta_usuario
            
            nom_val = str(datos.get("nombre", "")).strip().upper()
            ape_val = str(datos.get("apellidos", "")).strip().upper()
            cor_val = str(datos.get("correo", "")).strip()
            cla_val = str(datos.get("clave", "") or cor_val).strip()
            pue_val = str(datos.get("puesto", "")).strip()
            ini_val = datetime.datetime.now().strftime("%d/%m/%Y")
            fin_val = (datetime.datetime.now() + datetime.timedelta(days=90)).strftime("%d/%m/%Y")
            zon_val = "(UTC-06:00) Guadalajara, Ciudad de México, Monterrey"

            payload = {
                "Nombre": nom_val,
                "nombre": nom_val,
                "Apellidos": ape_val,
                "apellidos": ape_val,
                "Clave": cla_val,
                "clave": cla_val,
                "Correo": cor_val,
                "correo": cor_val,
                "Telefono": "0101010101",
                "telefono": "0101010101",
                "Inicio": ini_val,
                "inicio": ini_val,
                "Fin": fin_val,
                "fin": fin_val,
                "ZonaHoraria": zon_val,
                "zonahoraria": zon_val,
                "Idioma": "Español (México)",
                "idioma": "Español (México)",
                "Posicion": pue_val,
                "posicion": pue_val,
                "Area": "",
                "area": ""
            }

            ok, msg = ejecutar_alta_usuario(payload, guardar_en_produccion=guardar_en_produccion)
            return ok, msg
        except Exception as e:
            return False, f"Excepción ejecutando Selenium: {str(e)}"
