"""
Domain Service: Procesamiento y Normalización Inteligente de Nombres de Contratistas.
Elimina figuras mercantiles (SA DE CV, S DE RL, etc.), prefijos de sistema (EK-, PROV-)
y formatea nombres personales y corporativos para óptima visualización en gafetes.
"""

import re
import unicodedata
from typing import List, Dict, Set, Tuple

# Nombres de pila comunes en México
COMMON_FIRST_NAMES: Set[str] = {
    "JUAN", "JOSE", "MARIA", "LUIS", "CARLOS", "MIGUEL", "ANGEL", "FRANCISCO",
    "JESUS", "JORGE", "PEDRO", "MANUEL", "ALEJANDRO", "FERNANDO", "DANIEL",
    "EDUARDO", "ROBERTO", "RICARDO", "JAVIER", "RAFAEL", "VICTOR", "ANTONIO",
    "ARTURO", "RAUL", "MARIO", "SERGIO", "ENRIQUE", "GUADALUPE", "ANA",
    "PATRICIA", "LETICIA", "ROSA", "CLAUDIA", "MONICA", "GABRIELA", "LAURA",
    "ADRIANA", "TERESA", "CARMEN", "GLORIA", "SILVIA", "SANDRA", "IRMA",
    "MARTHA", "YOLANDA", "HECTOR", "MARTIN", "RAMON", "ALFREDO", "CESAR",
    "OSCAR", "HUGO", "JULIO", "RUBEN", "EDGAR", "JAIME", "ARMANDO", "FELIPE",
    "GUILLERMO", "GUSTAVO", "SALVADOR", "IGNACIO", "ESTEBAN"
}

# Apellidos comunes en México
COMMON_SURNAMES: Set[str] = {
    "HERNANDEZ", "GARCIA", "MARTINEZ", "LOPEZ", "GONZALEZ", "PEREZ", "RODRIGUEZ",
    "SANCHEZ", "RAMIREZ", "FLORES", "GOMEZ", "MORALES", "VAZQUEZ", "JIMENEZ",
    "REYES", "DIAZ", "TORRES", "GUTIERREZ", "RUIZ", "MENDOZA", "AGUILAR",
    "ORTIZ", "MORENO", "CASTILLO", "ROMERO", "ALVAREZ", "MENDEZ", "CHAVEZ",
    "RIVERA", "JUAREZ", "DOMINGUEZ", "HERRERA", "MEDINA", "VARGAS", "CASTRO",
    "GUZMAN", "VELAZQUEZ", "SALAZAR", "ROJAS", "CRUZ", "CONTRERAS", "LUNA",
    "SILVA", "RAMOS", "DELGADO", "SOTO", "CARRILLO", "CERVANTES", "GUERRERO",
    "ESTRADA", "BAUTISTA", "CORTEZ", "LARA", "SANDOVAL", "MEJIA", "RIOS"
}

# Palabras clave corporativas
COMPANY_KEYWORDS: Set[str] = {
    "TRADING", "GLOBAL", "LOGISTICS", "SOLUCIONES", "SERVICIOS", "CONSTRUCCIONES",
    "CONSTRUCTORA", "INGENIERIA", "TECNOLOGIAS", "EQUIPOS", "GRUPO", "COMERCIALIZADORA",
    "TRANSPORTES", "DISTRIBUIDORA", "INMOBILIARIA", "CONSULTORES", "PROYECTOS",
    "EDIFICADORA", "ARQUITECTURA", "SUMINISTROS", "SISTEMAS", "INDUSTRIAL",
    "INDUSTRIAS", "CORPORATIVO", "SEGURIDAD", "CONSULTORIA", "MATERIALES", "OPERADORA",
    "DESARROLLOS", "MANTENIMIENTO", "ELECTRICA", "HIDRAULICA", "METALES", "AUTOMOTRIZ"
}

PREFIX_PATTERNS = [
    r"^(?:EK|PROV|CONT|CTTO|ID|COD|NO|REG|FOLIO)[-_\s\.:#0-9]*",
    r"^[#0-9\-_./\s]+",
]

LEGAL_SUFFIXES_REGEX = [
    r"[\s,]+S\.?A\.?P\.?I\.?\s+DE\s+C\.?V\.?\.?",
    r"[\s,]+S\.?A\.?P\.?I\.?\.?",
    r"[\s,]+S\.?A\.?\s+DE\s+C\.?V\.?\.?",
    r"[\s,]+S\.?\s+DE\s+R\.?L\.?\s+DE\s+C\.?V\.?\.?",
    r"[\s,]+S\.?\s+DE\s+R\.?L\.?\.?",
    r"[\s,]+S\.?A\.?B\.?\s+DE\s+C\.?V\.?\.?",
    r"[\s,]+S\.?A\.?B\.?\.?",
    r"[\s,]+S\.?A\.?S\.?(\s+DE\s+C\.?V\.?)?\.?",
    r"[\s,]+S\.?C\.?(\s+DE\s+C\.?V\.?)?\.?",
    r"[\s,]+A\.?C\.?\.?",
    r"[\s,]+S\.?A\.?\.?",
    r"[\s,]+S\.?N\.?C\.?\.?",
    r"[\s,]+S\.?C\.?S\.?\.?",
    r"[\s,]+S\.?C\.?A\.?\.?",
    r"[\s,]+L\.?L\.?C\.?\.?",
    r"[\s,]+I\.?N\.?C\.?\.?",
    r"[\s,]+C\.?O\.?R\.?P\.?\.?",
    r"[\s,]+L\.?T\.?D\.?\.?",
    r"[\s,]+G\.?M\.?B\.?H\.?\.?",
    r"[\s,]+DE\s+C\.?V\.?\.?",
    r"[\s,]+C\.?V\.?\.?",
    r"[\s,]+SOCIEDAD\s+ANONIMA(\s+BURSATIL)?\s+DE\s+CAPITAL\s+VARIABLE",
    r"[\s,]+SOCIEDAD\s+ANONIMA\s+PROMOTORA\s+DE\s+INVERSION(\s+DE\s+CAPITAL\s+VARIABLE)?",
    r"[\s,]+SOCIEDAD\s+DE\s+RESPONSABILIDAD\s+LIMITADA(\s+DE\s+CAPITAL\s+VARIABLE)?",
    r"[\s,]+SOCIEDAD\s+POR\s+ACCIONES\s+SIMPLIFICADA",
    r"[\s,]+SOCIEDAD\s+CIVIL",
    r"[\s,]+ASOCIACION\s+CIVIL",
]

SHORT_CONNECTORS = {"Y", "E", "O", "U", "DE", "DEL", "LA", "LAS", "LOS", "EN", "CON", "AL"}


def normalize_text(text: str) -> str:
    """Normaliza espacios, signos de puntuación y mayúsculas, conservando la Ñ."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text.upper()


def strip_accents(text: str) -> str:
    """Elimina acentos diacríticos conservando la letra Ñ."""
    text = text.replace("Ñ", "###N_TILDE###").replace("ñ", "###n_tilde###")
    nfkd = unicodedata.normalize("NFKD", text)
    result = "".join([c for c in nfkd if not unicodedata.combining(c)])
    result = result.replace("###N_TILDE###", "Ñ").replace("###n_tilde###", "ñ")
    return result


def remove_system_prefixes(name: str) -> str:
    """Elimina prefijos de captura como 'EK-', 'PROV-', '01-', etc."""
    cleaned = name
    for pattern in PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def remove_legal_suffixes(name: str) -> str:
    """Elimina figuras mercantiles (S.A. DE C.V., S. DE R.L., etc.)."""
    cleaned = name
    for pattern in LEGAL_SUFFIXES_REGEX:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"[,\.-]+$", "", cleaned).strip()
    return cleaned


def is_corporate_entity(tokens: List[str]) -> bool:
    """Determina si un nombre corresponde a una persona moral (empresa) o física."""
    for token in tokens:
        if token in COMPANY_KEYWORDS:
            return True
    first_name_matches = sum(1 for t in tokens if t in COMMON_FIRST_NAMES)
    surname_matches = sum(1 for t in tokens if t in COMMON_SURNAMES)
    if first_name_matches >= 1 and surname_matches >= 1:
        return False
    if first_name_matches == 0 and surname_matches <= 1 and len(tokens) >= 2:
        return True
    return False


def extract_person_name(tokens: List[str]) -> List[str]:
    """
    Extrae la combinación óptima de nombre personal:
    - 2 nombres + 1er apellido (ej. LUIS GUILLERMO MONTIEL)
    - 1 nombre + 1 apellido (ej. MARLENE LOYA)
    """
    if len(tokens) <= 2:
        return tokens

    if len(tokens) == 3:
        return tokens

    if len(tokens) >= 4:
        # Si tiene 2 nombres de pila al inicio
        if tokens[0] in COMMON_FIRST_NAMES and tokens[1] in COMMON_FIRST_NAMES:
            return [tokens[0], tokens[1], tokens[2]]
        # Si tiene 1 nombre y varios apellidos
        if tokens[0] in COMMON_FIRST_NAMES:
            return [tokens[0], tokens[1], tokens[2]]
        # Caso general: primeros 3 tokens
        return tokens[:3]

    return tokens[:3]


def group_lines_smartly(tokens: List[str], max_lines: int = 3) -> List[str]:
    """Agrupa tokens en líneas balanceadas de texto para gafete."""
    if not tokens:
        return []
    if len(tokens) == 1:
        return tokens

    # Si son 2 palabras
    if len(tokens) == 2:
        return tokens

    # Si son 3 palabras
    if len(tokens) == 3:
        if tokens[1] in SHORT_CONNECTORS:
            return [tokens[0], f"{tokens[1]} {tokens[2]}"]
        return tokens

    # Si son 4 o más palabras
    lines = []
    i = 0
    while i < len(tokens):
        current = tokens[i]
        if i + 1 < len(tokens):
            next_w = tokens[i + 1]
            if current in SHORT_CONNECTORS:
                current = f"{current} {next_w}"
                i += 1
            elif next_w in SHORT_CONNECTORS and i + 2 < len(tokens):
                current = f"{current} {next_w} {tokens[i + 2]}"
                i += 2
        lines.append(current)
        i += 1
        if len(lines) == max_lines - 1 and i < len(tokens):
            lines.append(" ".join(tokens[i:]))
            break

    return lines[:max_lines]


def process_contractor_name(raw_name: str) -> Dict[str, any]:
    """
    Pipeline completo de procesamiento de nombre para gafete.
    Retorna diccionario estructurado con:
    - nombre_limpio
    - nombre_destacado
    - lineas
    - tipo_entidad (PERSONA o EMPRESA)
    """
    norm = normalize_text(raw_name)
    without_prefix = remove_system_prefixes(norm)
    clean = remove_legal_suffixes(without_prefix)
    clean = strip_accents(clean)

    tokens = [t for t in clean.split() if t]
    if not tokens:
        tokens = [raw_name.strip().upper()]

    is_corp = is_corporate_entity(tokens)
    entity_type = "EMPRESA" if is_corp else "PERSONA"

    if not is_corp:
        featured_tokens = extract_person_name(tokens)
    else:
        featured_tokens = tokens[:4] if len(tokens) >= 4 else tokens

    lines = group_lines_smartly(featured_tokens, max_lines=3)
    featured_name = " ".join(featured_tokens)

    return {
        "nombre_original": raw_name,
        "nombre_limpio": clean,
        "nombre_destacado": featured_name,
        "lineas": lines,
        "tipo_entidad": entity_type
    }

