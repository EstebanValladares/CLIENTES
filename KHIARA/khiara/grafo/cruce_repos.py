"""
Motor de Cruce y Trazabilidad Multi-Repositorio (Inspirado en Microsoft GraphRAG).
Conecta múltiples proyectos locales en un Grafo de Conocimiento Unificado,
identificando tablas compartidas, módulos comunes y flujos de datos inter-repositorio.
"""

from typing import Dict, Any, List, Optional
import networkx as nx
from khiara.grafo.red import RedConocimiento


class CruceMultiRepositorio:
    def __init__(self, red: RedConocimiento):
        self.red = red

    def detectar_y_enlazar_intersecciones(self) -> Dict[str, Any]:
        """
        Escanea todos los proyectos registrados en el grafo y crea relaciones
        cruzadas entre ellos (tablas compartidas, esquemas JSON y módulos).
        """
        g = self.red.grafo
        proyectos = [n for n, attr in g.nodes(data=True) if attr.get("tipo") == "PROYECTO"]

        if len(proyectos) < 2:
            return {
                "ok": True,
                "mensaje": f"Se necesitan al menos 2 proyectos indexados para cruzar. Actualmente hay {len(proyectos)}.",
                "total_proyectos": len(proyectos),
                "intersecciones_creadas": 0
            }

        tablas_por_proyecto: Dict[str, Dict[str, str]] = {}
        archivos_por_proyecto: Dict[str, Dict[str, str]] = {}

        for p in proyectos:
            tablas_por_proyecto[p] = {}
            archivos_por_proyecto[p] = {}
            # Obtener descendientes
            descendientes = nx.descendants(g, p)
            for d in descendientes:
                tipo = g.nodes[d].get("tipo")
                nombre = g.nodes[d].get("nombre", "")
                if tipo == "TABLA_DB":
                    tablas_por_proyecto[p][nombre.lower()] = d
                elif tipo == "ARCHIVO":
                    archivos_por_proyecto[p][nombre.lower()] = d

        intersecciones = 0
        detalles_cruce = []

        # Comparar pares de proyectos
        lista_proys = list(tablas_por_proyecto.keys())
        for i in range(len(lista_proys)):
            for j in range(i + 1, len(lista_proys)):
                p1, p2 = lista_proys[i], lista_proys[j]
                
                # Cruce de Tablas
                t1 = set(tablas_por_proyecto[p1].keys())
                t2 = set(tablas_por_proyecto[p2].keys())
                comunes_tablas = t1.intersection(t2)

                for t_name in comunes_tablas:
                    nodo_t1 = tablas_por_proyecto[p1][t_name]
                    nodo_t2 = tablas_por_proyecto[p2][t_name]
                    self.red.agregar_relacion(nodo_t1, nodo_t2, "TABLA_COMPARTIDA")
                    intersecciones += 1
                    detalles_cruce.append(f"Tabla compartida '{t_name}' entre {p1} y {p2}")

                # Cruce de nombres de archivos clave (ej. config.py, database.py, .env)
                a1 = set(archivos_por_proyecto[p1].keys())
                a2 = set(archivos_por_proyecto[p2].keys())
                archivos_clave = {"config.py", "database.py", "db.py", "settings.py", "models.py", "auth.py"}
                comunes_arch = a1.intersection(a2).intersection(archivos_clave)

                for a_name in comunes_arch:
                    nodo_a1 = archivos_por_proyecto[p1][a_name]
                    nodo_a2 = archivos_por_proyecto[p2][a_name]
                    self.red.agregar_relacion(nodo_a1, nodo_a2, "MODULO_HOMOLOGO")
                    intersecciones += 1
                    detalles_cruce.append(f"Módulo homólogo '{a_name}' entre {p1} y {p2}")

        if intersecciones > 0:
            self.red.guardar()

        return {
            "ok": True,
            "total_proyectos": len(proyectos),
            "intersecciones_creadas": intersecciones,
            "detalles": detalles_cruce
        }

    def trazar_camino_entre_entidades(self, entidad_origen: str, entidad_destino: str) -> Dict[str, Any]:
        """
        Encuentra cómo viaja o se conecta la información entre dos proyectos o entidades
        usando el algoritmo de camino más corto en el Grafo Unificado.
        """
        g = self.red.grafo
        # Buscar nodos más parecidos
        nodos_origen = [n for n in g.nodes if entidad_origen.lower() in n.lower()]
        nodos_destino = [n for n in g.nodes if entidad_destino.lower() in n.lower()]

        if not nodos_origen:
            return {"ok": False, "error": f"No se encontró la entidad de origen '{entidad_origen}' en el grafo."}
        if not nodos_destino:
            return {"ok": False, "error": f"No se encontró la entidad de destino '{entidad_destino}' en el grafo."}

        # Convertir temporalmente a no dirigido para buscar camino bidireccional
        undirected_g = g.to_undirected()

        nodo_a = nodos_origen[0]
        nodo_b = nodos_destino[0]

        try:
            camino = nx.shortest_path(undirected_g, source=nodo_a, target=nodo_b)
            pasos = []
            for i in range(len(camino) - 1):
                u, v = camino[i], camino[i + 1]
                # Buscar datos de la arista
                rel = g.get_edge_data(u, v, default=g.get_edge_data(v, u, default={})).get("relacion", "CONECTADO_CON")
                pasos.append(f"({g.nodes[u].get('tipo', 'NODO')}) {u} --[{rel}]--> ({g.nodes[v].get('tipo', 'NODO')}) {v}")

            return {
                "ok": True,
                "origen": nodo_a,
                "destino": nodo_b,
                "longitud_saltos": len(camino) - 1,
                "ruta_nodos": camino,
                "pasos_explicados": pasos
            }
        except nx.NetworkXNoPath:
            return {
                "ok": False,
                "error": f"No existe una ruta directa conectada en el grafo entre '{nodo_a}' y '{nodo_b}'. Prueba indexar repositorios intermedios."
            }
        except Exception as e:
            return {"ok": False, "error": f"Error buscando camino en grafo: {str(e)}"}
