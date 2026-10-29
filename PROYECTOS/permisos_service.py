"""
Módulo de Gestión de Permisos y Reglas de Negocio para PROYECTOS.
Centraliza la carga, normalización y filtrado de obras y usuarios protegidos.
"""
import json
import os
import unicodedata
from pathlib import Path
from typing import Iterable, List, Optional, Set

from PROYECTOS.selectores import (
    RUTA_OBRAS_JSON,
    RUTA_USUARIOS_TXT,
    USUARIOS_PROTEGIDOS_BASE,
)


def normalizar_texto(texto: Optional[str]) -> str:
    """
    Elimina acentos, convierte a mayúsculas y normaliza espacios múltiples
    para comparaciones seguras de nombres de usuarios y obras.
    """
    if not texto:
        return ""
    sin_acentos = (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ASCII", "ignore")
        .decode("utf-8")
    )
    return " ".join(sin_acentos.strip().upper().split())


def cargar_obras(
    lista_obras: Optional[Iterable[str]] = None,
    ruta_json: Optional[str | Path] = None,
) -> List[str]:
    """
    Obtiene la lista de obras a procesar desde un iterable en memoria
    o desde el archivo obras_permisos.json.
    """
    if lista_obras is not None:
        return [str(o).strip().upper() for o in lista_obras if str(o).strip()]

    ruta = Path(ruta_json) if ruta_json else RUTA_OBRAS_JSON
    if ruta.exists():
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
                if isinstance(datos, list):
                    return [str(o).strip().upper() for o in datos if str(o).strip()]
        except Exception as e:
            print(f"[PermisosService] Error leyendo {ruta}: {e}")
    return []


def cargar_usuarios_protegidos(
    lista_personalizada: Optional[Iterable[str]] = None,
    ruta_txt: Optional[str | Path] = None,
    imprimir_resumen: bool = True,
) -> Set[str]:
    """
    Carga y normaliza el conjunto de usuarios protegidos.
    Combina USUARIOS_PROTEGIDOS_BASE con ENKONTROL.TXT.
    """
    if lista_personalizada is not None:
        return {
            normalizar_texto(u)
            for u in lista_personalizada
            if normalizar_texto(u)
        }

    usuarios_protegidos = {normalizar_texto(u) for u in USUARIOS_PROTEGIDOS_BASE}

    ruta = Path(ruta_txt) if ruta_txt else RUTA_USUARIOS_TXT
    if ruta.exists():
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                for linea in f:
                    nom = normalizar_texto(linea)
                    if nom:
                        usuarios_protegidos.add(nom)
        except Exception as e:
            print(f"[PermisosService] Error leyendo {ruta}: {e}")

    if imprimir_resumen:
        print(
            f"Lista de usuarios protegidos activada ({len(usuarios_protegidos)} usuarios):",
            flush=True,
        )
        for u in sorted(usuarios_protegidos):
            print(f"  • {u}", flush=True)

    return usuarios_protegidos


def es_usuario_protegido(nombre_usuario: str, usuarios_protegidos: Set[str]) -> bool:
    """Verifica si un nombre de usuario coincide con algún usuario de la lista protegida."""
    nombre_norm = normalizar_texto(nombre_usuario)
    if not nombre_norm:
        return False
    return any(
        protegido in nombre_norm or nombre_norm in protegido
        for protegido in usuarios_protegidos
    )

