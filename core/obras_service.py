"""
Servicio de Alto Rendimiento para Gestión y Consulta de Obras, Frentes, Partidas y Tarjetas.
Optimizado con Tablas de Hash en memoria O(1) y sincronización con Firebase Firestore.
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OBRAS_JSON_PATH = os.path.join(BASE_DIR, "OBRAS", "obras.json")

class ObrasCoreService:
    _lock = threading.Lock()
    _cargado: bool = False
    _metadata: Dict[str, Any] = {}
    _obras_map: Dict[str, Any] = {}      # Hash Table O(1) por Clave e ID
    _catalogo_ligero: List[Dict[str, Any]] = []

    @classmethod
    def _cargar_en_memoria(cls):
        if cls._cargado:
            return

        with cls._lock:
            if cls._cargado:
                return

            # 1. Intentar cargar desde archivo local si existe
            if os.path.exists(OBRAS_JSON_PATH):
                try:
                    with open(OBRAS_JSON_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    cls._metadata = data.get("metadata", {})
                    obras = data.get("obras", [])

                    catalogo = []
                    mapa = {}

                    for o in obras:
                        clave = str(o.get("clave", "")).strip().upper()
                        id_obra = str(o.get("id_obra", "")).strip()

                        resumen = {
                            "id_obra": o.get("id_obra"),
                            "clave": o.get("clave", ""),
                            "nombre": o.get("nombre", ""),
                            "clave_presupuesto": o.get("clave_presupuesto", ""),
                            "tipo_wbs": o.get("tipo_wbs", ""),
                            "total_frentes": o.get("total_frentes", 0),
                            "total_partidas": o.get("total_partidas", 0),
                            "total_tarjetas": o.get("total_tarjetas", 0),
                            "importe_total": o.get("importe_total", 0.0),
                            "precio_total": o.get("precio_total", 0.0)
                        }
                        catalogo.append(resumen)

                        if clave:
                            mapa[clave] = o
                        if id_obra:
                            mapa[id_obra] = o

                    cls._catalogo_ligero = catalogo
                    cls._obras_map = mapa
                    cls._cargado = True
                    return
                except Exception as e:
                    print(f"[ObrasCoreService] Error al cargar obras.json local: {e}")

            # 1b. Intentar cargar desde catalogo_obras.json local si existe
            cat_local = os.path.join(BASE_DIR, "OBRAS", "catalogo_obras.json")
            if not cls._cargado and os.path.exists(cat_local):
                try:
                    with open(cat_local, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    catalogo = []
                    mapa = {}
                    for o in data:
                        clave = str(o.get("clave", "")).strip().upper()
                        id_obra = str(o.get("id", o.get("id_obra", ""))).strip()
                        resumen = {
                            "id_obra": id_obra,
                            "clave": clave,
                            "nombre": o.get("nombre", ""),
                            "clave_presupuesto": o.get("presupuesto_clave", ""),
                            "tipo_wbs": o.get("tipo_wbs", ""),
                            "total_frentes": o.get("total_frentes", 0),
                            "total_partidas": o.get("total_partidas", 0),
                            "total_tarjetas": o.get("total_tarjetas", 0),
                            "importe_total": o.get("importe_total", 0.0),
                            "precio_total": o.get("precio_total", 0.0)
                        }
                        catalogo.append(resumen)
                        if clave:
                            mapa[clave] = resumen
                        if id_obra:
                            mapa[id_obra] = resumen

                    cls._catalogo_ligero = catalogo
                    cls._obras_map = mapa
                    cls._metadata = {
                        "total_obras": len(catalogo),
                        "total_frentes": sum(o.get("total_frentes", 0) for o in catalogo),
                        "total_partidas": sum(o.get("total_partidas", 0) for o in catalogo),
                        "total_tarjetas": sum(o.get("total_tarjetas", 0) for o in catalogo),
                        "fecha_extraccion": None
                    }
                    cls._cargado = True
                    return
                except Exception as e_cat:
                    print(f"[ObrasCoreService] Error al cargar catalogo_obras.json: {e_cat}")

            # 2. Si no hay archivo local, cargar catálogo desde Firebase Firestore
            try:
                from core.firebase_client import FirebaseClient
                db = FirebaseClient.get_db()
                if db is not None:
                    cat_doc = db.collection("OBRAS").document("catalogo").get(timeout=3)
                    if cat_doc.exists:
                        d = cat_doc.to_dict()
                        cls._metadata = d.get("metadata", {})
                        cls._catalogo_ligero = d.get("lista", [])
                        cls._cargado = True
                        print(f"[ObrasCoreService] Catálogo de {len(cls._catalogo_ligero)} obras cargado desde Firebase Firestore.")
                        return
            except Exception as e_fb:
                print(f"[ObrasCoreService] Error cargando desde Firebase: {e_fb}")

            # 3. Fallback vacío
            cls._metadata = {
                "total_obras": 0,
                "total_frentes": 0,
                "total_partidas": 0,
                "total_tarjetas": 0,
                "fecha_extraccion": None
            }
            cls._catalogo_ligero = []
            cls._obras_map = {}
            cls._cargado = True

    @classmethod
    def recargar(cls):
        """Fuerza la recarga de obras a la memoria RAM."""
        with cls._lock:
            cls._cargado = False
        cls._cargar_en_memoria()
        return {"ok": True, "total_obras": len(cls._catalogo_ligero)}

    @classmethod
    def obtener_metricas(cls) -> Dict[str, Any]:
        cls._cargar_en_memoria()
        return dict(cls._metadata)

    @classmethod
    def obtener_catalogo(cls, busqueda: Optional[str] = None) -> List[Dict[str, Any]]:
        """Devuelve el catálogo de obras con filtrado rápido."""
        cls._cargar_en_memoria()
        if not busqueda:
            return cls._catalogo_ligero

        q = busqueda.strip().lower()
        return [
            o for o in cls._catalogo_ligero
            if q in str(o.get("clave", "")).lower() or q in str(o.get("nombre", "")).lower() or q in str(o.get("id_obra", "")).lower()
        ]

    @classmethod
    def obtener_arbol(cls, clave_o_id: str) -> Optional[Dict[str, Any]]:
        """
        Devuelve el árbol completo (Frentes -> Partidas -> Tarjetas) en O(1)
        usando la tabla de hash en memoria RAM o consultando Firebase Firestore bajo demanda.
        """
        cls._cargar_en_memoria()
        clave_limpia = str(clave_o_id).strip().upper()

        if clave_limpia in cls._obras_map and "frentes" in cls._obras_map[clave_limpia]:
            return cls._obras_map[clave_limpia]

        # 1. Buscar árbol en archivo local OBRAS/{clave}.json
        ruta_arbol_local = os.path.join(BASE_DIR, "OBRAS", f"{clave_limpia}.json")
        if os.path.exists(ruta_arbol_local):
            try:
                with open(ruta_arbol_local, "r", encoding="utf-8") as f:
                    arbol = json.load(f)
                with cls._lock:
                    cls._obras_map[clave_limpia] = arbol
                return arbol
            except Exception as e_arbol:
                print(f"[ObrasCoreService] Error leyendo {ruta_arbol_local}: {e_arbol}")

        # 2. Si no está en disco local, consultar Firebase Firestore
        try:
            from core.firebase_client import FirebaseClient
            db = FirebaseClient.get_db()
            if db is not None:
                doc = db.collection("OBRAS").document("arboles").collection("items").document(clave_limpia).get(timeout=3)
                if doc.exists:
                    arbol = doc.to_dict()
                    # Reensamblar obras particionadas (>850 KB como AUS)
                    if arbol.get("particionado"):
                        p2_doc = db.collection("OBRAS").document("arboles").collection("items").document(f"{clave_limpia}_PARTE2").get()
                        if p2_doc.exists:
                            f2 = p2_doc.to_dict().get("frentes", [])
                            arbol["frentes"] = arbol.get("frentes", []) + f2

                    with cls._lock:
                        cls._obras_map[clave_limpia] = arbol
                    return arbol
        except Exception as e_fb:
            print(f"[ObrasCoreService] Error consultando árbol en Firestore: {e_fb}")

        return None
