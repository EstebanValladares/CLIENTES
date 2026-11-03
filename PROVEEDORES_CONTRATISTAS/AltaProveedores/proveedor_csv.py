# -*- coding: utf-8 -*-
"""
proveedor_csv.py
----------------
Lee el CSV de un proveedor (formato vertical CAMPO,VALOR; un proveedor por archivo)
y lo convierte en un dict con claves normalizadas (sin acentos, minusculas, sin puntos).

  "Persona Fisica"/"Persona Física" = "Sí" -> tipo_persona FISICA
                                     = "No" -> tipo_persona MORAL

Uso: python proveedor_csv.py archivo1.csv [archivo2.csv ...]  -> imprime lo interpretado
"""

import csv
import io
import re
import sys
import unicodedata

# Campos que deben traer valor en el CSV segun el tipo de persona. En el formulario
# (Html/campos_obligatorios.txt) los obligatorios con asterisco son Clave, Nombre y RFC
# para ambos tipos; la Clave se genera del nombre (generar_clave).
REQUERIDOS = {
    "FISICA": ("nombre", "a paterno", "rfc"),
    "MORAL": ("nombre", "rfc"),
}


def normalizar(texto):
    """'Deleg. ó Mpio.' -> 'deleg o mpio'"""
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9 ]", " ", texto.lower().replace(".", ""))
    return re.sub(r"\s+", " ", texto).strip()


# ---------------------------------------------------------------------------
# Clave del proveedor
# ---------------------------------------------------------------------------
PREFIJO_CLAVE = "EK-PROV-"
LARGO_CLAVE = 24

# Abreviaturas comunes en razones sociales (palabra normalizada -> abreviatura)
ABREVIATURAS = {
    "compania": "CIA", "comercializadora": "COMER", "comercial": "COM", "corporativo": "CORP",
    "corporacion": "CORP", "constructora": "CONST", "construcciones": "CONST", "construccion": "CONST",
    "distribuidora": "DIST", "distribuciones": "DIST", "industrial": "IND", "industrias": "IND",
    "internacional": "INTL", "servicios": "SERV", "servicio": "SERV", "materiales": "MAT",
    "grupo": "GPO", "administracion": "ADMON", "administradora": "ADMON", "inmobiliaria": "INMOB",
    "mexicana": "MEX", "mexicano": "MEX", "mexico": "MEX", "nacional": "NAL", "asociados": "ASOC",
    "proyectos": "PROY", "ingenieria": "ING", "tecnologia": "TEC", "tecnologias": "TEC",
    "soluciones": "SOL", "mantenimiento": "MANTTO", "equipos": "EQ", "suministros": "SUMIN",
    "transportes": "TRANSP", "arrendadora": "ARREND", "arrendamiento": "ARREND",
    "desarrollos": "DES", "desarrolladora": "DES", "instalaciones": "INST", "electricos": "ELEC",
    "electrica": "ELEC", "ferreteria": "FERR", "consultores": "CONS", "consultoria": "CONS",
    "productos": "PROD", "promotora": "PROM", "fabricaciones": "FAB", "acabados": "ACAB",
    "importadora": "IMP", "exportadora": "EXP", "operadora": "OPER", "edificaciones": "EDIF",
    "sistemas": "SIST", "maquinaria": "MAQ", "hermanos": "HNOS", "laboratorio": "LAB",
    "infraestructura": "INFRA", "urbanizacion": "URB", "urbanizadora": "URB",
}
# Regimen societario al final de la razon social (se elimina: no distingue al proveedor)
REGIMEN_SOCIETARIO = re.compile(
    r"\b(s ?a ?p ?i|s ?a ?b|s ?a ?s|s ?a|s ?c|s ?c ?p|s ?en ?c|s ?de ?r ?l|s ?r ?l|a ?c|s ?c ?l)"
    r"( de c ?v| de r ?l)*( de c ?v)?\s*$")
CONECTORES = {"de", "del", "la", "las", "los", "el", "y", "e"}


def _clave(partes):
    clave = (PREFIJO_CLAVE + "-".join(p for p in partes if p))[:LARGO_CLAVE]
    return clave.rstrip("-")


def generar_clave(tipo, campos, paterno_completo=False):
    """
    FISICA: EK-PROV- + 3 primeras letras de nombre, apellido paterno y materno, unidas con '-'.
            JOSE ROBERTO RAMOS PADILLA -> EK-PROV-JOS-RAM-PAD
            Con paterno_completo (la clave anterior ya existe) -> EK-PROV-JOS-RAMOS-PAD
    MORAL:  EK-PROV- + palabras de la razon social unidas con '-', con abreviaturas, sin
            regimen societario ni conectores. ILA MERCANTIL S DE RL DE CV -> EK-PROV-ILA-MERCANTIL
    Todo en mayusculas, sin acentos ni espacios, truncado a 24 caracteres.
    """
    if tipo == "FISICA":
        partes = [normalizar(campos.get(c, "")).replace(" ", "").upper()
                  for c in ("nombre", "a paterno", "a materno")]
        partes = [p if i == 1 and paterno_completo else p[:3] for i, p in enumerate(partes)]
        return _clave(partes)
    nombre = REGIMEN_SOCIETARIO.sub("", normalizar(campos.get("nombre", ""))).strip()
    partes = [ABREVIATURAS.get(p, p).upper() for p in nombre.split() if p not in CONECTORES]
    return _clave(partes)


def es_si(valor):
    return normalizar(valor) in ("si", "s", "yes", "1", "true", "x")


def decodificar(contenido):
    """bytes -> str probando utf-8 (con o sin BOM) y cp1252."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return contenido.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("No se pudo decodificar el CSV")


def leer_proveedor(contenido, nombre_archivo=""):
    """
    contenido: bytes o str del CSV.
    Retorna dict con:
      campos       {clave_normalizada: valor}
      etiquetas    {clave_normalizada: etiqueta original}
      tipo_persona "FISICA" | "MORAL"
      faltantes    [etiquetas requeridas sin valor]
      archivo      nombre_archivo
    """
    texto = decodificar(contenido) if isinstance(contenido, bytes) else contenido
    filas = [f for f in csv.reader(io.StringIO(texto)) if f and any(c.strip() for c in f)]
    if filas and normalizar(filas[0][0]) == "campo":
        filas = filas[1:]

    campos, etiquetas = {}, {}
    for fila in filas:
        clave = normalizar(fila[0])
        if not clave:
            continue
        # Un valor con comas sin comillas se parte en varias columnas: se vuelve a unir
        campos[clave] = ",".join(fila[1:]).strip()
        etiquetas[clave] = fila[0].strip()

    if "persona fisica" not in campos:
        raise ValueError(f"{nombre_archivo}: no trae el renglon 'Persona Física'")
    tipo = "FISICA" if es_si(campos["persona fisica"]) else "MORAL"
    faltantes = [etiquetas.get(c, c) for c in REQUERIDOS[tipo] if not campos.get(c)]
    return {"archivo": nombre_archivo, "tipo_persona": tipo, "clave": generar_clave(tipo, campos),
            "campos": campos, "etiquetas": etiquetas, "faltantes": faltantes}


def leer_archivo(ruta):
    with open(ruta, "rb") as f:
        return leer_proveedor(f.read(), ruta)


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        p = leer_archivo(ruta)
        print(f"===== {ruta}")
        print(f"  Tipo de Persona: {p['tipo_persona']}")
        print(f"  Clave generada:  {p['clave']}")
        for clave, valor in p["campos"].items():
            print(f"  {p['etiquetas'][clave]:22} [{clave}] = {valor}")
        print(f"  Faltantes: {p['faltantes'] or 'ninguno'}")
