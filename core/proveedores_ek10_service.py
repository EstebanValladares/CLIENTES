"""
Core Domain: Catálogo Local y Sincronización de Proveedores EK10 (EK-PROV-...)
Fuente: Enkontrol 10 Cloud (https://suite.ekloud.net:1445/Aryve/#/scp/proveedores)
Guarda copia local en data/proveedores_ek10.json para consulta O(1) offline/instantánea
y permite sincronizar nuevos proveedores en cualquier momento.
"""

import difflib
import json
import os
import re
import threading
import time
import unicodedata
from typing import Any, Dict, List, Optional

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_PATH = os.path.join(BASE_DIR, "data", "proveedores_ek10.json")
_lock = threading.Lock()

_STOPWORDS_FISCALES = {
    "SA", "CV", "S", "DE", "RL", "SC", "SAPI", "SAB", "AC", "SPR", "SOFOM", "ENR", "EN", "R", "L", "A", "C"
}


def _normalizar_nombre(texto: Any, quitar_fiscales: bool = False) -> str:
    if texto is None:
        return ""
    s = str(texto).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t]
    if quitar_fiscales:
        sin_fiscales = [t for t in tokens if t not in _STOPWORDS_FISCALES]
        if sin_fiscales:
            tokens = sin_fiscales
    return " ".join(tokens)


class ProveedoresEk10Service:
    _cache_memoria: Optional[Dict[str, Any]] = None
    _indice_exacto: Dict[str, Dict[str, Any]] = {}
    _indice_base: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _reconstruir_indices(cls, data: Dict[str, Any]) -> None:
        exacto: Dict[str, Dict[str, Any]] = {}
        base: Dict[str, Dict[str, Any]] = {}
        for p in data.get("proveedores", []):
            nombre = p.get("nombre", "")
            norm = _normalizar_nombre(nombre, quitar_fiscales=False)
            norm_base = _normalizar_nombre(nombre, quitar_fiscales=True)
            if norm and norm not in exacto:
                exacto[norm] = p
            if norm_base and norm_base not in base:
                base[norm_base] = p
        cls._indice_exacto = exacto
        cls._indice_base = base

    @classmethod
    def cargar_catalogo(cls) -> Dict[str, Any]:
        with _lock:
            if cls._cache_memoria is not None:
                return cls._cache_memoria

            if os.path.exists(CATALOG_PATH):
                try:
                    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and isinstance(data.get("proveedores"), list):
                            cls._cache_memoria = data
                            cls._reconstruir_indices(data)
                            return data
                except Exception:
                    pass

            vacio = {"actualizado": "", "total": 0, "proveedores": []}
            cls._cache_memoria = vacio
            cls._reconstruir_indices(vacio)
            return vacio

    @classmethod
    def guardar_catalogo(cls, proveedores: List[Dict[str, Any]]) -> Dict[str, Any]:
        data = {
            "actualizado": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(proveedores),
            "proveedores": proveedores,
        }
        with _lock:
            os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
            tmp = CATALOG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, CATALOG_PATH)
            cls._cache_memoria = data
            cls._reconstruir_indices(data)
        return data

    @classmethod
    def estado(cls) -> Dict[str, Any]:
        data = cls.cargar_catalogo()
        return {
            "actualizado": data.get("actualizado", ""),
            "total": int(data.get("total", len(data.get("proveedores", [])))),
        }

    @classmethod
    def _crear_sesion_enkontrol(cls) -> Optional[requests.Session]:
        load_dotenv(os.path.join(BASE_DIR, ".env"))
        user = os.getenv("EK10_USER", "").strip()
        pwd = os.getenv("EK10_PASS", "").strip()
        if not user or not pwd:
            return None

        session = requests.Session()
        session.verify = False
        login_url = "https://suite.ekloud.net:1445/Aryve/kontrol/login/validate"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://suite.ekloud.net:1445/Aryve/"}
        try:
            r = session.post(
                login_url,
                data={"username": user, "password": pwd, "returnUrl": "", "msj": ""},
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200 and ".AspNet.ApplicationCookie" in session.cookies:
                return session
        except Exception:
            pass
        return None

    @classmethod
    def sincronizar_desde_enkontrol(cls) -> Dict[str, Any]:
        session = cls._crear_sesion_enkontrol()
        if not session:
            return {
                "ok": False,
                "mensaje": "No se pudo iniciar sesión en Enkontrol 10 Cloud. Verifica EK10_USER y EK10_PASS en .env.",
            }

        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://suite.ekloud.net:1445/Aryve/"}
        candidatos = [
            ("POST", "https://suite.ekloud.net:1445/Aryve/base/scp/Proveedores/GetBP/GetAll/", {"parametros": {}}),
            ("POST", "https://suite.ekloud.net:1445/Aryve/base/scp/proveedores/GetBP/GetAll/", {"parametros": {}}),
            ("GET", "https://suite.ekloud.net:1445/Aryve/base/scp/Proveedores/Get/GetAll/", None),
            ("POST", "https://suite.ekloud.net:1445/Aryve/base/scp/Proveedores/GetBP/GetProveedores/", {"parametros": {}}),
        ]

        lista_raw = None
        ultimo_status = None
        for metodo, url, payload in candidatos:
            try:
                if metodo == "POST":
                    res = session.post(url, json=payload, headers=headers, timeout=35)
                else:
                    res = session.get(url, headers=headers, timeout=35)
                ultimo_status = res.status_code
                if res.status_code == 200:
                    parsed = res.json()
                    if isinstance(parsed, list):
                        lista_raw = parsed
                        break
                    if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
                        lista_raw = parsed["data"]
                        break
                    if isinstance(parsed, dict) and isinstance(parsed.get("Result"), list):
                        lista_raw = parsed["Result"]
                        break
            except Exception:
                continue

        if lista_raw is None:
            return {
                "ok": False,
                "mensaje": f"No se pudo descargar el catálogo de proveedores desde EK10 Cloud (HTTP {ultimo_status}).",
            }

        proveedores: List[Dict[str, Any]] = []
        vistos = set()
        for item in lista_raw:
            if not isinstance(item, dict):
                continue
            clave = str(item.get("Clave") or item.get("clave") or "").strip()
            nombre = str(
                item.get("NombreCompleto")
                or item.get("Nombre")
                or item.get("RazonSocial")
                or item.get("nombre")
                or ""
            ).strip()
            if not clave and not nombre:
                continue
            key_dedup = f"{clave}|{nombre}"
            if key_dedup in vistos:
                continue
            vistos.add(key_dedup)
            proveedores.append({
                "id": item.get("ID") or item.get("Id") or item.get("id") or 0,
                "clave": clave,
                "nombre": nombre,
                "nombre_corto": str(item.get("NombreCorto") or item.get("nombre_corto") or "").strip(),
                "rfc": str(item.get("RFC") or item.get("rfc") or "").strip(),
            })

        guardado = cls.guardar_catalogo(proveedores)
        return {
            "ok": True,
            "actualizado": guardado["actualizado"],
            "total": guardado["total"],
        }

    @classmethod
    def buscar(cls, consulta: str, limit: int = 12) -> Dict[str, Any]:
        data = cls.cargar_catalogo()
        proveedores = data.get("proveedores", [])
        if not consulta or not proveedores:
            return {"mejor": None, "sugerencias": []}

        q_norm = _normalizar_nombre(consulta, quitar_fiscales=False)
        q_base = _normalizar_nombre(consulta, quitar_fiscales=True)
        q_raw = str(consulta).strip().upper()

        # 1. Coincidencia exacta
        if q_norm in cls._indice_exacto:
            p = cls._indice_exacto[q_norm]
            return {"mejor": {**p, "score": 1.0}, "sugerencias": [{**p, "score": 1.0}]}

        # 2. Coincidencia exacta sin razón social fiscal (SA DE CV, etc.)
        if q_base and q_base in cls._indice_base:
            p = cls._indice_base[q_base]
            return {"mejor": {**p, "score": 0.96}, "sugerencias": [{**p, "score": 0.96}]}

        # 3. Búsqueda por clave, RFC, subcadena y similitud difusa
        resultados: List[Dict[str, Any]] = []
        q_tokens = set(q_base.split())

        for p in proveedores:
            clave = (p.get("clave") or "").upper()
            rfc = (p.get("rfc") or "").upper()
            nombre = p.get("nombre") or ""
            p_base = _normalizar_nombre(nombre, quitar_fiscales=True)

            score = 0.0
            if q_raw and (q_raw in clave or q_raw in rfc):
                score = 0.95
            elif q_base and p_base:
                if q_base in p_base or p_base in q_base:
                    score = 0.88
                else:
                    p_tokens = set(p_base.split())
                    if q_tokens and p_tokens:
                        inter = len(q_tokens & p_tokens) / max(len(q_tokens), len(p_tokens))
                    else:
                        inter = 0.0
                    seq = difflib.SequenceMatcher(None, q_base, p_base).ratio()
                    score = max(seq, (seq + inter) / 2.0)

            if score >= 0.45:
                resultados.append({**p, "score": round(score, 3)})

        resultados.sort(key=lambda x: x["score"], reverse=True)
        top = resultados[:limit]
        mejor = top[0] if top and top[0]["score"] >= 0.78 else None
        return {"mejor": mejor, "sugerencias": top}
