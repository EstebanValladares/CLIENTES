import os
import sys
import time
import threading

# Ruta base del proyecto CONTROL_PAGOS_OC
BASE_OC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "CONTROL_PAGOS_OC"))
if BASE_OC not in sys.path:
    sys.path.insert(0, BASE_OC)

_hilo_daemon = None
_detener_flag = False

def _demonio_loop(intervalo_segundos: int = 60):
    """
    Bucle en segundo plano que sincroniza las OCs creadas en Enkontrol cada 60 segundos.
    Ejecución incremental ultrarrápida (0.15s - 0.3s).
    """
    print(f"\n[DAEMON OC] Auto-sincronizador Enkontrol iniciado (cada {intervalo_segundos}s)...")
    while not _detener_flag:
        try:
            time.sleep(intervalo_segundos)
            if _detener_flag:
                break
            
            import sincronizar_ordenes_ek9
            # Sincroniza los últimos 2 días para capturar cualquier OC creada o editada hoy
            res = sincronizar_ordenes_ek9.sincronizar_ordenes_rapido(dias_atras=2, verbose=False)
            if res.get("status") == "ok":
                # Avisar al cache local de pagos si estuviera disponible
                pass
        except Exception as e:
            print(f"[DAEMON OC ERROR] Falla en auto-sincronización: {e}")

def iniciar_demonio_oc(intervalo_segundos: int = 60):
    """Inicia el demonio en un hilo Daemon de Python independiente."""
    global _hilo_daemon, _detener_flag
    if _hilo_daemon is not None and _hilo_daemon.is_alive():
        return
    
    _detener_flag = False
    _hilo_daemon = threading.Thread(
        target=_demonio_loop,
        args=(intervalo_segundos,),
        name="DemonioSyncOC",
        daemon=True
    )
    _hilo_daemon.start()

def forzar_sincronizacion_ahora(dias_atras: int = 2) -> dict:
    """Ejecuta una sincronización inmediata bajo demanda."""
    try:
        import sincronizar_ordenes_ek9
        return sincronizar_ordenes_ek9.sincronizar_ordenes_rapido(dias_atras=dias_atras, verbose=False)
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

