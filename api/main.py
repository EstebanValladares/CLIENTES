def _es_modo_master() -> bool:
    """Verifica si estamos ejecutando en el entorno Master (DASHBOARD_EK10)"""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    publisher_script = os.path.join(base_dir, "publicar_version_equipo.py")
    return os.path.exists(publisher_script)

import os
import json
import time
import threading
import urllib.request
import urllib.error
import subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from api.routes import usuarios, bots, operaciones, obras, proveedores_contratistas, chat
from core.user_service import UserService
from core.daemon_oc_service import iniciar_demonio_oc, forzar_sincronizacion_ahora
from core.auto_publisher import iniciar_auto_publisher

app = FastAPI(
    title="Dashboard Intelligence Solutions - VELAS",
    description="Clean Architecture API para control de bots RPA, Selenium y Gestión de Usuarios",
    version="2.0.0"
)

# CORS habilitado para flexibilidad de integración
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas de dominio
app.include_router(usuarios.router)
app.include_router(bots.router)
app.include_router(operaciones.router)
app.include_router(obras.router)
app.include_router(proveedores_contratistas.router)
app.include_router(chat.router)

@app.get("/api/metricas")
def metricas_globales():
    """KPIs del NUCLEO optimizados"""
    lista_usr = UserService.obtener_usuarios()
    catalogo = bots.BotRunnerService.obtener_catalogo()

    # Historial NUCLEO
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    hist_path = os.path.join(base_dir, "NUCLEO", "reportes", "historial.jsonl")
    total_ejec = 0
    total_ok = 0

    if os.path.exists(hist_path):
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        total_ejec += 1
                        try:
                            d = json.loads(line)
                            if d.get("veredicto") == "OK":
                                total_ok += 1
                        except Exception:
                            pass
        except Exception:
            pass

    tasa_exito = round((total_ok / total_ejec * 100), 1) if total_ejec > 0 else 100.0

    return {
        "total_usuarios": len(lista_usr),
        "total_bots": len(catalogo),
        "total_ejecuciones": total_ejec,
        "tasa_exito": tasa_exito
    }

# ==============================================================================
# TORRE DE CONTROL: TELEMETRÍA EN VIVO (OC & CLIENTES)
# ==============================================================================
_estado_torre_cache = {
    "id": "OC",
    "nombre": "OC",
    "descripcion": "Control de Pagos & Órdenes de Compra",
    "icono": "fa-solid fa-file-invoice-dollar",
    "salud": "0%",
    "estado": "OFFLINE",
    "activo": False,
    "servicios": "Desconectado",
    "conexion": "http://127.0.0.1:5000",
    "ocs_hoy": 0,
    "monto_hoy": 0.0,
    "total_ocs": 0,
    "errores": 1,
    "latencia_ms": 0,
    "uptime": "0s",
    "ultima_fecha": "-"
}
_lock_torre = threading.Lock()

def _sondear_telemetria_oc():
    """Consulta la telemetría en segundo plano sin congelar la API ni las búsquedas"""
    global _estado_torre_cache
    oc_url = os.getenv("CONTROL_PAGOS_OC_URL", "http://127.0.0.1:5000/api/telemetria")
    
    estado_oc = {
        "id": "OC",
        "nombre": "OC",
        "descripcion": "Control de Pagos & Órdenes de Compra",
        "icono": "fa-solid fa-file-invoice-dollar",
        "salud": "0%",
        "estado": "OFFLINE",
        "activo": False,
        "servicios": "Desconectado",
        "conexion": "http://127.0.0.1:5000",
        "ocs_hoy": 0,
        "monto_hoy": 0.0,
        "total_ocs": 0,
        "errores": 1,
        "latencia_ms": 0,
        "uptime": "0s",
        "ultima_fecha": "-"
    }

    try:
        req = urllib.request.Request(oc_url, headers={"User-Agent": "TorreControl-CLIENTES"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                datos = data.get("datos", {})
                
                uptime_seg = data.get("uptime_segundos", 0)
                if uptime_seg > 3600:
                    uptime_str = f"{uptime_seg // 3600}h {(uptime_seg % 3600) // 60}m"
                elif uptime_seg > 60:
                    uptime_str = f"{uptime_seg // 60}m {uptime_seg % 60}s"
                else:
                    uptime_str = f"{uptime_seg}s"

                dia_nombre = datos.get("dia_hoy", "Hoy")
                estado_oc.update({
                    "salud": data.get("salud", "100%"),
                    "estado": data.get("estado", "OPERATIVO"),
                    "activo": True,
                    "servicios": "Aryve / Enkontrol (En Línea)",
                    "dia_actual": dia_nombre,
                    "ocs_hoy_aryve": datos.get("ocs_hoy_aryve", 0),
                    "ocs_hoy_velas": datos.get("ocs_hoy_velas", 0),
                    "ocs_hoy_total": datos.get("ocs_hoy_total", 0),
                    "total_aryve": datos.get("total_aryve", 0),
                    "total_velas": datos.get("total_velas", 0),
                    "total_global": datos.get("total_global", 0),
                    "historial_dias": datos.get("historial_dias", []),
                    "errores": datos.get("errores", 0),
                    "latencia_ms": data.get("latencia_db_ms", 0),
                    "uptime": uptime_str
                })
    except Exception:
        pass

    with _lock_torre:
        _estado_torre_cache = estado_oc

def _obtener_estado_cliente() -> dict:
    """Verifica si la versión pública/equipo (CLIENTES) está sincronizada con Master"""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    publisher_script = os.path.join(base_dir, "publicar_version_equipo.py")
    meta_path = os.path.join(base_dir, ".ultima_publicacion.json")
    client_dir = os.path.join(os.path.dirname(base_dir), "CLIENTES")
    
    es_master = os.path.exists(publisher_script)
    desactualizado = False
    archivos_modificados = []
    ultima_fecha = "Pendiente"
    tiempo_str = "Sin publicar"
    commit_hash = "-"
    
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            last_pub_ts = meta.get("timestamp", 0)
            ultima_fecha = meta.get("fecha_hora", "-")
            commit_hash = meta.get("commit", "-")
            
            # Calcular tiempo transcurrido
            delta = time.time() - last_pub_ts
            if delta < 60:
                tiempo_str = "Hace unos segundos"
            elif delta < 3600:
                tiempo_str = f"Hace {int(delta // 60)} min"
            elif delta < 86400:
                tiempo_str = f"Hace {int(delta // 3600)} h"
            else:
                tiempo_str = f"Hace {int(delta // 86400)} d"
                
            # Verificar si algún archivo del master fue modificado después de la última publicación
            if es_master:
                rutas_a_monitorear = [
                    os.path.join(base_dir, "api", "main.py"),
                    os.path.join(base_dir, "vue", "index.html"),
                    os.path.join(base_dir, "vue", "static", "js", "app.js"),
                    os.path.join(base_dir, "vue", "static", "css", "styles.css"),
                    os.path.join(base_dir, "USUARIOS", "data", "Usuarios.json"),
                    os.path.join(base_dir, "USUARIOS", "data", "puestos.json"),
                    os.path.join(base_dir, "OBRAS", "catalogo_obras.json"),
                ]
                
                for carpeta in ["api", "core"]:
                    c_path = os.path.join(base_dir, carpeta)
                    if os.path.exists(c_path):
                        for root, _, files in os.walk(c_path):
                            for f in files:
                                if f.endswith(".py"):
                                    rutas_a_monitorear.append(os.path.join(root, f))
                                    
                for ruta in rutas_a_monitorear:
                    if os.path.exists(ruta):
                        mtime = os.path.getmtime(ruta)
                        if mtime > (last_pub_ts + 1.0):
                            desactualizado = True
                            archivos_modificados.append(os.path.basename(ruta))
                            
                # Obtener commit actual de CLIENTES
                if os.path.exists(client_dir):
                    c_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=client_dir, capture_output=True, text=True)
                    if c_res.returncode == 0 and c_res.stdout.strip():
                        commit_hash = c_res.stdout.strip()
                desactualizado = len(archivos_modificados) > 0
        except Exception as e:
            desactualizado = False
    else:
        desactualizado = True if es_master else False
        
    if not os.path.exists(client_dir) and es_master:
        desactualizado = True
        
    estado = "CAMBIOS PENDIENTES" if desactualizado else "ACTUALIZADO"
    
    return {
        "id": "CLIENTES",
        "nombre": "CLIENTES",
        "descripcion": "Versión Limpia / Equipo (Autónomo)",
        "icono": "fa-solid fa-users-gear",
        "salud": "100%" if not desactualizado else "85%",
        "estado": estado,
        "activo": True,
        "desactualizado": desactualizado,
        "archivos_pendientes": len(archivos_modificados),
        "es_master": es_master,
        "servicios": "GitHub / origin main",
        "ultima_publicacion": ultima_fecha,
        "tiempo_transcurrido": tiempo_str,
        "commit": commit_hash,
        "latencia_ms": 1,
        "uptime": tiempo_str
    }

@app.on_event("startup")
def startup_event():
    # Solo ejecutar demonio de OC si estamos en el entorno MASTER
    if _es_modo_master():
        iniciar_demonio_oc(intervalo_segundos=60)
        # Desactivamos el auto-publisher en background silencioso para que Esteban tenga control manual de RE-PUBLICAR
        def _bucle_torre():
            while True:
                _sondear_telemetria_oc()
                time.sleep(4)
        threading.Thread(target=_bucle_torre, daemon=True).start()

@app.post("/api/torre/sync-oc")
def sync_oc_manual():
    """Fuerza la sincronización inmediata de OCs desde Enkontrol"""
    res = forzar_sincronizacion_ahora(dias_atras=2)
    _sondear_telemetria_oc()
    return res

@app.post("/api/torre/publicar-cliente")
def publicar_version_cliente_api():
    """Ejecuta la sincronización y blindaje de la versión del equipo/cliente."""
    try:
        from publicar_version_equipo import publicar_version
        res = publicar_version()
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "mensaje": str(e)})

@app.get("/api/sistema/verificar-actualizacion")
def verificar_actualizacion():
    """Comprueba si hay una versión más nueva en GitHub para este cliente."""
    if _es_modo_master():
        return {"es_master": True, "hay_actualizacion": False}
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    try:
        c_local_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=base_dir, capture_output=True, text=True, timeout=5)
        c_local = c_local_res.stdout.strip() if c_local_res.returncode == 0 else ""
        
        # Consultar la última versión publicada registrada en Torre
        torre_url = os.getenv("TORRE_CHAT_URL", "http://10.10.200.147:8000")
        try:
            req = urllib.request.Request(f"{torre_url}/api/sistema/version", headers={"User-Agent": "Client/2.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    c_torre = data.get("commit", "")
                    if c_torre and c_local and c_torre != c_local:
                        return {
                            "es_master": False,
                            "hay_actualizacion": True,
                            "commit_local": c_local,
                            "commit_remoto": c_torre
                        }
        except Exception:
            pass
            
        return {"es_master": False, "hay_actualizacion": False, "commit_local": c_local}
    except Exception:
        return {"es_master": False, "hay_actualizacion": False}

@app.post("/api/sistema/actualizar")
def ejecutar_actualizacion_cliente():
    """
    En clientes (compañeros), descarga inmediatamente la última versión de GitHub
    sin necesidad de cerrar la consola ni reiniciar el proceso.
    """
    if _es_modo_master():
        return {"ok": False, "mensaje": "En modo Master se usa 'Publicar a Clientes'."}
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    try:
        # 1. Fetch de GitHub
        subprocess.run(["git", "fetch", "origin", "main"], cwd=base_dir, capture_output=True, text=True, timeout=15)
        # 2. Reset hard para garantizar sincronización limpia
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=base_dir, capture_output=True, timeout=15)
        # 3. Pull
        pull_res = subprocess.run(["git", "pull", "origin", "main"], cwd=base_dir, capture_output=True, text=True, timeout=15)
        
        # 4. Commit resultante
        c_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=base_dir, capture_output=True, text=True, timeout=5)
        nuevo_commit = c_res.stdout.strip() if c_res.returncode == 0 else "actualizado"

        return {
            "ok": True,
            "commit": nuevo_commit,
            "mensaje": f"¡Sistema actualizado con éxito al commit {nuevo_commit}!"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "mensaje": f"Error actualizando: {str(e)}"})

@app.get("/api/sistema/version")
def obtener_version_sistema():
    """Retorna el commit actual para clientes o torre."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    meta_path = os.path.join(base_dir, ".ultima_publicacion.json")
    commit_actual = "v2.0"
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=base_dir, capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            commit_actual = r.stdout.strip()
    except Exception:
        pass
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                commit_actual = json.load(f).get("commit", commit_actual)
        except Exception:
            pass
    return {"ok": True, "es_master": _es_modo_master(), "commit": commit_actual}

@app.get("/api/entorno")
def obtener_entorno():
    """Indica si el Dashboard se ejecuta en Modo Master o en Modo Cliente (Equipo)."""
    return {"ok": True, "es_master": _es_modo_master()}

@app.get("/api/torre/proyectos")
def obtener_proyectos_torre():
    """
    Torre de Control: Devuelve al instante el estado de la telemetría
    SOLO en MODO MASTER. En la versión de CLIENTES (Equipo) retorna lista vacía [].
    """
    if not _es_modo_master():
        return []
    with _lock_torre:
        oc = dict(_estado_torre_cache)
    cliente = _obtener_estado_cliente()
    return [oc, cliente]

# Servir Frontend (Vue)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "vue")
app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR, "static")), name="static")

@app.get("/")
@app.get("/{full_path:path}")
def servir_frontend(full_path: str = ""):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Ruta de API no encontrada"})
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"mensaje": "Frontend no encontrado"})
