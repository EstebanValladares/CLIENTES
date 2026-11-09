"""
Shared Controller: Rutas de API para verificación y sincronización de versiones.
Proporciona endpoints tanto para la Torre Master (publicación) como para los Clientes (actualización).
"""
import os
import json
import urllib.request
import subprocess
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from Shared.config import BASE_DIR, META_PATH, es_modo_master

router = APIRouter(tags=["Shared & Sincronización"])

@router.get("/api/entorno")
def obtener_entorno():
    """Indica si el Dashboard se ejecuta en Modo Master o en Modo Cliente (Equipo)."""
    return {"ok": True, "es_master": es_modo_master()}

@router.get("/api/sistema/version")
def obtener_version_sistema():
    """Retorna el commit actual para clientes o torre."""
    commit_actual = "v2.0"
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            commit_actual = r.stdout.strip()
    except Exception:
        pass

    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                commit_actual = json.load(f).get("commit", commit_actual)
        except Exception:
            pass

    return {"ok": True, "es_master": es_modo_master(), "commit": commit_actual}

@router.get("/api/sistema/verificar-actualizacion")
def verificar_actualizacion():
    """Comprueba si hay una versión más nueva en GitHub para este cliente."""
    if es_modo_master():
        return {"es_master": True, "hay_actualizacion": False}

    try:
        c_local_res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=5
        )
        c_local = c_local_res.stdout.strip() if c_local_res.returncode == 0 else ""

        # 1. Consultar directamente en GitHub
        try:
            req_gh = urllib.request.Request(
                "https://raw.githubusercontent.com/EstebanValladares/CLIENTES/main/.ultima_publicacion.json",
                headers={"User-Agent": "Dashboard-Client/2.0", "Cache-Control": "no-cache"}
            )
            with urllib.request.urlopen(req_gh, timeout=3.0) as resp_gh:
                if resp_gh.status == 200:
                    data_gh = json.loads(resp_gh.read().decode("utf-8"))
                    c_gh = data_gh.get("commit", "")
                    if c_gh and c_local and c_gh != c_local:
                        return {
                            "es_master": False,
                            "hay_actualizacion": True,
                            "commit_local": c_local,
                            "commit_remoto": c_gh,
                            "fuente": "github"
                        }
        except Exception:
            pass

        # 2. Consultar la última versión publicada registrada en Torre local
        candidatos_torre = [
            os.getenv("TORRE_CHAT_URL", "http://10.10.200.147:8000"),
            "http://10.10.200.31:8000",
            "http://Esteban:8000"
        ]
        for t_url in candidatos_torre:
            try:
                req = urllib.request.Request(f"{t_url.rstrip('/')}/api/sistema/version", headers={"User-Agent": "Client/2.0"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode())
                        c_torre = data.get("commit", "")
                        if c_torre and c_local and c_torre != c_local:
                            return {
                                "es_master": False,
                                "hay_actualizacion": True,
                                "commit_local": c_local,
                                "commit_remoto": c_torre,
                                "fuente": "torre"
                            }
            except Exception:
                continue

        return {"es_master": False, "hay_actualizacion": False, "commit_local": c_local}
    except Exception:
        return {"es_master": False, "hay_actualizacion": False}

@router.api_route("/api/sistema/actualizar", methods=["GET", "POST"])
def ejecutar_actualizacion_cliente():
    """
    En clientes (compañeros), descarga inmediatamente la última versión de GitHub
    sin necesidad de cerrar la consola ni reiniciar el proceso.
    """
    if es_modo_master():
        return {"ok": False, "mensaje": "En modo Master se usa 'ACTUALIZAR EQUIPO' para publicar a GitHub."}

    try:
        # 1. Fetch de GitHub
        subprocess.run(["git", "fetch", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=20)
        # 2. Reset hard para garantizar sincronización limpia
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=BASE_DIR, capture_output=True, timeout=20)
        # 3. Pull
        subprocess.run(["git", "pull", "origin", "main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=20)

        # 4. Commit resultante
        c_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True, timeout=5)
        nuevo_commit = c_res.stdout.strip() if c_res.returncode == 0 else "actualizado"

        return {
            "ok": True,
            "commit": nuevo_commit,
            "mensaje": f"¡Dashboard actualizado con éxito al commit {nuevo_commit}!"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "mensaje": f"Error actualizando: {str(e)}"})

@router.post("/api/torre/publicar-cliente")
def publicar_version_cliente_api():
    """Ejecuta la sincronización, blindaje y subida a GitHub de la versión del equipo."""
    if not es_modo_master():
        return JSONResponse(status_code=403, content={"ok": False, "mensaje": "Esta acción solo está disponible en Modo Master."})

    try:
        from Shared.publisher import publicar_version
        res = publicar_version()
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "mensaje": str(e)})

@router.post("/api/torre/publicar-oc")
def publicar_version_oc_api():
    """Ejecuta la sincronización, blindaje y subida a GitHub/Servidor de CONTROL_PAGOS."""
    if not es_modo_master():
        return JSONResponse(status_code=403, content={"ok": False, "mensaje": "Esta acción solo está disponible en Modo Master."})

    try:
        from Shared.publisher_oc import publicar_control_pagos
        res = publicar_control_pagos()
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "mensaje": str(e)})
