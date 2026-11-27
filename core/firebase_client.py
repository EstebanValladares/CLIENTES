"""
Core Domain: Gestor Centralizado de Datos Locales + Sincronización Firestore (db-velas).
Mantiene lectura ultrarrápida O(1) en RAM y archivos locales (.json), sincronizando
bidireccionalmente con Firebase Firestore cuando firebase_credentials.json está presente.
"""

import os
import re
import json
import time
import threading
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CRED_PATH = os.path.join(BASE_DIR, "firebase_credentials.json")
DIR_USUARIOS_DATA = os.path.join(BASE_DIR, "USUARIOS", "data")
USUARIOS_LOCAL_PATH = os.path.join(DIR_USUARIOS_DATA, "Usuarios.json")
PUESTOS_LOCAL_PATH = (
    os.path.join(DIR_USUARIOS_DATA, "puestos.json")
    if os.path.exists(os.path.join(DIR_USUARIOS_DATA, "puestos.json"))
    else os.path.join(BASE_DIR, "USUARIOS", "puestos.json")
)


def _sanitizar_doc_id(texto: str) -> str:
    """Normaliza un identificador para usarlo como ID de documento válido en Firestore."""
    limpio = re.sub(r"[/\\]+", "_", str(texto or "").strip())
    return limpio or "SIN_NOMBRE"


class FirebaseClient:
    """Cliente unificado local-first con sincronización bidireccional a Firestore."""
    _lock = threading.Lock()
    _db = None
    _init_attempted = False
    _cache_puestos: Dict[str, Any] = {}
    _ultimo_fetch_puestos: float = 0

    @classmethod
    def get_db(cls):
        """Retorna instancia de Firestore si firebase_credentials.json existe y es válido."""
        if cls._db is not None:
            return cls._db

        with cls._lock:
            if cls._db is not None:
                return cls._db
            if cls._init_attempted or not os.path.exists(CRED_PATH):
                return None
            cls._init_attempted = True
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                if not firebase_admin._apps:
                    cred = credentials.Certificate(CRED_PATH)
                    firebase_admin.initialize_app(cred)
                cls._db = firestore.client()
                return cls._db
            except Exception as e:
                print(f"[FirebaseClient] No se pudo inicializar Firestore: {e}")
                return None

    # =========================================================================
    # MÓDULO USUARIOS: POSICIONES (PUESTOS Y CLASIFICADORES)
    # =========================================================================
    @classmethod
    def _leer_puestos_locales(cls) -> Dict[str, Any]:
        if os.path.exists(PUESTOS_LOCAL_PATH):
            try:
                with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("puestos", {}) or {}
            except Exception as e:
                print(f"[FirebaseClient] Error leyendo puestos.json local: {e}")
        return {}

    @classmethod
    def _escribir_puestos_locales(cls, puestos: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(PUESTOS_LOCAL_PATH), exist_ok=True)
        datos_loc: Dict[str, Any] = {
            "_comentario": "Catálogo oficial de puestos y posiciones",
            "puestos": puestos,
        }
        if os.path.exists(PUESTOS_LOCAL_PATH):
            try:
                with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                    prev = json.load(f)
                    if isinstance(prev, dict):
                        prev["puestos"] = puestos
                        datos_loc = prev
            except Exception:
                pass
        datos_loc["total_posiciones"] = len(puestos)
        datos_loc["ultima_actualizacion"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(PUESTOS_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(datos_loc, f, indent=2, ensure_ascii=False)

    @classmethod
    def obtener_puestos(cls, forzar: bool = False) -> Dict[str, Any]:
        """Obtiene el catálogo de puestos desde RAM / puestos.json (y Firestore si local está vacío)."""
        with cls._lock:
            if not forzar and cls._cache_puestos:
                return dict(cls._cache_puestos)

            puestos = cls._leer_puestos_locales()
            if puestos:
                cls._cache_puestos = puestos
                cls._ultimo_fetch_puestos = time.time()
                return dict(puestos)

        # Fallback a Firestore si no hay puestos locales
        db = cls.get_db()
        if db is not None:
            try:
                remotos: Dict[str, Any] = {}
                for doc in db.collection("POSICIONES").stream(timeout=10):
                    if doc.id == "META_CONSECUTIVO":
                        continue
                    d = doc.to_dict() or {}
                    nombre = str(d.get("nombre") or doc.id).strip().upper()
                    remotos[nombre] = d
                if remotos:
                    with cls._lock:
                        cls._escribir_puestos_locales(remotos)
                        cls._cache_puestos = remotos
                        cls._ultimo_fetch_puestos = time.time()
                    return dict(remotos)
            except Exception as e:
                print(f"[FirebaseClient] Error leyendo POSICIONES desde Firestore: {e}")

        return {}

    @classmethod
    def obtener_puesto_por_nombre(cls, nombre: str) -> Optional[Dict[str, Any]]:
        """Busca la configuración de un puesto específico."""
        puestos = cls.obtener_puestos()
        nombre_clean = str(nombre).strip().upper()
        if nombre_clean in puestos:
            return puestos[nombre_clean]

        for k, v in puestos.items():
            if k.upper() == nombre_clean:
                return v
        return None

    @classmethod
    def guardar_puesto(
        cls,
        nombre: str,
        area: str,
        niveles: list,
        grupos: list,
        clasificadores: dict
    ) -> Dict[str, Any]:
        """Guarda un puesto en puestos.json local y lo replica a Firestore (POSICIONES)."""
        nombre_limpio = nombre.strip().upper()
        if not nombre_limpio:
            return {"ok": False, "error": "El nombre del puesto no puede estar vacío."}

        conteo_abuelos = {}
        conteo_total = 0
        for k, v in clasificadores.items():
            sub = len(v) if isinstance(v, list) else 0
            conteo_abuelos[k] = sub
            conteo_total += sub

        nuevo_puesto_data = {
            "nombre": nombre_limpio,
            "area_organizacional": area.strip().upper(),
            "total_clasificadores": conteo_total,
            "resumen_clasificadores_por_abuelo": conteo_abuelos,
            "niveles_asignados": niveles,
            "grupos": grupos,
            "clasificadores": clasificadores,
            "actualizado_en": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            with cls._lock:
                puestos = cls._leer_puestos_locales()
                puestos[nombre_limpio] = nuevo_puesto_data
                cls._escribir_puestos_locales(puestos)
                cls._cache_puestos = puestos

            en_nube = False
            db = cls.get_db()
            if db is not None:
                try:
                    doc_id = _sanitizar_doc_id(nombre_limpio)
                    db.collection("POSICIONES").document(doc_id).set(nuevo_puesto_data, merge=True)
                    en_nube = True
                except Exception as e_fb:
                    print(f"[FirebaseClient] Aviso guardando '{nombre_limpio}' en Firestore: {e_fb}")

            return {
                "ok": True,
                "offline": not en_nube,
                "firebase_synced": en_nube,
                "mensaje": f"Puesto '{nombre_limpio}' guardado" + (" y sincronizado en Firestore." if en_nube else " localmente.")
            }
        except Exception as e_loc:
            print(f"[FirebaseClient] Error guardando puesto local: {e_loc}")
            return {"ok": False, "error": str(e_loc)}

    @classmethod
    def sincronizar_puestos(cls) -> Dict[str, Any]:
        """Sincroniza bidireccionalmente puestos.json <-> colección POSICIONES en Firestore."""
        locales = cls._leer_puestos_locales()
        db = cls.get_db()
        if db is None:
            with cls._lock:
                cls._cache_puestos = locales
            return {
                "ok": True,
                "total": len(locales),
                "firebase_synced": False,
                "mensaje": f"Catálogo local recargado con {len(locales)} posiciones (Firestore no disponible)."
            }

        try:
            col = db.collection("POSICIONES")
            remotos: Dict[str, Any] = {}
            for doc in col.stream(timeout=15):
                if doc.id == "META_CONSECUTIVO":
                    continue
                d = doc.to_dict() or {}
                nombre = str(d.get("nombre") or doc.id).strip().upper()
                remotos[nombre] = d

            # Mezclar: si viene algo de Firestore que no está en local (o es más reciente), traerlo
            combinados = dict(remotos)
            por_subir: Dict[str, Any] = {}
            for k, v_loc in locales.items():
                k_up = k.strip().upper()
                v_clean = dict(v_loc)
                v_clean.setdefault("nombre", k_up)
                v_clean["fecha_sincronizacion"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                v_rem = remotos.get(k_up)
                if not v_rem or str(v_loc.get("actualizado_en", "")) >= str(v_rem.get("actualizado_en", "")):
                    combinados[k_up] = v_clean
                    por_subir[k_up] = v_clean

            # Subir en lotes de 400
            items = list(por_subir.items())
            for i in range(0, len(items), 400):
                batch = db.batch()
                for k_up, payload in items[i:i + 400]:
                    doc_ref = col.document(_sanitizar_doc_id(k_up))
                    batch.set(doc_ref, payload, merge=True)
                batch.commit()

            with cls._lock:
                cls._escribir_puestos_locales(combinados)
                cls._cache_puestos = combinados
                cls._ultimo_fetch_puestos = time.time()

            return {
                "ok": True,
                "total": len(combinados),
                "subidos": len(por_subir),
                "descargados": max(0, len(combinados) - len(locales)),
                "firebase_synced": True,
                "mensaje": f"Sincronizadas {len(combinados)} posiciones con Firestore (POSICIONES)."
            }
        except Exception as e:
            print(f"[FirebaseClient] Error sincronizando POSICIONES: {e}")
            return {"ok": False, "error": str(e), "total": len(locales)}

    @classmethod
    def obtener_max_consecutivo_posicion(cls) -> int:
        """Lee en 1 sola lectura (POSICIONES/META_CONSECUTIVO) el consecutivo POS-XXXX más alto en Firestore."""
        db = cls.get_db()
        if db is None:
            return 0
        try:
            snap = db.collection("POSICIONES").document("META_CONSECUTIVO").get(timeout=3)
            if snap.exists:
                data = snap.to_dict() or {}
                return int(data.get("max_numero") or 0)
        except Exception as e:
            print(f"[FirebaseClient] Aviso leyendo POSICIONES/META_CONSECUTIVO: {e}")
        return 0

    @classmethod
    def registrar_posicion_en_firestore(
        cls,
        clave: str,
        nombre: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Guarda una posición en POSICIONES y actualiza POSICIONES/META_CONSECUTIVO si el consecutivo es mayor."""
        db = cls.get_db()
        if db is None:
            return False
        try:
            col = db.collection("POSICIONES")
            doc_data = dict(payload)
            doc_data["nombre"] = nombre.strip().upper()
            doc_data["clave_posicion_cloud"] = clave.strip().upper()
            doc_data["fecha_sincronizacion"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            col.document(_sanitizar_doc_id(doc_data["nombre"])).set(doc_data, merge=True)

            m = re.search(r"POS-(\d+)", str(clave or ""), re.IGNORECASE)
            if m:
                num = int(m.group(1))
                meta_ref = col.document("META_CONSECUTIVO")
                snap = meta_ref.get(timeout=3)
                actual = int((snap.to_dict() or {}).get("max_numero") or 0) if snap.exists else 0
                if num >= actual:
                    meta_ref.set({
                        "max_numero": num,
                        "ultima_clave": f"POS-{num:04d}" if num < 10000 else f"POS-{num}",
                        "ultima_posicion_nombre": doc_data["nombre"],
                        "actualizado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }, merge=True)
            return True
        except Exception as e:
            print(f"[FirebaseClient] Aviso registrando posición '{nombre}' en Firestore: {e}")
            return False

    @classmethod
    def obtener_estado_sincronizacion_puestos(cls) -> Dict[str, Any]:
        """Retorna el estado operativo del catálogo local y Firestore."""
        puestos = cls.obtener_puestos()
        db = cls.get_db()
        return {
            "firebase_online": db is not None,
            "total_puestos": len(puestos),
            "total_puestos_local": len(puestos),
            "pendientes_subir": 0,
            "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "modo": "Local + Firestore (db-velas)" if db is not None else "Local Autónomo"
        }

    # =========================================================================
    # MÓDULO USUARIOS: SINCRONIZACIÓN A COLECCIÓN USUARIOS
    # =========================================================================
    @staticmethod
    def _normalizar_usuario_firestore(u: Dict[str, Any]) -> Optional[tuple[str, Dict[str, Any]]]:
        uid = str(u.get("ID") or u.get("id") or "").strip()
        if not uid:
            return None

        nombre = str(u.get("Nombre") or u.get("nombre") or "").strip()
        apellidos = str(u.get("Apellidos") or u.get("apellidos") or "").strip()
        nombre_completo = str(u.get("nombre_completo") or f"{nombre} {apellidos}".strip()).strip()
        id_val: Any = int(uid) if uid.isdigit() else uid

        payload = {
            "id": id_val,
            "clave": str(u.get("Clave") or u.get("clave") or "").strip(),
            "email": str(u.get("Email") or u.get("email") or u.get("correo") or "").strip(),
            "nombre": nombre,
            "apellidos": apellidos,
            "nombre_completo": nombre_completo,
            "telefono": str(u.get("Telefono") or u.get("telefono") or "").strip(),
            "puesto": str(u.get("Posicion") or u.get("puesto") or "").strip(),
            "clave_posicion": str(u.get("ClavePosicion") or u.get("clave_posicion") or "").strip(),
            "id_posicion": str(u.get("IdPosicion") or u.get("id_posicion") or "").strip(),
            "area_organizacion": str(u.get("AreaOrganizacion") or u.get("area_organizacion") or u.get("area_organizacional") or "").strip(),
            "id_area": str(u.get("IdArea") or u.get("id_area") or "").strip(),
            "estatus": str(u.get("Estatus") or u.get("estatus") or "Activo").strip(),
            "bloqueado": bool(u.get("Bloqueado") if "Bloqueado" in u else u.get("bloqueado", False)),
            "creado": str(u.get("Creado") or u.get("creado") or "").strip(),
            "modificado": str(u.get("Modificado") or u.get("modificado") or "").strip(),
            "inicio_operaciones": str(u.get("InicioOperaciones") or u.get("inicio_operaciones") or "").strip(),
            "vigencia_inicio": str(u.get("VigenciaInicio") or u.get("vigencia_inicio") or "").strip(),
            "vigencia_fin": str(u.get("VigenciaFin") or u.get("vigencia_fin") or "").strip(),
            "fecha_sincronizacion": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        return _sanitizar_doc_id(uid), payload

    @classmethod
    def sincronizar_usuarios_a_firestore(cls, usuarios: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Sube/actualiza los usuarios en la colección USUARIOS de Firestore en lotes."""
        db = cls.get_db()
        if db is None:
            return {"ok": False, "mensaje": "Firestore no disponible (falta firebase_credentials.json).", "total": 0}

        if usuarios is None:
            if not os.path.exists(USUARIOS_LOCAL_PATH):
                return {"ok": False, "mensaje": "No se encontró Usuarios.json.", "total": 0}
            with open(USUARIOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                usuarios = json.load(f)

        normalizados: List[tuple[str, Dict[str, Any]]] = []
        for u in usuarios or []:
            if isinstance(u, dict):
                norm = cls._normalizar_usuario_firestore(u)
                if norm:
                    normalizados.append(norm)

        col = db.collection("USUARIOS")
        for i in range(0, len(normalizados), 400):
            batch = db.batch()
            for doc_id, payload in normalizados[i:i + 400]:
                batch.set(col.document(doc_id), payload, merge=True)
            batch.commit()

        return {"ok": True, "total": len(normalizados), "mensaje": f"{len(normalizados)} usuarios sincronizados en Firestore (USUARIOS)."}

    @classmethod
    def sincronizar_obras_a_firestore(cls, obras_resultado: dict) -> bool:
        """No-op: las obras (56 MB) se gestionan de forma autónoma en obras.json."""
        return True
