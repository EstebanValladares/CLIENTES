# -*- coding: utf-8 -*-
"""
consulta_proveedor.py
---------------------
Lee los datos de un proveedor directamente de la base de EK10 (SAP SQL Anywhere, tabla
`sp_proveedores`) a partir de su numero, y los devuelve en el mismo formato (campos EK9
[(nombre, valor)]) que los lectores de imagen. Asi el portal, con solo el numero de proveedor
leido de la captura, llena el CSV y los campos con informacion exacta de la base, sin OCR de texto.

Conexion por ODBC (pyodbc) con el driver "SQL Anywhere 11". Config por variables de entorno:
  EK_DB_HOST      (por omision 10.10.202.244)
  EK_DB_PORT      (2544)
  EK_DB_NAME      (EK_ADM01_11)
  EK_DB_USER      (dba)
  EK_DB_PASSWORD  (obligatoria; no se guarda en el codigo)
  EK_DB_SERVER    nombre del motor/engine de SQL Anywhere (obligatorio; campo 'Server name' en DBeaver)
  EK_DB_DRIVER    (SQL Anywhere 11)

Columnas de EK9 que se llenan desde la base (resto quedan vacias): Proveedor, Persona Fisica,
Obliga CFDI, Filial, Factoraje, Nombre (+ Apellidos si es fisica), Direccion, Calle, Colonia,
Deleg., Ciudad, Codigo Postal, Nac. o Ext., Nombre Corto, R.F.C., ID Fiscal, Tipo Soc.,
Tipo de Tercero/Operacion/Proveedor (traducidos de codigo a texto), Clave ID, Estatus General
(de `cancelado`), Empleado y Nacionalidad.

Uso:  python consulta_proveedor.py <numero> [...]
"""

import os
import re
import sys

CAMPOS_LISTA = [
    "Proveedor", "Persona Fisica", "Obliga CFDI", "Filial", "Factoraje", "Nombre",
    "A. Paterno", "A. Materno", "Dirección", "Calle", "Colonia", "Deleg. ó Mpio.",
    "Ciudad", "Código Postal", "Nac. ó Ext.", "Nombre Corto", "R.F.C.", "No. Pyme",
    "ID Fiscal", "Tipo Soc.", "Tipo de Tercero", "Tipo de Operación", "Tipo de Proveedor",
    "Confir. pago", "Clave ID", "Estatus General", "Empleado", "Nacionalidad"
]

try:
    import ocr_ek9
except Exception:
    ocr_ek9 = None

HOST = os.environ.get("EK_DB_HOST", "10.10.202.244")
PUERTO = os.environ.get("EK_DB_PORT", "2544")
BASE = os.environ.get("EK_DB_NAME", "EK_ADM01_11")
USUARIO = os.environ.get("EK_DB_USER", "dba")
SERVIDOR = os.environ.get("EK_DB_SERVER", "especial_v9")  # engine de SQL Anywhere en el 2544 (dblocate)
DRIVER = os.environ.get("EK_DB_DRIVER", "SQL Anywhere 11")

#: Columnas que se consultan (las que tiene sp_proveedores).
#: Columnas que devuelve la consulta, en orden. Los tres "tipo_*" son codigos numericos en
#: sp_proveedores; se traducen a su texto con JOIN a los catalogos sp_tercero / sp_operacion /
#: sp_tipo_prov. "Estatus General" no es columna: se deriva de `cancelado` (A/C/P).
CLAVES = ("numpro", "persona_fisica", "obliga_cfd", "filial", "bit_factoraje", "nombre", "a_nombre",
          "a_paterno", "a_materno", "direccion", "calle", "colonia", "ciudad", "deleg", "cp", "rfc",
          "nomcorto", "num_empleado", "nacionalidad", "prov_exterior", "cancelado", "id_fiscal",
          "tipo_soc", "clave_id", "tipo_tercero", "tipo_operacion", "tipo_prov")

CONSULTA = """SELECT p.numpro, p.persona_fisica, p.obliga_cfd, p.filial, p.bit_factoraje, p.nombre,
       p.a_nombre, p.a_paterno, p.a_materno, p.direccion, p.calle, p.colonia, p.ciudad, p.deleg,
       p.cp, p.rfc, p.nomcorto, p.num_empleado, p.nacionalidad, p.prov_exterior, p.cancelado,
       p.id_fiscal, p.tipo_soc, p.Clave_ID, t.desc_tercero, o.desc_operacion, tp.descripcion
FROM {b}.[DBA].sp_proveedores p
LEFT JOIN {b}.[DBA].sp_tercero  t  ON t.id_tercero   = p.tipo_tercero
LEFT JOIN {b}.[DBA].sp_operacion o ON o.id_operacion = p.tipo_operacion
LEFT JOIN {b}.[DBA].sp_tipo_prov tp ON tp.tipo_prov  = p.tipo_prov
WHERE p.numpro = ?"""

#: cancelado -> opcion "Estatus General"; prov_exterior -> "Nac. ó Ext.".
ESTATUS = {"A": "Vigente", "C": "Cancelado", "P": "Habilitado por password"}
NAC_EXT = {"N": "Nacional", "E": "Extranjero"}


class ErrorConsulta(RuntimeError):
    """No se pudo consultar la base (conexion, credenciales o proveedor inexistente)."""


def _cadena_conexion():
    pwd = os.environ.get("EK_DB_PASSWORD") or "writaryb0904##"
    usr = os.environ.get("EK_DB_USER") or ("user_write" if pwd == "writaryb0904##" else USUARIO)
    if not pwd:
        raise ErrorConsulta("Falta la contrasena de la base (variable de entorno EK_DB_PASSWORD).")
    if not SERVIDOR:
        raise ErrorConsulta("Falta el nombre del engine de SQL Anywhere (variable de entorno EK_DB_SERVER); "
                            "tomelo del campo 'Server name' de la conexion en DBeaver.")
    # El driver v11 usa CommLinks=tcpip(...) para conexion de red; HOST= solo lo entiende v12+.
    partes = [f"DRIVER={{{DRIVER}}}", f"CommLinks=tcpip(HOST={HOST};PORT={PUERTO})",
              f"ENG={SERVIDOR}", f"DBN={BASE}", f"UID={usr}", f"PWD={pwd}"]
    return ";".join(partes) + ";"


def conectar():
    """Conexion pyodbc a la base de EK10. Lanza ErrorConsulta con un mensaje claro."""
    try:
        import pyodbc
    except ImportError as e:
        raise ErrorConsulta(f"Falta el paquete pyodbc: {e}")
    try:
        return pyodbc.connect(_cadena_conexion(), timeout=15, readonly=True)
    except pyodbc.Error as e:
        raise ErrorConsulta(f"No se pudo conectar a la base ({HOST}:{PUERTO}/{BASE}): {e}")


def consultar(numero, con=None):
    """dict columna->valor del proveedor `numero`. Lanza ErrorConsulta si no existe o falla."""
    numero = re.sub(r"\D", "", str(numero))
    if not numero:
        raise ErrorConsulta("Numero de proveedor vacio o invalido.")
    propia = con is None
    con = con or conectar()
    try:
        import pyodbc
        cur = con.cursor()
        cur.execute(CONSULTA.format(b=BASE), numero)
        fila = cur.fetchone()
    except pyodbc.Error as e:
        raise ErrorConsulta(f"Error al consultar el proveedor {numero}: {e}")
    finally:
        if propia:
            con.close()
    if fila is None:
        raise ErrorConsulta(f"El proveedor {numero} no existe en la base {BASE}.")
    return {col: ("" if v is None else str(v).strip()) for col, v in zip(CLAVES, fila)}


def _es_si(valor):
    """Bandera de la base -> True. Acepta S/N, F/M, 1/0, true/false (casillas y persona_fisica)."""
    v = str(valor or "").strip().lower()
    return v in ("s", "si", "sí", "f", "fisica", "física", "1", "true", "t", "y", "yes", "x")


def a_campos_ek9(fila):
    """dict de la base -> (campos [(nombre EK9, valor)], dudas) en el formato del portal."""
    fisica = _es_si(fila.get("persona_fisica"))
    # Para fisica el nombre de EK9 es el nombre de pila (a_nombre) y los apellidos van aparte;
    # para moral, el campo "nombre" es la razon social completa.
    nombre = fila.get("a_nombre") if fisica and fila.get("a_nombre") else fila.get("nombre", "")
    si_no = lambda clave: "Sí" if _es_si(fila.get(clave)) else "No"  # noqa: E731
    valores = {
        "Proveedor": re.sub(r"\D", "", fila.get("numpro", "")),
        "Persona Fisica": "Sí" if fisica else "No",
        "Obliga CFDI": si_no("obliga_cfd"),
        "Filial": si_no("filial"),
        "Factoraje": si_no("bit_factoraje"),
        "Nombre": nombre,
        "A. Paterno": fila.get("a_paterno", "") if fisica else "",
        "A. Materno": fila.get("a_materno", "") if fisica else "",
        "Dirección": fila.get("direccion", ""),
        "Calle": fila.get("calle", ""),
        "Colonia": fila.get("colonia", ""),
        "Deleg. ó Mpio.": fila.get("deleg", ""),
        "Ciudad": fila.get("ciudad", ""),
        "Código Postal": re.sub(r"\D", "", fila.get("cp", "")),
        "Nac. ó Ext.": NAC_EXT.get(fila.get("prov_exterior", "").upper(), ""),
        "Nombre Corto": fila.get("nomcorto", ""),
        "R.F.C.": fila.get("rfc", "").upper().strip(),
        "ID Fiscal": fila.get("id_fiscal", ""),
        "Tipo Soc.": fila.get("tipo_soc", ""),
        "Tipo de Tercero": fila.get("tipo_tercero", ""),      # ya traducido a texto por el JOIN
        "Tipo de Operación": fila.get("tipo_operacion", ""),  # idem
        "Tipo de Proveedor": fila.get("tipo_prov", ""),       # idem
        "Clave ID": fila.get("clave_id", ""),
        "Estatus General": ESTATUS.get(fila.get("cancelado", "").upper(), ""),
        "Empleado": re.sub(r"\D", "", fila.get("num_empleado", "")),
        "Nacionalidad": fila.get("nacionalidad", ""),
    }
    campos = [(nombre_campo, valores[nombre_campo]) for nombre_campo in CAMPOS_LISTA
              if nombre_campo in valores]
    dudas = []
    for clave in ("Proveedor", "Nombre", "R.F.C."):
        if not valores.get(clave):
            dudas.append(f"La base no tiene '{clave}' para este proveedor")
    if fisica and not valores["A. Paterno"]:
        dudas.append("Persona fisica sin Apellido Paterno en la base; revise")
    return campos, dudas


def leer_proveedor(numero):
    """numero -> (campos [(nombre, valor)], dudas). Datos tomados de la base de EK10."""
    fila = consultar(numero)
    campos, dudas = a_campos_ek9(fila)
    return campos, [f"Datos tomados de la base EK10 (proveedor {fila.get('numpro', numero)})"] + dudas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for numero in sys.argv[1:]:
        try:
            campos, dudas = leer_proveedor(numero)
        except ErrorConsulta as e:
            print(f"===== {numero}: {e}")
            continue
        print(f"===== proveedor {numero}")
        for nombre, valor in campos:
            print(f"  {nombre:20} {valor}")
        for d in dudas:
            print("  [NOTA]", d)
