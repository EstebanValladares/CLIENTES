"""
Servicio de Alto Rendimiento para Gestión y Consulta de Obras, Frentes, Partidas y Tarjetas.
Optimizado con Tablas de Hash en memoria O(1) leyendo el catálogo unificado tipo lista (obras.json).
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
    _catalogo_ligero: List[Dict[str, Any]] = []
    _obras_map_id: Dict[str, Any] = {}
    _obras_map_clave: Dict[str, Any] = {}

    @classmethod
    def _cargar_en_memoria(cls):
        if cls._cargado:
            return

        with cls._lock:
            if cls._cargado:
                return

            if os.path.exists(OBRAS_JSON_PATH):
                try:
                    with open(OBRAS_JSON_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Si es lista directa [ {...}, {...} ] estilo Usuarios.json
                    if isinstance(data, list):
                        lista_obras = data
                    else:
                        lista_obras = data.get("catalogo") or data.get("obras", [])

                    catalogo = []
                    mapa_id = {}
                    mapa_clave = {}

                    total_frentes = 0
                    total_partidas = 0
                    total_tarjetas = 0

                    for o in lista_obras:
                        clave = str(o.get("clave", "")).strip().upper()
                        id_obra = str(o.get("id_obra", "")).strip()

                        tf = o.get("total_frentes", len(o.get("frentes", [])))
                        tp = o.get("total_partidas", 0)
                        tt = o.get("total_tarjetas", 0)

                        total_frentes += tf
                        total_partidas += tp
                        total_tarjetas += tt

                        resumen = {
                            "id_obra": o.get("id_obra"),
                            "clave": o.get("clave", ""),
                            "nombre": o.get("nombre", ""),
                            "clave_presupuesto": o.get("clave_presupuesto", ""),
                            "tipo_wbs": o.get("tipo_wbs", ""),
                            "total_frentes": tf,
                            "total_partidas": tp,
                            "total_tarjetas": tt,
                            "importe_total": o.get("importe_total", 0.0),
                            "precio_total": o.get("precio_total", 0.0)
                        }
                        catalogo.append(resumen)

                        if id_obra:
                            mapa_id[id_obra] = o
                        if clave and clave != "NONE":
                            mapa_clave[clave] = o

                    cls._metadata = {
                        "total_obras": len(catalogo),
                        "total_frentes": total_frentes,
                        "total_partidas": total_partidas,
                        "total_tarjetas": total_tarjetas
                    }
                    cls._catalogo_ligero = catalogo
                    cls._obras_map_id = mapa_id
                    cls._obras_map_clave = mapa_clave
                    cls._cargado = True
                    return
                except Exception as e:
                    print(f"[ObrasCoreService] Error al cargar obras.json: {e}")

            # 1b. Intentar cargar desde catalogo_obras.json si no se cargó obras.json
            cat_local = os.path.join(BASE_DIR, "OBRAS", "catalogo_obras.json")
            if not cls._cargado and os.path.exists(cat_local):
                try:
                    with open(cat_local, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cls._catalogo_ligero = data
                    cls._obras_map_clave = {str(o.get("clave", "")).strip().upper(): o for o in data if o.get("clave")}
                    cls._obras_map_id = {str(o.get("id_obra", "")).strip(): o for o in data if o.get("id_obra")}
                    cls._metadata = {
                        "total_obras": len(data),
                        "total_frentes": sum(o.get("total_frentes", 0) for o in data),
                        "total_partidas": sum(o.get("total_partidas", 0) for o in data),
                        "total_tarjetas": sum(o.get("total_tarjetas", 0) for o in data)
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
            cls._metadata = {
                "total_obras": 0,
                "total_frentes": 0,
                "total_partidas": 0,
                "total_tarjetas": 0
            }
            cls._catalogo_ligero = []
            cls._obras_map_id = {}
            cls._obras_map_clave = {}
            cls._cargado = True

    @classmethod
    def recargar(cls):
        """Fuerza la recarga del archivo obras.json en la memoria RAM."""
        with cls._lock:
            cls._cargado = False
        cls._cargar_en_memoria()
        return {"ok": True, "total_obras": len(cls._catalogo_ligero)}

    @classmethod
    def obtener_metricas(cls) -> Dict[str, Any]:
        """Devuelve las métricas consolidadas del catálogo de obras."""
        cls._cargar_en_memoria()
        return {
            **cls._metadata,
            "ultima_sincronizacion": "Local Autónoma"
        }

    @classmethod
    def obtener_catalogo(cls, busqueda: str = "") -> List[Dict[str, Any]]:
        """Devuelve el catálogo de obras con filtrado rápido O(N)."""
        cls._cargar_en_memoria()
        if not busqueda or not isinstance(busqueda, str):
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
        inmediato desde las tablas de hash en memoria RAM.
        """
        cls._cargar_en_memoria()
        ref = str(clave_o_id).strip().upper()

        # 1. Búsqueda directa por Clave en RAM
        if ref in cls._obras_map_clave:
            return cls._obras_map_clave[ref]

        # 2. Búsqueda directa por ID en RAM
        if ref in cls._obras_map_id:
            return cls._obras_map_id[ref]

        # 3. Fallback a Firebase Firestore bajo demanda
        try:
            from core.firebase_client import FirebaseClient
            db = FirebaseClient.get_db()
            if db is not None:
                doc = db.collection("OBRAS").document(ref).get(timeout=3)
                if doc.exists:
                    arbol = doc.to_dict()
                    with cls._lock:
                        cls._obras_map_clave[ref] = arbol
                    return arbol
        except Exception as e_fb:
            print(f"[ObrasCoreService] Error consultando árbol en Firestore: {e_fb}")

        return None
