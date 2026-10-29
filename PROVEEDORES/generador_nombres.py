import re
import unicodedata

# Diccionario inteligente de abreviaciones para rubros y palabras genéricas frecuentes
ABREVIATURAS = {
    # Construcción y edificación
    "EDIFICACIONES": "EDIF",
    "EDIFICACION": "EDIF",
    "EDIFICADORA": "EDIF",
    "CONSTRUCCIONES": "CONST",
    "CONSTRUCCION": "CONST",
    "CONSTRUCTORA": "CONST",
    "CONSTRUCTOR": "CONST",
    "ARQUITECTURA": "ARQ",
    "ARQUITECTOS": "ARQ",
    "INGENIERIA": "ING",
    "INGENIEROS": "ING",
    "CERRAMIENTOS": "CERRAM",
    "CERRAMIENTO": "CERRAM",

    # Comercio y suministros
    "ABASTECEDORA": "ABAST",
    "ABASTECEDOR": "ABAST",
    "ABASTECIMIENTOS": "ABAST",
    "ABASTECIMIENTO": "ABAST",
    "COMERCIALIZADORA": "COM",
    "COMERCIAL": "COM",
    "DISTRIBUIDORA": "DIST",
    "DISTRIBUCIONES": "DIST",
    "DISTRIBUCION": "DIST",
    "PROVEEDORA": "PROV",
    "PROVEEDOR": "PROV",
    "PROVEEDORES": "PROV",
    "SUMINISTROS": "SUM",
    "SUMINISTRO": "SUM",
    "MATERIALES": "MAT",
    "MATERIAL": "MAT",
    "ACEROS": "ACERO",
    "ACERO": "ACERO",

    # Servicios y mantenimiento
    "SERVICIOS": "SERV",
    "SERVICIO": "SERV",
    "MANTENIMIENTO": "MTTO",
    "INSTALACIONES": "INST",
    "INSTALACION": "INST",
    "CONSULTORES": "CONS",
    "CONSULTORIA": "CONS",
    "SOLUCIONES": "SOL",
    "SOLUCION": "SOL",
    "LOGISTICA": "LOG",
    "TRANSPORTES": "TRANS",
    "TRANSPORTE": "TRANS",
    "ARRENDADORA": "ARREND",
    "ARRENDAMIENTO": "ARREND",
    "FABRICACION": "FAB",
    "FABRICANTE": "FAB",
    "INDUSTRIAL": "IND",
    "INDUSTRIAS": "IND",
    "INMOBILIARIA": "INMOB",
    "DESARROLLOS": "DES",
    "DESARROLLO": "DES",
    "CORPORATIVO": "CORP",
    "GRUPO": "GPO",
    "NACIONAL": "NAL",
    "INTERNACIONAL": "INT"
}

# Palabras y regímenes societarios que no aportan identidad al proveedor
PALABRAS_DESCARTAR = {
    "SA", "DE", "CV", "SAPI", "SC", "SCL", "SRL", "MI", "SOFOM", "EN", "POR", "ACCIONES",
    "SIMPLIFICADA", "SAS", "RESPONSABILIDAD", "LIMITADA", "CAPITAL", "VARIABLE", 
    "SOCIEDAD", "ANONIMA", "S", "A", "C", "V", "R", "L", "Y", "E", "DEL", "LOS", "LAS", "LA", "EL"
}


def normalizar_texto(texto: str) -> str:
    """Elimina acentos y caracteres especiales, convirtiendo a mayúsculas."""
    if not texto:
        return ""
    txt = unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('utf-8')
    return txt.upper().strip()


def extraer_tokens_relevantes(nombre: str) -> list:
    """Extrae las palabras descartando términos societarios y conectores."""
    txt = normalizar_texto(nombre)
    tokens = re.findall(r'[A-Z0-9]+', txt)
    palabras = [t for t in tokens if t not in PALABRAS_DESCARTAR]
    return palabras if palabras else tokens


def generar_clave_proveedor(nombre: str, max_chars: int = 20) -> str:
    """
    Genera la clave del proveedor obligatoriamente con el prefijo EK-PROV.
    - Toma como máximo las 2 características principales del nombre (ej: ACERLUM CERRAMIENTOS).
    - Aplica abreviaturas a términos conocidos.
    - Une todo con guiones medios '-' respetando el límite max_chars.
    """
    prefijo = "EK-PROV"
    palabras = extraer_tokens_relevantes(nombre)
    if not palabras:
        return prefijo

    # Regla: Máximo 2 características representativas
    caracteristicas = palabras[:2]
    caract_proc = [ABREVIATURAS.get(w, w) for w in caracteristicas]

    # 1. Probar si ambas palabras completas/abreviadas caben con EK-PROV-
    candidato = f"{prefijo}-" + "-".join(caract_proc)
    if len(candidato) <= max_chars:
        return candidato

    # 2. Si hay 2 palabras y excede max_chars
    p1 = caract_proc[0]
    if len(caract_proc) > 1:
        p2 = caract_proc[1]
        palabra_original_2 = caracteristicas[1]

        # REGLA DE PROTECCIÓN: Si la segunda palabra es un nombre distintivo/propio (no está en ABREVIATURAS),
        # priorizar que p2 quede COMPLETO y ajustar/abreviar la primera si hace falta.
        if palabra_original_2 not in ABREVIATURAS:
            espacio_p1 = max_chars - len(prefijo) - len(p2) - 2  # 2 guiones
            if espacio_p1 >= 3:
                return f"{prefijo}-{p1[:espacio_p1]}-{p2}"

        # Si no fue posible o ambas son genéricas, mantener p1 y recortar p2
        base = f"{prefijo}-{p1}"
        espacio_p2 = max_chars - len(base) - 1
        if espacio_p2 >= 3:
            return f"{base}-{p2[:espacio_p2]}"

        if len(base) <= max_chars:
            return base

    # 3. Si solo hay una palabra o no cupo la base completa
    disponible = max_chars - len(prefijo) - 1
    return f"{prefijo}-{p1[:disponible]}"


def generar_nombre_corto(nombre: str, max_chars: int = 20) -> str:
    """
    Genera el nombre corto característico del proveedor usando ESPACIOS (sin guiones),
    omitiendo regímenes societarios (SA, DE, CV, etc.) y tomando como máximo 2 características.
    Ejemplo:
      'ACERLUM CERRAMIENTOS SA DE CV' -> 'ACERLUM CERRAMIENTOS'
      'EDIFICACIONES GOODWIN SA DE CV' -> 'EDIF GOODWIN'
      'ABASTECEDORA PRAGA SA DE CV'    -> 'ABAST PRAGA'
    """
    palabras = extraer_tokens_relevantes(nombre)
    if not palabras:
        return normalizar_texto(nombre)[:max_chars]

    # Regla: Máximo 2 características representativas
    caracteristicas = palabras[:2]

    # 1. Probar si caben las 2 palabras originales sin abreviar
    candidato_original = " ".join(caracteristicas)
    if len(candidato_original) <= max_chars:
        return candidato_original

    # 2. Probar abreviando términos conocidos
    caract_proc = [ABREVIATURAS.get(w, w) for w in caracteristicas]
    candidato_proc = " ".join(caract_proc)
    if len(candidato_proc) <= max_chars:
        return candidato_proc

    # 3. Si aún excede, ajustar la segunda palabra
    p1 = caract_proc[0]
    if len(caract_proc) > 1:
        p2 = caract_proc[1]
        espacio_p2 = max_chars - len(p1) - 1
        if espacio_p2 >= 3:
            return f"{p1} {p2[:espacio_p2]}"

    return p1[:max_chars]


# Nombres de pila comunes en México para lógica de Persona Física
NOMBRES_COMUNES = {
    "JUAN", "JOSE", "MARIA", "LUIS", "CARLOS", "MANUEL", "JESUS", "MIGUEL", "FRANCISCO",
    "ANTONIO", "PEDRO", "JORGE", "ALBERTO", "ALEJANDRO", "EDUARDO", "FERNANDO", "RICARDO",
    "ROBERTO", "DANIEL", "HECTOR", "RAUL", "JAVIER", "ENRIQUE", "MARIO", "SERGIO", "ANA",
    "CARMEN", "ROSA", "GUADALUPE", "TERESA", "LETICIA", "ADRIANA", "MARTHA", "PATRICIA"
}


def generar_clave_persona_fisica(nombre: str, apellido_paterno: str, max_chars: int = 20) -> str:
    """
    Genera la clave para persona física con formato EK-PROV-...
    - Si el nombre NO es común (ej: SALVADOR, ARMANDO, GERARDO): usa solo el nombre -> EK-PROV-SALVADOR
    - Si el nombre es COMÚN (ej: JUAN, JOSE, LUIS): combina nombre y paterno -> EK-PROV-JUAN-PEREZ
    """
    prefijo = "EK-PROV"
    tokens_nombre = [t for t in normalizar_texto(nombre).split() if t]
    nom_principal = tokens_nombre[0] if tokens_nombre else "PROV"
    paterno_norm = normalizar_texto(apellido_paterno)

    es_comun = nom_principal in NOMBRES_COMUNES

    if es_comun and paterno_norm:
        # Combinar NOMBRE y APELLIDO PATERNO
        candidato = f"{prefijo}-{nom_principal}-{paterno_norm}"
        if len(candidato) <= max_chars:
            return candidato
        
        # Si excede 20 caracteres, ajustar paterno
        base = f"{prefijo}-{nom_principal}"
        disp = max_chars - len(base) - 1
        if disp >= 3:
            return f"{base}-{paterno_norm[:disp]}"
        return f"{prefijo}-{paterno_norm[:max_chars - len(prefijo) - 1]}"
    else:
        # Nombre no común: solo el nombre
        candidato = f"{prefijo}-{nom_principal}"
        if len(candidato) <= max_chars:
            return candidato
        return f"{prefijo}-{nom_principal[:max_chars - len(prefijo) - 1]}"


def generar_nombre_corto_persona_fisica(nombre: str, apellido_paterno: str, max_chars: int = 20) -> str:
    """
    Genera el nombre corto para persona física usando espacios (ej: 'SALVADOR PEREZ' o 'JUAN PEREZ').
    """
    tokens_nombre = [t for t in normalizar_texto(nombre).split() if t]
    nom_principal = tokens_nombre[0] if tokens_nombre else ""
    paterno_norm = normalizar_texto(apellido_paterno)

    if nom_principal and paterno_norm:
        candidato = f"{nom_principal} {paterno_norm}"
        if len(candidato) <= max_chars:
            return candidato
        return candidato[:max_chars]
    elif nom_principal:
        return nom_principal[:max_chars]
    return paterno_norm[:max_chars]

