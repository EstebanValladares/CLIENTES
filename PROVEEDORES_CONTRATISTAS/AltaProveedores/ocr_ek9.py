# -*- coding: utf-8 -*-
"""
ocr_ek9.py
----------
Lee la captura de la pestana "Datos Generales" de proveedores (EK9) con el OCR integrado
de Windows (sin internet ni API key) y devuelve los campos en el orden del CSV CAMPO,VALOR.

Como funciona:
  1. Detecta (OpenCV) los cuadros blancos de captura, las casillas y los botones de opcion.
  2. Lee toda la imagen ampliada para ubicar las etiquetas y asigna a cada cuadro la etiqueta
     que tiene a su izquierda (a las opciones de Estatus General, la de su derecha).
  3. Lee cada cuadro por separado (recortado, con margen blanco y ampliado) y limpia el valor
     segun el tipo de campo (numeros, RFC, listas).
  4. Casillas y opciones: marcadas si tienen pixeles oscuros dentro.
  5. Agrega "dudas" para revisar: RFC/CP con formato raro, campos clave no encontrados, etc.

Requisitos: pip install opencv-python numpy pillow winrt-runtime winrt-Windows.Media.Ocr
  winrt-Windows.Graphics.Imaging winrt-Windows.Storage winrt-Windows.Storage.Streams
  winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.Globalization
  y el idioma Espanol con reconocimiento optico instalado en Windows.

Uso: python ocr_ek9.py captura.png   -> imprime los campos leidos
"""

import asyncio
import difflib
import io
import os
import re
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from proveedor_csv import normalizar

ESCALA = 3       # ampliacion para el OCR
MAX_LADO = 9500  # el OCR de Windows admite hasta 10000 px por lado
MARGEN = 12      # margen blanco alrededor de cada recorte (px antes de ampliar)
SEPARACION = 30  # espacio vertical entre recortes apilados (px antes de ampliar)

# (nombre en el CSV, tipo, se incluye aunque no aparezca en la pantalla)
CAMPOS = [
    ("Proveedor", "numero", True),
    ("Persona Fisica", "casilla", True),
    ("Cemex", "casilla", False),
    ("Obliga CFDI", "casilla", True),
    ("Filial", "casilla", True),
    ("Factoraje", "casilla", True),
    ("Nombre", "texto", True),
    ("A. Paterno", "texto", False),
    ("A. Materno", "texto", False),
    ("Dirección", "texto", True),
    ("Calle", "texto", True),
    ("Colonia", "texto", True),
    ("Deleg. ó Mpio.", "texto", True),
    ("Ciudad", "lista", True),
    ("Código Postal", "numero", True),
    ("Nac. ó Ext.", "lista", True),
    ("Nombre Corto", "texto", True),
    ("R.F.C.", "rfc", True),
    ("No. Pyme", "texto", True),
    ("ID Fiscal", "texto", True),
    ("Tipo Soc.", "texto", True),
    ("Tipo de Tercero", "lista", True),
    ("Tipo de Operación", "lista", True),
    ("Tipo de Proveedor", "lista", True),
    ("Confir. pago", "lista", True),
    ("Clave ID", "texto", True),
    ("Estatus General", "opcion", True),
    ("Empleado", "numero", True),
    ("Nacionalidad", "texto", True),
]
TIPO = {nombre: tipo for nombre, tipo, _ in CAMPOS}
OPCIONES_ESTATUS = ("Vigente", "Cancelado", "Habilitado por password")


class ErrorOCR(RuntimeError):
    pass


# =============================================================================
# OCR DE WINDOWS
# =============================================================================
def _ocr_archivos(rutas):
    """[ruta png] -> [[(texto, x, y, ancho, alto) por palabra]] usando Windows.Media.Ocr."""
    try:
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage import FileAccessMode, StorageFile
    except ImportError as e:
        raise ErrorOCR(f"Falta el componente de OCR de Windows para Python ({e.name})")

    async def leer():
        motor = None
        for idioma in ("es-MX", "es-ES", "es"):
            if OcrEngine.is_language_supported(Language(idioma)):
                motor = OcrEngine.try_create_from_language(Language(idioma))
                break
        motor = motor or OcrEngine.try_create_from_user_profile_languages()
        if motor is None:
            raise ErrorOCR("Windows no tiene instalado el reconocimiento de texto en espanol")
        resultados = []
        for ruta in rutas:
            archivo = await StorageFile.get_file_from_path_async(ruta)
            flujo = await archivo.open_async(FileAccessMode.READ)
            imagen = await (await BitmapDecoder.create_async(flujo)).get_software_bitmap_async()
            res = await motor.recognize_async(imagen)
            resultados.append([(w.text, w.bounding_rect.x, w.bounding_rect.y,
                                w.bounding_rect.width, w.bounding_rect.height)
                               for linea in res.lines for w in linea.words])
        return resultados

    return asyncio.run(leer())


def ocr_imagenes(imagenes):
    """[PIL.Image] -> palabras de cada una (via archivos temporales)."""
    rutas = []
    try:
        for im in imagenes:
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            im.save(f, format="PNG")
            f.close()
            rutas.append(f.name)
        return _ocr_archivos(rutas)
    finally:
        for ruta in rutas:
            try:
                os.remove(ruta)
            except OSError:
                pass


# =============================================================================
# DETECCION DE CONTROLES
# =============================================================================
def es_seleccion(rgb):
    """Azul de seleccion de Windows (p.ej. 0,120,215 / 51,153,255)."""
    r, g, b = (rgb[:, :, i].astype(int) for i in range(3))
    return (r < 80) & (g > 80) & (g < 170) & (b > 190)


def detectar_controles(rgb):
    """Cuadros de texto, casillas y circulos de opcion como (x, y, w, h) en la imagen original."""
    r, g, b = (rgb[:, :, i].astype(int) for i in range(3))
    blanco = (r > 245) & (g > 245) & (b > 245)
    seleccion = es_seleccion(rgb)  # texto seleccionado (fondo azul)
    mascara = ((blanco | seleccion) * 255).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=4)
    cuadros, marcas = [], []
    for x, y, w, h, area in stats[1:n]:
        relleno = area / float(w * h)
        # Interior de un cuadro de captura (el texto baja el relleno; los bordes 3D quedan ~0.05)
        if 12 <= h <= 30 and w >= 25 and relleno > 0.45:
            cuadros.append((x, y, w, h))
        # Circulos de opcion (y casillas grandes): pequenos y casi cuadrados
        elif 8 <= w <= 20 and 8 <= h <= 20 and abs(w - h) <= 3 and relleno > 0.15:
            marcas.append((x, y, w, h))
    return unir_contiguos(cuadros), marcas


def unir_contiguos(cuadros):
    """Une piezas del mismo cuadro partidas por el texto seleccionado (blanco | azul)."""
    unidos = []
    for c in sorted(cuadros, key=lambda c: (c[1], c[0])):
        if unidos:
            x, y, w, h = unidos[-1]
            if abs(c[1] - y) <= 2 and abs(c[3] - h) <= 2 and 0 <= c[0] - (x + w) <= 3:
                unidos[-1] = (x, min(y, c[1]), c[0] + c[2] - x, max(h, c[3]))
                continue
        unidos.append(c)
    return unidos


def casilla_junto_a(gris, borde_x, cy):
    """Busca el cuadrito de una casilla a la derecha de su etiqueta; None, "Sí" o "No"."""
    y0, y1 = int(cy) - 11, int(cy) + 11
    x0, x1 = int(borde_x) + 1, int(borde_x) + 32
    zona = gris[max(0, y0):y1, x0:x1].astype(int)
    if zona.size == 0:
        return None
    # Pixeles que no son fondo (marco, interior blanco, palomita)
    ys, xs = np.where(np.abs(zona - 240) > 12)
    if len(ys) < 20:
        return None
    by0, by1, bx0, bx1 = ys.min(), ys.max(), xs.min(), xs.max()
    if not (8 <= by1 - by0 <= 20 and 8 <= bx1 - bx0 <= 20):
        return None
    interior = zona[by0 + 3:by1 - 2, bx0 + 3:bx1 - 2]
    return "Sí" if int((interior < 110).sum()) >= 4 else "No"


def tiene_marca(gris, caja, recorte=2):
    """Casilla/circulo marcado: pixeles oscuros dentro."""
    x, y, w, h = caja
    interior = gris[y + recorte:y + h - recorte, x + recorte:x + w - recorte]
    return interior.size > 0 and int((interior < 110).sum()) >= 4


def extension_derecha(rgb, caja, maximo=4):
    """
    Columnas extra a la derecha del cuadro que todavia tienen trazo de letra: los numeros van
    alineados a la derecha y el ultimo digito puede tocar el borde ("11556" se leia "115%").
    Se detiene en la primera columna sin trazo o que parezca borde (oscura casi toda la altura).
    """
    x, y, w, h = caja
    gris = rgb[y + 1:y + h - 1].astype(int).mean(axis=2)
    extra = 0
    for k in range(maximo):
        col = x + w - 1 + k
        if col >= gris.shape[1]:
            break
        oscuros = int((gris[:, col] < 170).sum())
        if oscuros == 0 or oscuros > 0.7 * gris.shape[0]:
            break
        extra = k + 1
    return extra


def recorte_base(rgb, caja, extra_derecha=0, canal_oscuro=False):
    """
    Recorta el interior del cuadro en grises y pone el texto seleccionado (azul) en negro sobre blanco.
    canal_oscuro: gris = canal mas oscuro de cada pixel; los bordes de color de ClearType se vuelven
    parte del trazo (mejora los numeros: "11556" se leia "115%"; empeora el texto).
    """
    x, y, w, h = caja
    sub = rgb[y + 1:y + h - 1, x + 1:x + w - 1 + extra_derecha].astype(int)
    if canal_oscuro:
        gris = sub.min(axis=2).astype(float)
    else:
        gris = (0.299 * sub[:, :, 0] + 0.587 * sub[:, :, 1] + 0.114 * sub[:, :, 2])
    azul = es_seleccion(sub)
    ys, xs = np.where(azul)
    # Solo si hay un bloque solido de azul de seleccion (los bordes ClearType del texto no cuentan)
    if len(ys) >= 40:
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        if azul[y0:y1, x0:x1].mean() > 0.5:
            # Inversion gradual: fondo azul -> blanco, texto blanco -> negro (conserva el suavizado)
            fondo = float(np.median(gris[y0:y1, x0:x1][azul[y0:y1, x0:x1]]))
            zona = gris[y0:y1, x0:x1]
            zona[:] = np.clip(255 * (1 - (zona - fondo) / max(1.0, 255 - fondo)), 0, 255)
    # Cursor de texto: linea vertical delgada de toda la altura -> se borra
    oscuras = (gris < 128).mean(axis=0) > 0.8
    for x0 in np.where(oscuras)[0]:
        if not (oscuras[max(0, x0 - 2):x0].any() and oscuras[x0 + 1:x0 + 3].any()):
            gris[:, x0] = 255
    return Image.fromarray(np.clip(gris, 0, 255).astype(np.uint8))


def _ampliar(im, factor, filtro):
    im = ImageOps.expand(im, border=MARGEN, fill=255)
    return im.resize((im.width * factor, im.height * factor), filtro)


def _ensanchar(im, ancho):
    """Extiende los trazos oscuros en horizontal (la "I" de 1 px deja de perderse)."""
    return Image.fromarray(cv2.erode(np.array(im), np.ones((1, ancho), np.uint8)))


# Preparaciones del recorte: cada una acierta en casos distintos (la "I" delgada se pierde en
# la lectura normal; ensanchada se recupera pero a veces se pegan palabras). Se vota por campo.
VARIANTES = (
    lambda im: ImageOps.autocontrast(_ampliar(im, 3, Image.LANCZOS)),
    lambda im: _ensanchar(ImageOps.autocontrast(_ampliar(im, 3, Image.LANCZOS)), 2),
    lambda im: _ensanchar(ImageOps.autocontrast(_ampliar(im, 4, Image.LANCZOS)), 3),
)


def _otsu(im, factor):
    """Ampliado y binarizado (Otsu): separa mejor 3/6/8 en los numeros."""
    a = np.array(ImageOps.autocontrast(_ampliar(im, factor, Image.LANCZOS)))
    _, b = cv2.threshold(a, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(b)


# Numeros (Proveedor, Codigo Postal, Empleado): el OCR confunde 6/8 con 3 segun la preparacion
# y segun lo que tenga apilado alrededor. Se leen solos y con estas preparaciones; gana la
# lectura mas repetida (empate: la primera de la lista).
VARIANTES_NUMERO = (
    lambda im: _otsu(im, 4),
    lambda im: _otsu(im, 6),
    VARIANTES[2],
    VARIANTES[0],
    lambda im: ImageOps.autocontrast(_ampliar(im, 3, Image.LANCZOS)).filter(ImageFilter.SHARPEN),
)


def leer_numero(bases, formato=None):
    """
    Lee un recorte numerico con VARIANTES_NUMERO sobre cada version de `bases` (gris normal y
    canal oscuro: cada una acierta en capturas distintas, ClearType vs JPG). Cada lectura por
    separado; gana la mas repetida. (valor, dudoso)
    """
    lecturas = [re.sub(r"\D", "", leer_recortes([v(b)])[0].translate(A_DIGITO))
                for b in bases for v in VARIANTES_NUMERO]
    candidatos = [l for l in lecturas if l]
    if formato is not None and any(formato.fullmatch(c) for c in candidatos):
        candidatos = [c for c in candidatos if formato.fullmatch(c)]
    if not candidatos:
        return "", False
    valor = max(candidatos, key=lambda c: (candidatos.count(c), -candidatos.index(c)))
    # Dudoso si no gano con mayoria clara de las lecturas validas
    return valor, candidatos.count(valor) * 2 <= len(candidatos)


def leer_recortes(imagenes):
    """Lee varias imagenes de una sola linea apiladas en un lienzo (una llamada al OCR)."""
    if not imagenes:
        return []
    sep = SEPARACION * ESCALA
    ancho = max(i.width for i in imagenes) + 2 * sep
    textos, grupo, alto = [], [], sep
    # El OCR de Windows admite hasta MAX_LADO px por lado: se parte en lienzos si hace falta
    for im in imagenes + [None]:
        if im is None or alto + im.height + sep > MAX_LADO:
            lienzo = Image.new("L", (ancho, alto), 255)
            tramos, y = [], sep
            for g in grupo:
                lienzo.paste(g, (sep, y))
                tramos.append((y, y + g.height))
                y += g.height + sep
            leidas = ocr_imagenes([lienzo])[0] if grupo else []
            for y0, y1 in tramos:
                textos.append(" ".join(t for t, x, yy, w, h in sorted(leidas, key=lambda p: p[1])
                                       if y0 - 10 <= yy + h / 2 <= y1 + 10))
            grupo, alto = [], sep
        if im is not None:
            grupo.append(im)
            alto += im.height + sep
    return textos


def _subsecuencia(corta, larga):
    """True si `corta` se obtiene quitando caracteres a `larga`."""
    it = iter(larga)
    return len(corta) < len(larga) and all(c in it for c in corta)


FORMATOS = {
    "R.F.C.": re.compile(r"[A-ZÑ&]{3,4}-\d{6}-[A-Z0-9]{3}"),
    "Código Postal": re.compile(r"\d{5}"),
    "Proveedor": re.compile(r"\d{4,6}"),
}


def votar(lecturas, formato=None):
    """
    Elige entre las lecturas de las VARIANTES (la primera es la lectura normal). El OCR tiende
    a OMITIR letras delgadas, casi nunca a inventarlas: una lectura que es otra con letras de
    menos ("GUTERREZ" / "GUTIERREZ", "11" / "11568") cuenta como apoyo (0.9) a la mas completa.
    Los espacios no cuentan para comparar. Empate: la variante anterior (la normal primero).
    Devuelve (valor, dudoso): dudoso si ninguna otra variante la leyo igual.
    """
    candidatos = [l for l in lecturas if l]
    if not candidatos:
        return "", False
    # Campos con formato conocido (RFC, CP): si alguna lectura lo cumple, solo esas compiten
    if formato is not None and any(formato.fullmatch(c) for c in candidatos):
        candidatos = [c for c in candidatos if formato.fullmatch(c)]
    # Con ClearType la "U" a veces se lee "IJ" (ESPIRITU -> ESPIRTIJ): para comparar son iguales
    compacta = [c.replace(" ", "").replace("IJ", "U") for c in candidatos]

    def puntos(i):
        exactos = sum(1 for c in compacta if c == compacta[i])
        omitidas = sum(0.9 for c in compacta if _subsecuencia(c, compacta[i]))
        return exactos + omitidas, -i

    mejor = max(range(len(candidatos)), key=puntos)
    exactos = sum(1 for c in compacta if c == compacta[mejor])
    # Entre lecturas equivalentes se prefiere la que trae "U" en lugar de "IJ"
    iguales = [c for c, k in zip(candidatos, compacta) if k == compacta[mejor]]
    elegido = next((c for c in iguales if "IJ" not in c), candidatos[mejor])
    return con_espacios(elegido, candidatos[0]), exactos < 2 and len(set(compacta)) > 1


def con_espacios(elegido, plantilla):
    """Las variantes ensanchadas pegan palabras ("PIPILA310"): toma los espacios de la normal."""
    if " " not in plantilla or elegido == plantilla:
        return elegido
    resultado = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, elegido, plantilla, autojunk=False).get_opcodes():
        if op == "insert" and plantilla[b0:b1].strip() == "":
            resultado.append(" ")
        elif op != "insert":
            resultado.append(elegido[a0:a1])
    return re.sub(r"\s+", " ", "".join(resultado)).strip()


# =============================================================================
# ETIQUETAS
# =============================================================================
def dentro(palabra, cajas):
    px, py = palabra[1] + palabra[3] / 2, palabra[2] + palabra[4] / 2
    return any(x <= px <= x + w and y <= py <= y + h for x, y, w, h in cajas)


def etiqueta_izquierda(caja, palabras, max_hueco=90, hueco_palabras=14):
    """Texto de las palabras inmediatamente a la izquierda del control, en su misma fila."""
    x, y, w, h = caja
    fila = [p for p in palabras
            if y - 4 <= p[2] + p[4] / 2 <= y + h + 4 and p[1] + p[3] <= x + 3]
    fila.sort(key=lambda p: p[1] + p[3], reverse=True)
    tomadas, borde = [], x
    for p in fila:
        hueco = borde - (p[1] + p[3])
        if hueco > (max_hueco if not tomadas else hueco_palabras):
            break
        tomadas.append(p)
        borde = p[1]
    return " ".join(p[0] for p in reversed(tomadas))


def campo_de_etiqueta(texto, candidatos):
    """Nombre de campo cuya etiqueta se parece mas al texto leido (o None)."""
    leido = normalizar(texto).replace(" ", "")
    if not leido:
        return None
    mejor, puntaje = None, 0.0
    for nombre in candidatos:
        objetivo = normalizar(nombre).replace(" ", "")
        p = difflib.SequenceMatcher(None, leido, objetivo).ratio()
        # La etiqueta leida puede traer palabras de mas a la izquierda ("CFDI Filial")
        if leido.endswith(objetivo):
            p = max(p, 0.95)
        if p > puntaje:
            mejor, puntaje = nombre, p
    return mejor if puntaje >= 0.72 else None


# =============================================================================
# LIMPIEZA DE VALORES
# =============================================================================
A_DIGITO = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "C": "0", "U": "0",
                          "I": "1", "l": "1", "|": "1", "L": "1",
                          "i": "1", "S": "5", "s": "5", "B": "8", "Z": "2", "z": "2", "G": "6", "g": "9"})


def limpiar(nombre, texto):
    tipo = TIPO[nombre]
    texto = re.sub(r"\s+", " ", texto or "").strip()
    if tipo == "numero":
        return re.sub(r"\D", "", texto.translate(A_DIGITO))
    if tipo == "lista":
        # La flecha de la lista a veces se lee como "v", "V" o simbolos
        return re.sub(r"(\s+[vV∨˅YyÝ|>]+)+$", "", texto).strip()
    if tipo == "rfc":
        return limpiar_rfc(texto)
    # EK9 captura en mayusculas; el OCR a veces da "Año" por "AÑO"
    letras = [c for c in texto if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) >= 0.6:
        texto = texto.upper()
    return texto


def limpiar_rfc(texto):
    """Mayusculas sin espacios; en la fecha (6 posiciones tras las letras) letras -> digitos."""
    t = re.sub(r"[\s_.]", "", texto.upper()).replace("—", "-").replace("–", "-")
    m = re.match(r"^([A-ZÑ&]{3,4})-?([A-Z0-9]{6})-?([A-Z0-9]{3})$", t)
    if m:
        letras, fecha, homo = m.groups()
        return f"{letras}-{fecha.translate(A_DIGITO)}-{homo}"
    return t


def dudas_de(campos, encontrados):
    dudas = []
    valores = dict(campos)
    for clave in ("Proveedor", "Persona Fisica", "Nombre", "R.F.C."):
        if clave not in encontrados:
            dudas.append(f"No se encontro el campo '{clave}' en la imagen")
    rfc = valores.get("R.F.C.", "")
    if rfc and not re.fullmatch(r"[A-ZÑ&]{3,4}-\d{6}-[A-Z0-9]{3}", rfc):
        dudas.append(f"RFC con formato inesperado: '{rfc}'")
    elif rfc:
        dudas.append(f"Verifique la homoclave del RFC '{rfc}' (letras/numeros parecidos: O/0, I/1, S/5, B/8)")
    m = re.match(r"([A-ZÑ&]+)-", rfc)
    if m:
        esperadas = 4 if valores.get("Persona Fisica") == "Sí" else 3
        if len(m.group(1)) != esperadas:
            dudas.append(f"El RFC '{rfc}' tiene {len(m.group(1))} letras; el de persona "
                         f"{'fisica' if esperadas == 4 else 'moral'} lleva {esperadas}")
    cp = valores.get("Código Postal", "")
    if cp and not re.fullmatch(r"\d{5}", cp):
        dudas.append(f"Codigo Postal con formato inesperado: '{cp}'")
    fisica = valores.get("Persona Fisica") == "Sí"
    if fisica != ("A. Paterno" in encontrados):
        dudas.append("La casilla Persona Fisica no coincide con la pantalla (apellidos visibles: "
                     f"{'si' if 'A. Paterno' in encontrados else 'no'}); revise el tipo de persona")
    if "Estatus General" not in encontrados:
        dudas.append("No se pudo leer Estatus General")
    return dudas


# =============================================================================
# EXTRACCION
# =============================================================================
def leer_captura(contenido):
    """bytes de la imagen -> (campos [(nombre, valor)], dudas [str])."""
    try:
        imagen = Image.open(io.BytesIO(contenido)).convert("RGB")
    except OSError:
        raise ErrorOCR("No se pudo abrir la imagen")
    rgb = np.array(imagen)
    gris = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    cuadros, marcas = detectar_controles(rgb)

    # 1) Etiquetas: se borra el contenido de los cuadros (con su borde) para que el OCR no
    #    mezcle etiquetas con valores, y se lee toda la imagen ampliada
    solo_etiquetas = gris.copy()
    for x, y, w, h in cuadros:
        solo_etiquetas[max(0, y - 3):y + h + 3, max(0, x - 3):x + w + 3] = 240
    grande = ImageOps.autocontrast(Image.fromarray(solo_etiquetas).resize(
        (imagen.width * ESCALA, imagen.height * ESCALA), Image.LANCZOS))
    etiquetas = [(t, x / ESCALA, y / ESCALA, w / ESCALA, h / ESCALA)
                 for t, x, y, w, h in ocr_imagenes([grande])[0]]

    valores, encontrados, dudas = {}, set(), []
    textos = [n for n, t, _ in CAMPOS if t not in ("casilla", "opcion")]
    nombres_casilla = [n for n, t, _ in CAMPOS if t == "casilla"]

    # 2) Cada cuadro/casilla toma la etiqueta de su izquierda. A los que quedan sin etiqueta
    #    (el OCR de la imagen completa a veces pierde palabras cortas como "Calle:") se les lee
    #    por separado la franja de la izquierda.
    # Casillas: se localiza la etiqueta ("Obliga CFDI") y se examina el cuadrito a su derecha
    # (en la pantalla clasica la palomita llena casi toda la casilla y no queda blanco que detectar)
    for nombre in nombres_casilla:
        mejor = None
        for i in range(len(etiquetas)):
            for j in range(i, min(i + 3, len(etiquetas))):
                tramo = etiquetas[i:j + 1]
                if any(abs(p[2] - tramo[0][2]) > 6 for p in tramo):
                    break
                texto = " ".join(p[0] for p in tramo)
                p = difflib.SequenceMatcher(None, normalizar(texto).replace(" ", ""),
                                            normalizar(nombre).replace(" ", "")).ratio()
                if p >= 0.8 and (mejor is None or p > mejor[0]):
                    mejor = (p, tramo[-1])
        if mejor:
            ultima = mejor[1]
            valor = casilla_junto_a(gris, ultima[1] + ultima[3], ultima[2] + ultima[4] / 2)
            if valor:
                encontrados.add(nombre)
                valores[nombre] = valor

    controles = [(c, textos, 90) for c in sorted(cuadros, key=lambda c: (c[1], c[0]))]
    controles += [(c, nombres_casilla, 40) for c in marcas]
    candidatos = {}
    for caja, opciones, hueco in controles:
        candidatos[caja] = campo_de_etiqueta(etiqueta_izquierda(caja, etiquetas, max_hueco=hueco), opciones)
    sin_etiqueta = [(caja, opciones, hueco) for caja, opciones, hueco in controles if candidatos[caja] is None]
    franjas = []
    for (x, y, w, h), _, hueco in sin_etiqueta:
        x0 = max(0, x - hueco - 80)
        franja = Image.fromarray(solo_etiquetas[max(0, y - 3):y + h + 3, x0:x])
        franjas.append(ImageOps.autocontrast(_ampliar(franja, ESCALA, Image.LANCZOS)) if x > x0 else None)
    leidas = leer_recortes([f for f in franjas if f is not None])
    for (caja, opciones, _), franja in zip(sin_etiqueta, franjas):
        if franja is not None:
            texto = leidas.pop(0)
            # De la franja interesa la etiqueta pegada al control: se prueban las ultimas palabras
            palabras = texto.split()
            for n in range(1, min(4, len(palabras)) + 1):
                nombre = campo_de_etiqueta(" ".join(palabras[-n:]), opciones)
                if nombre:
                    candidatos[caja] = nombre
                    break

    asignados = []
    for caja, opciones, _ in controles:
        nombre = candidatos[caja]
        if nombre and nombre not in encontrados:
            encontrados.add(nombre)
            if nombre in nombres_casilla:
                valores[nombre] = "Sí" if tiene_marca(gris, caja) else "No"
            else:
                asignados.append((nombre, caja))

    # 3) Valores: cada cuadro se lee con todas las VARIANTES y se vota por campo.
    #    Los numericos se leen aparte, uno por uno (leer_numero).
    for nombre, caja in asignados:
        if TIPO[nombre] == "numero":
            extra = extension_derecha(rgb, caja)
            bases = [recorte_base(rgb, caja, extra), recorte_base(rgb, caja, extra, canal_oscuro=True)]
            valores[nombre], desacuerdo = leer_numero(bases, FORMATOS.get(nombre))
            if desacuerdo:
                dudas.append(f"Verifique {nombre}: '{valores[nombre]}' (las lecturas no coincidieron)")
    # Los textos se leen apilados con TODOS los cuadros (incluidos los numericos): el OCR de
    # Windows lee distinto segun lo que tenga alrededor y asi se obtuvo la mejor precision.
    bases = [recorte_base(rgb, caja) for _, caja in asignados]
    por_variante = [leer_recortes([v(b) for b in bases]) for v in VARIANTES]
    for i, (nombre, caja) in enumerate(asignados):
        if TIPO[nombre] == "numero":
            continue
        lecturas = [limpiar(nombre, textos_v[i]) for textos_v in por_variante]
        if TIPO[nombre] == "rfc":
            # El RFC (con el se revisan duplicados en EK10) se lee ademas solo y con ambos grises
            for b in (recorte_base(rgb, caja), recorte_base(rgb, caja, canal_oscuro=True)):
                lecturas += [limpiar(nombre, leer_recortes([v(b)])[0]) for v in VARIANTES]
        valores[nombre], desacuerdo = votar(lecturas, FORMATOS.get(nombre))
        # ClearType: la "U" se lee "IJ". En espanol "IJ" siempre va seguido de vocal (HIJO,
        # TIJUANA); sin vocal despues (fin de palabra o consonante) es una "U" mal leida.
        corregido = re.sub(r"IJ(?![AEIOUÁÉÍÓÚ])", "U", valores[nombre])
        if corregido != valores[nombre]:
            dudas.append(f"Verifique {nombre}: se leyo '{valores[nombre]}' y se corrigio a '{corregido}' (IJ -> U)")
            valores[nombre], desacuerdo = corregido, False
        if desacuerdo:
            otras = sorted({l for l in lecturas if l and l != valores[nombre]})
            dudas.append(f"Verifique {nombre}: '{valores[nombre]}' (otras lecturas: {', '.join(otras)})")

    # 5) Estatus General: circulo a la izquierda de cada opcion
    for opcion in OPCIONES_ESTATUS:
        primera = normalizar(opcion.split()[0])
        palabra = next((p for p in etiquetas
                        if difflib.SequenceMatcher(None, normalizar(p[0]).strip("@c) "), primera).ratio() > 0.75), None)
        if palabra is None:
            continue
        cy = palabra[2] + palabra[4] / 2
        # El OCR a veces junta el circulo con la palabra ("@Vigente"): se permite traslape
        circulo = next((c for c in marcas
                        if abs(c[1] + c[3] / 2 - cy) <= 8 and -20 <= palabra[1] - (c[0] + c[2]) <= 30), None)
        if circulo is not None:
            encontrados.add("Estatus General")
            if tiene_marca(gris, circulo, recorte=3):
                valores["Estatus General"] = opcion

    # 6) En EK9 la Direccion es siempre Calle + Colonia: si ambas se leyeron, se arma con ellas
    calle, colonia = valores.get("Calle", ""), valores.get("Colonia", "")
    if calle and colonia:
        armada = f"{calle} {colonia}"
        leida = valores.get("Dirección", "")
        if difflib.SequenceMatcher(None, leida.replace(" ", ""), armada.replace(" ", "")).ratio() < 0.9:
            dudas = [d for d in dudas if not d.startswith("Verifique Dirección")]
            dudas.append(f"Dirección armada con Calle + Colonia: '{armada}' (el OCR leyo '{leida}')")
        valores["Dirección"] = armada

    campos = [(n, valores.get(n, "")) for n, _, siempre in CAMPOS if siempre or n in encontrados]
    return campos, dudas + dudas_de(campos, encontrados)


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        with open(ruta, "rb") as f:
            campos, dudas = leer_captura(f.read())
        print(f"===== {ruta}")
        for nombre, valor in campos:
            print(f"  {nombre:20} {valor}")
        for d in dudas:
            print("  [REVISAR]", d)
