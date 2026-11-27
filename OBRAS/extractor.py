import os
import csv
import json
import urllib3
import requests
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OBRAS_DIR = os.path.join(BASE_DIR, "OBRAS")
CAT_OBRAS_CSV = os.path.join(OBRAS_DIR, "CAT_OBRAS.csv")
CAT_OBRAS_JSON = os.path.join(OBRAS_DIR, "catalogo_obras.json")

load_dotenv(os.path.join(BASE_DIR, ".env"))

class ObrasService:
    _session = None

    @classmethod
    def _obtener_sesion(cls):
        if cls._session is not None:
            return cls._session

        user = os.getenv("EK10_USER", "")
        pwd = os.getenv("EK10_PASS", "")

        session = requests.Session()
        session.verify = False

        login_url = "https://suite.ekloud.net:1445/Aryve/kontrol/login/validate"
        data = {"username": user, "password": pwd, "returnUrl": "", "msj": ""}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://suite.ekloud.net:1445/Aryve/",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json; charset=UTF-8"
        }
        r = session.post(login_url, data=data, timeout=15)
        if r.status_code != 200 or ".AspNet.ApplicationCookie" not in session.cookies:
            raise RuntimeError(f"Fallo al autenticar en Aryve (Código {r.status_code})")

        cls._session = session
        cls._headers = headers
        return cls._session

    @classmethod
    def obtener_catalogo_obras(cls) -> list[dict]:
        """Devuelve el catálogo de obras con Id, Clave y Nombre."""
        if os.path.exists(CAT_OBRAS_JSON):
            try:
                with open(CAT_OBRAS_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        obras = []
        if os.path.exists(CAT_OBRAS_CSV):
            with open(CAT_OBRAS_CSV, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    cid = row.get("Id", "").strip()
                    cve = row.get("Clave", "").strip()
                    nom = row.get("Nombre", "").strip()
                    if cid and cve:
                        obras.append({
                            "id": int(cid) if cid.isdigit() else cid,
                            "clave": cve,
                            "nombre": nom,
                            "centro_costo": row.get("IdCentroC", "").strip(),
                            "responsable": row.get("Responsable", "").strip(),
                            "estatus": row.get("IdEstatus", "").strip()
                        })
            with open(CAT_OBRAS_JSON, "w", encoding="utf-8") as f:
                json.dump(obras, f, indent=2, ensure_ascii=False)

        return obras

    @classmethod
    def buscar_obra_por_clave(cls, clave: str) -> dict | None:
        """Busca una obra por su clave (ej. 'AT1', 'CR1')."""
        clave_limpia = clave.strip().upper()
        for o in cls.obtener_catalogo_obras():
            if o["clave"].upper() == clave_limpia:
                return o
        return None

    @classmethod
    def extraer_arbol_obra(cls, clave_o_id: str | int) -> dict:
        """
        Descarga directamente desde Aryve Cloud la estructura jerárquica
        completa (Obra -> Frentes -> Partidas -> Tarjetas) y la guarda en OBRAS/{clave}.json.
        """
        id_obra = None
        clave_obra = ""

        if isinstance(clave_o_id, int) or str(clave_o_id).isdigit():
            id_obra = int(clave_o_id)
            # Buscar clave correspondiente
            for o in cls.obtener_catalogo_obras():
                if o["id"] == id_obra:
                    clave_obra = o["clave"]
                    break
        else:
            obra_info = cls.buscar_obra_por_clave(str(clave_o_id))
            if not obra_info:
                raise ValueError(f"No se encontró la obra con clave '{clave_o_id}'.")
            id_obra = obra_info["id"]
            clave_obra = obra_info["clave"]

        session = cls._obtener_sesion()
        url = "https://suite.ekloud.net:1445/Aryve/base/scco/PresupuestosBase/GetBP/GetArbol/"
        payload = {"parametros": {"IdObra": id_obra}}

        r = session.post(url, json=payload, headers=cls._headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Error consultando árbol en Aryve (Código {r.status_code}): {r.text[:200]}")

        raw_data = r.json()
        if not isinstance(raw_data, list) or len(raw_data) < 2:
            raise ValueError("Respuesta inválida de la API de Aryve.")

        metadatos_wbs = raw_data[0][0] if (raw_data[0] and isinstance(raw_data[0], list)) else {}
        nodos = raw_data[1]

        obra_meta = {
            "id_obra": id_obra,
            "clave": clave_obra or metadatos_wbs.get("ClaveTipoWBS", ""),
            "nombre": "",
            "presupuesto_clave": metadatos_wbs.get("ClavePresupuesto", ""),
            "tipo_wbs": metadatos_wbs.get("ClaveTipoWBS", ""),
            "nombre_wbs": metadatos_wbs.get("NombreTipoWBS", ""),
            "id_tabulador": metadatos_wbs.get("IdTabulador"),
            "moneda": metadatos_wbs.get("ClaveMonedaBase", "MXN"),
            "valuada": metadatos_wbs.get("Valuada", False),
            "explosionada": metadatos_wbs.get("Explosionada", False),
            "total_nodos": len(nodos)
        }

        frentes = {}
        partidas = {}

        total_tarjetas = 0
        total_partidas = 0
        total_frentes = 0

        for n in nodos:
            nivel = n.get("Nivel")
            cod = str(n.get("Codigo", "")).strip()
            tipo_nivel = n.get("TipoNivel")
            nom = str(n.get("Nombre", "")).strip()

            if nivel == 0 or cod == "1":
                obra_meta["nombre"] = nom
                obra_meta["id_nodo_raiz"] = n.get("Id")
                obra_meta["importe_total"] = n.get("Importe", 0.0)
                obra_meta["precio_total"] = n.get("Precio", 0.0)
            elif nivel == 1 or tipo_nivel == "F":
                total_frentes += 1
                frentes[cod] = {
                    "id": n.get("Id"),
                    "codigo": cod,
                    "tipo": "FRENTE",
                    "nombre": nom,
                    "tipo_avance": n.get("TipoAvance", ""),
                    "cantidad": n.get("Cantidad", 1.0),
                    "precio": n.get("Precio", 0.0),
                    "importe": n.get("Importe", 0.0),
                    "autorizado": n.get("Autorizado", False),
                    "partidas": []
                }
            elif nivel == 2 or tipo_nivel == "P":
                total_partidas += 1
                cod_padre = ".".join(cod.split(".")[:2])
                partida_obj = {
                    "id": n.get("Id"),
                    "codigo": cod,
                    "tipo": "PARTIDA",
                    "nombre": nom,
                    "cantidad": n.get("Cantidad", 1.0),
                    "precio": n.get("Precio", 0.0),
                    "importe": n.get("Importe", 0.0),
                    "autorizado": n.get("Autorizado", False),
                    "estatus_ap": n.get("EstatusAutorizacionPresupuesto", ""),
                    "tarjetas": []
                }
                partidas[cod] = partida_obj
                if cod_padre in frentes:
                    frentes[cod_padre]["partidas"].append(partida_obj)
            elif nivel == 3 or len(cod.split(".")) == 4:
                total_tarjetas += 1
                cod_padre = ".".join(cod.split(".")[:3])
                tarjeta_obj = {
                    "id": n.get("Id"),
                    "codigo": cod,
                    "tipo": "TARJETA",
                    "clave_tarjeta": n.get("Clave", ""),
                    "nombre": nom,
                    "cantidad": n.get("Cantidad", 0.0),
                    "unidad": n.get("Unidad", ""),
                    "precio_unitario": n.get("Precio", 0.0),
                    "importe": n.get("Importe", 0.0),
                    "autorizado": n.get("Autorizado", False),
                    "estatus_ap": n.get("EstatusAutorizacionPresupuesto", ""),
                    "bloqueado": n.get("Bloqueado")
                }
                if cod_padre in partidas:
                    partidas[cod_padre]["tarjetas"].append(tarjeta_obj)

        obra_meta["total_frentes"] = total_frentes
        obra_meta["total_partidas"] = total_partidas
        obra_meta["total_tarjetas"] = total_tarjetas

        resultado = {
            "obra": obra_meta,
            "frentes": list(frentes.values())
        }

        # Guardar en OBRAS/{clave}.json
        os.makedirs(OBRAS_DIR, exist_ok=True)
        ruta_archivo = os.path.join(OBRAS_DIR, f"{clave_obra or id_obra}.json")
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)

        return resultado

    @classmethod
    def extraer_todas_las_obras(cls, max_workers: int = 8) -> dict:
        """
        Descarga directamente desde Aryve Cloud todas las obras con presupuesto
        y compila la jerarquía completa en OBRAS/obras.json.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from datetime import datetime

        session = cls._obtener_sesion()
        url_obras = "https://suite.ekloud.net:1445/Aryve/base/scco/PresupuestosBase/GetBP/GetObras/"
        r = session.post(url_obras, json={"parametros": {}}, headers=cls._headers, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"Error consultando obras: {r.status_code}")

        obras_list = r.json()
        obras_procesadas = []

        def worker(o):
            try:
                res = cls.extraer_arbol_obra(o["IdObra"])
                return res["obra"] if "obra" in res else None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker, o) for o in obras_list]
            for f in as_completed(futures):
                res = f.result()
                if res:
                    obras_procesadas.append(res)

        if not obras_procesadas:
            print("[Extractor] ALERTA: No se pudo extraer ninguna obra de Aryve Cloud. Se conserva el archivo obras.json existente para evitar pérdida de datos.")
            return {
                "metadata": {
                    "total_obras": 0,
                    "error": "No se obtuvieron obras válidas en la extracción"
                },
                "obras": []
            }

        obras_procesadas.sort(key=lambda x: str(x.get("clave", "")))

        resultado_final = {
            "metadata": {
                "total_obras": len(obras_procesadas),
                "total_obras_solicitadas": len(obras_list),
                "total_frentes": sum(o.get("total_frentes", 0) for o in obras_procesadas),
                "total_partidas": sum(o.get("total_partidas", 0) for o in obras_procesadas),
                "total_tarjetas": sum(o.get("total_tarjetas", 0) for o in obras_procesadas),
                "fecha_extraccion": datetime.now().isoformat()
            },
            "obras": obras_procesadas
        }

        with open(os.path.join(OBRAS_DIR, "obras.json"), "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, indent=2, ensure_ascii=False)

        # Sincronización automática a Firebase Firestore (Colección OBRAS)
        try:
            from core.firebase_client import FirebaseClient
            FirebaseClient.sincronizar_obras_a_firestore(resultado_final)
        except Exception as e_fb:
            print(f"[ObrasService] Aviso sincronización Firebase: {e_fb}")

        return resultado_final

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extractor de Estructuras de Obra desde Aryve Cloud")
    parser.add_argument("--obra", default="AT1", help="Clave de la obra (por defecto AT1)")
    args = parser.parse_args()

    print(f"Iniciando extracción para la obra: {args.obra}")
    datos = ObrasService.extraer_arbol_obra(args.obra)
    print(f"Estructura guardada exitosamente en OBRAS/{args.obra}.json")
    print(f"Total frentes: {datos['obra']['total_frentes']}, partidas: {datos['obra']['total_partidas']}, tarjetas: {datos['obra']['total_tarjetas']}")

