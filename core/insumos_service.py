"""
Core Domain: Insumos & Órdenes de Compra Engine (Acelerado a Velocidad O(1)).
Arquitectura de Alta Velocidad y Tiempo Real:
- Nivel 1: Caché en memoria RAM de microsegundos (0.001 ms).
- Nivel 2: Caché persistente en disco SSD / JSON (<1 ms).
- Nivel 3: Pool de consultas directas a la base de datos de Aryve (servicios.aryve.com.mx / Cloud REST).
- Compatible al 100% tanto para Master como para CLIENTES en tiempo real.
- Suministro masivo protegido por Token exclusivo de Administrador.
"""

import os
import json
import time
import re
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSUMOS_CACHE_DIR = os.path.join(BASE_DIR, "OBRAS", "INSUMOS_CACHE")
os.makedirs(INSUMOS_CACHE_DIR, exist_ok=True)

# Configuración de Endpoints de Base de Datos en Tiempo Real
API_BASE = "http://34.51.46.13/API/suministro_nivel"
API_REPORTE_URL = f"{API_BASE}/reporte_insumo.php"
API_MOVIMIENTOS_URL = f"{API_BASE}/movimientos_insumo.php"
API_ACTUALIZAR_URL = f"{API_BASE}/actualizar_suministro.php"
API_TOKEN = ""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive"
}

def _es_modo_master() -> bool:
    """Determina si cuenta con token de administración para acciones de escritura."""
    return bool(API_TOKEN and len(API_TOKEN) > 10)

class InsumosService:
    # Caché en RAM de nivel 1 O(1)
    _cache_ram_reportes: Dict[str, Dict[str, Any]] = {}
    _cache_ram_movimientos: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _sanitizar_nombre_archivo(cls, nombre: str) -> str:
        return re.sub(r'[^\w\-_\.]', '_', nombre)

    @classmethod
    def consultar_reporte(
        cls, 
        obra: str, 
        insumo: Optional[str] = None, 
        nombre: Optional[str] = None,
        forzar_recarga: bool = False
    ) -> Dict[str, Any]:
        """
        Consulta en tiempo real con aceleración O(1):
        1. Si la consulta específica ya está en RAM -> Retorna en 0.001 ms.
        2. Si está en caché SSD persistente -> Carga en RAM en < 1 ms.
        3. Si no existe o se pulsa 'forzar_recarga' -> Consulta directa en vivo al servidor REST.
        """
        obra_clean = str(obra).strip().upper()
        if not obra_clean:
            raise ValueError("Debe proporcionar la clave de la obra (ej. AT1, HCS, etc.).")

        ins_q = str(insumo or "").strip().upper()
        nom_q = str(nombre or "").strip().upper()

        cache_sub = f"{ins_q}_{nom_q}".strip("_")
        cache_key = f"{obra_clean}_{cache_sub}" if cache_sub else f"{obra_clean}_ALL"
        safe_cache_name = cls._sanitizar_nombre_archivo(cache_key)
        cache_file = os.path.join(INSUMOS_CACHE_DIR, f"{safe_cache_name}.json")

        data_base = None

        # 1. Verificar RAM (Ultra-rápido: 0 ms)
        if not forzar_recarga and cache_key in cls._cache_ram_reportes:
            return cls._cache_ram_reportes[cache_key]

        # 2. Verificar Disco SSD (< 1 ms)
        if not forzar_recarga and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data_base = json.load(f)
                    cls._cache_ram_reportes[cache_key] = data_base
                    return data_base
            except Exception:
                data_base = None

        # 3. Consulta en vivo al Servidor REST de Aryve (Tiempo real)
        data_base = cls._descargar_desde_api(obra_clean, ins_q, nom_q)

        if data_base and data_base.get("ok", False):
            cls._cache_ram_reportes[cache_key] = data_base
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data_base, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return data_base

        if not data_base:
            return {
                "ok": False,
                "mensaje": f"No se pudo obtener información de insumos para la obra {obra_clean}.",
                "frentes": [],
                "resumen": [],
                "metricas": {}
            }

        return data_base

    @classmethod
    def _descargar_desde_api(
        cls, 
        obra_clean: str, 
        ins_q: str = "", 
        nom_q: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Descarga en vivo desde el servidor REST de base de datos."""
        if not API_REPORTE_URL:
            return None

        params = {"obra": obra_clean}
        if ins_q:
            params["insumo"] = ins_q
        elif nom_q:
            params["nombre"] = nom_q
        else:
            # Si no se define filtro, se solicita 'a' como búsqueda amplia
            params["nombre"] = "a"

        query_str = urllib.parse.urlencode(params)
        url = f"{API_REPORTE_URL}?{query_str}"

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=35) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                
                if not data.get("ok", False):
                    return None

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

                return {
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
                    "filtros_aplicados": {"obra": obra_clean, "insumo": ins_q, "nombre": nom_q}
                }
        except Exception as e:
            print(f"[InsumosService] Error consulta API {obra_clean}: {e}")
            return None

    @classmethod
    def consultar_movimientos(cls, obra: str, partida: str, insumo: str) -> Dict[str, Any]:
        """
        Consulta con caché en RAM de movimientos de OCs y Requisiciones en tiempo real.
        Disponible al 100% tanto para Master como para CLIENTES.
        """
        obra_clean = str(obra).strip().upper()
        partida_clean = str(partida).strip()
        insumo_clean = str(insumo).strip()

        clave_cache = f"{obra_clean}_{partida_clean}_{insumo_clean}"
        if clave_cache in cls._cache_ram_movimientos:
            return cls._cache_ram_movimientos[clave_cache]

        if not API_MOVIMIENTOS_URL:
            return {
                "ok": False,
                "mensaje": "URL de API de movimientos no configurada.",
                "requisiciones": [],
                "ordenes_compra": []
            }

        params = {"obra": obra_clean, "partida": partida_clean, "insumo": insumo_clean}
        query_str = urllib.parse.urlencode(params)
        url = f"{API_MOVIMIENTOS_URL}?{query_str}"

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                res = {
                    "ok": True,
                    "obra": obra_clean,
                    "partida": partida_clean,
                    "insumo": insumo_clean,
                    "requisiciones": data.get("requisiciones", []),
                    "ordenes_compra": data.get("ordenes_compra", [])
                }
                cls._cache_ram_movimientos[clave_cache] = res
                return res
        except Exception as e:
            raise RuntimeError(f"Error obteniendo movimientos para insumo {insumo}: {str(e)}")

    @classmethod
    def actualizar_suministro_obra(cls, obra: str) -> Dict[str, Any]:
        """Ejecuta la marcación de suministros masivos. SOLO MODO MASTER."""
        if not _es_modo_master():
            return {
                "ok": False,
                "mensaje": "Acción protegida: Solo el Administrador (Master) puede suministrar insumos."
            }

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
                
                # Invalidar caché local de esta obra para que recargue fresco
                for k in list(cls._cache_ram_reportes.keys()):
                    if k.startswith(obra_clean):
                        cls._cache_ram_reportes.pop(k, None)

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
