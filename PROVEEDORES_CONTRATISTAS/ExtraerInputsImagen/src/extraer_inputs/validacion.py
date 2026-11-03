"""Paso 4: validacion cruzada entre el modelo de vision y el OCR (rapidfuzz + regex)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from rapidfuzz import fuzz, process

from extraer_inputs import config
from extraer_inputs.ocr import LineaOCR

REGEX_CRITICOS: dict[str, re.Pattern] = {
    # Persona moral: 3 letras; fisica: 4. Luego AAMMDD y homoclave de 3. EK9 lo muestra con
    # guiones (GMA-130830-MZ5), por eso se aceptan opcionales.
    "RFC": re.compile(r"^[A-ZÑ&]{3,4}-?\d{6}-?[A-Z0-9]{3}$"),
    "CODIGO POSTAL": re.compile(r"^\d{5}$"),
    "PROVEEDOR": re.compile(r"^\S.*$"),
    "NOMBRE": re.compile(r"^\S.{2,}$"),
    "DIRECCION": re.compile(r"^\S.{2,}$"),
}


@dataclass
class CampoValidado:
    etiqueta: str
    valor: str
    tipo: str
    valor_modelo: str | None
    valor_ocr: str
    similitud: float | None
    revisar: bool
    critico: str          # nombre del campo critico ("" si no lo es)
    motivo: str           # por que se marca revisar

    def como_dict(self) -> dict:
        return asdict(self)


def normalizar_etiqueta(texto: str) -> str:
    """'Código Postal:*' -> 'CODIGO POSTAL'; 'R.F.C.' -> 'R F C'."""
    sin_acentos = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", sin_acentos)).strip().upper()


_SINONIMOS = {normalizar_etiqueta(s): critico for critico, sinonimos in config.CAMPOS_CRITICOS.items()
              for s in sinonimos}


def campo_critico(etiqueta: str) -> str:
    return _SINONIMOS.get(normalizar_etiqueta(etiqueta), "")


def _espacios(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _candidatos(lineas: list[LineaOCR]) -> list[str]:
    """Textos del OCR para comparar: cada linea completa, lo que sigue a ':' (etiqueta: valor) y
    cada fragmento de palabras consecutivas, porque el OCR suele juntar en una linea el valor con
    la etiqueta vecina (ej. "11571 Persona Fisica", "Deleg. ó Mpio. TAMAULIPAS")."""
    candidatos: list[str] = []
    for linea in lineas:
        texto = _espacios(linea.texto)
        candidatos.append(texto)
        if ":" in texto:
            resto = texto.split(":", 1)[1].strip()
            if resto:
                candidatos.append(resto)
        palabras = texto.split(" ")
        if len(palabras) <= 25:
            candidatos.extend(" ".join(palabras[i:j]) for i in range(len(palabras))
                              for j in range(i + 1, len(palabras) + 1) if j - i < len(palabras))
    return list(dict.fromkeys(candidatos))


def _es_etiqueta(linea: LineaOCR, etiqueta: str) -> bool:
    objetivo = normalizar_etiqueta(etiqueta)
    texto = normalizar_etiqueta(linea.texto.split(":", 1)[0])
    return bool(objetivo) and (texto == objetivo or fuzz.ratio(texto, objetivo) / 100 >= config.UMBRAL_ETIQUETA)


def recuperar_por_posicion(etiqueta: str, lineas: list[LineaOCR]) -> str:
    """Valor de la etiqueta segun el OCR: lo que sigue a ':' en la misma linea, la linea a la derecha
    (misma altura) o la linea de abajo mas cercana."""
    for lin in lineas:
        if not _es_etiqueta(lin, etiqueta):
            continue
        if ":" in lin.texto and lin.texto.split(":", 1)[1].strip():
            return _espacios(lin.texto.split(":", 1)[1])
        alto = lin.caja[3] - lin.caja[1]
        derecha = [o for o in lineas if o is not lin and o.caja[0] >= lin.caja[2] - 2
                   and abs(o.centro_y - lin.centro_y) <= alto * 0.6]
        if derecha:
            return _espacios(min(derecha, key=lambda o: o.caja[0]).texto)
        abajo = [o for o in lineas if o is not lin and o.caja[1] >= lin.caja[3] - 2
                 and o.caja[0] < lin.caja[2] + 3 * alto and o.caja[2] > lin.caja[0] - 3 * alto]
        if abajo:
            return _espacios(min(abajo, key=lambda o: o.caja[1]).texto)
    return ""


def validar(campos: list[dict], lineas: list[LineaOCR]) -> list[CampoValidado]:
    """Cruza cada campo del modelo con el OCR y marca los que hay que revisar."""
    candidatos = _candidatos(lineas)
    resultado: list[CampoValidado] = []
    vistos_criticos: set[str] = set()
    for c in campos:
        etiqueta, valor_modelo, tipo = c["etiqueta"], c["valor"], c["tipo"]
        critico = campo_critico(etiqueta)
        vistos_criticos.add(critico)
        resultado.append(_validar_campo(etiqueta, valor_modelo, tipo, critico, candidatos, lineas))
    # Campos criticos que el modelo no devolvio: se buscan en el OCR y se marcan para revisar
    for critico, sinonimos in config.CAMPOS_CRITICOS.items():
        if critico in vistos_criticos:
            continue
        valor_ocr = next((v for s in sinonimos if (v := recuperar_por_posicion(s, lineas))), "")
        resultado.append(CampoValidado(critico, valor_ocr, "texto", None, valor_ocr, None, True, critico,
                                       "el modelo no devolvio este campo critico; valor tomado del OCR por posicion"
                                       if valor_ocr else "campo critico no encontrado en la imagen"))
    return resultado


def _validar_campo(etiqueta, valor_modelo, tipo, critico, candidatos, lineas) -> CampoValidado:
    motivos: list[str] = []
    valor_ocr, similitud = "", None
    if valor_modelo is None:
        # El modelo no pudo leerlo: recuperar del OCR por posicion
        valor = valor_ocr = recuperar_por_posicion(etiqueta, lineas)
        motivos.append("el modelo devolvio null; valor tomado del OCR por posicion" if valor
                       else "el modelo devolvio null y no se encontro en el OCR")
        revisar = True
    elif tipo in ("checkbox", "vacio") or valor_modelo == "":
        valor, revisar = valor_modelo, False  # sin texto que comparar
    else:
        valor = _espacios(valor_modelo)
        mejor = process.extractOne(valor, candidatos, scorer=fuzz.ratio) if candidatos else None
        if mejor:
            valor_ocr, similitud = mejor[0], round(mejor[1] / 100, 3)
        if similitud is not None and similitud >= config.UMBRAL_SIMILITUD \
                and re.sub(r"\s+", "", valor_ocr) == re.sub(r"\s+", "", valor):
            # Solo difieren en espacios: el OCR suele perderlos ("PLANTA BAJAALTAMIRA"); se
            # conserva el texto del modelo, que respeta la separacion visual
            revisar = False
        elif similitud is not None and similitud >= config.UMBRAL_SIMILITUD:
            # En un campo critico, si OCR y modelo no coinciden exactamente no se puede saber cual
            # acerto (ej. el OCR leyo "MAGO10203K64" y el modelo "MAG010203K64"): se marca.
            difieren = valor_ocr != valor
            valor, revisar = valor_ocr, False  # el OCR es caracter por caracter
            if critico and difieren:
                revisar = True
                motivos.append(f"OCR y modelo difieren (similitud {similitud:.2f}); confirmar contra valor_modelo")
        else:
            revisar = True
            motivos.append(f"similitud con el OCR {similitud if similitud is not None else 0:.2f} < "
                           f"{config.UMBRAL_SIMILITUD}")
    if critico:
        if not REGEX_CRITICOS[critico].match(_espacios(valor or "")):
            revisar = True
            motivos.append(f"{critico} con formato invalido o vacio")
    return CampoValidado(etiqueta, valor or "", tipo, valor_modelo, valor_ocr, similitud, revisar, critico,
                         "; ".join(motivos))
