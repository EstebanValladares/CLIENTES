"""
Catálogo centralizado de selectores DOM (IDs, XPaths y URLs) para Aryve (Enkontrol 10).
"""
import os
from pathlib import Path

# --- RUTAS Y DIRECTORIOS ---
BASE_DIR = Path(__file__).resolve().parent
ECOSYSTEM_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
PUESTOS_JSON_PATH = DATA_DIR / "puestos.json" if (DATA_DIR / "puestos.json").exists() else BASE_DIR / "puestos.json"
LOGGER_DIR = BASE_DIR / "logger"
FALLOS_CLASIFICADORES_JSONL = LOGGER_DIR / "fallos_clasificadores.jsonl"
REGISTRO_USUARIOS_JSONL = LOGGER_DIR / "registro_usuarios.jsonl"

# --- URLs OFICIALES DE ARYVE ---
ARYVE_BASE_URL = os.getenv("ARYVE_BASE_URL", "")
ARYVE_NUEVO_USUARIO_URL = f"{ARYVE_BASE_URL.rstrip('/')}/#/kontrol/usuarios/id?nuevo"

def obtener_url_perfil_usuario(id_usuario: str | int) -> str:
    """Retorna la URL directa del perfil del usuario en Aryve."""
    return f"{ARYVE_BASE_URL.rstrip('/')}/#/kontrol/usuarios/{id_usuario}"

# --- TIMEOUTS DE ESPERA (SEGUNDOS) ---
TIMEOUT_CORTO = 4.0
TIMEOUT_MEDIO = 10.0
TIMEOUT_LARGO = 18.0
POLL_INTERVAL_RAPIDO = 0.15
ID_SIMULADO_PRUEBA = "88888"

# --- BANDERAS DE DOMINIO ---
OMITIR_OBRAS_Y_CENTROS_COSTO = True
PATRONES_CLASIFICADORES_OMITIDOS = (
    "OBRAS (DESARROLLOS)",
    "OBRAS",
    "CENTROS DE COSTOS",
    "CENTRO DE COSTO",
)


class SafeSelectorDict(dict):
    """Diccionario que devuelve cadena vacía si se consulta una clave inexistente."""
    def __missing__(self, key: str) -> str:
        return ""


SELECTORES = SafeSelectorDict({
    # --- LOGIN ---
    "login_user_id": "username",
    "login_pass_id": "password",
    "login_submit_id": "btnSubmit",
    "login_user_xpath": "//input[@id='username' or @type='text' or contains(@name, 'user') or contains(@id, 'user')]",
    "login_pass_xpath": "//input[@id='password' or @type='password']",
    "login_submit_xpath": "//button[@id='btnSubmit' or @type='submit' or contains(text(), 'Entrar') or contains(text(), 'Iniciar')]",

    # --- DATOS GENERALES DE USUARIO ---
    "nombre": "formControl_Nombre",
    "apellidos": "formControl_Apellidos",
    "clave": "formControl_Clave",
    "correo": "formControl_Email",
    "telefono": "formControl_Telefono",
    "inicio": "formControl_VigenciaInicio",
    "fin": "formControl_VigenciaFin",
    "estatus_activo": "formControl_usuarios_Estatus",

    # --- POSICIÓN EN LA ORGANIZACIÓN ---
    "caja_posicion": "select2-formControl_Posicion-container",
    "caja_area": "select2-formControl_AreaOrganizacion-container",

    # --- CONFIGURACIÓN REGIONAL ---
    "caja_timezone": "select2-formControl_TimeZone-container",
    "caja_idioma": "select2-formControl_Idioma-container",

    # --- NIVELES ASIGNADOS ---
    "caja_compania": "select2-formControl_Compania-container",
    "caja_nivel": "select2-formControl_Nivel-container",
    "btn_guardar_niveles": "Niveles_saveButtonKey",

    # --- GRUPOS ---
    "caja_grupo": "select2-formControl_Grupo-container",
    "btn_guardar_grupos": "Grupos_saveButtonKey",

    # --- CLASIFICADORES ---
    "caja_tipo_clasificador": "select2-formControl_TipoClasificador-container",
    "btn_guardar_clasificadores": "Clasificadores_saveButtonKey",

    # --- BOTÓN GUARDAR USUARIO GENERAL ---
    "btn_guardar_usuario": "//button[contains(@title, 'Guardar') and .//i[contains(@class, 'icon-cloud-upload')]]",

    # --- EDICIÓN Y CLASIFICADORES DE USUARIO EXISTENTE ---
    "btn_editar_usuario": "//button[contains(@class, 'btn-editar') or contains(@title, 'Editar')]",
    "botones_agregar": "//button[contains(@class, 'btn-ico-ek') and @title='Agregar']",
    "input_busqueda_select2": "//input[contains(@class, 'select2-search__field')]",
    "input_busqueda_clasificadores": "(//input[@aria-label='Buscar en la tabla de datos'])[last()]",
    "icono_checkbox_custom": ".//i[contains(@class, 'fa-square') or contains(@onclick, 'dgOnClickSelect')]",
})

