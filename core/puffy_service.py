"""
Core Domain: Integración con Puffy Web (http://34.51.46.13/puffy)
Permite preparar requisiciones en EK10 enviando los insumos checkeados (obra, insumo,
cantidad/falta, partida) a Puffy, y confirmar la acción pendiente para fijar el folio
definitivo de Requisición EK10 de forma persistente.
"""

import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FOLIOS_FIJOS_PATH = os.path.join(BASE_DIR, "data", "ek9_ek10_folios_fijos.json")
_lock = threading.Lock()


class PuffyService:
    _session: Optional[requests.Session] = None

    @classmethod
    def _config(cls) -> Dict[str, str]:
        load_dotenv(os.path.join(BASE_DIR, ".env"))
        return {
            "base_url": os.getenv("PUFFY_URL", "http://34.51.46.13/puffy").rstrip("/"),
            "usuario": os.getenv("PUFFY_USER", "yeudiel.esteban").strip(),
            "clave": os.getenv("PUFFY_PASS", "uDFkmJWaa4abQ56").strip(),
        }

    @classmethod
    def _get_session(cls, force_login: bool = False) -> requests.Session:
        cfg = cls._config()
        if cls._session is not None and not force_login:
            try:
                r = cls._session.get(f"{cfg['base_url']}/api/yo", timeout=8)
                if r.status_code == 200:
                    return cls._session
            except Exception:
                pass

        s = requests.Session()
        s.headers.update({
            "X-Puffy": "1",
            "Origin": "http://34.51.46.13",
            "Referer": f"{cfg['base_url']}/",
        })
        r = s.post(
            f"{cfg['base_url']}/api/entrar",
            json={"usuario": cfg["usuario"], "clave": cfg["clave"]},
            timeout=15,
        )
        if r.status_code != 200:
            raise RuntimeError(f"No se pudo iniciar sesión en Puffy (HTTP {r.status_code}).")
        cls._session = s
        return s

    @classmethod
    def extraer_folio(cls, texto: str, obra: str = "") -> str:
        if not texto:
            return ""
        obra_clean = re.sub(r"[^A-Z0-9]", "", str(obra or "").upper())
        if obra_clean:
            m = re.search(rf"\b({re.escape(obra_clean)}-\d{{5,}})\b", texto, re.IGNORECASE)
            if m:
                return m.group(1).upper()
        m = re.search(r"\b([A-Z0-9]{2,6}-\d{5,})\b", texto, re.IGNORECASE)
        return m.group(1).upper() if m else ""

    @classmethod
    def preparar_requisicion(
        cls,
        obra: str,
        items: List[Dict[str, Any]],
        contratacion: str = "MARY EK9_1",
        solicitante: str = "Yeudiel Esteban Richard Pérez",
    ) -> Dict[str, Any]:
        """
        Envía a Puffy el mensaje para preparar la requisición con los insumos checkeados
        y devuelve la respuesta + id de acción pendiente + folio tentativo.
        """
        if not items:
            raise ValueError("Marca al menos un insumo con el check antes de enviar a Puffy.")

        obra_clean = str(obra or "EY0").strip().upper()
        lineas = [
            f"puedes hacer una requisicion",
            f"Obra: {obra_clean}, contratación {contratacion} y a nombre de {solicitante}",
        ]
        for it in items:
            insumo = re.sub(r"\.0+$", "", str(it.get("insumo") or "").strip())
            cant = it.get("cantidad")
            partida = str(it.get("partida") or "").strip()
            if not insumo:
                continue
            if partida:
                lineas.append(f"{insumo}, {cant}, {partida}")
            else:
                lineas.append(f"{insumo}, {cant}")

        if len(lineas) <= 2:
            raise ValueError("Los insumos seleccionados no tienen clave válida.")

        texto_prompt = "\n".join(lineas)
        cfg = cls._config()
        s = cls._get_session()

        r = s.post(f"{cfg['base_url']}/api/chat", json={"texto": texto_prompt}, timeout=60)
        if r.status_code == 401:
            s = cls._get_session(force_login=True)
            r = s.post(f"{cfg['base_url']}/api/chat", json={"texto": texto_prompt}, timeout=60)

        if r.status_code != 200:
            raise RuntimeError(f"Error al consultar Puffy (HTTP {r.status_code}): {r.text[:250]}")

        data = r.json()
        respuesta = data.get("respuesta") or ""
        acciones = data.get("acciones") or []
        accion_pendiente = next(
            (a for a in acciones if a.get("estado") == "pendiente" or a.get("id")),
            None,
        )
        accion_id = accion_pendiente.get("id") if accion_pendiente else None
        folio_tentativo = cls.extraer_folio(respuesta, obra_clean)

        return {
            "ok": True,
            "prompt_enviado": texto_prompt,
            "respuesta": respuesta,
            "accion_id": accion_id,
            "accion": accion_pendiente,
            "folio_tentativo": folio_tentativo,
        }

    @classmethod
    def confirmar_requisicion(cls, accion_id: Any, obra: str = "") -> Dict[str, Any]:
        """Confirma en Puffy la acción pendiente (equivale al botón Confirmar / Like)."""
        if not accion_id:
            raise ValueError("No hay una acción pendiente de Puffy para confirmar.")

        cfg = cls._config()
        s = cls._get_session()
        url = f"{cfg['base_url']}/api/acciones/{accion_id}/confirmar"

        r = s.post(url, json={"seleccion": None}, timeout=60)
        if r.status_code == 401:
            s = cls._get_session(force_login=True)
            r = s.post(url, json={"seleccion": None}, timeout=60)

        if r.status_code != 200:
            try:
                err_json = r.json()
                msg = err_json.get("error") or err_json.get("detail") or err_json.get("mensaje") or r.text
            except Exception:
                msg = r.text
            raise RuntimeError(f"Puffy no pudo confirmar la requisición (HTTP {r.status_code}): {msg}")

        data = r.json()
        texto_completo = json.dumps(data, ensure_ascii=False)
        folio = (
            data.get("folio")
            or data.get("Folio")
            or cls.extraer_folio(str(data.get("respuesta") or "") + " " + str(data.get("mensaje") or "") + " " + texto_completo, obra)
        )
        return {
            "ok": True,
            "folio": str(folio or "").strip(),
            "respuesta": data.get("respuesta") or data.get("mensaje") or "Requisición confirmada en Puffy.",
            "raw": data,
        }

    # ------------------------------------------------------------------
    # Persistencia permanente de folios fijados (sobrevive recargas)
    # ------------------------------------------------------------------
    @classmethod
    def cargar_folios_fijos(cls) -> Dict[str, Dict[str, Any]]:
        with _lock:
            if not os.path.exists(FOLIOS_FIJOS_PATH):
                return {}
            try:
                with open(FOLIOS_FIJOS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception:
                return {}

    @classmethod
    def guardar_folio_fijo(
        cls,
        cc: str,
        numero: int,
        folio: Optional[str] = None,
        oc: Optional[str] = None,
        requi_fija: Optional[bool] = None,
    ) -> None:
        if folio is None and oc is None:
            return
        key = f"{str(cc or 'EY0').strip().upper()}_{int(numero)}"
        with _lock:
            data = {}
            if os.path.exists(FOLIOS_FIJOS_PATH):
                try:
                    with open(FOLIOS_FIJOS_PATH, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                except Exception:
                    data = {}

            prev = data.get(key) or {}
            nuevo_folio = prev.get("folio", "") if folio is None else str(folio).strip().upper()
            nueva_oc = prev.get("oc", "") if oc is None else str(oc).strip().upper()
            es_fija = prev.get("requi_fija", False) if requi_fija is None else bool(requi_fija)

            data[key] = {
                "cc": str(cc or "EY0").strip().upper(),
                "numero": int(numero),
                "folio": nuevo_folio,
                "oc": nueva_oc,
                "requi_fija": es_fija,
                "actualizado": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            os.makedirs(os.path.dirname(FOLIOS_FIJOS_PATH), exist_ok=True)
            tmp = FOLIOS_FIJOS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, FOLIOS_FIJOS_PATH)
