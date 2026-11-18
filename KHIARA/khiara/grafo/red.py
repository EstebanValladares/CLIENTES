"""
Motor de Grafos de Conocimiento de KHIARA (NetworkX + Persistencia JSON).
Permite modelar entidades, relaciones, jerarquías de proyectos y conexiones lógicas.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import networkx as nx
from khiara.core.config import GRAFO_DEFAULT_FILE


class RedConocimiento:
    def __init__(self, archivo_persistencia: Optional[Path] = None):
        self.archivo = archivo_persistencia or GRAFO_DEFAULT_FILE
        self.grafo = nx.DiGraph()
        self.cargar()

    def agregar_nodo(self, nodo_id: str, tipo: str, datos: Optional[Dict[str, Any]] = None):
        """Agrega o actualiza un nodo con sus metadatos (ej. Proyecto, Archivo, Tabla, Función)."""
        attrs = {"tipo": tipo}
        if datos:
            attrs.update(datos)
        self.grafo.add_node(nodo_id, **attrs)

    def agregar_relacion(self, origen_id: str, destino_id: str, relacion: str, peso: float = 1.0):
        """Crea una conexión dirigida entre dos nodos (ej. CONTIENE, CONSULTA, IMPORTA)."""
        self.grafo.add_edge(origen_id, destino_id, relacion=relacion, peso=peso)

    def buscar_nodos(self, query: str, tipo: Optional[str] = None, limite: int = 10) -> List[Dict[str, Any]]:
        """Busca nodos por coincidencias en el ID o sus atributos."""
        q = query.lower()
        resultados = []
        for n, d in self.grafo.nodes(data=True):
            if tipo and d.get("tipo") != tipo:
                continue
            texto_nodo = f"{n} {json.dumps(d, ensure_ascii=False)}".lower()
            if q in texto_nodo:
                res = {"id": n, **d}
                resultados.append(res)
                if len(resultados) >= limite:
                    break
        return resultados

    def obtener_vecinos(self, nodo_id: str) -> Dict[str, Any]:
        """Obtiene las conexiones salientes y entrantes de un nodo."""
        if nodo_id not in self.grafo:
            return {"error": f"Nodo '{nodo_id}' no encontrado"}
        salientes = []
        for _, dest, data in self.grafo.out_edges(nodo_id, data=True):
            dest_data = self.grafo.nodes[dest]
            salientes.append({"destino": dest, "relacion": data.get("relacion"), "tipo": dest_data.get("tipo")})
        entrantes = []
        for orig, _, data in self.grafo.in_edges(nodo_id, data=True):
            orig_data = self.grafo.nodes[orig]
            entrantes.append({"origen": orig, "relacion": data.get("relacion"), "tipo": orig_data.get("tipo")})
        return {
            "nodo": nodo_id,
            "atributos": self.grafo.nodes[nodo_id],
            "salientes": salientes,
            "entrantes": entrantes
        }

    def metricas(self) -> Dict[str, Any]:
        """Estadísticas generales de la red de conocimiento."""
        conteo_tipos = {}
        for _, d in self.grafo.nodes(data=True):
            t = d.get("tipo", "general")
            conteo_tipos[t] = conteo_tipos.get(t, 0) + 1
        return {
            "total_nodos": self.grafo.number_of_nodes(),
            "total_relaciones": self.grafo.number_of_edges(),
            "nodos_por_tipo": conteo_tipos
        }

    def guardar(self):
        """Serializa el grafo a formato JSON compatible."""
        data = nx.node_link_data(self.grafo)
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def cargar(self):
        """Carga el grafo desde disco si existe."""
        if self.archivo.exists():
            try:
                with open(self.archivo, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.grafo = nx.node_link_graph(data)
            except Exception:
                self.grafo = nx.DiGraph()
