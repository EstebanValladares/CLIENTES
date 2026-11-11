"""
Core Domain: Servicios de Datos de Usuarios y Posiciones.
Mantiene consultas O(1) con tablas Hash y Tries en RAM, desacoplado de la UI.
"""
import os
import json
import datetime
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIR_USUARIOS_DATA = os.path.join(BASE_DIR, "USUARIOS", "data")

# Rutas autónomas canónicas de USUARIOS
RUTA_USUARIOS_JSON = os.path.join(DIR_USUARIOS_DATA, "Usuarios.json")
REGISTRO_USUARIOS_JSONL = os.path.join(BASE_DIR, "USUARIOS", "logger", "registro_usuarios.jsonl")
PUESTOS_PATH = (
    os.path.join(DIR_USUARIOS_DATA, "puestos.json")
    if os.path.exists(os.path.join(DIR_USUARIOS_DATA, "puestos.json"))
    else os.path.join(BASE_DIR, "USUARIOS", "puestos.json")
)
FALLOS_CLASIFICADORES_PATH = os.path.join(BASE_DIR, "USUARIOS", "logger", "fallos_clasificadores.jsonl")

class UserService:
    _cache_usuarios: Optional[List[Dict[str, Any]]] = None
    _cache_puestos: Optional[Dict[str, Any]] = None
    _last_load_time: Optional[datetime.datetime] = None

    @classmethod
    def obtener_usuarios(cls, force_reload: bool = False) -> List[Dict[str, Any]]:
        ahora = datetime.datetime.now()
        if not force_reload and cls._cache_usuarios is not None and cls._last_load_time:
            if (ahora - cls._last_load_time).total_seconds() < 60:
                return cls._cache_usuarios

        usuarios: List[Dict[str, Any]] = []
        ids_vistos = set()
        puestos_catalogo = cls.obtener_puestos()

        if os.path.exists(RUTA_USUARIOS_JSON):
            try:
                with open(RUTA_USUARIOS_JSON, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    for u in datos:
                        uid = str(u.get("ID", "")).strip()
                        nom = str(u.get("Nombre", "")).strip()
                        ape = str(u.get("Apellidos", "")).strip()
                        nom_comp = f"{nom} {ape}".strip() or nom
                        puesto = str(u.get("Posicion", "No especificado")).strip()
                        email = str(u.get("Email", "")).strip() or str(u.get("Clave", "")).strip()

                        # Clave alfanumerica de posicion oficial directamente desde Enkontrol (ej. POS-0270)
                        id_pos = str(u.get("IdPosicion", "")).strip()
                        clave_pos = str(u.get("ClavePosicion", "")).strip()
                        if not clave_pos:
                            pos_raw = u.get("Posicion")
                            if isinstance(pos_raw, dict):
                                clave_pos = str(pos_raw.get("Clave", "") or "").strip()

                        # Fallback secundario si la API no reportó clave directa
                        if not clave_pos:
                            info_puesto = puestos_catalogo.get(puesto) or puestos_catalogo.get(puesto.upper().strip()) or {}
                            clave_pos = str(info_puesto.get("clave_posicion_cloud", "")).strip()
                            if not clave_pos:
                                if puesto.upper().strip() == "LIDER DE VENTAS TAMPICO":
                                    clave_pos = "POS-0283"
                                elif id_pos and id_pos.isdigit():
                                    clave_pos = f"POS-{int(id_pos):04d}"
                                elif id_pos:
                                    clave_pos = f"POS-{id_pos}"

                        user_dict = {
                            "id": uid,
                            "nombre": nom,
                            "apellidos": ape,
                            "nombre_completo": nom_comp,
                            "clave": str(u.get("Clave", "")).strip(),
                            "correo": email,
                            "puesto": puesto,
                            "id_posicion": id_pos,
                            "clave_posicion": clave_pos,
                            "area_organizacion": str(u.get("AreaOrganizacion", "No especificada")).strip(),
                            "estatus": str(u.get("Estatus", "Activo")).strip(),
                            "vigencia_inicio": str(u.get("VigenciaInicio", "")).strip(),
                            "vigencia_fin": str(u.get("VigenciaFin", "")).strip(),
                            "fecha_creacion": str(u.get("Creado", "")).strip(),
                            "telefono": str(u.get("Telefono", "")).strip(),
                            "time_zone": str(u.get("TimeZone", "")).strip(),
                            "url_aryve": ""
                        }
                        usuarios.append(user_dict)
                        if uid:
                            ids_vistos.add(uid)
            except Exception as e:
                print(f"[UserService] Error leyendo Usuarios.json: {e}")

        # Fallback a Firebase Firestore si no hay archivo local
        if not usuarios:
            try:
                from core.firebase_client import FirebaseClient
                db = FirebaseClient.get_db()
                if db is not None:
                    docs = db.collection("USUARIOS").stream(timeout=3)
                    for d in docs:
                        u = d.to_dict()
                        uid = str(u.get("id", ""))
                        if uid and uid in ids_vistos:
                            continue
                        ids_vistos.add(uid)
                        usuarios.append({
                            "id": uid,
                            "nombre": u.get("nombre", ""),
                            "apellidos": u.get("apellidos", ""),
                            "nombre_completo": u.get("nombre_completo", ""),
                            "clave": u.get("clave", ""),
                            "correo": u.get("email", ""),
                            "puesto": u.get("puesto", ""),
                            "area_organizacion": u.get("area_organizacion", "General"),
                            "estatus": u.get("estatus", "Activo"),
                            "vigencia_inicio": u.get("vigencia_inicio", ""),
                            "vigencia_fin": u.get("vigencia_fin", ""),
                            "fecha_creacion": u.get("creado", ""),
                            "telefono": u.get("telefono", ""),
                            "time_zone": "",
                            "url_aryve": ""
                        })
                    if usuarios:
                        print(f"[UserService] {len(usuarios)} usuarios cargados desde Firebase Firestore.")
            except Exception as e_fb:
                print(f"[UserService] Error consultando Firestore: {e_fb}")

        # Complementar con procesados del bot
        if os.path.exists(REGISTRO_USUARIOS_JSONL):
            try:
                with open(REGISTRO_USUARIOS_JSONL, "r", encoding="utf-8") as f:
                    for linea in f:
                        if not linea.strip():
                            continue
                        try:
                            reg = json.loads(linea)
                            uid = str(reg.get("id", "") or reg.get("ID", "")).strip()
                            if uid and uid in ids_vistos:
                                continue
                            nom = str(reg.get("nombre", "")).strip()
                            ape = str(reg.get("apellidos", "")).strip()
                            usuarios.append({
                                "id": uid or "BOT_TEMP",
                                "nombre": nom,
                                "apellidos": ape,
                                "nombre_completo": f"{nom} {ape}".strip() or nom,
                                "clave": str(reg.get("clave", "")).strip(),
                                "correo": str(reg.get("correo", "") or reg.get("email", "")).strip(),
                                "puesto": str(reg.get("puesto", "") or reg.get("posicion", "")).strip(),
                                "area_organizacion": str(reg.get("area", "") or reg.get("area_organizacion", "")).strip(),
                                "estatus": "Procesado Bot",
                                "vigencia_inicio": "",
                                "vigencia_fin": "",
                                "fecha_creacion": str(reg.get("fecha", "")).strip(),
                                "telefono": "",
                                "time_zone": "",
                                "url_aryve": ""
                            })
                            if uid:
                                ids_vistos.add(uid)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[UserService] Error leyendo registro_usuarios.jsonl: {e}")

        cls._cache_usuarios = usuarios
        cls._last_load_time = ahora
        return usuarios

    @classmethod
    def recargar(cls) -> List[Dict[str, Any]]:
        """Invalida la caché y recarga los usuarios desde el archivo JSON local."""
        cls._cache_usuarios = None
        cls._last_load_time = None
        return cls.obtener_usuarios(force_reload=True)

    @classmethod
    def buscar_usuarios(cls, query: str = "", filtro_vigencia: str = "TODOS") -> List[Dict[str, Any]]:
        usuarios = cls.obtener_usuarios()
        if not query and filtro_vigencia == "TODOS":
            return usuarios

        q = query.strip().upper()
        ahora = datetime.datetime.now()

        def coincide(u: Dict[str, Any]) -> bool:
            if q:
                cadena_busqueda = f"{u['id']} {u['nombre_completo']} {u['correo']} {u['puesto']} {u.get('clave_posicion', '')} {u['area_organizacion']}".upper()
                if q not in cadena_busqueda:
                    return False

            if filtro_vigencia != "TODOS":
                v_fin = u.get("vigencia_fin", "")
                dt = cls._parse_fecha(v_fin)
                if filtro_vigencia == "VENCIDOS":
                    return dt is not None and dt.date() < ahora.date() and dt.year < 2050
                elif filtro_vigencia == "ESTE_MES":
                    return dt is not None and dt.year == ahora.year and dt.month == ahora.month
                elif filtro_vigencia == "PROX_MES":
                    prox_m = ahora.month + 1 if ahora.month < 12 else 1
                    prox_y = ahora.year if ahora.month < 12 else ahora.year + 1
                    return dt is not None and dt.year == prox_y and dt.month == prox_m
                elif filtro_vigencia == "ACTIVOS":
                    return dt is None or dt.date() >= ahora.date()

            return True

        return [u for u in usuarios if coincide(u)]

    @classmethod
    def obtener_puestos(cls) -> Dict[str, Any]:
        # 1. Firebase solo si se activa explícitamente por variable de entorno
        if os.getenv("USE_FIREBASE", "0").lower() in ("1", "true", "yes"):
            try:
                from core.firebase_client import FirebaseClient
                puestos_cloud = FirebaseClient.obtener_puestos()
                if puestos_cloud:
                    return puestos_cloud
            except Exception as e:
                pass

        # 2. Respaldo local si no hay conexión a internet
        if os.path.exists(PUESTOS_PATH):
            try:
                with open(PUESTOS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("puestos", {})
            except Exception as e:
                print(f"[UserService] Error en puestos.json local: {e}")
        return {}

    @classmethod
    def guardar_puesto(cls, nombre: str, area: str, niveles: list, grupos: list, clasificadores: dict) -> Dict[str, Any]:
        nombre_limpio = nombre.strip().upper()
        if not nombre_limpio:
            return {"ok": False, "error": "El nombre del puesto no puede estar vacío"}

        from core.firebase_client import FirebaseClient
        return FirebaseClient.guardar_puesto(
            nombre=nombre_limpio,
            area=area,
            niveles=niveles,
            grupos=grupos,
            clasificadores=clasificadores
        )

    @classmethod
    def sincronizar_puestos(cls) -> Dict[str, Any]:
        from core.firebase_client import FirebaseClient
        return FirebaseClient.sincronizar_puestos()

    @classmethod
    def obtener_estado_sincronizacion(cls) -> Dict[str, Any]:
        from core.firebase_client import FirebaseClient
        return FirebaseClient.obtener_estado_sincronizacion_puestos()

    @classmethod
    def crear_posicion_simple(cls, clave: str, nombre: str, categoria: str, padre: str) -> Dict[str, Any]:
        nombre = nombre.strip().upper()
        if not nombre:
            return {"ok": False, "error": "El nombre de la posicion es obligatorio."}
        clave = clave.strip().upper()
        if not clave:
            meta = cls.obtener_meta_posiciones()
            clave = meta["siguiente_clave"]
        
        try:
            if os.path.exists(PUESTOS_PATH):
                with open(PUESTOS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"puestos": {}}
            
            puestos = data.setdefault("puestos", {})
            puestos[nombre] = {
                "categoria": categoria or nombre,
                "puesto_origen": padre or categoria or nombre,
                "area_organizacion": categoria or "GENERAL",
                "clave_posicion_cloud": clave,
                "clasificadores": {},
                "total_clasificadores": 0
            }
            data["total_posiciones"] = len(puestos)
            data["ultima_actualizacion"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(PUESTOS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            cls._cache_puestos = None
            return {
                "ok": True,
                "mensaje": f"Posicion {nombre} ({clave}) guardada exitosamente.",
                "clave": clave,
                "meta": cls.obtener_meta_posiciones()
            }
        except Exception as e:
            return {"ok": False, "error": f"Error guardando posicion: {str(e)}"}

    @classmethod
    def sincronizar_desde_aryve(cls) -> Dict[str, Any]:
        """En versión del equipo, recarga los datos del catálogo local de Usuarios.json"""
        cls.recargar()
        return {"ok": True, "mensaje": "Catálogo de usuarios recargado localmente con éxito."}
    @classmethod
    def obtener_meta_posiciones(cls, sincronizar_en_vivo: bool = False) -> Dict[str, Any]:
        """
        Retorna la clave máxima encontrada (ej. POS-1080),
        la siguiente clave consecutiva (ej. POS-1081),
        y la lista de nombres de puestos y categorías disponibles.
        Si sincronizar_en_vivo es True, consulta en vivo a Enkontrol para traer lo más nuevo.
        """
        import re

        if sincronizar_en_vivo:
            try:
                cls.sincronizar_desde_aryve()
            except Exception as e:
                logger.warning(f"No se pudo sincronizar en vivo con Aryve: {e}")

        ruta_puestos = os.path.join(DIR_USUARIOS_DATA, "puestos.json")
        max_num = 0
        puestos_nombres = set()
        categorias = set()

        # 1. Analizar catálogo de puestos.json
        if os.path.exists(ruta_puestos):
            try:
                with open(ruta_puestos, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    puestos_dict = data.get("puestos", {})
                    for nom_puesto, info in puestos_dict.items():
                        if nom_puesto:
                            puestos_nombres.add(str(nom_puesto).strip())
                        if isinstance(info, dict):
                            cat = info.get("categoria")
                            if cat:
                                categorias.add(str(cat).strip())
                            clave = str(info.get("clave_posicion_cloud") or "")
                            m = re.search(r"POS-(\d+)", clave, re.IGNORECASE)
                            if m:
                                num = int(m.group(1))
                                if num > max_num:
                                    max_num = num

                    # Analizar también catálogo ordenado de posiciones registradas
                    for reg in data.get("posiciones_registradas", []):
                        if isinstance(reg, dict):
                            reg_nom = reg.get("nombre")
                            if reg_nom:
                                puestos_nombres.add(str(reg_nom).strip())
                            reg_cat = reg.get("categoria")
                            if reg_cat:
                                categorias.add(str(reg_cat).strip())
                            reg_clave = str(reg.get("clave") or "")
                            m_reg = re.search(r"POS-(\d+)", reg_clave, re.IGNORECASE)
                            if m_reg:
                                num_reg = int(m_reg.group(1))
                                if num_reg > max_num:
                                    max_num = num_reg
            except Exception as e:
                logger.error(f"Error analizando puestos.json para meta posiciones: {e}")

        # 2. Analizar catálogo real de Usuarios.json (posiciones asignadas en vivo en Enkontrol)
        ruta_usuarios = os.path.join(DIR_USUARIOS_DATA, "Usuarios.json")
        if os.path.exists(ruta_usuarios):
            try:
                with open(ruta_usuarios, "r", encoding="utf-8") as f:
                    raw_u = json.load(f)
                    for u in raw_u:
                        pos = u.get("Posicion")
                        if pos and isinstance(pos, str):
                            puestos_nombres.add(pos.strip())
                        area = u.get("AreaOrganizacion")
                        if area:
                            categorias.add(str(area).strip())

                        # Extraer clave de posición del usuario (ej. POS-1080)
                        cve_u = str(u.get("ClavePosicion", "") or "").strip()
                        if not cve_u and isinstance(pos, dict):
                            cve_u = str(pos.get("Clave", "") or "").strip()
                        if not cve_u and isinstance(pos, str):
                            cve_u = pos.strip()

                        m_u = re.search(r"POS-(\d+)", cve_u, re.IGNORECASE)
                        if m_u:
                            num_u = int(m_u.group(1))
                            if num_u > max_num:
                                max_num = num_u
            except Exception as e:
                logger.error(f"Error analizando Usuarios.json para meta posiciones: {e}")

        # Baseline oficial
        if max_num < 1079:
            max_num = 1079

        sig_num = max_num + 1
        ultima_clave = f"POS-{max_num:04d}" if max_num < 10000 else f"POS-{max_num}"
        siguiente_clave = f"POS-{sig_num:04d}" if sig_num < 10000 else f"POS-{sig_num}"

        return {
            "ok": True,
            "ultima_clave": ultima_clave,
            "siguiente_clave": siguiente_clave,
            "max_numero": max_num,
            "siguiente_numero": sig_num,
            "puestos": sorted(list(puestos_nombres)),
            "categorias": sorted(list(categorias))
        }

    @classmethod
    def crear_posicion_simple(cls, clave: str, nombre: str, categoria: str = "", padre: str = "") -> Dict[str, Any]:
        """
        Crea/registra una nueva posición en puestos.json y actualiza el catálogo.
        """
        nombre = (nombre or "").strip().upper()
        clave = (clave or "").strip().upper()
        categoria = (categoria or "").strip().upper()
        padre = (padre or "").strip()

        if not nombre:
            return {"ok": False, "error": "El nombre de la posición es obligatorio."}
        if not clave:
            meta = cls.obtener_meta_posiciones()
            clave = meta.get("siguiente_clave", "POS-1052")

        ruta_puestos = os.path.join(DIR_USUARIOS_DATA, "puestos.json")
        data = {"puestos": {}}
        if os.path.exists(ruta_puestos):
            try:
                with open(ruta_puestos, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"Error cargando puestos.json: {e}")

        puestos_dict = data.setdefault("puestos", {})
        
        puestos_dict[nombre] = {
            "categoria": categoria or nombre,
            "clasificadores": {},
            "puesto_origen": padre or nombre,
            "time_zone": "(UTC-06:00) Guadalajara, Ciudad de México, Monterrey",
            "id_posicion_cloud": None,
            "total_clasificadores": 0,
            "area_organizacion": categoria or "GENERAL",
            "clave_posicion_cloud": clave,
            "padre": padre
        }

        # Registrar en el historial ordenado de posiciones
        registradas = data.setdefault("posiciones_registradas", [])
        registradas = [r for r in registradas if isinstance(r, dict) and r.get("clave") != clave]
        registradas.append({
            "clave": clave,
            "nombre": nombre,
            "categoria": categoria or nombre,
            "padre": padre,
            "fecha_registro": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        data["posiciones_registradas"] = registradas

        data["total_posiciones"] = len(puestos_dict)
        data["ultima_actualizacion"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(ruta_puestos, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando nueva posición en puestos.json: {e}")
            return {"ok": False, "error": str(e)}

        meta_actualizada = cls.obtener_meta_posiciones()

        return {
            "ok": True,
            "mensaje": f"Posición {clave} - {nombre} guardada exitosamente.",
            "posicion": {
                "clave": clave,
                "nombre": nombre,
                "categoria": categoria,
                "padre": padre
            },
            "meta": meta_actualizada
        }

    @staticmethod
    def _parse_fecha(fecha_str: str) -> Optional[datetime.datetime]:
        if not fecha_str:
            return None
        clean = str(fecha_str).strip().split(' ')[0]
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
            try:
                return datetime.datetime.strptime(clean, fmt)
            except Exception:
                pass
        return None
