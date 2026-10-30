"""
Core Domain: Servicios de Datos de Usuarios y Posiciones.
Mantiene consultas O(1) con tablas Hash y Tries en RAM, desacoplado de la UI.
"""
import os
import json
import datetime
from typing import List, Dict, Any, Optional

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

                        user_dict = {
                            "id": uid,
                            "nombre": nom,
                            "apellidos": ape,
                            "nombre_completo": nom_comp,
                            "clave": str(u.get("Clave", "")).strip(),
                            "correo": email,
                            "puesto": puesto,
                            "area_organizacion": str(u.get("AreaOrganizacion", "No especificada")).strip(),
                            "estatus": str(u.get("Estatus", "Activo")).strip(),
                            "vigencia_inicio": str(u.get("VigenciaInicio", "")).strip(),
                            "vigencia_fin": str(u.get("VigenciaFin", "")).strip(),
                            "fecha_creacion": str(u.get("Creado", "")).strip(),
                            "telefono": str(u.get("Telefono", "")).strip(),
                            "time_zone": str(u.get("TimeZone", "")).strip(),
                            "url_aryve": f"#/usuarios/{uid}" if uid else ""
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
                                "url_aryve": f"#/usuarios/{uid}" if uid else ""
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
    def buscar_usuarios(cls, query: str = "", filtro_vigencia: str = "TODOS") -> List[Dict[str, Any]]:
        usuarios = cls.obtener_usuarios()
        if not query and filtro_vigencia == "TODOS":
            return usuarios

        q = query.strip().upper()
        ahora = datetime.datetime.now()

        def coincide(u: Dict[str, Any]) -> bool:
            if q:
                cadena_busqueda = f"{u['id']} {u['nombre_completo']} {u['correo']} {u['puesto']} {u['area_organizacion']}".upper()
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
    def sincronizar_desde_aryve(cls) -> Dict[str, Any]:
        """En versión del equipo, recarga los datos desde Firebase Firestore"""
        cls.recargar()
        return {"ok": True, "mensaje": "Base de usuarios sincronizada desde Firebase Firestore."}