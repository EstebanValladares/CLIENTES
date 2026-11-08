"""
Paquete Shared: Módulo Unificado de Sincronización, Detección de Cambios y Publicación para el Equipo.
"""
from Shared.config import BASE_DIR, CLIENT_DIR, CLIENT_REPO_URL, META_PATH, es_modo_master
from Shared.detector import obtener_estado_cliente, hay_cambios_pendientes
from Shared.controller import router

try:
    from Shared.publisher import publicar_version
except ImportError:
    publicar_version = None

__all__ = [
    "BASE_DIR",
    "CLIENT_DIR",
    "CLIENT_REPO_URL",
    "META_PATH",
    "es_modo_master",
    "obtener_estado_cliente",
    "hay_cambios_pendientes",
    "router",
    "publicar_version",
]
