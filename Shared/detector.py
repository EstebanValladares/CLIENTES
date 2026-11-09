"""
Shared Domain: Detector y Analizador de Cambios de Versión.
Monitorea continuamente si el código Master ha recibido modificaciones respecto
a la última publicación oficial (.ultima_publicacion.json), alimentando la tarjeta
visual de la Torre ("CAMBIOS PENDIENTES" / "ACTUALIZADO").
"""
import os
import json
import time
import subprocess
from typing import Dict, Any, List
from Shared.config import BASE_DIR, CLIENT_DIR, META_PATH, es_modo_master, OC_SRC_DIR, OC_CLIENT_DIR, OC_META_PATH

def obtener_rutas_monitoreadas() -> List[str]:
    """Retorna la lista de rutas críticas que deben activar la sugerencia de actualización al modificarse."""
    rutas = [
        os.path.join(BASE_DIR, "api", "main.py"),
        os.path.join(BASE_DIR, "vue", "index.html"),
        os.path.join(BASE_DIR, "vue", "static", "js", "app.js"),
        os.path.join(BASE_DIR, "vue", "static", "css", "styles.css"),
        os.path.join(BASE_DIR, "USUARIOS", "data", "Usuarios.json"),
        os.path.join(BASE_DIR, "USUARIOS", "data", "puestos.json"),
        os.path.join(BASE_DIR, "OBRAS", "catalogo_obras.json"),
        os.path.join(BASE_DIR, "OBRAS", "obras.json"),
        os.path.join(BASE_DIR, "OBRAS", "GRUPO_INSUMOS_TIPO.json"),
        os.path.join(BASE_DIR, "data", "mapeo_lotes.db"),
    ]

    # Monitorear carpetas de código backend y vistas modulares
    carpetas_a_escanear = [
        os.path.join(BASE_DIR, "api"),
        os.path.join(BASE_DIR, "core"),
        os.path.join(BASE_DIR, "Shared"),
        os.path.join(BASE_DIR, "vue", "views"),
        os.path.join(BASE_DIR, "vue", "static", "js", "modules"),
    ]

    for c_path in carpetas_a_escanear:
        if os.path.exists(c_path):
            for root, _, files in os.walk(c_path):
                if "__pycache__" in root or ".git" in root:
                    continue
                for f in files:
                    if f.endswith((".py", ".js", ".html")):
                        rutas.append(os.path.join(root, f))

    return rutas

def obtener_estado_cliente() -> Dict[str, Any]:
    """
    Evalúa el estado de sincronización de la versión del equipo (CLIENTES).
    Genera el modelo de datos exacto que consume la tarjeta de la Torre:
    - Estado: 'CAMBIOS PENDIENTES' o 'ACTUALIZADO'
    - Tiempo transcurrido desde la última publicación
    - Commit actual del repositorio de clientes
    - Salud operativa
    """
    master = es_modo_master()
    desactualizado = False
    archivos_modificados = []
    ultima_fecha = "Pendiente"
    tiempo_str = "Sin publicar"
    commit_hash = "-"

    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
            last_pub_ts = meta.get("timestamp", 0)
            ultima_fecha = meta.get("fecha_hora", "-")
            commit_hash = meta.get("commit", "-")

            # Calcular tiempo transcurrido en formato amigable
            delta = time.time() - last_pub_ts
            if delta < 60:
                tiempo_str = "Hace unos segundos"
            elif delta < 3600:
                tiempo_str = f"Hace {int(delta // 60)} min"
            elif delta < 86400:
                tiempo_str = f"Hace {int(delta // 3600)} h"
            else:
                tiempo_str = f"Hace {int(delta // 86400)} d"

            # Verificar si algún archivo del Master fue modificado después de la última publicación
            if master:
                rutas = obtener_rutas_monitoreadas()
                for ruta in rutas:
                    if os.path.exists(ruta):
                        try:
                            mtime = os.path.getmtime(ruta)
                            if mtime > (last_pub_ts + 1.0):
                                desactualizado = True
                                archivos_modificados.append(os.path.basename(ruta))
                        except Exception:
                            pass

                # Obtener commit actual en la carpeta local de CLIENTES
                if os.path.exists(CLIENT_DIR):
                    try:
                        c_res = subprocess.run(
                            ["git", "rev-parse", "--short", "HEAD"],
                            cwd=CLIENT_DIR,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if c_res.returncode == 0 and c_res.stdout.strip():
                            commit_hash = c_res.stdout.strip()
                    except Exception:
                        pass

                desactualizado = len(archivos_modificados) > 0
        except Exception:
            desactualizado = False
    else:
        desactualizado = True if master else False

    if not os.path.exists(CLIENT_DIR) and master:
        desactualizado = True

    estado = "CAMBIOS PENDIENTES" if desactualizado else "ACTUALIZADO"

    return {
        "id": "CLIENTES",
        "nombre": "CLIENTES",
        "descripcion": "Versión Limpia / Equipo (Autónomo)",
        "icono": "fa-solid fa-users-gear",
        "salud": "100%" if not desactualizado else "85%",
        "estado": estado,
        "activo": True,
        "desactualizado": desactualizado,
        "archivos_pendientes": len(archivos_modificados),
        "archivos_detalle": archivos_modificados[:10],
        "es_master": master,
        "servicios": "GitHub / origin main",
        "ultima_publicacion": ultima_fecha,
        "tiempo_transcurrido": tiempo_str,
        "commit": commit_hash,
        "latencia_ms": 1,
        "uptime": tiempo_str
    }

def hay_cambios_pendientes() -> bool:
    """Verifica de forma rápida si hay cambios en Master pendientes de publicar."""
    st = obtener_estado_cliente()
    return bool(st.get("desactualizado"))

def obtener_rutas_monitoreadas_oc() -> List[str]:
    """Retorna las rutas monitoreadas de CONTROL_PAGOS_OC para detectar cambios."""
    rutas = []
    if not os.path.exists(OC_SRC_DIR):
        return rutas

    for root, _, files in os.walk(OC_SRC_DIR):
        if any(p in root for p in ["__pycache__", ".git", ".vscode", "datos"]):
            continue
        for f in files:
            if f.startswith("Docker") or f.startswith("docker") or f == ".dockerignore":
                continue
            if f.endswith((".py", ".html", ".js", ".css", ".sql", ".yml", ".yaml", ".env.example")):
                rutas.append(os.path.join(root, f))
    return rutas

def obtener_estado_oc_publicacion() -> Dict[str, Any]:
    """
    Monitorea si CONTROL_PAGOS_OC tiene cambios pendientes de publicar hacia CONTROL_PAGOS (Servidor).
    Retorna el estado de sincronización, commit y tiempo transcurrido.
    """
    master = es_modo_master()
    desactualizado = False
    archivos_modificados = []
    ultima_fecha = "Pendiente"
    tiempo_str = "Sin publicar"
    commit_hash = "-"

    if os.path.exists(OC_META_PATH):
        try:
            with open(OC_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
            last_pub_ts = meta.get("timestamp", 0)
            ultima_fecha = meta.get("fecha_hora", "-")
            commit_hash = meta.get("commit", "-")

            delta = time.time() - last_pub_ts
            if delta < 60:
                tiempo_str = "Hace unos segundos"
            elif delta < 3600:
                tiempo_str = f"Hace {int(delta // 60)} min"
            elif delta < 86400:
                tiempo_str = f"Hace {int(delta // 3600)} h"
            else:
                tiempo_str = f"Hace {int(delta // 86400)} d"

            if master:
                rutas = obtener_rutas_monitoreadas_oc()
                for ruta in rutas:
                    if os.path.exists(ruta):
                        try:
                            mtime = os.path.getmtime(ruta)
                            if mtime > (last_pub_ts + 1.0):
                                desactualizado = True
                                archivos_modificados.append(os.path.basename(ruta))
                        except Exception:
                            pass

                if os.path.exists(OC_CLIENT_DIR):
                    try:
                        c_res = subprocess.run(
                            ["git", "rev-parse", "--short", "HEAD"],
                            cwd=OC_CLIENT_DIR,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if c_res.returncode == 0 and c_res.stdout.strip():
                            commit_hash = c_res.stdout.strip()
                    except Exception:
                        pass

                desactualizado = len(archivos_modificados) > 0
        except Exception:
            desactualizado = False
    else:
        desactualizado = True if master and os.path.exists(OC_SRC_DIR) else False

    if not os.path.exists(OC_CLIENT_DIR) and master:
        desactualizado = True

    return {
        "desactualizado": desactualizado,
        "archivos_pendientes": len(archivos_modificados),
        "archivos_detalle": archivos_modificados[:10],
        "ultima_publicacion": ultima_fecha,
        "tiempo_transcurrido": tiempo_str,
        "commit": commit_hash,
        "destino": "CONTROL_PAGOS"
    }
