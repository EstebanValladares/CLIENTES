"""
Memoria Vectorial Semántica y RAG Local para KHIARA.
Permite almacenar fragmentos de código, documentación, requerimientos y
memorias de proyectos en representaciones vectoriales para recuperarlas
por similitud semántica mediante búsqueda por coseno (NumPy + Gemini Embeddings).
"""

import os
import json
import math
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

from khiara.core.config import GEMINI_API_KEY, MEMORIA_DIR


class MemoriaVectorial:
    def __init__(self, ruta_archivo: Optional[str] = None):
        if ruta_archivo:
            self.archivo_memoria = Path(ruta_archivo).resolve()
        else:
            self.archivo_memoria = MEMORIA_DIR / "memoria_vectorial.json"

        self.archivo_memoria.parent.mkdir(parents=True, exist_ok=True)
        self.documentos: Dict[str, Dict[str, Any]] = {}
        self._cargar_memoria()

    def _cargar_memoria(self):
        if self.archivo_memoria.exists():
            try:
                with open(self.archivo_memoria, "r", encoding="utf-8") as f:
                    self.documentos = json.load(f)
            except Exception:
                self.documentos = {}

    def _guardar_memoria(self):
        try:
            with open(self.archivo_memoria, "w", encoding="utf-8") as f:
                json.dump(self.documentos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AVISO] No se pudo guardar memoria vectorial: {e}")

    def _generar_embedding(self, texto: str) -> List[float]:
        """
        Genera el vector de embedding.
        Si hay GEMINI_API_KEY disponible, usa el modelo 'text-embedding-004' de Google GenAI.
        Si no hay API key o hay error de red, utiliza un vectorizador semántico local de contingencia.
        """
        if GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                res = client.models.embed_content(
                    model="text-embedding-004",
                    contents=texto[:2000]
                )
                if hasattr(res, "embedding") and hasattr(res.embedding, "values"):
                    return list(res.embedding.values)
                elif hasattr(res, "embeddings") and res.embeddings:
                    return list(res.embeddings[0].values)
            except Exception:
                pass

        # Vectorizador local alternativo (Hashing n-grams de 128 dimensiones normalizado)
        dim = 128
        vec = np.zeros(dim, dtype=np.float32)
        palabras = re.findall(r"\w+", texto.lower())
        if not palabras:
            return vec.tolist()

        for i, p in enumerate(palabras):
            idx = abs(hash(p)) % dim
            vec[idx] += 1.0 / (1.0 + math.log1p(i))
            # bi-gram
            if i > 0:
                bi_idx = abs(hash(f"{palabras[i-1]}_{p}")) % dim
                vec[bi_idx] += 1.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def guardar_recuerdo(self, id_doc: str, texto: str, metadatos: Optional[Dict[str, Any]] = None) -> bool:
        """Registra un nuevo fragmento de información, código o memoria en la base vectorial."""
        if not texto.strip():
            return False

        vector = self._generar_embedding(texto)
        self.documentos[id_doc] = {
            "id": id_doc,
            "texto": texto,
            "metadatos": metadatos or {},
            "vector": vector,
            "tamano_caracteres": len(texto)
        }
        self._guardar_memoria()
        return True

    def buscar_similares(self, consulta: str, top_k: int = 5, umbral_minimo: float = 0.25) -> List[Dict[str, Any]]:
        """
        Busca los documentos y recuerdos más relevantes para una consulta usando similitud de coseno.
        """
        if not self.documentos or not consulta.strip():
            return []

        q_vec = np.array(self._generar_embedding(consulta), dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        resultados = []
        for doc_id, doc in self.documentos.items():
            d_vec = np.array(doc["vector"], dtype=np.float32)
            d_norm = np.linalg.norm(d_vec)
            if d_norm == 0 or len(d_vec) != len(q_vec):
                continue

            similitud = float(np.dot(q_vec, d_vec) / (q_norm * d_norm))
            if similitud >= umbral_minimo:
                resultados.append({
                    "id": doc_id,
                    "similitud": round(similitud, 4),
                    "texto": doc["texto"],
                    "metadatos": doc.get("metadatos", {})
                })

        resultados.sort(key=lambda x: x["similitud"], reverse=True)
        return resultados[:top_k]

    def total_recuerdos(self) -> int:
        return len(self.documentos)

    def limpiar(self):
        self.documentos = {}
        self._guardar_memoria()
