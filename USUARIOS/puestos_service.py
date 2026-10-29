"""
Módulo de Gestión de Puestos, Plantillas y Clasificadores para Aryve.
Centraliza las reglas de negocio del árbol de clasificadores y la lectura de puestos.json / Firebase.
"""
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from USUARIOS.selectores import (
    OMITIR_OBRAS_Y_CENTROS_COSTO,
    PATRONES_CLASIFICADORES_OMITIDOS,
    PUESTOS_JSON_PATH,
)


# ==============================================================================
# MODELOS DE DOMINIO
# ==============================================================================

@dataclass
class ConfiguracionPuesto:
    """Plantilla de configuración de un puesto obtenida de puestos.json o Firebase."""
    nombre_puesto: str = ""
    niveles_asignados: list[dict[str, str]] = field(default_factory=list)
    grupos: list[str] = field(default_factory=list)
    clasificadores: dict[str, Any] = field(default_factory=dict)
    area_organizacional: str = ""

    @property
    def total_clasificadores(self) -> int:
        """Calcula el número total de clasificadores hijos configurados."""
        pares = extraer_padres_e_hijos(self.clasificadores, filtrar_omitidos=False)
        return sum(len(hijos) for _, hijos in pares)

    def as_tuple(self) -> tuple[list[dict[str, str]], list[str], dict[str, Any], str]:
        """Formato de tupla compatible para desestructuración."""
        return (
            self.niveles_asignados,
            self.grupos,
            self.clasificadores,
            self.area_organizacional,
        )

    def __iter__(self):
        return iter(self.as_tuple())


# ==============================================================================
# UTILIDADES DE NORMALIZACIÓN
# ==============================================================================

def normalizar_alnum(texto: str | None) -> str:
    """Normaliza una cadena eliminando acentos y caracteres especiales en MAYÚSCULAS."""
    if not texto:
        return ""
    norm = unicodedata.normalize("NFKD", str(texto)).encode("ASCII", "ignore").decode("utf-8")
    norm = re.sub(r"[^A-Z0-9]", " ", norm.upper())
    return " ".join(norm.split())


def normalizar_texto_comparacion(texto: str | None) -> str:
    """Normaliza texto eliminando diacríticos y colapsando espacios en minúsculas."""
    texto_str = unicodedata.normalize("NFKD", str(texto if texto is not None else ""))
    sin_acentos = "".join(c for c in texto_str if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_acentos).strip().casefold()


def obtener_campo(datos: dict[str, Any] | Any, *llaves: str, default: str = "") -> str:
    """Extrae un campo de un diccionario probando múltiples variantes de nombre de llave."""
    if not isinstance(datos, dict):
        return default
    for k in llaves:
        if k in datos and datos[k] is not None:
            return str(datos[k]).strip()
        for dk, dv in datos.items():
            if dk and dk.strip().lower() == k.lower() and dv is not None:
                return str(dv).strip()
    return default


# ==============================================================================
# REGLAS DE NEGOCIO PARA CLASIFICADORES
# ==============================================================================

def es_clasificador_omitido(
    nombre_clasificador: str | None,
    omitir_activo: bool | None = None,
) -> bool:
    """Determina si un clasificador (ej. OBRAS o CENTROS DE COSTOS) debe omitirse temporalmente."""
    flag = OMITIR_OBRAS_Y_CENTROS_COSTO if omitir_activo is None else omitir_activo
    if not flag or not nombre_clasificador:
        return False
    texto = str(nombre_clasificador).strip().upper()
    return any(p in texto for p in PATRONES_CLASIFICADORES_OMITIDOS)


def extraer_padres_e_hijos(
    clasificadores_dict: dict[str, Any],
    filtrar_omitidos: bool = True,
    omitir_activo: bool | None = None,
) -> list[tuple[str, list[str]]]:
    """
    Extrae la lista de tuplas (padre, lista_hijos) a partir de la estructura arborescente.
    Excluye temporalmente OBRAS y CENTROS DE COSTOS si filtrar_omitidos es True.
    """
    resultado: list[tuple[str, list[str]]] = []
    if not isinstance(clasificadores_dict, dict):
        return resultado

    def recorrer(nodo: Any) -> None:
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if filtrar_omitidos and es_clasificador_omitido(clave, omitir_activo=omitir_activo):
                    continue
                if isinstance(valor, list):
                    resultado.append((clave, valor))
                elif isinstance(valor, dict):
                    recorrer(valor)

    recorrer(clasificadores_dict)
    return resultado


def expandir_rangos(texto: str) -> list[str]:
    """Expande expresiones de rango como 'TAM-001 al TAM-015' conservando ceros a la izquierda."""
    patron = r"^([A-Za-z0-9_-]+?)(\d+)\s+al\s+([A-Za-z0-9_-]+?)?(\d+)$"
    match = re.match(patron, str(texto).strip(), re.IGNORECASE)
    if match:
        prefix1, num1_str, prefix2, num2_str = match.groups()
        prefijo = prefix1 if prefix1 else (prefix2 if prefix2 else "")
        num1 = int(num1_str)
        num2 = int(num2_str)
        padding = len(num1_str)
        inicio = min(num1, num2)
        fin = max(num1, num2)
        return [f"{prefijo}{str(i).zfill(padding)}" for i in range(inicio, fin + 1)]
    return [str(texto).strip()]


# ==============================================================================
# LECTURA Y GESTIÓN DE PLANTILLAS DE PUESTOS
# ==============================================================================

def leer_puestos_json() -> dict[str, Any]:
    """Lee el diccionario completo de puestos desde puestos.json local."""
    if not PUESTOS_JSON_PATH.exists():
        return {}
    try:
        with open(PUESTOS_JSON_PATH, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("puestos", {})
    except Exception as e:
        print(f"[PuestosService] Error al leer {PUESTOS_JSON_PATH}: {e}")
        return {}


def obtener_configuracion_puesto(nombre_puesto: str) -> ConfiguracionPuesto:
    """
    Busca la configuración de un puesto por coincidencia exacta o flexible.
    Consulta primero Firebase Firestore (con fallback automático a puestos.json local).
    """
    puesto_limpio = str(nombre_puesto).strip() if nombre_puesto else ""
    if not puesto_limpio:
        return ConfiguracionPuesto()

    # 1. Intentar desde Firebase Firestore
    try:
        from core.firebase_client import FirebaseClient
        cfg_cloud = FirebaseClient.obtener_puesto_por_nombre(puesto_limpio)
        if cfg_cloud:
            return ConfiguracionPuesto(
                nombre_puesto=cfg_cloud.get("nombre", puesto_limpio),
                niveles_asignados=cfg_cloud.get("niveles_asignados", []),
                grupos=cfg_cloud.get("grupos", []),
                clasificadores=cfg_cloud.get("clasificadores", {}),
                area_organizacional=cfg_cloud.get("area_organizacional", ""),
            )
    except Exception:
        pass

    # 2. Respaldo en puestos.json local
    puestos = leer_puestos_json()
    config = puestos.get(puesto_limpio)

    if not config:
        puesto_norm = puesto_limpio.upper()
        for clave, contenido in puestos.items():
            if clave.strip().upper() == puesto_norm:
                config = contenido
                puesto_limpio = clave
                break

    if config:
        return ConfiguracionPuesto(
            nombre_puesto=puesto_limpio,
            niveles_asignados=config.get("niveles_asignados", []),
            grupos=config.get("grupos", []),
            clasificadores=config.get("clasificadores", {}),
            area_organizacional=config.get("area_organizacional", ""),
        )

    print(f"[PuestosService] Aviso: El puesto '{puesto_limpio}' no está registrado.")
    return ConfiguracionPuesto(nombre_puesto=puesto_limpio)

