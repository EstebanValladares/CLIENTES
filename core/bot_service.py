"""
Core Domain: Gestor de Ejecución de Bots RPA.
Carga el catálogo oficial de proyectos activos y ejecuta subprocesos con streaming de logs.
"""
import os
import sys
import json
import subprocess
import threading
import datetime
from typing import Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROYECTOS_PATH = os.path.join(BASE_DIR, "NUCLEO", "proyectos.json")

ALIAS_BOTS = {
    "CREACION_USUARIOS": "USUARIOS",
    "DEPURACION_PERMISOS": "PROYECTOS",
    "CREACON_PROVEEDORES": "PROVEEDORES",
    "CREACION_PROVEEDORES": "PROVEEDORES"
}

class BotRunnerService:
    _procesos_activos: Dict[str, Any] = {}
    _logs_buffer: Dict[str, List[str]] = {}

    @classmethod
    def _normalizar_id(cls, bot_id: str) -> str:
        return ALIAS_BOTS.get(bot_id, bot_id)

    @classmethod
    def obtener_catalogo(cls) -> Dict[str, Any]:
        """Obtiene el catálogo de bots activos del ecosistema."""
        catalogo = {}

        if os.path.exists(PROYECTOS_PATH):
            try:
                with open(PROYECTOS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for bot_id, info in data.get("proyectos", {}).items():
                        catalogo[bot_id] = {
                            "id": bot_id,
                            "nombre": bot_id.replace("_", " ").title(),
                            "descripcion": info.get("descripcion", ""),
                            "tipo": "RPA_SELENIUM",
                            "archivos_requeridos": info.get("requiere_archivos", []),
                            "ruta_script": os.path.join(BASE_DIR, bot_id, info.get("script", "main.py"))
                        }
            except Exception as e:
                print(f"[BotRunner] Error leyendo proyectos.json: {e}")

        # Enriquecer con estados en tiempo real
        resultado = {}
        for bot_id, info in catalogo.items():
            activo = bot_id in cls._procesos_activos and cls._procesos_activos[bot_id]["estado"] == "EJECUTANDO"
            resultado[bot_id] = {
                **info,
                "estado": "EJECUTANDO" if activo else "LISTO",
                "ultimo_resultado": cls._procesos_activos.get(bot_id, {}).get("veredicto", "N/A"),
                "fecha_inicio": cls._procesos_activos.get(bot_id, {}).get("inicio", None)
            }

        return resultado

    @classmethod
    def obtener_python_bin(cls) -> str:
        candidatos = [sys.executable, "python", "py"]
        for py in candidatos:
            if os.path.exists(py):
                return py
        return sys.executable

    @classmethod
    def ejecutar_bot(cls, bot_id: str) -> Dict[str, Any]:
        bot_id = cls._normalizar_id(bot_id)
        if bot_id in cls._procesos_activos and cls._procesos_activos[bot_id]["estado"] == "EJECUTANDO":
            return {"ok": False, "error": f"El bot {bot_id} ya se encuentra en ejecución."}

        catalogo = cls.obtener_catalogo()
        bot_info = catalogo.get(bot_id)

        if not bot_info:
            return {"ok": False, "error": f"El bot {bot_id} no existe en el catálogo."}

        script_path = bot_info["ruta_script"]
        cwd = os.path.dirname(script_path)

        cls._logs_buffer[bot_id] = [f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Iniciando {bot_id}..."]
        cls._procesos_activos[bot_id] = {
            "estado": "EJECUTANDO",
            "inicio": datetime.datetime.now().isoformat(),
            "fin": None,
            "veredicto": "EN_PROCESO"
        }

        hilo = threading.Thread(target=cls._worker_ejecucion, args=(bot_id, cwd, script_path), daemon=True)
        hilo.start()

        return {"ok": True, "mensaje": f"Bot {bot_id} iniciado en segundo plano.", "bot_id": bot_id}

    @classmethod
    def _worker_ejecucion(cls, bot_id: str, cwd: str, script_path: str):
        py_bin = cls.obtener_python_bin()
        cls._agregar_log(bot_id, f"Iniciando proceso: {py_bin} {script_path}")

        # Inyectar PYTHONPATH y forzar UTF-8 para evitar errores de charmap en Windows
        env = os.environ.copy()
        env["PYTHONPATH"] = BASE_DIR
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        try:
            proceso = subprocess.Popen(
                [py_bin, "-u", "-X", "utf8", script_path],
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )

            for linea in iter(proceso.stdout.readline, ''):
                if linea:
                    cls._agregar_log(bot_id, linea.strip())

            proceso.stdout.close()
            ret_code = proceso.wait()

            veredicto = "EXITO" if ret_code == 0 else f"FINALIZADO (Código {ret_code})"
            cls._procesos_activos[bot_id]["estado"] = "FINALIZADO"
            cls._procesos_activos[bot_id]["fin"] = datetime.datetime.now().isoformat()
            cls._procesos_activos[bot_id]["veredicto"] = veredicto
            cls._agregar_log(bot_id, f"=== PROCESO FINALIZADO: {veredicto} ===")

        except Exception as e:
            cls._procesos_activos[bot_id]["estado"] = "ERROR"
            cls._procesos_activos[bot_id]["veredicto"] = f"ERROR: {str(e)}"
            cls._agregar_log(bot_id, f"[EXCEPCIÓN CRÍTICA]: {str(e)}")

    @classmethod
    def _agregar_log(cls, bot_id: str, texto: str):
        if bot_id not in cls._logs_buffer:
            cls._logs_buffer[bot_id] = []
        cls._logs_buffer[bot_id].append(texto)
        if len(cls._logs_buffer[bot_id]) > 300:
            cls._logs_buffer[bot_id].pop(0)

    @classmethod
    def obtener_logs(cls, bot_id: str, desde_linea: int = 0) -> Dict[str, Any]:
        bot_id = cls._normalizar_id(bot_id)
        logs = cls._logs_buffer.get(bot_id, [])
        return {
            "bot_id": bot_id,
            "estado": cls._procesos_activos.get(bot_id, {}).get("estado", "INACTIVO"),
            "veredicto": cls._procesos_activos.get(bot_id, {}).get("veredicto", "N/A"),
            "logs": logs[desde_linea:],
            "total_lineas": len(logs)
        }
