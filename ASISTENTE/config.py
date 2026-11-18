"""
Configuración central del Módulo Asistente Centinela.
Constantes, rutas, tiempos de espera y parámetros de personalidad.
"""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_ASISTENTE_PATH = os.path.join(DATA_DIR, "asistente.db")
DB_CHAT_PATH = os.path.join(DATA_DIR, "chat_equipo.db")
DB_ESC_PATH = os.path.join(DATA_DIR, "escalatorias.db")
DB_MAPEO_PATH = os.path.join(DATA_DIR, "mapeo_lotes.db")

# Parámetros del Personaje
NOMBRE_DEFAULT = "Toastie"
AVATAR_DEFAULT = "/static/img/toast.png"
AVATAR_IMG = AVATAR_DEFAULT
LEMA_DEFAULT = "¡OMFG HELLO! Cuidando tus pendientes en tiempo real."

# Tiempos de UI (segundos)
DURACION_GLOBO_SEGUNDOS = 9
INTERVALO_POLLING_SEGUNDOS = 4.5
MAX_HISTORIAL_MEMORIA = 20
