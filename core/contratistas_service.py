"""
Core Domain: Servicios de Contratistas (Consulta DBA, Comparación con JSON, Cola y RPA Asíncrono).
"""

import os
import sys
import json
import time
import shutil
import threading
from typing import Dict, Any, List, Optional, Tuple

try:
    import pyodbc
except ImportError:
    pyodbc = None

# Rutas del Proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTRATISTAS_DIR = os.path.join(BASE_DIR, "CONTRATISTAS")
JSON_MAP_PATH = os.path.join(CONTRATISTAS_DIR, "contratista_mapeado.json")
OUTPUT_IMAGES_DIR = os.path.join(CONTRATISTAS_DIR, "output")

from CONTRATISTAS.config.settings import resolver_credenciales
from CONTRATISTAS.domain.text_processor import process_contractor_name
from CONTRATISTAS.domain.image_generator import generate_badge_for_contractor
from CONTRATISTAS.domain.catalog_service import load_mapped_catalog


# Cadena de Conexión a Enkontrol EK_ADM01_11 (SQL Anywhere)
ODBC_CONN_STR = (
    "Driver={SQL Anywhere 11};"
    "EngineName=especial_v9;"
    "DatabaseName=EK_ADM01_11;"
    "CommLinks=tcpip(host=10.10.202.244:2544);"
    "UID=user_write;"
    "PWD=writaryb0904##;"
)


class ContratistasService:
    _lock = threading.Lock()
    _cola_memoria: List[Dict[str, Any]] = []
    _cache_db: List[Dict[str, Any]] = []
    _ultimo_pull_db: float = 0
    _TTL_CACHE_SEG: int = 30  # Cache de 30s para máxima fluidez y protección de la BD
    _db_query_en_curso: bool = False  # Single-Flight Guard: evita peticiones simultáneas a SQL Anywhere

    _estado_ejecucion: Dict[str, Any] = {
        "ejecutando": False,
        "detener": False,
        "actual": 0,
        "total": 0,
        "contratista_actual": "",
        "logs": [],
        "veredicto": "LISTO"
    }

    @classmethod
    def obtener_contratistas_dba(cls, forzar_recarga: bool = False) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de contratistas oficiales con sus IDs reales ordenados de forma descendente
        (priorizando los más recientes: 229, 228, 227, 226, 225, 224, 223, 222...)
        enriqueciendo con la información de Enkontrol.
        """
        ahora = time.time()
        with cls._lock:
            # 1. Retorno instantáneo si el caché está vigente (<30s)
            if not forzar_recarga and cls._cache_db and (ahora - cls._ultimo_pull_db < cls._TTL_CACHE_SEG):
                return list(cls._cache_db)

            # 2. Si ya hay una consulta en curso, devolver caché existente para no saturar
            if cls._db_query_en_curso and cls._cache_db:
                return list(cls._cache_db)

            cls._db_query_en_curso = True

        try:
            # 1. Cargar el catálogo oficial de contratistas desde Firebase Firestore (en la nube con fallback local)
            mapeados = None
            if os.getenv("USE_FIREBASE", "0").lower() in ("1", "true", "yes"):
                try:
                    from core.firebase_client import FirebaseClient
                    mapeados = FirebaseClient.obtener_contratistas(forzar=forzar_recarga)
                except Exception:
                    pass
            if not mapeados:
                mapeados = load_mapped_catalog(JSON_MAP_PATH)
            mapeados_claves = {str(c.get("clave", "")).strip(): c for c in mapeados if c.get("clave")}
            max_id = max((c.get("id") or 0 for c in mapeados), default=0)

            # 2. Consultar BD Enkontrol de forma segura para complementar datos y detectar nuevos
            datos_db = {}
            nuevos_db = []
            try:
                if pyodbc is not None:
                    cn = pyodbc.connect(ODBC_CONN_STR, timeout=6)
                cur = cn.cursor()
                query = """
                    SELECT 
                        c.NUMPRO AS numpro,
                        c.DSCONTRATISTA AS nombre,
                        c.RFC AS rfc,
                        c.REPRESENTANTE AS representante,
                        c.REG_IMSS AS reg_imss
                    FROM DBA.SU_CONTRATISTAS c
                """
                cur.execute(query)
                for row in cur.fetchall():
                    if row.numpro is not None:
                        try:
                            n_val = int(row.numpro)
                        except (ValueError, TypeError):
                            continue
                        n_str = str(n_val)
                        info = {
                            "nombre": (row.nombre or "").strip(),
                            "rfc": (row.rfc or "").strip(),
                            "representante": (row.representante or "").strip(),
                            "reg_imss": (row.reg_imss or "").strip(),
                        }
                        datos_db[n_str] = info
                        # Si no está en contratista_mapeado.json, incorporarlo desde DBA
                        if n_str not in mapeados_claves:
                            nuevos_db.append((n_val, n_str, info))

                # Complementar con sp_proveedores (Catálogo General Enkontrol) para contratistas como 10705, 11580, etc.
                try:
                    cur.execute("""
                        SELECT 
                            p.numpro,
                            p.nombre,
                            p.rfc,
                            p.responsable,
                            p.REG_IMSS_CONTRATISTA
                        FROM DBA.sp_proveedores p
                    """)
                    for row_sp in cur.fetchall():
                        if row_sp.numpro is not None:
                            try:
                                sp_val = int(row_sp.numpro)
                            except (ValueError, TypeError):
                                continue
                            sp_str = str(sp_val)
                            info_sp = {
                                "nombre": (row_sp.nombre or "").strip(),
                                "rfc": (row_sp.rfc or "").strip(),
                                "representante": (row_sp.responsable or "").strip(),
                                "reg_imss": (row_sp.REG_IMSS_CONTRATISTA or "").strip(),
                            }
                            if sp_str not in datos_db:
                                datos_db[sp_str] = info_sp
                            else:
                                if not datos_db[sp_str].get("rfc") and info_sp.get("rfc"):
                                    datos_db[sp_str]["rfc"] = info_sp["rfc"]
                                if not datos_db[sp_str].get("representante") and info_sp.get("representante"):
                                    datos_db[sp_str]["representante"] = info_sp["representante"]
                except Exception as e_sp:
                    cls._agregar_log(f"[DB ENKONTROL] Aviso consultando sp_proveedores: {e_sp}")

                cn.close()
            except Exception as e_db:
                cls._agregar_log(f"[DB ENKONTROL] Error al consultar DBA.SU_CONTRATISTAS: {e_db}")

            # 3. Construir la lista estructurada con ID prioritario
            resultado_mapeados = []
            for c in mapeados:
                cid = c.get("id")
                cve = str(c.get("clave", "")).strip()
                foto = c.get("foto")
                # Solo se considera con foto si contiene 'KontrolFiles'
                tiene_foto = bool(foto and "KontrolFiles" in str(foto))
                info_db = datos_db.get(cve, {})

                resultado_mapeados.append({
                    "id": cid,
                    "id_aryve": cid,
                    "numpro": cve,
                    "clave": cve,
                    "nombre": c.get("nombre", "") or info_db.get("nombre", ""),
                    "nombre_destacado": c.get("nombre_destacado", c.get("nombre", "")),
                    "rfc": c.get("rfc", "") or info_db.get("rfc", ""),
                    "representante": info_db.get("representante") or c.get("representante") or "",
                    "reg_imss": info_db.get("reg_imss") or c.get("nss") or "",
                    "tiene_foto": tiene_foto,
                    "en_json": True,
                    "estatus": "COMPLETO" if tiene_foto else "SIN_FOTO",
                    "seleccionable": True
                })

            # Ordenar mapeados oficiales por su ID en Aryve descendente (229, 228, 227...)
            resultado_mapeados.sort(key=lambda x: (x.get("id") or 0), reverse=True)

            # 4. Agregar los contratistas de DBA.SU_CONTRATISTAS ordenados por NUMPRO descendente
            nuevos_db.sort(key=lambda x: x[0], reverse=True)
            resultado_nuevos = []
            for n_val, n_str, info in nuevos_db:
                resultado_nuevos.append({
                    "id": None,
                    "id_aryve": None,
                    "numpro": n_str,
                    "clave": n_str,
                    "nombre": info.get("nombre", f"CONTRATISTA {n_str}"),
                    "nombre_destacado": info.get("nombre", f"CONTRATISTA {n_str}"),
                    "rfc": info.get("rfc", ""),
                    "representante": info.get("representante", ""),
                    "reg_imss": info.get("reg_imss", ""),
                    "tiene_foto": False,
                    "en_json": False,
                    "estatus": "SIN_FOTO",
                    "seleccionable": True
                })

            resultado = resultado_mapeados + resultado_nuevos

            with cls._lock:
                cls._cache_db = resultado
                cls._ultimo_pull_db = time.time()
                return list(cls._cache_db)

        except Exception as e:
            cls._agregar_log(f"[AVISO] Error cargando lista de contratistas: {e}")
            with cls._lock:
                if cls._cache_db:
                    return list(cls._cache_db)
            return []

        finally:
            with cls._lock:
                cls._db_query_en_curso = False

    # --------------------------------------------------------------------------
    # GESTIÓN DE COLA ("EN FILA")
    # --------------------------------------------------------------------------
    @classmethod
    def obtener_cola(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return list(cls._cola_memoria)

    @classmethod
    def agregar_a_cola(cls, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        with cls._lock:
            cid = str(item.get("id", "")).strip()
            cve = str(item.get("clave", item.get("numpro", ""))).strip()
            # Evitar duplicados en la cola
            if not any(
                (cid and str(x.get("id", "")).strip() == cid) or
                (cve and str(x.get("clave", x.get("numpro", ""))).strip() == cve)
                for x in cls._cola_memoria
            ):
                cls._cola_memoria.append(item)
            return list(cls._cola_memoria)

    @classmethod
    def quitar_de_cola(cls, key: Any) -> List[Dict[str, Any]]:
        with cls._lock:
            k_str = str(key).strip()
            cls._cola_memoria = [
                x for x in cls._cola_memoria
                if str(x.get("numpro", "")).strip() != k_str
                and str(x.get("clave", "")).strip() != k_str
                and str(x.get("id", "")).strip() != k_str
                and str(x.get("id_aryve", "")).strip() != k_str
            ]
            return list(cls._cola_memoria)

    @classmethod
    def vaciar_cola(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            cls._cola_memoria = []
            return []

    @classmethod
    def toggle_cola(cls, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        cid = str(item.get("id", "")).strip()
        cve = str(item.get("clave", item.get("numpro", ""))).strip()
        with cls._lock:
            idx = -1
            for i, x in enumerate(cls._cola_memoria):
                x_id = str(x.get("id", "")).strip()
                x_cve = str(x.get("clave", x.get("numpro", ""))).strip()
                if (cid and x_id and cid == x_id) or (cve and x_cve and cve == x_cve):
                    idx = i
                    break

            if idx >= 0:
                cls._cola_memoria.pop(idx)
            else:
                cls._cola_memoria.append(item)
            return list(cls._cola_memoria)

    @classmethod
    def sincronizar_cola_por_lote(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        with cls._lock:
            existentes_keys = set()
            for x in cls._cola_memoria:
                if x.get("id") is not None:
                    existentes_keys.add(f"id:{x['id']}")
                if x.get("clave"):
                    existentes_keys.add(f"cve:{str(x['clave']).strip()}")
                elif x.get("numpro"):
                    existentes_keys.add(f"cve:{str(x['numpro']).strip()}")

            for it in items:
                it_id = f"id:{it['id']}" if it.get("id") is not None else None
                it_cve = f"cve:{str(it.get('clave', it.get('numpro', ''))).strip()}"
                if (it_id and it_id in existentes_keys) or (it_cve in existentes_keys):
                    continue
                cls._cola_memoria.append(it)
                if it_id:
                    existentes_keys.add(it_id)
                existentes_keys.add(it_cve)
            return list(cls._cola_memoria)

    @classmethod
    def registrar_foto_en_catalogo(cls, contractor_id: int, numpro: Optional[str] = None, nombre: Optional[str] = None) -> bool:
        """
        Actualiza o agrega el contratista directamente en Firebase Firestore (nube) y en respaldo local,
        indicando que ya tiene foto de perfil (KontrolFiles), actualiza la caché en memoria y emite log.
        """
        with cls._lock:
            try:
                cid = int(contractor_id)
                foto_path = f"KontrolFiles/GetFile/Contratistas/{cid}/images/{int(time.time() * 1000)}"
                cve_str = str(numpro).strip() if numpro else ""

                # 1. Persistir en Firebase Firestore (Nube) y sincronizar respaldo local
                try:
                    from core.firebase_client import FirebaseClient
                    FirebaseClient.registrar_foto_contratista(
                        contractor_id=cid,
                        numpro=numpro,
                        nombre=nombre,
                        foto_path=foto_path
                    )
                except Exception as e_fb:
                    cls._agregar_log(f"   -> [AVISO FIREBASE] Error sincronizando a Firestore: {e_fb}")

                # 2. Actualizar caché en memoria inmediatamente para reflejo instantáneo en la UI (verde)
                for item in cls._cache_db:
                    it_id = item.get("id")
                    it_cve = str(item.get("clave", item.get("numpro", ""))).strip()
                    if (it_id is not None and int(it_id) == cid) or (cve_str and it_cve == cve_str):
                        item["tiene_foto"] = True
                        item["estatus"] = "COMPLETO"
                        item["en_json"] = True
                        item["foto"] = foto_path

                cls._agregar_log(f"   -> [ACTUALIZADO EN FIREBASE] Contratista #{cid} guardado en Cloud Firestore. Estatus: Con Foto (Verde).")
                return True
            except Exception as e:
                cls._agregar_log(f"   -> [AVISO] Error al registrar foto para contratista #{contractor_id}: {e}")
                return False

    # --------------------------------------------------------------------------
    # ESTADO Y LOGS DE EJECUCIÓN
    # --------------------------------------------------------------------------
    @classmethod
    def _agregar_log(cls, mensaje: str):
        marca = time.strftime("[%H:%M:%S]")
        linea = f"{marca} {mensaje}"
        cls._estado_ejecucion["logs"].append(linea)
        # Mantener últimos 1000 logs
        if len(cls._estado_ejecucion["logs"]) > 1000:
            cls._estado_ejecucion["logs"] = cls._estado_ejecucion["logs"][-1000:]
        print(linea)

    @classmethod
    def obtener_estado(cls) -> Dict[str, Any]:
        with cls._lock:
            return {
                **cls._estado_ejecucion,
                "total_cola": len(cls._cola_memoria),
                "cola": list(cls._cola_memoria)
            }

    @classmethod
    def detener_ejecucion(cls) -> Dict[str, Any]:
        """Envía la señal de detención inmediata al bot."""
        with cls._lock:
            if cls._estado_ejecucion["ejecutando"]:
                cls._estado_ejecucion["detener"] = True
                cls._agregar_log("[AVISO] Solicitud de detención recibida. Finalizando operación actual...")
                return {"ok": True, "mensaje": "Detención solicitada al bot"}
            return {"ok": False, "mensaje": "No hay ningún proceso activo"}

    # --------------------------------------------------------------------------
    # EJECUCIÓN RPA ASÍNCRONA
    # --------------------------------------------------------------------------
    @classmethod
    def iniciar_procesamiento(cls) -> Tuple[bool, str]:
        """Inicia el ciclo de generación y carga de imágenes en segundo plano."""
        with cls._lock:
            if cls._estado_ejecucion["ejecutando"]:
                return False, "Ya hay un proceso de carga ejecutándose actualmente."
            if not cls._cola_memoria:
                return False, "La lista 'EN FILA' está vacía. Selecciona al menos un contratista."

            cls._estado_ejecucion["ejecutando"] = True
            cls._estado_ejecucion["detener"] = False
            cls._estado_ejecucion["actual"] = 0
            cls._estado_ejecucion["total"] = len(cls._cola_memoria)
            cls._estado_ejecucion["logs"] = []
            cls._estado_ejecucion["veredicto"] = "EJECUTANDO"

        # Lanzar hilo independiente para no congelar la API
        hilo = threading.Thread(target=cls._bucle_ejecucion_bot, daemon=True)
        hilo.start()
        return True, f"Proceso iniciado para {len(cls._cola_memoria)} contratista(s)."

    @classmethod
    def _bucle_ejecucion_bot(cls):
        from automation.contractor_bot import ContractorBot

        cls._agregar_log("=" * 70)
        cls._agregar_log("INICIANDO PROCESO DE GAFETES Y CARGA AUTOMÁTICA EN ARYVE (EK10)")
        cls._agregar_log(f"Total de contratistas en fila a procesar: {cls._estado_ejecucion['total']}")
        cls._agregar_log("=" * 70)

        elementos_a_procesar = cls.obtener_cola()
        bot = None
        imagenes_creadas = []

        try:
            # 1. Instanciar e iniciar sesión en Aryve
            cls._agregar_log("Conectando con navegador Chrome e iniciando sesión en Aryve...")
            bot = ContractorBot(headless=False, images_dir=OUTPUT_IMAGES_DIR)
            bot.login()
            cls._agregar_log("[OK] Sesión autenticada correctamente en Aryve.")

            for i, c in enumerate(elementos_a_procesar):
                if cls._estado_ejecucion["detener"]:
                    cls._agregar_log("[DETENIDO] Proceso cancelado por el usuario.")
                    break

                numpro = str(c.get("numpro", ""))
                nombre = c.get("nombre", "")
                id_aryve = c.get("id_aryve")

                # Si no tiene id_aryve directo, intentar obtenerlo del numpro
                target_id = id_aryve or (int(numpro) if numpro.isdigit() else None)
                if not target_id:
                    cls._agregar_log(f"[OMITIDO] Contratista '{nombre}' (Clave: {numpro}) no cuenta con ID numérico para Aryve.")
                    continue

                cls._estado_ejecucion["actual"] = i + 1
                cls._estado_ejecucion["contratista_actual"] = f"{target_id} - {nombre}"
                cls._agregar_log("-" * 60)
                cls._agregar_log(f"[{i + 1}/{len(elementos_a_procesar)}] Contratista ID: {target_id} | {nombre}")

                # 2. Analizar nombre y generar imagen de perfil temporal (762x686 px)
                cls._agregar_log("   -> Analizando razón social y formateando líneas de gafete...")
                analisis = process_contractor_name(nombre)
                cls._agregar_log(f"   -> Líneas calculadas: {' / '.join(analisis['lineas'])}")

                img_path = generate_badge_for_contractor(
                    contractor_id=target_id,
                    contractor_name=nombre,
                    custom_lines=analisis["lineas"],
                    output_dir=OUTPUT_IMAGES_DIR
                )
                imagenes_creadas.append(img_path)
                cls._agregar_log(f"   -> Gafete 762x686 generado temporalmente: {os.path.basename(img_path)}")

                # 3. Proceso Selenium en Aryve
                cls._agregar_log(f"   -> Navegando a perfil: #/scco/Contratistas/{target_id}...")
                resultado = bot.process_contractor(target_id)
                cls._agregar_log(f"   -> Resultado en Aryve: [{resultado['status']}] {resultado['motivo']}")

                # 4. Registrar en contratista_mapeado.json y cambiar a estatus verde
                if resultado.get("status") in ("GUARDADO", "OMITIDO"):
                    cls.registrar_foto_en_catalogo(contractor_id=target_id, numpro=numpro, nombre=nombre)

                # 5. Eliminar la imagen creada para no dejar la carpeta pesada
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                        cls._agregar_log(f"   -> [LIMPIEZA] Imagen '{os.path.basename(img_path)}' eliminada con éxito para liberar espacio.")
                    except Exception as e:
                        cls._agregar_log(f"   -> [AVISO] No se pudo eliminar {img_path}: {e}")

                # 6. Remover de la cola de memoria
                cls.quitar_de_cola(numpro)
                time.sleep(1)

            cls._agregar_log("=" * 70)
            cls._agregar_log("[ÉXITO TOTAL] Se ha finalizado la cola de contratistas.")
            cls._agregar_log("Todas las imágenes temporales creadas han sido depuradas del disco.")
            cls._agregar_log("=" * 70)
            cls._estado_ejecucion["veredicto"] = "COMPLETADO"

        except Exception as e:
            cls._agregar_log(f"[ERROR CRÍTICO]: {e}")
            cls._estado_ejecucion["veredicto"] = "ERROR"

        finally:
            # Limpiar cualquier residuo de imágenes creadas que no se hayan borrado
            for path in imagenes_creadas:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

            if bot:
                try:
                    bot.close()
                except Exception:
                    pass

            with cls._lock:
                cls._estado_ejecucion["ejecutando"] = False
                cls._estado_ejecucion["detener"] = False
                # Forzar actualización de cache para que la tabla refresque los nuevos estatus
                cls._ultimo_pull_db = 0

