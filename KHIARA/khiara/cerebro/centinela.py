"""
Centinela Proactivo en Segundo Plano para KHIARA (Background Watcher).
Vigila directorios de proyectos registrados, detecta cambios o adiciones
de archivos y genera auditorías/alertas proactivas para el usuario.
"""

import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from khiara.core.config import MEMORIA_DIR
from khiara.grafo.red import RedConocimiento
from khiara.grafo.repo_map import RepoMap


class CentinelaProactivo:
    def __init__(self, red: Optional[RedConocimiento] = None, intervalo_segundos: int = 15):
        self.intervalo = intervalo_segundos
        self.rutas_vigiladas: List[str] = []
        self.archivo_alertas = MEMORIA_DIR / "alertas_centinela.json"
        self.activo = False
        self._hilo: Optional[threading.Thread] = None
        self.red = red or RedConocimiento()
        self.repo_map = RepoMap(self.red)
        self.alertas: List[Dict[str, Any]] = []
        self._cargar_alertas()

    def _cargar_alertas(self):
        if self.archivo_alertas.exists():
            try:
                with open(self.archivo_alertas, "r", encoding="utf-8") as f:
                    self.alertas = json.load(f)
            except Exception:
                self.alertas = []

    def _guardar_alertas(self):
        try:
            with open(self.archivo_alertas, "w", encoding="utf-8") as f:
                json.dump(self.alertas[-50:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def registrar_ruta(self, ruta: str) -> bool:
        p = Path(ruta).resolve()
        if p.exists() and p.is_dir() and str(p) not in self.rutas_vigiladas:
            self.rutas_vigiladas.append(str(p))
            # Inicializar hashes
            self.repo_map.detectar_cambios_en_directorio(str(p))
            return True
        return False

    def iniciar(self):
        if self.activo:
            return
        self.activo = True
        self._hilo = threading.Thread(target=self._bucle_vigilancia, daemon=True)
        self._hilo.start()

    def detener(self):
        self.activo = False

    def _bucle_vigilancia(self):
        while self.activo:
            for ruta in list(self.rutas_vigiladas):
                try:
                    cambios = self.repo_map.detectar_cambios_en_directorio(ruta)
                    if cambios.get("archivos_nuevos") or cambios.get("archivos_modificados"):
                        alerta = {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "proyecto": cambios.get("proyecto"),
                            "nuevos": cambios.get("archivos_nuevos", []),
                            "modificados": cambios.get("archivos_modificados", []),
                            "leida": False
                        }
                        self.alertas.append(alerta)
                        self._guardar_alertas()
                except Exception:
                    pass
            time.sleep(self.intervalo)

    def obtener_alertas_recientes(self, solo_no_leidas: bool = True) -> List[Dict[str, Any]]:
        if solo_no_leidas:
            no_leidas = [a for a in self.alertas if not a.get("leida", False)]
            for a in no_leidas:
                a["leida"] = True
            self._guardar_alertas()
            return no_leidas
        return self.alertas[-10:]

    def estado(self) -> Dict[str, Any]:
        return {
            "activo": self.activo,
            "intervalo_segundos": self.intervalo,
            "total_rutas_vigiladas": len(self.rutas_vigiladas),
            "rutas": self.rutas_vigiladas,
            "total_alertas_registradas": len(self.alertas)
        }
