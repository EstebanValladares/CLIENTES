"""
Paquete Shared: Módulo Unificado de Sincronización, Detección de Cambios y Publicación para el Equipo.
"""
from Shared.config import BASE_DIR, CLIENT_DIR, CLIENT_REPO_URL, META_PATH, es_modo_master, OC_SRC_DIR, OC_CLIENT_DIR, OC_REPO_URL, OC_META_PATH
from Shared.detector import obtener_estado_cliente, hay_cambios_pendientes, obtener_estado_oc_publicacion
from Shared.controller import router

try:
    from Shared.publisher import publicar_version
except ImportError:
    publicar_version = None

try:
    from Shared.publisher_oc import publicar_control_pagos
except ImportError:
    publicar_control_pagos = None

__all__ = [
    "BASE_DIR",
    "CLIENT_DIR",
    "CLIENT_REPO_URL",
    "META_PATH",
    "OC_SRC_DIR",
    "OC_CLIENT_DIR",
    "OC_REPO_URL",
    "OC_META_PATH",
    "es_modo_master",
    "obtener_estado_cliente",
    "obtener_estado_oc_publicacion",
    "hay_cambios_pendientes",
    "router",
    "publicar_version",
    "publicar_control_pagos",
]
