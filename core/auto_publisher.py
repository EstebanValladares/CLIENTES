"""
Core Domain: Auto-Publicador (DESHABILITADO PARA EVITAR COMMITS AUTOMÁTICOS).
Solo se publica cuando el usuario hace clic manualmente en 'ACTUALIZAR EQUIPO'.
"""
import threading

_hilo_auto_publisher = None
_detener_flag = True
_lock_pub = threading.Lock()

def ejecutar_publicacion_y_push():
    """Deshabilitado para evitar commits automáticos no deseados."""
    return

def _bucle_auto_publisher(intervalo_segundos: int = 30):
    """Deshabilitado."""
    return

def iniciar_auto_publisher(intervalo_segundos: int = 30):
    """Deshabilitado. La publicación ahora es 100% manual por decisión del usuario."""
    return
