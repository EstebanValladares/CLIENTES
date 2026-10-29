"""
Modelos de dominio y esquema de datos para Proveedores en Aryve.
"""
from dataclasses import dataclass
from typing import Any, Dict, Mapping

COLUMNAS_CSV: list[str] = [
    "TIPO PERSONA",
    "CLAVE",
    "NOMBRE",
    "PATERNO",
    "MATERNO",
    "RFC",
    "NOMBRE CORTO",
    "CALLE",
    "EXT",
    "COLONIA",
    "CP",
]


@dataclass
class ProveedorData:
    """Entidad de dominio que representa un proveedor listo para darse de alta en Aryve."""
    tipo_persona: str = "MORAL"
    clave: str = ""
    nombre: str = ""
    paterno: str = ""
    materno: str = ""
    rfc: str = ""
    nombre_corto: str = ""
    calle: str = ""
    ext: str = ""
    colonia: str = ""
    cp: str = ""

    def __post_init__(self) -> None:
        self.tipo_persona = self._limpiar(self.tipo_persona) or "MORAL"
        if "FISICA" in self.tipo_persona or "FÍSICA" in self.tipo_persona:
            self.tipo_persona = "FÍSICA"
        else:
            self.tipo_persona = "MORAL"

        self.clave = self._limpiar(self.clave)
        self.nombre = self._limpiar(self.nombre)
        self.paterno = self._limpiar(self.paterno)
        self.materno = self._limpiar(self.materno)
        self.rfc = self._limpiar(self.rfc)
        self.nombre_corto = self._limpiar(self.nombre_corto)
        self.calle = self._limpiar(self.calle)
        self.ext = self._limpiar(self.ext)
        self.colonia = self._limpiar(self.colonia)
        self.cp = self._limpiar(self.cp)

    @staticmethod
    def _limpiar(valor: Any) -> str:
        return str(valor or "").strip().upper()

    @property
    def es_persona_fisica(self) -> bool:
        return "FISICA" in self.tipo_persona or "FÍSICA" in self.tipo_persona

    @property
    def es_persona_moral(self) -> bool:
        return not self.es_persona_fisica

    @property
    def nombre_completo_display(self) -> str:
        if self.es_persona_fisica:
            partes = [self.nombre, self.paterno, self.materno]
            return " ".join(p for p in partes if p)
        return self.nombre

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProveedorData":
        """Construye un `ProveedorData` aceptando llaves de CSV ('TIPO PERSONA') o API ('tipo_persona')."""
        def _get(*keys: str, default: str = "") -> str:
            for k in keys:
                if k in data and data[k] is not None:
                    return str(data[k])
            return default

        return cls(
            tipo_persona=_get("TIPO PERSONA", "tipo_persona", default="MORAL"),
            clave=_get("CLAVE", "clave"),
            nombre=_get("NOMBRE", "nombre"),
            paterno=_get("PATERNO", "paterno"),
            materno=_get("MATERNO", "materno"),
            rfc=_get("RFC", "rfc"),
            nombre_corto=_get("NOMBRE CORTO", "nombre_corto"),
            calle=_get("CALLE", "calle"),
            ext=_get("EXT", "ext"),
            colonia=_get("COLONIA", "colonia"),
            cp=_get("CP", "cp"),
        )

    def to_csv_dict(self) -> Dict[str, str]:
        """Convierte la entidad al diccionario exacto requerido por `datos.csv`."""
        return {
            "TIPO PERSONA": self.tipo_persona,
            "CLAVE": self.clave,
            "NOMBRE": self.nombre,
            "PATERNO": self.paterno,
            "MATERNO": self.materno,
            "RFC": self.rfc,
            "NOMBRE CORTO": self.nombre_corto,
            "CALLE": self.calle,
            "EXT": self.ext,
            "COLONIA": self.colonia,
            "CP": self.cp,
        }

