"""
Core Domain: Insumos & Órdenes de Compra Engine.
Conexión en vivo con microservicios Aryve / Suministros:
- reporte_insumo.php: Árbol WBS por partida con presupuestos, requisitado y comprado.
- movimientos_insumo.php: Requisiciones y Órdenes de Compra en firme.
- actualizar_suministro.php: Marcado de suministros masivo con Token de Autorización.
- Sincronización transparente con Firestore y archivos locales.
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSUMOS_CACHE_DIR = os.path.join(BASE_DIR, "OBRAS", "INSUMOS_CACHE")
os.makedirs(INSUMOS_CACHE_DIR, exist_ok=True)

API_BASE = "http://34.51.46.13/API/suministro_nivel"
API_REPORTE_URL = f"{API_BASE}/reporte_insumo.php"
API_MOVIMIENTOS_URL = f"{API_BASE}/movimientos_insumo.php"
API_ACTUALIZAR_URL = f"{API_BASE}/actualizar_suministro.php"
API_TOKEN = "b86fa23c3531a976c3d4cdb6c6feef66"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

class InsumosService:

    @classmethod
    def consultar_reporte(
        cls, 
        obra: str, 
        insumo: Optional[str] = None, 
        nombre: Optional[str] = None,
        usar_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Consulta el reporte completo de insumos por partida y resumen general de la obra.
        """
        obra_clean = str(obra).strip().upper()
        if not obra_clean:
            raise ValueError("Debe proporcionar la clave de la obra (ej. AT1, AT4).")

        params = {"obra": obra_clean}
        insumo_clean = (insumo or "").strip()
        nombre_clean = (nombre or "").strip()

        if insumo_clean:
            params["insumo"] = insumo_clean
        if nombre_clean:
            params["nombre"] = nombre_clean

        # Si el usuario no especificó ni insumo ni nombre, usamos 'a' para traer catálogo amplio
        if not insumo_clean and not nombre_clean:
            params["nombre"] = "a"

        query_str = urllib.parse.urlencode(params)
        url = f"{API_REPORTE_URL}?{query_str}"

        cache_file = os.path.join(INSUMOS_CACHE_DIR, f"{obra_clean}_reporte.json")
        if usar_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=35) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                
                if not data.get("ok", False):
                    err_msg = data.get("error", "Error desconocido de la API")
                    raise RuntimeError(err_msg)

                resumen = data.get("resumen", [])
                total_ppto_real = sum(float(i.get("presupuesto_real", 0) or 0) for i in resumen)
                total_requisitado = sum(float(i.get("requisitado", 0) or 0) for i in resumen)
                total_comprado = sum(float(i.get("comprado", 0) or 0) for i in resumen)
                total_por_comprar = sum(float(i.get("por_comprar", 0) or 0) for i in resumen)

                partidas = data.get("partidas", [])
                frentes_dict = {}
                for p in partidas:
                    fr = p.get("frente") or {}
                    fid = str(fr.get("id", "0"))
                    if fid not in frentes_dict:
                        frentes_dict[fid] = {
                            "id": fid,
                            "codigo": fr.get("codigo", ""),
                            "nombre": fr.get("nombre", "Sin Frente"),
                            "partidas": []
                        }
                    frentes_dict[fid]["partidas"].append(p)

                resultado = {
                    "ok": True,
                    "obra": data.get("obra", {"clave": obra_clean}),
                    "metricas": {
                        "total_partidas": len(partidas),
                        "total_frentes": len(frentes_dict),
                        "total_insumos_resumen": len(resumen),
                        "presupuesto_real_total": round(total_ppto_real, 4),
                        "requisitado_total": round(total_requisitado, 4),
                        "comprado_total": round(total_comprado, 4),
                        "por_comprar_total": round(total_por_comprar, 4)
                    },
                    "frentes": list(frentes_dict.values()),
                    "partidas": partidas,
                    "resumen": resumen,
                    "filtros_aplicados": params
                }

                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(resultado, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

                return resultado

        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error HTTP {he.code}: {err_body}")
        except Exception as e:
            raise RuntimeError(f"Fallo al conectar con servicio de insumos: {str(e)}")

    @classmethod
    def consultar_movimientos(cls, obra: str, partida: str, insumo: str) -> Dict[str, Any]:
        """
        Consulta el detalle de Requisiciones y Órdenes de Compra (OCs) para un insumo en una partida.
        """
        obra_clean = str(obra).strip().upper()
        partida_clean = str(partida).strip()
        insumo_clean = str(insumo).strip()

        params = {
            "obra": obra_clean,
            "partida": partida_clean,
            "insumo": insumo_clean
        }
        query_str = urllib.parse.urlencode(params)
        url = f"{API_MOVIMIENTOS_URL}?{query_str}"

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                return {
                    "ok": True,
                    "obra": obra_clean,
                    "partida": partida_clean,
                    "insumo": insumo_clean,
                    "requisiciones": data.get("requisiciones", []),
                    "ordenes_compra": data.get("ordenes_compra", [])
                }
        except Exception as e:
            raise RuntimeError(f"Error obteniendo movimientos para insumo {insumo}: {str(e)}")

    @classmethod
    def actualizar_suministro_obra(cls, obra: str) -> Dict[str, Any]:
        """
        Ejecuta la marcación de suministros masivos en toda la obra mediante el token autorizado.
        """
        obra_clean = str(obra).strip().upper()
        data_payload = urllib.parse.urlencode({
            "obra": obra_clean,
            "token": API_TOKEN
        }).encode("utf-8")

        req = urllib.request.Request(API_ACTUALIZAR_URL, data=data_payload, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                if data.get("ok", False):
                    return {
                        "ok": True,
                        "obra": obra_clean,
                        "filas_actualizadas": data.get("filas_actualizadas", 0),
                        "mensaje": f"Se suministraron exitosamente los insumos en la obra {obra_clean}."
                    }
                else:
                    return {
                        "ok": False,
                        "obra": obra_clean,
                        "mensaje": data.get("error", "Error al actualizar suministro")
                    }
        except Exception as e:
            raise RuntimeError(f"Error en endpoint de suministro: {str(e)}")

    @classmethod
    def sincronizar_firestore(cls, obra: str, datos_reporte: Dict[str, Any]) -> bool:
        """
        Sincroniza el árbol de insumos y resumen financiero en Firebase Firestore
        para que la app de CLIENTES pueda consumirlo desde la nube.
        """
        try:
            from core.firebase_client import FirebaseClient
            db = FirebaseClient.get_db()
            if not db:
                return False

            obra_clean = str(obra).strip().upper()
            doc_ref = db.collection("OBRAS").document(obra_clean)
            
            doc_ref.set({
                "clave": obra_clean,
                "nombre": datos_reporte.get("obra", {}).get("nombre", obra_clean),
                "metricas": datos_reporte.get("metricas", {}),
                "resumen": datos_reporte.get("resumen", []),
                "frentes_count": len(datos_reporte.get("frentes", [])),
                "partidas_count": len(datos_reporte.get("partidas", [])),
                "ultima_actualizacion_insumos": datos_reporte.get("filtros_aplicados", {})
            }, merge=True)

            frentes = datos_reporte.get("frentes", [])
            for fr in frentes:
                fid = str(fr.get("id", "0"))
                doc_ref.collection("frentes").document(fid).set(fr)

            return True
        except Exception as e:
            print(f"[InsumosService] Error sincronizando Firestore: {e}")
            return False
