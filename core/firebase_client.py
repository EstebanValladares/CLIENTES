"""
Core Domain: Cliente Centralizado de Firebase Firestore para Dashboard EK10.
Maneja conexión segura, lectura/escritura en la nube y caché en memoria con fallback local.
"""

import os
# Bandera para alternar entre Firebase y Modo Autónomo Local (Llave Maestra Aryve)
USE_FIREBASE = os.getenv("USE_FIREBASE", "1").lower() in ("1", "true", "yes")

import json
import time
import threading
from typing import Dict, Any, Optional

import firebase_admin
from firebase_admin import credentials, firestore

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CRED_PATH = os.path.join(BASE_DIR, "firebase_credentials.json")
PUESTOS_LOCAL_PATH = (
    os.path.join(BASE_DIR, "USUARIOS", "data", "puestos.json")
    if os.path.exists(os.path.join(BASE_DIR, "USUARIOS", "data", "puestos.json"))
    else os.path.join(BASE_DIR, "USUARIOS", "puestos.json")
)
CONTRATISTAS_LOCAL_PATH = os.path.join(BASE_DIR, "CONTRATISTAS", "contratista_mapeado.json")


class FirebaseClient:
    _lock = threading.Lock()
    _app: Optional[firebase_admin.App] = None
    _db: Optional[firestore.Client] = None
    _cache_puestos: Dict[str, Any] = {}
    _ultimo_fetch_puestos: float = 0
    _TTL_PUESTOS_SEG: int = 20  # Refresca cada 20s para captar cambios de otros usuarios
    _cache_contratistas: list = []
    _ultimo_fetch_contratistas: float = 0
    _TTL_CONTRATISTAS_SEG: int = 15

    @classmethod
    def get_db(cls) -> Optional[firestore.Client]:
        """Obtiene o inicializa el cliente Firestore de forma singleton y thread-safe."""
        with cls._lock:
            if not USE_FIREBASE:
                return None
            if cls._db is not None:
                return cls._db

            if not os.path.exists(CRED_PATH):
                print(f"[FirebaseClient] No se encontró el archivo de credenciales: {CRED_PATH}")
                return None

            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate(CRED_PATH)
                    cls._app = firebase_admin.initialize_app(cred)
                else:
                    cls._app = firebase_admin.get_app()

                cls._db = firestore.client()
                print("[FirebaseClient] Conexión a Firebase Firestore inicializada exitosamente.")
                return cls._db
            except Exception as e:
                print(f"[FirebaseClient] Error inicializando Firebase Firestore: {e}")
                return None

    # =========================================================================
    # MÓDULO USUARIOS: PUESTOS Y CLASIFICADORES
    # =========================================================================
    @classmethod
    def obtener_puestos(cls, forzar: bool = False) -> Dict[str, Any]:
        """
        Obtiene el catálogo de puestos.
        Prioridad: Firebase Firestore (en la nube). Si hay puestos locales pendientes
        de subir, los sincroniza automáticamente.
        Respaldo: Si no hay internet o Firebase no responde, devuelve puestos.json local
        de forma transparente y sin errores.
        """
        ahora = time.time()
        with cls._lock:
            if not forzar and cls._cache_puestos and (ahora - cls._ultimo_fetch_puestos < cls._TTL_PUESTOS_SEG):
                return dict(cls._cache_puestos)

        db = cls.get_db()
        if db is not None:
            try:
                # 1. Revisar si hay puestos guardados en local que quedaron pendientes por falta de red
                cls._auto_subir_pendientes_si_hay(db)

                # 2. Descargar catálogo maestro desde Firestore
                doc_ref = db.collection("USUARIOS").document("puestos")
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict() or {}
                    puestos_nube = data.get("puestos", {})
                    if puestos_nube:
                        with cls._lock:
                            cls._cache_puestos = puestos_nube
                            cls._ultimo_fetch_puestos = time.time()

                        # 3. Mantener espejo local actualizado con lo que descargamos de la nube
                        try:
                            with open(PUESTOS_LOCAL_PATH, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                        except Exception:
                            pass

                        return dict(puestos_nube)
            except Exception as e:
                print(f"[FirebaseClient] Aviso: No se pudo conectar a Firebase ({e}). Usando catálogo local.")

        # Respaldo local inmediato si Firestore no responde o no hay internet
        if os.path.exists(PUESTOS_LOCAL_PATH):
            try:
                with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                    data_loc = json.load(f)
                    puestos_loc = data_loc.get("puestos", {})
                    with cls._lock:
                        cls._cache_puestos = puestos_loc
                        cls._ultimo_fetch_puestos = time.time()
                    return puestos_loc
            except Exception as e_loc:
                print(f"[FirebaseClient] Error leyendo puestos.json local: {e_loc}")

        return {}

    @classmethod
    def _auto_subir_pendientes_si_hay(cls, db: firestore.Client) -> int:
        """Sube silenciosamente cualquier puesto que se haya guardado localmente en modo offline."""
        if not os.path.exists(PUESTOS_LOCAL_PATH):
            return 0
        try:
            with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                datos_loc = json.load(f)
            puestos = datos_loc.get("puestos", {})
            pendientes = {k: v for k, v in puestos.items() if v.get("_pendiente_sincronizar")}
            if not pendientes:
                return 0

            doc_ref = db.collection("USUARIOS").document("puestos")
            doc = doc_ref.get()
            nube_dict = {}
            comentario = "Base de datos oficial centralizada en Firebase Firestore"
            if doc.exists:
                doc_data = doc.to_dict() or {}
                nube_dict = doc_data.get("puestos", {})
                comentario = doc_data.get("_comentario", comentario)

            items_coll = db.collection("USUARIOS").document("puestos").collection("items")
            for nombre_puesto, p_data in pendientes.items():
                limpio = dict(p_data)
                limpio.pop("_pendiente_sincronizar", None)
                nube_dict[nombre_puesto] = limpio
                puestos[nombre_puesto]["_pendiente_sincronizar"] = False

                doc_id = nombre_puesto.replace("/", "-")
                items_coll.document(doc_id).set(limpio)

            doc_ref.set({
                "_comentario": comentario,
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "puestos": nube_dict
            })

            # Guardar local sin las banderas de pendiente
            datos_loc["puestos"] = puestos
            with open(PUESTOS_LOCAL_PATH, "w", encoding="utf-8") as f:
                json.dump(datos_loc, f, indent=2, ensure_ascii=False)

            print(f"[FirebaseClient] Auto-sincronizados {len(pendientes)} puestos pendientes hacia Firebase.")
            return len(pendientes)
        except Exception as e:
            print(f"[FirebaseClient] No se pudieron auto-subir pendientes: {e}")
            return 0

    @classmethod
    def sincronizar_catalogo_completo(cls, catalogo_dict: Dict[str, Any]) -> bool:
        """Sube el diccionario completo de puestos y posiciones a Firebase Firestore."""
        db = cls.get_db()
        if db is None:
            return False
        try:
            doc_ref = db.collection("USUARIOS").document("puestos")
            doc_ref.set({
                "_comentario": "Catálogo integral de 230 puestos y posiciones sincronizado desde Aryve Cloud",
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_posiciones": len(catalogo_dict),
                "puestos": catalogo_dict
            })
            with cls._lock:
                cls._cache_puestos = dict(catalogo_dict)
                cls._ultimo_fetch_puestos = time.time()
            return True
        except Exception as e:
            print(f"[FirebaseClient] Error al sincronizar catálogo completo en Firestore: {e}")
            return False

    @classmethod
    def guardar_puesto(
        cls,
        nombre: str,
        area: str,
        niveles: list,
        grupos: list,
        clasificadores: dict
    ) -> Dict[str, Any]:
        """
        Guarda un nuevo puesto o actualiza uno existente.
        - Si hay internet: Guarda en Firestore y en puestos.json local (confirmado).
        - Si NO hay internet: Guarda en puestos.json local con marca '_pendiente_sincronizar: true'
          para que no se pierda y se suba automáticamente cuando vuelva la red.
        """
        nombre_limpio = nombre.strip().upper()
        if not nombre_limpio:
            return {"ok": False, "error": "El nombre del puesto no puede estar vacío."}

        # Calcular totales y resúmenes
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

        db = cls.get_db()
        exito_nube = False

        if db is not None:
            try:
                # 1. Actualizar el doc principal USUARIOS/puestos
                doc_ref = db.collection("USUARIOS").document("puestos")
                doc = doc_ref.get()
                puestos_dict = {}
                comentario = "Base de datos oficial centralizada en Firebase Firestore"
                if doc.exists:
                    doc_data = doc.to_dict() or {}
                    puestos_dict = doc_data.get("puestos", {})
                    comentario = doc_data.get("_comentario", comentario)

                puestos_dict[nombre_limpio] = nuevo_puesto_data

                doc_ref.set({
                    "_comentario": comentario,
                    "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "puestos": puestos_dict
                })

                # 2. Guardar también en la subcolección de items individuales
                doc_id = nombre_limpio.replace("/", "-")
                db.collection("USUARIOS").document("puestos").collection("items").document(doc_id).set(nuevo_puesto_data)

                exito_nube = True
                nuevo_puesto_data["_pendiente_sincronizar"] = False
                print(f"[FirebaseClient] Puesto '{nombre_limpio}' guardado exitosamente en Firebase Firestore.")

                with cls._lock:
                    cls._cache_puestos[nombre_limpio] = nuevo_puesto_data
                    cls._ultimo_fetch_puestos = time.time()

            except Exception as e:
                print(f"[FirebaseClient] Error guardando puesto en Firestore ({e}). Se guardará en respaldo local.")
                nuevo_puesto_data["_pendiente_sincronizar"] = True
        else:
            nuevo_puesto_data["_pendiente_sincronizar"] = True

        # 3. Guardar SIEMPRE en el JSON local como respaldo garantizado
        try:
            datos_loc = {"_comentario": "Respaldo local", "puestos": {}}
            if os.path.exists(PUESTOS_LOCAL_PATH):
                try:
                    with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                        datos_loc = json.load(f)
                except Exception:
                    pass

            if "puestos" not in datos_loc:
                datos_loc["puestos"] = {}

            datos_loc["puestos"][nombre_limpio] = nuevo_puesto_data
            datos_loc["ultima_actualizacion"] = time.strftime("%Y-%m-%d %H:%M:%S")

            with open(PUESTOS_LOCAL_PATH, "w", encoding="utf-8") as f:
                json.dump(datos_loc, f, indent=2, ensure_ascii=False)

            with cls._lock:
                cls._cache_puestos[nombre_limpio] = nuevo_puesto_data

        except Exception as e_loc:
            print(f"[FirebaseClient] Error guardando respaldo local: {e_loc}")

        if exito_nube:
            return {
                "ok": True,
                "offline": False,
                "mensaje": f"Puesto '{nombre_limpio}' guardado exitosamente en Firebase Firestore (Nube) y respaldo local."
            }
        else:
            return {
                "ok": True,
                "offline": True,
                "mensaje": f"Puesto '{nombre_limpio}' guardado en local (marcado para sincronizar con Firebase cuando haya red)."
            }

    @classmethod
    def sincronizar_puestos(cls) -> Dict[str, Any]:
        """
        Sincronización bidireccional forzada:
        1. Sube cualquier puesto local pendiente a Firestore.
        2. Descarga todos los puestos más recientes de Firestore.
        3. Actualiza puestos.json local y la memoria caché.
        """
        db = cls.get_db()
        if db is None:
            pendientes = 0
            if os.path.exists(PUESTOS_LOCAL_PATH):
                try:
                    with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        pendientes = sum(1 for v in d.get("puestos", {}).values() if v.get("_pendiente_sincronizar"))
                except Exception:
                    pass
            return {
                "ok": False,
                "offline": True,
                "pendientes": pendientes,
                "mensaje": "Sin conexión a Firebase. El sistema continúa operando con el catálogo local."
            }

        try:
            subidos = cls._auto_subir_pendientes_si_hay(db)
            puestos_cloud = cls.obtener_puestos(forzar=True)
            return {
                "ok": True,
                "offline": False,
                "pendientes_subidos": subidos,
                "total_puestos": len(puestos_cloud),
                "ultima_actualizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mensaje": f"Sincronización completa: {subidos} pendientes subidos, {len(puestos_cloud)} puestos al día."
            }
        except Exception as e:
            return {
                "ok": False,
                "offline": True,
                "error": str(e),
                "mensaje": f"Error durante la sincronización: {e}"
            }

    @classmethod
    def obtener_estado_sincronizacion_puestos(cls) -> Dict[str, Any]:
        """Informa si Firebase está alcanzable, cuántos puestos hay y si hay pendientes por subir."""
        db = cls.get_db()
        online = db is not None
        pendientes = 0
        total_local = 0
        ultima_act = ""

        if os.path.exists(PUESTOS_LOCAL_PATH):
            try:
                with open(PUESTOS_LOCAL_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    puestos = d.get("puestos", {})
                    total_local = len(puestos)
                    pendientes = sum(1 for v in puestos.values() if v.get("_pendiente_sincronizar"))
                    ultima_act = d.get("ultima_actualizacion", "")
            except Exception:
                pass

        return {
            "online": online,
            "pendientes_por_subir": pendientes,
            "total_puestos_local": total_local,
            "ultima_actualizacion": ultima_act,
            "modo": "Nube + Espejo Local" if online else "Solo Local (Offline)"
        }

    # =========================================================================
    # MÓDULO CONTRATISTAS: CATÁLOGO Y ESTATUS DE FOTOS
    # =========================================================================
    @classmethod
    def obtener_contratistas(cls, forzar: bool = False) -> list:
        """
        Obtiene el catálogo de contratistas mapeados directamente desde Firebase Firestore
        (colección CONTRATISTAS -> doc catalogo).
        Si falla la red o no hay conexión, usa contratista_mapeado.json local como respaldo.
        """
        ahora = time.time()
        with cls._lock:
            if not forzar and cls._cache_contratistas and (ahora - cls._ultimo_fetch_contratistas < cls._TTL_CONTRATISTAS_SEG):
                return list(cls._cache_contratistas)

        db = cls.get_db()
        if db is not None:
            try:
                doc_ref = db.collection("CONTRATISTAS").document("catalogo")
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict() or {}
                    lista_nube = data.get("contratistas", [])
                    if lista_nube:
                        with cls._lock:
                            cls._cache_contratistas = lista_nube
                            cls._ultimo_fetch_contratistas = time.time()

                        # Mantener respaldo local sincronizado
                        try:
                            with open(CONTRATISTAS_LOCAL_PATH, "w", encoding="utf-8") as f:
                                json.dump(lista_nube, f, indent=2, ensure_ascii=False)
                        except Exception:
                            pass

                        return list(lista_nube)
            except Exception as e:
                print(f"[FirebaseClient] Error consultando CONTRATISTAS en Firestore: {e}. Usando local.")

        # Respaldo local
        if os.path.exists(CONTRATISTAS_LOCAL_PATH):
            try:
                with open(CONTRATISTAS_LOCAL_PATH, "r", encoding="utf-8") as f:
                    lista_loc = json.load(f)
                    with cls._lock:
                        cls._cache_contratistas = lista_loc
                        cls._ultimo_fetch_contratistas = time.time()
                    return lista_loc
            except Exception as e_loc:
                print(f"[FirebaseClient] Error leyendo contratista_mapeado.json local: {e_loc}")

        return []

    @classmethod
    def registrar_foto_contratista(
        cls,
        contractor_id: int,
        numpro: Optional[str] = None,
        nombre: Optional[str] = None,
        foto_path: Optional[str] = None
    ) -> bool:
        """
        Registra la foto de un contratista directamente en Firebase Firestore
        (en CONTRATISTAS/catalogo y en el doc individual CONTRATISTAS/{id}),
        actualiza la caché y sincroniza el archivo local de respaldo.
        """
        cid = int(contractor_id)
        cve_str = str(numpro).strip() if numpro else ""
        now_str = time.strftime("%d/%m/%Y %H:%M:%S")
        if not foto_path:
            foto_path = f"KontrolFiles/GetFile/Contratistas/{cid}/images/{int(time.time() * 1000)}"

        # 1. Obtener lista actual (de Firestore o local)
        lista = cls.obtener_contratistas(forzar=True)
        encontrado = False

        for c in lista:
            c_id = c.get("id")
            c_cve = str(c.get("clave", "")).strip()
            if (c_id is not None and int(c_id) == cid) or (cve_str and c_cve == cve_str):
                c["foto"] = foto_path
                c["modificado"] = now_str
                c["modificado_por"] = "SISTEMA_DASHBOARD"
                c["archivo_imagen"] = f"{cid}.png"
                if nombre and not c.get("nombre"):
                    c["nombre"] = nombre
                item_actualizado = dict(c)
                encontrado = True
                break

        if not encontrado:
            item_actualizado = {
                "id": cid,
                "clave": cve_str or str(cid),
                "clave_ek9": None,
                "rfc": "",
                "nombre": nombre or f"CONTRATISTA {cid}",
                "nombre_limpio": nombre or f"CONTRATISTA {cid}",
                "nombre_destacado": nombre or f"CONTRATISTA {cid}",
                "lineas_imagen": [],
                "archivo_imagen": f"{cid}.png",
                "slug_imagen": f"{cid}.png",
                "tipo_entidad": "EMPRESA",
                "es_prueba": False,
                "id_proveedor": None,
                "proveedor": nombre or "",
                "representante": None,
                "direccion": None,
                "asentamiento": None,
                "domicilio": None,
                "nss": None,
                "estatus": "Activo",
                "activo": True,
                "regimen": None,
                "vinculo_proveedor": True,
                "destajista": False,
                "objeto_social": None,
                "foto": foto_path,
                "version": str(int(time.time())),
                "creado": now_str,
                "creado_por": "SISTEMA_DASHBOARD",
                "modificado": now_str,
                "modificado_por": "SISTEMA_DASHBOARD"
            }
            lista.append(item_actualizado)

        # 2. Guardar en Firebase Firestore
        db = cls.get_db()
        if db is not None:
            try:
                # Actualizar doc consolidado
                db.collection("CONTRATISTAS").document("catalogo").set({
                    "ultima_actualizacion": now_str,
                    "total": len(lista),
                    "contratistas": lista
                })
                # Actualizar doc individual
                db.collection("CONTRATISTAS").document(str(cid)).set(item_actualizado)
                print(f"[FirebaseClient] Foto de contratista #{cid} guardada exitosamente en Firebase Firestore.")
            except Exception as e:
                print(f"[FirebaseClient] Error guardando foto en Firestore para contratista #{cid}: {e}")

        # 3. Guardar en respaldo local
        try:
            with open(CONTRATISTAS_LOCAL_PATH, "w", encoding="utf-8") as f:
                json.dump(lista, f, indent=2, ensure_ascii=False)
        except Exception as e_loc:
            print(f"[FirebaseClient] Error guardando contratista local: {e_loc}")

        with cls._lock:
            cls._cache_contratistas = lista
            cls._ultimo_fetch_contratistas = time.time()

        return True


    # =========================================================================
    # MÓDULO USUARIOS: SINCRONIZACIÓN MASIVA A FIRESTORE
    # =========================================================================
    @classmethod
    def sincronizar_usuarios_a_firestore(cls, usuarios: list) -> bool:
        """Sube la lista de usuarios en lotes (batch) a la colección 'USUARIOS' en Firestore."""
        db = cls.get_db()
        if db is None:
            print("[FirebaseClient] Firestore no disponible para sincronizar usuarios.")
            return False

        from datetime import datetime
        total = len(usuarios)
        tam_lote = 400
        subidos = 0

        try:
            for i in range(0, total, tam_lote):
                lote = usuarios[i:i + tam_lote]
                batch = db.batch()

                for u in lote:
                    uid = str(u.get("ID", "")).strip()
                    if not uid:
                        continue

                    nom = str(u.get("Nombre", "")).strip()
                    ape = str(u.get("Apellidos", "")).strip()
                    nom_comp = f"{nom} {ape}".strip() or nom

                    doc_ref = db.collection("USUARIOS").document(uid)
                    doc_data = {
                        "id": int(uid) if uid.isdigit() else uid,
                        "nombre_completo": nom_comp,
                        "nombre": nom,
                        "apellidos": ape,
                        "email": str(u.get("Email", "")).strip() or str(u.get("Clave", "")).strip(),
                        "clave": str(u.get("Clave", "")).strip(),
                        "telefono": str(u.get("Telefono", "")).strip(),
                        "puesto": str(u.get("Posicion", "No especificado")).strip(),
                        "id_posicion": str(u.get("IdPosicion", "")).strip(),
                        "area_organizacion": str(u.get("AreaOrganizacion", "General")).strip(),
                        "id_area": str(u.get("IdAreaOrganizacion", "")).strip(),
                        "estatus": str(u.get("Estatus", "Activo")).strip(),
                        "vigencia_inicio": str(u.get("VigenciaInicio", "")).strip(),
                        "vigencia_fin": str(u.get("VigenciaFin", "")).strip(),
                        "inicio_operaciones": str(u.get("InicioOperaciones", "")).strip(),
                        "bloqueado": str(u.get("Bloqueado", "0")).strip() in ("1", "True", "true"),
                        "creado": str(u.get("Creado", "")).strip(),
                        "modificado": str(u.get("Modificado", "")).strip(),
                        "fecha_sincronizacion": datetime.now().isoformat()
                    }
                    batch.set(doc_ref, doc_data)

                batch.commit()
                subidos += len(lote)

            print(f"[FirebaseClient] {subidos} usuarios sincronizados en colección 'USUARIOS'.")
            return True
        except Exception as e:
            print(f"[FirebaseClient] Error sincronizando usuarios en Firestore: {e}")
            return False

    # =========================================================================
    # MÓDULO OBRAS: SINCRONIZACIÓN DE CATÁLOGO Y ÁRBOLES WBS A FIRESTORE
    # =========================================================================
    @classmethod
    def sincronizar_obras_a_firestore(cls, payload_obras: dict) -> bool:
        """Sincroniza el catálogo y los árboles jerárquicos en la colección 'OBRAS'."""
        db = cls.get_db()
        if db is None:
            print("[FirebaseClient] Firestore no disponible para sincronizar obras.")
            return False

        from datetime import datetime
        try:
            meta = payload_obras.get("metadata", {})
            obras = payload_obras.get("obras", [])
            total_obras = len(obras)

            # 1. Subir Catálogo Ligero en OBRAS/catalogo
            catalogo_ligero = []
            for o in obras:
                catalogo_ligero.append({
                    "id_obra": o.get("id_obra"),
                    "clave": o.get("clave"),
                    "nombre": o.get("nombre"),
                    "clave_presupuesto": o.get("clave_presupuesto"),
                    "tipo_wbs": o.get("tipo_wbs"),
                    "total_frentes": o.get("total_frentes", 0),
                    "total_partidas": o.get("total_partidas", 0),
                    "total_tarjetas": o.get("total_tarjetas", 0),
                    "importe_total": o.get("importe_total", 0.0)
                })

            db.collection("OBRAS").document("catalogo").set({
                "metadata": {
                    "total_obras": total_obras,
                    "total_frentes": meta.get("total_frentes", 0),
                    "total_partidas": meta.get("total_partidas", 0),
                    "total_tarjetas": meta.get("total_tarjetas", 0),
                    "fecha_extraccion": meta.get("fecha_extraccion"),
                    "fecha_sync_firebase": datetime.now().isoformat()
                },
                "lista": catalogo_ligero
            })

            # 2. Subir Árboles individuales en OBRAS/arboles/items/{CLAVE}
            col_items = db.collection("OBRAS").document("arboles").collection("items")
            LIMITE_DOC_BYTES = 850 * 1024

            for o in obras:
                clave = str(o.get("clave", "")).strip().upper()
                if not clave:
                    continue

                raw_size = len(json.dumps(o, ensure_ascii=False).encode('utf-8'))

                if raw_size < LIMITE_DOC_BYTES:
                    doc_data = {
                        "id_obra": o.get("id_obra"),
                        "clave": clave,
                        "nombre": o.get("nombre"),
                        "clave_presupuesto": o.get("clave_presupuesto"),
                        "tipo_wbs": o.get("tipo_wbs"),
                        "total_frentes": o.get("total_frentes", 0),
                        "total_partidas": o.get("total_partidas", 0),
                        "total_tarjetas": o.get("total_tarjetas", 0),
                        "importe_total": o.get("importe_total", 0.0),
                        "frentes": o.get("frentes", []),
                        "particionado": False,
                        "fecha_sync": datetime.now().isoformat()
                    }
                    col_items.document(clave).set(doc_data)
                else:
                    frentes = o.get("frentes", [])
                    mitad = len(frentes) // 2
                    col_items.document(clave).set({
                        "id_obra": o.get("id_obra"),
                        "clave": clave,
                        "nombre": o.get("nombre"),
                        "clave_presupuesto": o.get("clave_presupuesto"),
                        "tipo_wbs": o.get("tipo_wbs"),
                        "total_frentes": o.get("total_frentes", 0),
                        "total_partidas": o.get("total_partidas", 0),
                        "total_tarjetas": o.get("total_tarjetas", 0),
                        "importe_total": o.get("importe_total", 0.0),
                        "particionado": True,
                        "total_partes": 2,
                        "frentes": frentes[:mitad],
                        "fecha_sync": datetime.now().isoformat()
                    })
                    col_items.document(f"{clave}_PARTE2").set({
                        "clave": clave,
                        "parte": 2,
                        "frentes": frentes[mitad:]
                    })

            print(f"[FirebaseClient] {total_obras} obras sincronizadas exitosamente en 'OBRAS/arboles/items'.")
            return True
        except Exception as e:
            print(f"[FirebaseClient] Error sincronizando obras en Firestore: {e}")
            return False
