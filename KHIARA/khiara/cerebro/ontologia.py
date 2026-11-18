"""
Ontología de Negocio y Diccionario Semántico de KHIARA (La "Llave Maestra").
Permite a KHIARA comprender la jerga, reglas y equivalencias reales de la empresa
(Grupo Velas, Enkontrol, Aryve) sin adivinar:
- Escalatorias de precios
- Claves de posición (POS-XXXX)
- Homologación de lotes
- Catálogos de insumos y grupos
- Claves de obra (ej. AUS, ARE)
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from khiara.core.config import MEMORIA_DIR


class GlosarioNegocio:
    def __init__(self, ruta_archivo: Optional[str] = None):
        if ruta_archivo:
            self.archivo = Path(ruta_archivo).resolve()
        else:
            self.archivo = MEMORIA_DIR / "diccionario_negocio.json"

        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        self.terminos: Dict[str, Dict[str, Any]] = {}
        self._cargar_o_inicializar_glosario()

    def _cargar_o_inicializar_glosario(self):
        if self.archivo.exists():
            try:
                with open(self.archivo, "r", encoding="utf-8") as f:
                    self.terminos = json.load(f)
                    return
            except Exception:
                self.terminos = {}

        # Semilla con las reglas maestras de negocio
        self.terminos = {
            "POSICION": {
                "concepto": "Posición / Puesto de Usuario",
                "patron_clave": r"POS-\d+",
                "definicion": "Clave única de posición en Aryve / Enkontrol (ej. POS-1084). Representa el perfil, puesto y nivel de autorización de un usuario.",
                "sinonimos": ["posicion", "puesto", "clave usuario", "pos-"],
                "tablas_relacionadas": ["usuarios", "posiciones", "kontrol_posiciones"],
                "endpoints_relacionados": ["/api/usuarios/posiciones", "/api/posiciones/ultima"]
            },
            "ESCALATORIA": {
                "concepto": "Escalatoria de Precios",
                "patron_clave": r"escalatoria|variacion precio|ajuste precio",
                "definicion": "Variación porcentual o monetaria del costo de un insumo respecto a su precio base pactado. Se aplica por inflación o acuerdos comerciales de proveedor.",
                "sinonimos": ["escalatoria", "aumento de precio", "ajuste de precio", "diferencia precio", "precio base vs actual"],
                "tablas_relacionadas": ["escalatorias", "insumos_precios", "historico_costos"],
                "endpoints_relacionados": ["/api/escalatorias", "/api/insumos/escalatoria"]
            },
            "INSUMO": {
                "concepto": "Catálogo de Insumos y Grupos",
                "patron_clave": r"insumo|material|mano de obra|subcontrato|maquinaria",
                "definicion": "Elemento base del presupuesto de obra. Se clasifica en 4 grupos principales: Materiales (ej. cemento, block), Mano de Obra, Maquinaria y Subcontratos.",
                "sinonimos": ["insumo", "material", "grupo insumo", "catalogo insumos", "unidad de medida"],
                "tablas_relacionadas": ["insumos", "grupos_insumos", "precios_unitarios"],
                "endpoints_relacionados": ["/api/insumos/buscar", "/api/insumos/catalogo", "/api/insumos/grupos"]
            },
            "OBRA": {
                "concepto": "Clave y Administración de Obra",
                "patron_clave": r"\b[A-Z]{3,4}\b",
                "definicion": "Identificador de desarrollo o proyecto inmobiliario en Enkontrol (ej. AUS, ARE, BAL). Cada obra agrupa presupuestos, contratos y estimaciones.",
                "sinonimos": ["obra", "proyecto inmobiliario", "fraccionamiento", "clave obra"],
                "tablas_relacionadas": ["obras", "proyectos", "scco_obras"],
                "endpoints_relacionados": ["/api/obras/catalogo", "/api/obras/{clave}"]
            },
            "HOMOLOGACION_LOTES": {
                "concepto": "Homologación de Lotes (Enkontrol vs Aryve)",
                "patron_clave": r"homologacion|mapeo lotes|lote enkontrol",
                "definicion": "Equivalencia entre el identificador técnico de lote en el ERP Enkontrol y la nomenclatura comercial/operativa en Aryve (Manzana, Lote, Prototipo).",
                "sinonimos": ["homologacion", "mapeo de lotes", "lotes", "manzanas", "frentes"],
                "tablas_relacionadas": ["mapeo_lotes", "lotes_homologados", "frentes_obra"],
                "endpoints_relacionados": ["/api/lotes/homologados", "/api/lotes/mapeo"]
            },
            "ADITIVA": {
                "concepto": "Aditiva de Contrato / Presupuesto",
                "patron_clave": r"aditiva|ampliacion|extra volumen",
                "definicion": "Modificación al contrato que incrementa volumen de obra o precio, afectando el presupuesto base.",
                "sinonimos": ["aditiva", "ampliacion presupuesto", "volumen adicional"],
                "tablas_relacionadas": ["aditivas", "modificaciones_contrato"],
                "endpoints_relacionados": ["/api/contratos/aditivas"]
            }
        }
        self._guardar_glosario()

    def _guardar_glosario(self):
        try:
            with open(self.archivo, "w", encoding="utf-8") as f:
                json.dump(self.terminos, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def interpretar_consulta(self, consulta: str) -> Dict[str, Any]:
        """
        Analiza una pregunta en lenguaje natural y detecta conceptos clave,
        claves POS-XXXX, obras de 3 letras, tablas y endpoints sugeridos.
        """
        consulta_l = consulta.lower()
        conceptos_detectados = []
        claves_pos = re.findall(r"\bPOS-\d+\b", consulta, re.IGNORECASE)
        obras_posibles = [w for w in re.findall(r"\b[A-Z]{3,4}\b", consulta) if w not in {"PARA", "TODO", "ESTE", "SQL", "HTML", "JSON"}]

        for clave, t in self.terminos.items():
            if any(s in consulta_l for s in t["sinonimos"]):
                conceptos_detectados.append(t)

        tablas_sugeridas = set()
        endpoints_sugeridos = set()
        for c in conceptos_detectados:
            for tb in c.get("tablas_relacionadas", []):
                tablas_sugeridas.add(tb)
            for ep in c.get("endpoints_relacionados", []):
                endpoints_sugeridos.add(ep)

        return {
            "consulta": consulta,
            "conceptos": [c["concepto"] for c in conceptos_detectados],
            "claves_posicion": [p.upper() for p in claves_pos],
            "obras_detectadas": obras_posibles,
            "tablas_sugeridas": list(tablas_sugeridas),
            "endpoints_sugeridos": list(endpoints_sugeridos)
        }

    def consultar_termino(self, termino: str) -> Dict[str, Any]:
        """Busca la definición y metadatos de un término específico."""
        termino_u = termino.strip().upper()
        if termino_u in self.terminos:
            return {"ok": True, "termino": self.terminos[termino_u]}

        # Búsqueda por similitud
        for k, v in self.terminos.items():
            if termino.lower() in k.lower() or any(termino.lower() in s for s in v["sinonimos"]):
                return {"ok": True, "termino": v}

        return {"ok": False, "error": f"No se encontró el término '{termino}' en el glosario de negocio."}

    def registrar_o_actualizar_termino(
        self,
        clave: str,
        concepto: str,
        definicion: str,
        sinonimos: Optional[List[str]] = None,
        tablas: Optional[List[str]] = None,
        endpoints: Optional[List[str]] = None
    ) -> bool:
        """Registra un nuevo concepto de negocio o actualiza uno existente."""
        self.terminos[clave.upper()] = {
            "concepto": concepto,
            "definicion": definicion,
            "sinonimos": [s.lower().strip() for s in (sinonimos or [])],
            "tablas_relacionadas": tablas or [],
            "endpoints_relacionados": endpoints or []
        }
        self._guardar_glosario()
        return True

    def listar_conceptos(self) -> List[Dict[str, Any]]:
        return list(self.terminos.values())
