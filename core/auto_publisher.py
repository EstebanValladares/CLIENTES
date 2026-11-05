"""
Core Domain: Auto-Publicador Inteligente y Blindaje de Conexión en Segundo Plano.
Monitorea continuamente los archivos de la Torre (Master).
Cuando detecta cambios nuevos, los traslada a CLIENTES, ejecuta el blindaje de seguridad
y hace push a GitHub automáticamente para que el equipo SIEMPRE tenga la última versión al instante.
"""
import os
import sys
import time
import json
import threading
import subprocess

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLISHER_SCRIPT = os.path.join(BASE_DIR, "publicar_version_equipo.py")
META_PATH = os.path.join(BASE_DIR, ".ultima_publicacion.json")

_hilo_auto_publisher = None
_detener_flag = False
_lock_pub = threading.Lock()

def hay_cambios_pendientes() -> bool:
    """Verifica si algún archivo del Master fue modificado después de la última publicación."""
    if not os.path.exists(PUBLISHER_SCRIPT):
        return False

    last_pub_ts = 0
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
            last_pub_ts = meta.get("timestamp", 0)
        except Exception:
            last_pub_ts = 0

    rutas_a_monitorear = [
        os.path.join(BASE_DIR, "api", "main.py"),
        os.path.join(BASE_DIR, "vue", "index.html"),
        os.path.join(BASE_DIR, "vue", "static", "js", "app.js"),
        os.path.join(BASE_DIR, "vue", "static", "css", "styles.css"),
        os.path.join(BASE_DIR, "USUARIOS", "puestos.json"),
        os.path.join(BASE_DIR, "USUARIOS", "data", "puestos.json"),
        os.path.join(BASE_DIR, "OBRAS", "catalogo_obras.json"),
        os.path.join(BASE_DIR, "publicar_version_equipo.py"),
    ]

    for carpeta in ["api", "core"]:
        c_path = os.path.join(BASE_DIR, carpeta)
        if os.path.exists(c_path):
            for root, _, files in os.walk(c_path):
                for f in files:
                    if f.endswith(".py"):
                        rutas_a_monitorear.append(os.path.join(root, f))

    for ruta in rutas_a_monitorear:
        if os.path.exists(ruta):
            try:
                mtime = os.path.getmtime(ruta)
                if mtime > (last_pub_ts + 2.0):
                    return True
            except Exception:
                pass
    return False

def ejecutar_publicacion_y_push():
    """Ejecuta la publicación de CLIENTES y la subida en segundo plano sin bloquear el dashboard."""
    with _lock_pub:
        try:
            print("\n[AUTO-PUBLISHER] 🔄 Cambios detectados en Torre. Sincronizando y blindando para el equipo...")
            sys.path.insert(0, BASE_DIR)
            from publicar_version_equipo import publicar_version
            meta = publicar_version()
            if meta.get("pushed"):
                print(f"[AUTO-PUBLISHER] 🚀 Publicación exitosa subida a GitHub (Commit {meta.get('commit')})")
            else:
                print(f"[AUTO-PUBLISHER] ⚠️ Publicado localmente, pendiente subida: {meta.get('mensaje')}")
        except Exception as e:
            print(f"[AUTO-PUBLISHER ERROR] Falla al auto-publicar: {e}")

def _bucle_auto_publisher(intervalo_segundos: int = 30):
    print(f"[AUTO-PUBLISHER] Demonio de auto-publicación y blindaje activo (monitoreo cada {intervalo_segundos}s)...")
    while not _detener_flag:
        try:
            time.sleep(intervalo_segundos)
            if _detener_flag:
                break
            
            if hay_cambios_pendientes():
                # Cooldown de 10 segundos para permitir que finalicen escrituras en lote
                time.sleep(10)
                ejecutar_publicacion_y_push()
        except Exception as e:
            print(f"[AUTO-PUBLISHER] Error en bucle: {e}")

def iniciar_auto_publisher(intervalo_segundos: int = 30):
    """Inicia el demonio de auto-publicación solo si estamos en Master."""
    global _hilo_auto_publisher, _detener_flag
    if not os.path.exists(PUBLISHER_SCRIPT):
        return
    if _hilo_auto_publisher is not None and _hilo_auto_publisher.is_alive():
        return

    _detener_flag = False
    _hilo_auto_publisher = threading.Thread(
        target=_bucle_auto_publisher,
        args=(intervalo_segundos,),
        name="AutoPublisherTeam",
        daemon=True
    )
    _hilo_auto_publisher.start()
