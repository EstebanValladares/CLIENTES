import os
import json
import threading
import urllib.request
import urllib.error
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from api.routes import usuarios, bots, operaciones, contratistas, obras
from core.user_service import UserService
from core.daemon_oc_service import iniciar_demonio_oc, forzar_sincronizacion_ahora

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
app.include_router(contratistas.router)
app.include_router(obras.router)

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
# TORRE DE CONTROL: TELEMETRÍA EN VIVO DE CONTROL_PAGOS_OC (NO BLOQUEANTE)
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
        req = urllib.request.Request(oc_url, headers={"User-Agent": "TorreControl-DASHBOARD_EK10"})
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

@app.on_event("startup")
def startup_event():
    # Inicia el demonio que mantiene las OCs de Enkontrol sincronizadas en tiempo real cada 2 minutos
    iniciar_demonio_oc(intervalo_segundos=60)
    
    # Hilo de sondeo continuo de telemetría de CONTROL_PAGOS_OC (cada 4s)
    def _bucle_torre():
        import time
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

@app.get("/api/torre/proyectos")
def obtener_proyectos_torre():
    """
    Torre de Control: Devuelve al instante (<0.1ms) el estado de la telemetría
    sin bloquear a los usuarios ni congelar la pantalla.
    """
    with _lock_torre:
        return [dict(_estado_torre_cache)]

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
