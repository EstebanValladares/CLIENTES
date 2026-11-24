"""
Core Domain: Servicio de Cruce e Inteligencia de Bajas FORTIA vs Enkontrol.
Procesa el reporte de bajas de Recursos Humanos (FORTIA) y lo compara en RAM O(1)
con la base de usuarios de Enkontrol (Aryve), detectando cuentas en riesgo.
"""
from __future__ import annotations

import os
import re
import json
import time
import unicodedata
import threading
import subprocess
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from Shared.config import es_modo_master
except ImportError:
    def es_modo_master() -> bool:
        return True

from core.user_service import UserService

BASE_DIR = Path(__file__).resolve().parents[1]
RUTA_SALIDA_FORTIA = BASE_DIR / "FORTIA" / "data" / "salida"
RUTA_CRUCE_CACHE = BASE_DIR / "USUARIOS" / "data" / "bajas_fortia_cruce.json"


def normalizar_cadena(texto: Any) -> str:
    """Normaliza texto eliminando acentos, caracteres especiales y espacios redundantes."""
    if not texto:
        return ""
    texto_str = str(texto).strip().upper()
    # Descomponer caracteres con acento
    nfkd = unicodedata.normalize('NFKD', texto_str)
    sin_tildes = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Limpiar signos y compactar espacios
    limpio = re.sub(r'[^A-Z0-9\s]', ' ', sin_tildes)
    return re.sub(r'\s+', ' ', limpio).strip()


class FortiaService:
    _bot_estado: Dict[str, Any] = {
        "ejecutando": False,
        "inicio": None,
        "fin": None,
        "veredicto": "INACTIVO",
        "mensaje": "",
        "logs": []
    }
    _lock = threading.Lock()

    @classmethod
    def obtener_estado_bot(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._bot_estado)

    @classmethod
    def _agregar_log_bot(cls, texto: str):
        with cls._lock:
            cls._bot_estado["logs"].append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {texto}")
            if len(cls._bot_estado["logs"]) > 250:
                cls._bot_estado["logs"].pop(0)

    @classmethod
    def iniciar_consulta_bajas_asincrona(cls, dias_atras: int = 30, headless: bool = True) -> tuple[bool, str]:
        """Inicia el bot de Selenium FortiaReporteBajas en segundo plano."""
        if not es_modo_master():
            return False, "La descarga automatizada desde FORTIA se ejecuta directamente en la Torre Master."

        with cls._lock:
            if cls._bot_estado["ejecutando"]:
                return False, "Ya hay una consulta de FORTIA ejecutándose en segundo plano."
            cls._bot_estado["ejecutando"] = True
            cls._bot_estado["inicio"] = datetime.datetime.now().isoformat()
            cls._bot_estado["fin"] = None
            cls._bot_estado["veredicto"] = "EN_PROCESO"
            cls._bot_estado["mensaje"] = "Iniciando descarga de reporte 2411 desde FORTIA..."
            cls._bot_estado["logs"] = []

        hilo = threading.Thread(
            target=cls._worker_ejecucion_fortia,
            args=(dias_atras, headless),
            daemon=True
        )
        hilo.start()
        return True, "Consulta de bajas en FORTIA iniciada."

    @classmethod
    def _worker_ejecucion_fortia(cls, dias_atras: int, headless: bool):
        cls._agregar_log_bot("Conectando con el portal de FORTIA RH...")
        try:
            ruta_bot_dir = BASE_DIR / "FORTIA"
            script_path = ruta_bot_dir / "src" / "fortia_reporte_bajas" / "main.py"

            from core.bot_service import BotRunnerService
            py_bin = BotRunnerService.obtener_python_bin()

            # Leer .env principal y del submódulo
            from dotenv import load_dotenv
            load_dotenv(BASE_DIR / ".env")
            load_dotenv(ruta_bot_dir / ".env")

            usuario_fortia = os.getenv("FRB_FORTIA_USUARIO") or os.getenv("FORTIA_USER", "")
            password_fortia = os.getenv("FRB_FORTIA_PASSWORD") or os.getenv("FORTIA_PASS", "")

            if not usuario_fortia or not password_fortia:
                cls._agregar_log_bot("[AVISO]: Faltan credenciales de FORTIA en .env (FRB_FORTIA_USUARIO / FRB_FORTIA_PASSWORD).")
                cls._agregar_log_bot("[AYUDA]: Agrégalas al archivo .env o sube directamente el reporte con el botón 'Cargar Excel de Bajas'.")
                with cls._lock:
                    cls._bot_estado["ejecutando"] = False
                    cls._bot_estado["fin"] = datetime.datetime.now().isoformat()
                    cls._bot_estado["veredicto"] = "FALTAN_CREDENCIALES"
                    cls._bot_estado["mensaje"] = "Faltan credenciales de acceso a FORTIA en el archivo .env."
                return

            env = os.environ.copy()
            env["PYTHONPATH"] = f"{ruta_bot_dir / 'src'}{os.pathsep}{BASE_DIR}"
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["FRB_FORTIA_USUARIO"] = usuario_fortia
            env["FRB_FORTIA_PASSWORD"] = password_fortia

            args = [py_bin, "-u", str(script_path), "--dias-atras", str(dias_atras)]
            if headless:
                args.append("--headless")

            cls._agregar_log_bot(f"Ejecutando: {' '.join(args)}")

            proceso = subprocess.Popen(
                args,
                cwd=str(ruta_bot_dir),
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
                    cls._agregar_log_bot(linea.strip())

            proceso.stdout.close()
            ret_code = proceso.wait()

            with cls._lock:
                cls._bot_estado["ejecutando"] = False
                cls._bot_estado["fin"] = datetime.datetime.now().isoformat()
                if ret_code == 0:
                    cls._bot_estado["veredicto"] = "EXITO"
                    cls._bot_estado["mensaje"] = "Reporte de bajas descargado con éxito desde FORTIA."
                    cls._agregar_log_bot("Descarga finalizada. Procesando cruce en vivo con Enkontrol...")
                else:
                    cls._bot_estado["veredicto"] = "ERROR"
                    cls._bot_estado["mensaje"] = f"El proceso finalizó con código de error {ret_code}."
                    cls._agregar_log_bot(f"Proceso detenido con error {ret_code}.")

            # Si terminó bien, procesar el cruce automáticamente
            if ret_code == 0:
                cls.procesar_ultimo_reporte_descargado()

        except Exception as e:
            with cls._lock:
                cls._bot_estado["ejecutando"] = False
                cls._bot_estado["fin"] = datetime.datetime.now().isoformat()
                cls._bot_estado["veredicto"] = "ERROR"
                cls._bot_estado["mensaje"] = f"Excepción crítica: {e}"
            cls._agregar_log_bot(f"[ERROR CRÍTICO]: {e}")

    @classmethod
    def buscar_ultimo_excel_bajas(cls) -> Optional[Path]:
        """Localiza el archivo Excel de Altas y Bajas más reciente."""
        if not RUTA_SALIDA_FORTIA.exists():
            return None
        archivos = list(RUTA_SALIDA_FORTIA.glob("*.xlsx")) + list(RUTA_SALIDA_FORTIA.glob("*.xls"))
        if not archivos:
            return None
        archivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return archivos[0]

    @classmethod
    def leer_excel_bajas(cls, ruta_excel: Path | str) -> List[Dict[str, Any]]:
        """Lee el Excel exportado por FORTIA y extrae la lista de empleados dados de baja."""
        try:
            import openpyxl
        except ImportError:
            print("[FortiaService] openpyxl no está instalado en este equipo. En modo Cliente se consulta la caché generada por la Torre.")
            return []

        wb = openpyxl.load_workbook(ruta_excel, data_only=True, read_only=True)
        sheet = wb.active
        filas = list(sheet.iter_rows(values_only=True))
        if not filas:
            return []

        # Buscar la fila de encabezados
        idx_headers = -1
        idx_clave = -1
        idx_empleado = -1
        idx_fecha_baja = -1
        idx_puesto = -1
        idx_estatus = -1
        idx_rfc = -1

        for r_idx, fila in enumerate(filas[:15]):
            valores = [normalizar_cadena(c) for c in fila if c is not None]
            linea_str = " ".join(valores)
            if "EMPLEADO" in linea_str or "TRABAJADOR" in linea_str or "NOMBRE" in linea_str:
                idx_headers = r_idx
                for col_idx, celda in enumerate(fila):
                    c_norm = normalizar_cadena(celda)
                    if "CLAVE" in c_norm or "NUM" in c_norm:
                        if idx_clave == -1:
                            idx_clave = col_idx
                    elif "EMPLEADO" in c_norm or "NOMBRE" in c_norm:
                        if idx_empleado == -1:
                            idx_empleado = col_idx
                    elif "FECHA" in c_norm or "BAJA" in c_norm or "SALIDA" in c_norm:
                        if idx_fecha_baja == -1:
                            idx_fecha_baja = col_idx
                    elif "PUESTO" in c_norm or "CATEGORIA" in c_norm:
                        if idx_puesto == -1:
                            idx_puesto = col_idx
                    elif "ESTATUS" in c_norm or "ESTADO" in c_norm:
                        if idx_estatus == -1:
                            idx_estatus = col_idx
                    elif "RFC" in c_norm:
                        if idx_rfc == -1:
                            idx_rfc = col_idx
                break

        # Fallback si no hubo encabezado explícito:
        # Col B (1)=Clave, Col C (2)=Empleado, Col D (3)=Puesto/Fecha
        if idx_empleado == -1:
            idx_headers = 0
            idx_clave = 1
            idx_empleado = 2
            idx_fecha_baja = 3

        registros_bajas: List[Dict[str, Any]] = []
        for fila in filas[idx_headers + 1:]:
            if not fila:
                continue
            empleado = fila[idx_empleado] if idx_empleado >= 0 and idx_empleado < len(fila) else None
            if not empleado or not str(empleado).strip():
                continue

            clave = fila[idx_clave] if idx_clave >= 0 and idx_clave < len(fila) else ""
            fecha_baja = fila[idx_fecha_baja] if idx_fecha_baja >= 0 and idx_fecha_baja < len(fila) else ""
            puesto = fila[idx_puesto] if idx_puesto >= 0 and idx_puesto < len(fila) else ""
            estatus = fila[idx_estatus] if idx_estatus >= 0 and idx_estatus < len(fila) else "B"
            rfc = fila[idx_rfc] if idx_rfc >= 0 and idx_rfc < len(fila) else ""

            # Formatear fecha
            fecha_str = str(fecha_baja).strip()
            if isinstance(fecha_baja, (datetime.date, datetime.datetime)):
                fecha_str = fecha_baja.strftime("%Y-%m-%d")
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]

            registros_bajas.append({
                "clave_trabajador": str(clave).strip() if clave else "",
                "nombre_empleado": str(empleado).strip(),
                "nombre_norm": normalizar_cadena(empleado),
                "fecha_baja": fecha_str,
                "puesto": str(puesto).strip() if puesto else "",
                "estatus_fortia": str(estatus).strip() if estatus else "B",
                "rfc": str(rfc).strip() if rfc else ""
            })

        wb.close()
        return registros_bajas

    @classmethod
    def cruzar_con_usuarios_enkontrol(cls, bajas_fortia: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cruza en memoria O(N) las bajas de FORTIA contra los usuarios de Enkontrol."""
        usuarios_ek = UserService.obtener_usuarios(force_reload=False)

        # Mapeos rápidos de Enkontrol:
        # 1. Nombre normalizado exacto -> usuario
        # 2. Token sets (palabras del nombre) -> lista de usuarios
        map_exacto: Dict[str, Dict[str, Any]] = {}
        tokens_map: List[tuple[set[str], Dict[str, Any]]] = []

        for u in usuarios_ek:
            nom_comp = u.get("nombre_completo", "") or f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()
            norm = normalizar_cadena(nom_comp)
            if norm:
                map_exacto[norm] = u
                tokens = set(norm.split())
                if tokens:
                    tokens_map.append((tokens, u))

        en_riesgo: List[Dict[str, Any]] = []
        ya_inactivos: List[Dict[str, Any]] = []
        no_encontrados: List[Dict[str, Any]] = []

        ids_procesados = set()

        for b in bajas_fortia:
            norm_baja = b["nombre_norm"]
            match_usr = map_exacto.get(norm_baja)

            # Si no coincide exacto, buscar por tokens (permutación de nombres/apellidos)
            if not match_usr:
                tokens_baja = set(norm_baja.split())
                mejor_score = 0
                candidato = None

                for t_usr, usr in tokens_map:
                    # Intersección de palabras
                    comunes = tokens_baja.intersection(t_usr)
                    if len(comunes) >= 2:
                        score = len(comunes) / max(len(tokens_baja), len(t_usr))
                        if score > mejor_score and score >= 0.7:
                            mejor_score = score
                            candidato = usr

                if candidato:
                    match_usr = candidato

            item = {
                "clave_trabajador": b["clave_trabajador"],
                "nombre_fortia": b["nombre_empleado"],
                "fecha_baja": b["fecha_baja"],
                "puesto_fortia": b["puesto"],
                "estatus_fortia": b["estatus_fortia"]
            }

            if match_usr:
                uid = str(match_usr.get("id", ""))
                item.update({
                    "id_enkontrol": uid,
                    "nombre_enkontrol": match_usr.get("nombre_completo", ""),
                    "puesto_enkontrol": match_usr.get("puesto", ""),
                    "clave_enkontrol": match_usr.get("clave", ""),
                    "correo_enkontrol": match_usr.get("correo", ""),
                    "estatus_enkontrol": match_usr.get("estatus", "Activo"),
                    "url_aryve": match_usr.get("url_aryve", "")
                })

                estatus_ek = str(match_usr.get("estatus", "")).strip().upper()
                es_activo = (estatus_ek == "ACTIVO" or estatus_ek == "1" or not estatus_ek)

                if es_activo:
                    en_riesgo.append(item)
                else:
                    ya_inactivos.append(item)
                ids_procesados.add(uid)
            else:
                item.update({
                    "id_enkontrol": None,
                    "nombre_enkontrol": None,
                    "puesto_enkontrol": None,
                    "estatus_enkontrol": "SIN_CUENTA",
                    "url_aryve": ""
                })
                no_encontrados.append(item)

        resultado = {
            "fecha_cruce": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_bajas_fortia": len(bajas_fortia),
            "total_en_riesgo": len(en_riesgo),
            "total_ya_inactivos": len(ya_inactivos),
            "total_no_encontrados": len(no_encontrados),
            "en_riesgo": en_riesgo,
            "ya_inactivos": ya_inactivos,
            "no_encontrados": no_encontrados
        }

        # Guardar en caché JSON para lectura instantánea
        try:
            RUTA_CRUCE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(RUTA_CRUCE_CACHE, "w", encoding="utf-8") as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[FortiaService] Error guardando caché de cruce: {e}")

        return resultado

    @classmethod
    def procesar_ultimo_reporte_descargado(cls) -> Dict[str, Any]:
        """Busca el último Excel en la carpeta de salida y ejecuta el cruce."""
        excel_path = cls.buscar_ultimo_excel_bajas()
        if not excel_path:
            return {
                "ok": False,
                "error": "No se encontró ningún archivo Excel descargado de FORTIA en data/salida."
            }
        bajas = cls.leer_excel_bajas(excel_path)
        cruce = cls.cruzar_con_usuarios_enkontrol(bajas)
        cruce["ok"] = True
        cruce["archivo_origen"] = excel_path.name
        return cruce

    @classmethod
    def _obtener_candidatos_torre(cls) -> List[str]:
        """Obtiene la lista de URLs para consultar a la Torre Master desde clientes."""
        candidatos = []
        env_url = os.getenv("TORRE_CHAT_URL") or os.getenv("TORRE_URL")
        if env_url:
            candidatos.append(env_url.rstrip("/"))

        base_dir = Path(__file__).resolve().parents[1]
        data_dir = base_dir / "data"
        for p in [base_dir / "conexion_torre.json", data_dir / "conexion_torre.json"]:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    puerto = cfg.get("puerto", 8000)
                    if cfg.get("ip_torre"):
                        candidatos.append(f"http://{cfg['ip_torre']}:{puerto}")
                    if cfg.get("hostname_torre"):
                        candidatos.append(f"http://{cfg['hostname_torre']}:{puerto}")
                    for ip in cfg.get("ips_conocidas", []):
                        candidatos.append(f"http://{ip}:{puerto}")
                except Exception:
                    pass

        candidatos.extend([
            "http://10.10.200.31:8000",
            "http://Esteban:8000",
            "http://10.10.200.147:8000",
            "http://127.0.0.1:8000"
        ])

        vistos = set()
        unicos = []
        for c in candidatos:
            c_clean = c.rstrip("/")
            if c_clean not in vistos:
                vistos.add(c_clean)
                unicos.append(c_clean)
        return unicos

    @classmethod
    def _consultar_cruce_via_master(cls) -> Dict[str, Any]:
        """Consulta el cruce de bajas desde la Torre Master para clientes."""
        import urllib.request
        for host in cls._obtener_candidatos_torre():
            url = f"{host}/api/fortia/cruce"
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "DashboardClient/1.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if isinstance(data, dict):
                            return data
            except Exception:
                continue
        return {
            "ok": False,
            "error": "No se pudo conectar con la Torre Master para consultar el cruce de FORTIA."
        }

    @classmethod
    def obtener_cruce_actual(cls) -> Dict[str, Any]:
        """Obtiene el cruce guardado en caché o procesa el último archivo si existe."""
        if RUTA_CRUCE_CACHE.exists():
            try:
                with open(RUTA_CRUCE_CACHE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["ok"] = True
                    return data
            except Exception:
                pass

        if not es_modo_master():
            return cls._consultar_cruce_via_master()

        return cls.procesar_ultimo_reporte_descargado()
