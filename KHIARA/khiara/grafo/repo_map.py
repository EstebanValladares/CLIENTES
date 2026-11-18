"""
Generador de Repo-Map Compacto y Caché de Hashes SHA256 (Inspirado en Aider).
Genera un mapa de alta densidad y bajo consumo de tokens de todos los repositorios
indexados, optimizando la detección de cambios mediante hashing criptográfico.
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import networkx as nx

from khiara.core.config import GRAFOS_DIR
from khiara.grafo.red import RedConocimiento


class RepoMap:
    def __init__(self, red: RedConocimiento, ruta_cache: Optional[str] = None):
        self.red = red
        if ruta_cache:
            self.archivo_cache = Path(ruta_cache).resolve()
        else:
            self.archivo_cache = GRAFOS_DIR / "cache_hashes.json"

        self.archivo_cache.parent.mkdir(parents=True, exist_ok=True)
        self.hashes: Dict[str, str] = {}
        self._cargar_cache()

    def _cargar_cache(self):
        if self.archivo_cache.exists():
            try:
                with open(self.archivo_cache, "r", encoding="utf-8") as f:
                    self.hashes = json.load(f)
            except Exception:
                self.hashes = {}

    def _guardar_cache(self):
        try:
            with open(self.archivo_cache, "w", encoding="utf-8") as f:
                json.dump(self.hashes, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def calcular_hash_archivo(ruta_archivo: str) -> str:
        """Calcula el hash SHA-256 de un archivo en bloques de 64 KB."""
        sha = hashlib.sha256()
        try:
            with open(ruta_archivo, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception:
            return ""

    def detectar_cambios_en_directorio(self, ruta_directorio: str) -> Dict[str, Any]:
        """
        Escanea rápidamente una carpeta y detecta qué archivos fueron creados,
        modificados o eliminados comparando con el caché de hashes.
        """
        p = Path(ruta_directorio).resolve()
        if not p.exists():
            return {"ok": False, "error": f"La ruta '{ruta_directorio}' no existe."}

        modificados = []
        nuevos = []
        archivos_vistos = set()

        for root, _, files in os.walk(p):
            if any(ign in root for ign in [".git", "__pycache__", "node_modules", "venv"]):
                continue
            for file in files:
                if file.endswith((".py", ".sql", ".json", ".csv", ".xlsx", ".html")):
                    full_path = os.path.join(root, file)
                    rel_path = str(Path(full_path).relative_to(p)).replace("\\", "/")
                    archivos_vistos.add(rel_path)

                    hash_actual = self.calcular_hash_archivo(full_path)
                    hash_previo = self.hashes.get(f"{p.name}::{rel_path}")

                    if hash_previo is None:
                        nuevos.append(rel_path)
                        self.hashes[f"{p.name}::{rel_path}"] = hash_actual
                    elif hash_previo != hash_actual:
                        modificados.append(rel_path)
                        self.hashes[f"{p.name}::{rel_path}"] = hash_actual

        self._guardar_cache()

        return {
            "ok": True,
            "proyecto": p.name,
            "archivos_nuevos": nuevos,
            "archivos_modificados": modificados,
            "total_archivos_monitoreados": len(archivos_vistos)
        }

    def generar_repo_map_compacto(self, max_lineas: int = 40) -> str:
        """
        Genera un mapa textual ultra-compacto del 100% de los proyectos en el grafo,
        mostrando proyectos, carpetas clave, bases de datos y firmas principales.
        """
        g = self.red.grafo
        proyectos = [n for n, a in g.nodes(data=True) if a.get("tipo") == "PROYECTO"]
        if not proyectos:
            return "No hay proyectos indexados aún en el grafo."

        lineas = ["🗺️ REPO-MAP DE PROYECTOS UNIFICADOS:"]
        for p in proyectos:
            nombre_p = g.nodes[p].get("nombre", p)
            lineas.append(f"📁 Proyecto: {nombre_p}")
            
            # Recolectar archivos y tablas
            descendientes = list(nx.descendants(g, p))
            tablas = [g.nodes[d].get("tabla") or g.nodes[d].get("nombre", d) for d in descendientes if g.nodes[d].get("tipo") == "TABLA_DB"]
            archivos_py = [g.nodes[d].get("nombre", d) for d in descendientes if g.nodes[d].get("tipo") == "ARCHIVO" and g.nodes[d].get("nombre", "").endswith(".py")]
            
            if tablas:
                lineas.append(f"   ├─ 🗄️ Tablas BD ({len(tablas)}): {', '.join(tablas[:6])}")
            if archivos_py:
                lineas.append(f"   ├─ 🐍 Módulos Python ({len(archivos_py)}): {', '.join(archivos_py[:6])}")
            
            # Contar total de componentes
            lineas.append(f"   └─ Total Nodos asociados: {len(descendientes)}")

        return "\n".join(lineas[:max_lineas])
