"""
Core Domain: Auto-Publicador Inteligente y Blindaje de Conexión en Segundo Plano.
Monitorea continuamente los archivos de la Torre (Master) usando el módulo Shared.
Cuando detecta cambios nuevos, ejecuta la publicación y push a GitHub para el equipo.
"""
import time
import threading
from Shared import hay_cambios_pendientes, publicar_version, es_modo_master

_hilo_auto_publisher = None
_detener_flag = False
_lock_pub = threading.Lock()

def ejecutar_publicacion_y_push():
    """Ejecuta la publicación de CLIENTES y la subida en segundo plano sin bloquear el dashboard."""
    with _lock_pub:
        try:
            print("\n[AUTO-PUBLISHER] 🔄 Cambios detectados en Torre. Sincronizando y blindando para el equipo...")
            if publicar_version is not None:
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
    if not es_modo_master():
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
