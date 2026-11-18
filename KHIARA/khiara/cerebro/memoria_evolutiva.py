"""
Memoria Evolutiva y Motor de Reglas Persistentes de KHIARA (Inspirado en Mem0).
Aprende automáticamente reglas de negocio, correcciones de datos y preferencias
del usuario para que NUNCA se olviden entre sesiones y se inyecten de forma activa
en el razonamiento del agente.
"""

import os
import json
import uuid
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from khiara.core.config import MEMORIA_DIR


class MemoriaEvolutiva:
    CATEGORIAS_VALIDAS = {
        "REGLA_NEGOCIO",      # ej: "En la obra AUS el presupuesto es en USD"
        "PREFERENCIA_USUARIO",# ej: "Mostrar importes en MXN y con formato de tabla"
        "CORRECCION_DATO",    # ej: "El ID de Juan Perez es 104"
        "HECHO_SISTEMA"       # ej: "Enkontrol usa puerto 1433 en EK10_PROD"
    }

    def __init__(self, ruta_archivo: Optional[str] = None):
        if ruta_archivo:
            self.archivo = Path(ruta_archivo).resolve()
        else:
            self.archivo = MEMORIA_DIR / "reglas_evolutivas.json"

        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        self.reglas: Dict[str, Dict[str, Any]] = {}
        self._cargar_reglas()

    def _cargar_reglas(self):
        if self.archivo.exists():
            try:
                with open(self.archivo, "r", encoding="utf-8") as f:
                    self.reglas = json.load(f)
            except Exception:
                self.reglas = {}

    def _guardar_reglas(self):
        try:
            with open(self.archivo, "w", encoding="utf-8") as f:
                json.dump(self.reglas, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AVISO] Error guardando reglas evolutivas: {e}")

    def registrar_regla(
        self,
        texto_regla: str,
        categoria: str = "REGLA_NEGOCIO",
        palabras_clave: Optional[List[str]] = None,
        proyecto_asociado: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Almacena una nueva regla permanente aprendida de la interacción con el usuario.
        """
        texto_clean = texto_regla.strip()
        if not texto_clean:
            return {"ok": False, "error": "La regla no puede estar vacía."}

        cat = categoria.upper() if categoria.upper() in self.CATEGORIAS_VALIDAS else "REGLA_NEGOCIO"

        # Extraer palabras clave automáticamente si no vienen dadas
        if not palabras_clave:
            tokens = re.findall(r"\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b", texto_clean.lower())
            stop_words = {"para", "como", "siempre", "cuando", "este", "esta", "todo", "toda", "pero", "sobre", "entre"}
            keywords = [t for t in set(tokens) if t not in stop_words]
        else:
            keywords = [k.lower().strip() for k in palabras_clave]

        id_regla = f"RULE_{uuid.uuid4().hex[:8]}"
        registro = {
            "id": id_regla,
            "categoria": cat,
            "regla": texto_clean,
            "palabras_clave": keywords,
            "proyecto": proyecto_asociado or "GLOBAL",
            "creado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
            "veces_aplicada": 0
        }

        self.reglas[id_regla] = registro
        self._guardar_reglas()

        return {"ok": True, "id": id_regla, "registro": registro}

    def buscar_reglas_relevantes(self, consulta_o_contexto: str, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Encuentra las reglas activas que aplican a la consulta actual según palabras clave y temas.
        """
        if not self.reglas or not consulta_o_contexto.strip():
            return []

        tokens_consulta = set(re.findall(r"\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b", consulta_o_contexto.lower()))
        coincidencias = []

        for r_id, r in self.reglas.items():
            keys_regla = set(r.get("palabras_clave", []))
            # Calcular intersección de palabras clave
            interseccion = tokens_consulta.intersection(keys_regla)
            puntuacion = len(interseccion)

            # Buscar si el texto de la regla contiene términos directos
            for t in tokens_consulta:
                if t in r["regla"].lower():
                    puntuacion += 1.5

            if puntuacion > 0:
                coincidencias.append((puntuacion, r))

        coincidencias.sort(key=lambda x: x[0], reverse=True)

        resultados = []
        for _, regla in coincidencias[:limite]:
            # Marcar que se aplicó
            regla["veces_aplicada"] = regla.get("veces_aplicada", 0) + 1
            resultados.append(regla)

        if resultados:
            self._guardar_reglas()

        return resultados

    def formatear_bloque_contexto(self, consulta: str) -> str:
        """
        Genera el bloque de texto con reglas que se inyecta directamente
        en el pensamiento de Gemini antes de procesar la respuesta.
        """
        reglas_activas = self.buscar_reglas_relevantes(consulta, limite=4)
        if not reglas_activas:
            return ""

        lineas = ["\n[REGLAS Y APRENDIZAJES EVOLUTIVOS DE ESTEBAN A CONSIDERAR]:"]
        for r in reglas_activas:
            lineas.append(f"• [{r['categoria']}] {r['regla']}")
        return "\n".join(lineas)

    def listar_todas(self) -> List[Dict[str, Any]]:
        return list(self.reglas.values())

    def eliminar_regla(self, id_regla: str) -> bool:
        if id_regla in self.reglas:
            del self.reglas[id_regla]
            self._guardar_reglas()
            return True
        return False
