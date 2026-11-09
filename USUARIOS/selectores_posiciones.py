"""
Catálogo de Selectores y URLs para el Módulo de Creación de Posiciones / Puestos en Aryve.
Aisla los XPaths e IDs de la pantalla de posiciones para que no se empalmen con los de usuarios.
"""
import os
from pathlib import Path

# --- URLs DE POSICIONES EN ARYVE ---
ARYVE_BASE_URL = os.getenv("ARYVE_BASE_URL", "https://suite.ekloud.net:1445/Aryve/")
ARYVE_POSICIONES_URL = f"{ARYVE_BASE_URL.rstrip('/')}/#/kontrol/posiciones"
ARYVE_PUESTOS_URL = f"{ARYVE_BASE_URL.rstrip('/')}/#/kontrol/puestos"

SELECTORES_POSICION = {
    # --- RUTA Y NAVEGACIÓN ---
    "menu_rh": "//span[contains(text(), 'Recursos Humanos') or contains(text(), 'RH')]",
    "menu_posiciones": "//a[contains(@href, 'posiciones') or contains(text(), 'Posiciones') or contains(text(), 'Puestos')]",
    "btn_nueva_posicion": "//button[contains(@class, 'btn-nuevo') or contains(@title, 'Nuevo') or contains(text(), 'Nuevo')]",

    # --- FORMULARIO DE POSICIONES ---
    "clave": "formControl_Clave",
    "nombre": "formControl_Nombre",
    "padre": "select2-formControl_PosicionPadre-container",
    "categoria": "select2-formControl_Categoria-container",
    "estatus": "formControl_Estatus",
    "descripcion": "formControl_Descripcion",

    # --- INPUTS DE BÚSQUEDA SELECT2 ---
    "input_busqueda_select2": "//input[contains(@class, 'select2-search__field')]",
    "select2_opcion_resultado": "//li[contains(@class, 'select2-results__option')]",

    # --- BOTONES DE ACCIÓN ---
    "btn_guardar": "//button[contains(@title, 'Guardar') or contains(@class, 'btn-guardar') or .//i[contains(@class, 'icon-cloud-upload')]]",
    "btn_cancelar": "//button[contains(@title, 'Cancelar') or contains(text(), 'Cancelar')]",
    "alerta_exito": "//div[contains(@class, 'alert-success') or contains(text(), 'guardado correctamente') or contains(text(), 'éxito')]",
}
