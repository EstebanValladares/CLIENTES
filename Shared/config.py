"""
Configuración centralizada y detección de entorno para Shared.
Mantiene las rutas, URLs de repositorios y validación Master vs Cliente.
"""
import os

SHARED_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(SHARED_DIR, ".."))
PARENT_DIR = os.path.dirname(BASE_DIR)
CLIENT_DIR = os.path.join(PARENT_DIR, "CLIENTES")
CLIENT_REPO_URL = "https://github.com/EstebanValladares/CLIENTES.git"
META_PATH = os.path.join(BASE_DIR, ".ultima_publicacion.json")

# Configuración de Publicación: CONTROL_PAGOS_OC -> CONTROL_PAGOS (Servidor)
OC_SRC_DIR = os.path.join(PARENT_DIR, "CONTROL_PAGOS_OC")
OC_CLIENT_DIR = os.path.join(PARENT_DIR, "CONTROL_PAGOS")
OC_REPO_URL = os.getenv("CONTROL_PAGOS_REPO_URL", "https://github.com/EstebanValladares/CONTROL_PAGOS.git")
OC_META_PATH = os.path.join(BASE_DIR, ".ultima_publicacion_oc.json")

def es_modo_master() -> bool:
    """
    Verifica si se está ejecutando en el entorno Torre / Master (DASHBOARD_EK10).
    En la versión del equipo (CLIENTES), el archivo publisher.py se omite por seguridad,
    garantizando que este método retorne False automáticamente para los clientes.
    """
    publisher_file = os.path.join(SHARED_DIR, "publisher.py")
    legacy_file = os.path.join(BASE_DIR, "publicar_version_equipo.py")
    return os.path.exists(publisher_file) or os.path.exists(legacy_file)
