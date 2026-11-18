"""
Conector Autónomo de APIs REST y OpenAPI / Swagger para KHIARA.
Permite a KHIARA conectarse al backend de FastAPI (Dashboard EK10),
ingerir automáticamente el archivo 'openapi.json', descubrir todos los endpoints
(insumos, escalatorias, posiciones, obras) y consumirlos en vivo.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from khiara.core.config import MEMORIA_DIR


class ConectorAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.archivo_cache = MEMORIA_DIR / "api_spec.json"
        self.spec: Dict[str, Any] = {}
        self.endpoints_indexados: Dict[str, Dict[str, Any]] = {}
        self._cargar_cache()

    def _cargar_cache(self):
        if self.archivo_cache.exists():
            try:
                with open(self.archivo_cache, "r", encoding="utf-8") as f:
                    self.spec = json.load(f)
                    self._construir_indice_endpoints()
            except Exception:
                self.spec = {}

    def _guardar_cache(self):
        try:
            with open(self.archivo_cache, "w", encoding="utf-8") as f:
                json.dump(self.spec, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def cargar_especificacion(self, url_o_ruta: str) -> Dict[str, Any]:
        """
        Carga el esquema OpenAPI/Swagger desde una URL viva o un archivo local .json.
        """
        origen = url_o_ruta.strip()
        data = None

        if origen.startswith("http://") or origen.startswith("https://"):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(origen)
                    resp.raise_for_status()
                    data = resp.json()
                    # Actualizar base_url a partir del origen
                    partes = origen.split("/openapi.json")[0].split("/docs")[0]
                    self.base_url = partes.rstrip("/")
            except Exception as e:
                return {"ok": False, "error": f"Error conectando a la API en '{origen}': {str(e)}"}
        else:
            p = Path(origen).resolve()
            if not p.exists():
                return {"ok": False, "error": f"El archivo OpenAPI '{origen}' no existe."}
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                return {"ok": False, "error": f"Error leyendo archivo OpenAPI: {str(e)}"}

        if not isinstance(data, dict) or "paths" not in data:
            return {"ok": False, "error": "El documento proporcionado no es un esquema OpenAPI válido (falta clave 'paths')."}

        self.spec = data
        self._guardar_cache()
        total = self._construir_indice_endpoints()

        info = self.spec.get("info", {})
        return {
            "ok": True,
            "titulo": info.get("title", "API FastAPI"),
            "version": info.get("version", "1.0.0"),
            "total_endpoints": total,
            "base_url": self.base_url
        }

    def _construir_indice_endpoints(self) -> int:
        self.endpoints_indexados = {}
        paths = self.spec.get("paths", {})
        for ruta, metodos in paths.items():
            for met, det in metodos.items():
                if met.lower() in {"get", "post", "put", "delete", "patch"}:
                    clave = f"{met.upper()} {ruta}"
                    self.endpoints_indexados[clave] = {
                        "metodo": met.upper(),
                        "ruta": ruta,
                        "resumen": det.get("summary", ""),
                        "descripcion": det.get("description", ""),
                        "tags": det.get("tags", []),
                        "parametros": det.get("parameters", []),
                        "tiene_body": bool(det.get("requestBody"))
                    }
        return len(self.endpoints_indexados)

    def buscar_endpoints(self, termino: str = "") -> List[Dict[str, Any]]:
        """Busca endpoints por ruta, tag o descripción."""
        if not self.endpoints_indexados:
            return []

        if not termino.strip():
            return list(self.endpoints_indexados.values())[:25]

        termino_l = termino.lower().strip()
        coincidencias = []
        for clave, ep in self.endpoints_indexados.items():
            texto = f"{clave} {ep['resumen']} {ep['descripcion']} {' '.join(ep['tags'])}".lower()
            if termino_l in texto:
                coincidencias.append(ep)
        return coincidencias

    def ejecutar_llamada(
        self,
        metodo: str,
        ruta: str,
        parametros: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta una petición HTTP en vivo contra el backend de la API.
        """
        url_final = f"{self.base_url}/{ruta.lstrip('/')}"
        metodo_u = metodo.upper()

        try:
            with httpx.Client(timeout=15.0) as client:
                if metodo_u == "GET":
                    resp = client.get(url_final, params=parametros)
                elif metodo_u == "POST":
                    resp = client.post(url_final, params=parametros, json=body)
                elif metodo_u == "PUT":
                    resp = client.put(url_final, params=parametros, json=body)
                elif metodo_u == "DELETE":
                    resp = client.delete(url_final, params=parametros)
                else:
                    return {"ok": False, "error": f"Método HTTP no soportado: {metodo}"}

                try:
                    datos = resp.json()
                except Exception:
                    datos = resp.text

                return {
                    "ok": resp.is_success,
                    "status_code": resp.status_code,
                    "url": str(resp.url),
                    "datos": datos
                }
        except httpx.ConnectError:
            return {
                "ok": False,
                "error": f"No se pudo conectar a '{url_final}'. Asegúrate de que el backend de FastAPI esté corriendo en ese puerto."
            }
        except Exception as e:
            return {"ok": False, "error": f"Error ejecutando petición API: {str(e)}"}
