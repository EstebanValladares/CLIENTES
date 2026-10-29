"""
Módulo de Auditoría y Bitácoras para el flujo de Usuarios y Clasificadores.
Gestiona el registro de fallos en fallos_clasificadores.jsonl y la bitácora de ejecuciones.
"""
import datetime
import json
import os
import re
from typing import Any

from USUARIOS.selectores import (
    FALLOS_CLASIFICADORES_JSONL,
    LOGGER_DIR,
    REGISTRO_USUARIOS_JSONL,
)


def _asegurar_directorio_logger() -> None:
    os.makedirs(LOGGER_DIR, exist_ok=True)


def registrar_fallo_clasificador(
    datos_empleado: Any,
    tipo_clasificador: str,
    nombre_clasificador: str,
    detalle_error: str = "",
) -> None:
    """Guarda en fallos_clasificadores.jsonl un registro detallado de un clasificador no encontrado."""
    try:
        _asegurar_directorio_logger()
        if isinstance(datos_empleado, str):
            nombre_completo = datos_empleado.strip()
        elif isinstance(datos_empleado, dict):
            nom = datos_empleado.get("Nombre", "") or datos_empleado.get("nombre", "")
            ape = datos_empleado.get("Apellidos", "") or datos_empleado.get("apellidos", "")
            nombre_completo = f"{nom} {ape}".strip() or "Sin Nombre"
        elif hasattr(datos_empleado, "nombre_completo"):
            nombre_completo = datos_empleado.nombre_completo
        else:
            nombre_completo = str(datos_empleado or "Sin Nombre")

        registro = {
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": nombre_completo,
            "tipo_clasificador": str(tipo_clasificador).strip(),
            "nombre_clasificador": str(nombre_clasificador).strip(),
            "detalle_error": str(detalle_error).strip(),
        }

        with open(FALLOS_CLASIFICADORES_JSONL, mode="a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

        print(f"[BITACORA FALLO] Registrado -> Usuario: '{nombre_completo}' | Tipo: '{tipo_clasificador}' | Hijo: '{nombre_clasificador}'")
    except Exception as e:
        print(f"[BITACORA ERROR] No se pudo guardar fallo: {e}")


def limpiar_fallos_resueltos(nombre_usuario: str) -> None:
    """Elimina del archivo de fallos los registros resueltos de nombre_usuario."""
    try:
        if not FALLOS_CLASIFICADORES_JSONL.exists():
            return

        with open(FALLOS_CLASIFICADORES_JSONL, "r", encoding="utf-8") as f:
            lineas = [l for l in f if l.strip()]

        nombre_norm = str(nombre_usuario).strip().upper()
        nuevas: list[str] = []
        for line in lineas:
            try:
                reg = json.loads(line)
                u = str(reg.get("usuario", "")).strip().upper()
                if u != nombre_norm:
                    nuevas.append(line)
            except Exception:
                nuevas.append(line)

        with open(FALLOS_CLASIFICADORES_JSONL, "w", encoding="utf-8") as f:
            f.writelines(nuevas)
    except Exception as e:
        print(f"[BITACORA ERROR] Fallo al limpiar bitácora: {e}")


def registrar_log_usuario(
    driver: Any,
    datos_empleado: Any,
    id_forzado: str | None = None,
    url_forzada: str | None = None,
) -> None:
    """Registra la bitácora del usuario procesado en registro_usuarios.jsonl."""
    try:
        _asegurar_directorio_logger()

        url_actual = url_forzada if url_forzada else "No disponible"
        if not url_forzada and driver:
            try:
                url_actual = driver.current_url
            except Exception:
                pass

        if id_forzado:
            id_usuario = str(id_forzado)
        else:
            m = re.search(r"/usuarios/(\d+)", url_actual) or re.search(r"(\d{3,5})", url_actual)
            id_usuario = m.group(1) if m else "No detectado"

        nom = datos_empleado.get("Nombre", "") or datos_empleado.get("nombre", "") if isinstance(datos_empleado, dict) else ""
        ape = datos_empleado.get("Apellidos", "") or datos_empleado.get("apellidos", "") if isinstance(datos_empleado, dict) else ""
        nombre_completo = f"{nom} {ape}".strip() or "Sin Nombre"

        registro = {
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_usuario": id_usuario,
            "url_actual": url_actual,
            "nombre_completo": nombre_completo,
            "puesto": datos_empleado.get("Posicion", "") if isinstance(datos_empleado, dict) else "",
        }

        with open(REGISTRO_USUARIOS_JSONL, mode="a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[BITACORA ERROR] No se pudo guardar bitácora de usuario: {e}")

