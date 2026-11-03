"""Pruebas de la validacion cruzada (no requieren Ollama ni OCR)."""

from extraer_inputs.ocr import LineaOCR
from extraer_inputs.validacion import campo_critico, recuperar_por_posicion, validar


def _l(texto, x0, y0, x1, y1):
    return LineaOCR(texto, (x0, y0, x1, y1), 0.99)


LINEAS = [
    _l("PROVEEDOR", 60, 130, 200, 155), _l("PRV-004512", 78, 177, 260, 205),
    _l("NOMBRE", 60, 250, 160, 275), _l("MATERIALES Y ACEROS DEL GOLFO SA DE CV", 78, 297, 700, 325),
    _l("CODIGO POSTAL", 60, 490, 260, 515), _l("89230", 78, 537, 170, 565),
    _l("RFC: MAG010203K64", 60, 610, 400, 640),
]


def test_campo_critico_sinonimos_y_acentos():
    assert campo_critico("Dirección:") == "DIRECCION"
    assert campo_critico("C.P.") == "CODIGO POSTAL"
    assert campo_critico("Razón social") == "NOMBRE"
    assert campo_critico("R.F.C.") == "RFC"
    assert campo_critico("TELEFONO") == ""


def test_usa_texto_ocr_si_similitud_alta():
    # El modelo confundio O por 0; el OCR tiene el texto literal
    campos = validar([{"etiqueta": "NOMBRE", "valor": "MATERIALES Y ACER0S DEL GOLFO SA DE CV", "tipo": "texto"},
                      {"etiqueta": "TELEFONO", "valor": "833 214 5567", "tipo": "texto"}],
                     LINEAS + [_l("833 214 5566", 78, 700, 300, 730)])
    nombre = next(c for c in campos if c.critico == "NOMBRE")
    assert nombre.valor == "MATERIALES Y ACEROS DEL GOLFO SA DE CV" and nombre.similitud >= 0.9
    # Critico: OCR y modelo difieren -> se usa el OCR pero se marca para revisar
    assert nombre.revisar and nombre.valor_modelo == "MATERIALES Y ACER0S DEL GOLFO SA DE CV"
    # No critico: se usa el OCR sin marcar
    tel = next(c for c in campos if c.etiqueta == "TELEFONO")
    assert tel.valor == "833 214 5566" and not tel.revisar


def test_critico_identico_en_ocr_y_modelo_no_se_marca():
    campos = validar([{"etiqueta": "NOMBRE", "valor": "MATERIALES Y ACEROS DEL GOLFO SA DE CV", "tipo": "texto"}],
                     LINEAS)
    nombre = next(c for c in campos if c.critico == "NOMBRE")
    assert nombre.similitud == 1.0 and not nombre.revisar


def test_marca_revisar_si_similitud_baja():
    campos = validar([{"etiqueta": "PROVEEDOR", "valor": "XYZ-99", "tipo": "texto"}], LINEAS)
    prov = next(c for c in campos if c.critico == "PROVEEDOR")
    assert prov.revisar and prov.valor == "XYZ-99"


def test_regex_rfc_y_cp():
    campos = validar([{"etiqueta": "RFC", "valor": "MAG010203K64", "tipo": "texto"},
                      {"etiqueta": "CODIGO POSTAL", "valor": "8923", "tipo": "numero"}], LINEAS)
    rfc = next(c for c in campos if c.critico == "RFC")
    cp = next(c for c in campos if c.critico == "CODIGO POSTAL")
    assert rfc.valor == "MAG010203K64" and not rfc.revisar  # coincide con lo que sigue a "RFC:"
    assert cp.revisar  # 4 digitos: no pasa la regex


def test_valor_pegado_a_otra_etiqueta_en_la_linea_ocr():
    # Captura real EK9: el OCR junta el numero de proveedor con la etiqueta de la casilla vecina
    lineas = [_l("Proveedor:", 30, 70, 110, 85), _l("11571 Persona Fisica", 150, 70, 330, 85),
              _l("Deleg. ó Mpio. TAMAULIPAS", 460, 170, 660, 185)]
    campos = validar([{"etiqueta": "Proveedor", "valor": "11571", "tipo": "numero"},
                      {"etiqueta": "Deleg. ó Mpio.", "valor": "TAMAULIPAS", "tipo": "texto"}], lineas)
    assert all(c.similitud == 1.0 and not c.revisar for c in campos if c.etiqueta in ("Proveedor", "Deleg. ó Mpio."))


def test_solo_difieren_en_espacios_conserva_modelo():
    # Captura real EK9: el OCR perdio el espacio entre "BAJA" y "ALTAMIRA"
    lineas = [_l("MARIANO MATAMOROS 503 B PLANTA BAJAALTAMIRA CENTRO", 150, 120, 900, 135)]
    modelo = "MARIANO MATAMOROS 503 B PLANTA BAJA ALTAMIRA CENTRO"
    campos = validar([{"etiqueta": "Dirección", "valor": modelo, "tipo": "texto"}], lineas)
    d = next(c for c in campos if c.critico == "DIRECCION")
    assert d.valor == modelo and not d.revisar


def test_rfc_con_guiones_como_ek9():
    lineas = [_l("R.F.C.:", 60, 10, 120, 30), _l("GMA-130830-MZ5", 130, 10, 330, 30)]
    campos = validar([{"etiqueta": "R.F.C.", "valor": "GMA-130830-MZ5", "tipo": "texto"}], lineas)
    rfc = next(c for c in campos if c.critico == "RFC")
    assert rfc.valor == "GMA-130830-MZ5" and not rfc.revisar


def test_null_se_recupera_por_posicion():
    assert recuperar_por_posicion("CODIGO POSTAL", LINEAS) == "89230"   # debajo de la etiqueta
    assert recuperar_por_posicion("RFC", LINEAS) == "MAG010203K64"      # en la misma linea tras ':'
    campos = validar([{"etiqueta": "CODIGO POSTAL", "valor": None, "tipo": "numero"}], LINEAS)
    cp = next(c for c in campos if c.critico == "CODIGO POSTAL")
    assert cp.valor == "89230" and cp.revisar


def test_criticos_faltantes_se_agregan_para_revisar():
    campos = validar([], LINEAS)
    criticos = {c.critico: c for c in campos if c.critico}
    assert set(criticos) == {"PROVEEDOR", "NOMBRE", "DIRECCION", "CODIGO POSTAL", "RFC"}
    assert all(c.revisar for c in criticos.values())
    assert criticos["PROVEEDOR"].valor == "PRV-004512"


def test_modo_campos_json_plano():
    # Formulario conocido: el modelo devuelve {etiqueta: valor}; faltantes y null -> valor None
    from extraer_inputs.vision import _esquema_campos, _validar_campos
    etiquetas = ["Proveedor", "A. Paterno", "Código Postal"]
    assert _esquema_campos(etiquetas)["required"] == etiquetas
    datos = _validar_campos('{"Proveedor": "11571", "A. Paterno": null, "Código Postal": ""}', etiquetas)
    assert datos["campos"] == [{"etiqueta": "Proveedor", "valor": "11571", "tipo": "texto"},
                               {"etiqueta": "A. Paterno", "valor": None, "tipo": "vacio"},
                               {"etiqueta": "Código Postal", "valor": "", "tipo": "vacio"}]
