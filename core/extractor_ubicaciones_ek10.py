"""
Script de Extracción Oficial: Homologación de Ubicaciones EK10 - ENK (Aryve).
Extrae el catálogo completo de equivalencias entre EK10 (Suite Web) y ENK (Enkontrol V9)
para todas las compañías (01 Aryve, 09 Punta Bete, 14 Grupo Velas, etc.).

Genera salidas limpias y estructuradas:
1. data/ek10_homologacion_ubicaciones.json
2. data/ek10_homologacion_ubicaciones.sqlite
3. data/ek10_homologacion_ubicaciones.csv
"""

import os
import sys
import time
import json
import sqlite3
import csv
import requests
import urllib3
urllib3.disable_warnings()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from USUARIOS.automation.browser import crear_driver_chrome
from USUARIOS.automation.ui_helpers import iniciar_sesion

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

JSON_OUT = os.path.join(DATA_DIR, "ek10_homologacion_ubicaciones.json")
SQLITE_OUT = os.path.join(DATA_DIR, "ek10_homologacion_ubicaciones.sqlite")
CSV_OUT = os.path.join(DATA_DIR, "ek10_homologacion_ubicaciones.csv")

# Diccionario de compañías oficiales de la Suite Aryve
COMPANIAS = [
    {"id_api": 1, "clave": "01", "nombre": "CONSTRUCCIONES ARYVE S.A. DE C.V."},
    {"id_api": 9, "clave": "09", "nombre": "PROMOTORA TURISTICA PUNTA BETE"},
    {"id_api": 2, "clave": "14", "nombre": "GRUPO VELAS DIVISION CONSTRUCCION SA DE CV"},
    {"id_api": 3, "clave": "19", "nombre": "VELAHOGARES SA DE CV"},
    {"id_api": 7, "clave": "20", "nombre": "CONSOLIDADORA"},
    {"id_api": 8, "clave": "30", "nombre": "PEDRO PERALES CASTILLO"}
]

def obtener_diccionario_enk_sybase():
    """Obtiene el catálogo de ENKid -> INFORMACIÓN ENK desde kv10Sync_ubicaciones (Sybase)."""
    enk_dict = {}
    try:
        import pyodbc
        print("Conectando a Sybase SQL Anywhere para obtener INFORMACIÓN ENK...")
        conn_ek = pyodbc.connect(
            "Driver={SQL Anywhere 11};"
            "EngineName=especial_v9;"
            "DatabaseName=EK_ADM01_11;"
            "CommLinks=tcpip(host=10.10.202.244:2544);"
            "UID=user_write;"
            "PWD=writaryb0904##;",
            timeout=10,
            readonly=True
        )
        cur = conn_ek.cursor()
        cur.execute("SELECT ENKid, ENKclave FROM DBA.kv10Sync_ubicaciones")
        for r in cur.fetchall():
            if r[0] is not None:
                enk_dict[str(r[0])] = str(r[1] or "")
        conn_ek.close()
        print(f"Diccionario ENK cargado con {len(enk_dict):,} registros.")
    except Exception as e:
        print(f"Advertencia: no se pudo consultar Sybase directamente ({e}). Se usarán datos de la API.")
    return enk_dict

def extraer_todas_las_ubicaciones():
    print("=" * 70)
    print("INICIANDO EXTRACCIÓN DE HOMOLOGACIÓN DE UBICACIONES (EK10 - ENK)")
    print("=" * 70)

    # 1. Cargar diccionario ENK complementario (Sybase)
    enk_info_map = obtener_diccionario_enk_sybase()

    # 2. Iniciar sesión y obtener cookies
    print("\nIniciando sesión segura en Aryve para obtener credenciales de API...")
    driver, service = crear_driver_chrome(detach=False, maximizar=False)
    
    try:
        driver.get("https://suite.ekloud.net:1445/Aryve/#/kontrol/DashBoards")
        iniciar_sesion(driver)
        time.sleep(2)

        session = requests.Session()
        for c in driver.get_cookies():
            session.cookies.set(c['name'], c['value'], domain=c.get('domain'))

        user_agent = driver.execute_script("return navigator.userAgent;")
    finally:
        driver.quit()

    headers = {
        'User-Agent': user_agent,
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Referer': 'https://suite.ekloud.net:1445/Aryve/'
    }

    url_api = "https://suite.ekloud.net:1445/Aryve/base/Kontrol/InterfaceConversionCatalogos/api/GetConversionCatalogos"

    registros_totales = []
    resumen_companias = {}

    for cia in COMPANIAS:
        cia_id = cia["id_api"]
        cia_cve = cia["clave"]
        cia_nom = cia["nombre"]
        
        print(f"\n[Extrayendo] Cia {cia_cve} - {cia_nom} (ID API: {cia_id})...")
        payload = {"parametros": {"IdEntidad": 4, "IdCompania": cia_id}}
        
        try:
            resp = session.put(url_api, headers=headers, json=payload, verify=False, timeout=60)
            if resp.status_code == 200:
                raw_items = resp.json()
                print(f"  -> {len(raw_items):,} registros obtenidos.")
                
                con_enk = 0
                for item in raw_items:
                    id_ek10 = item.get("IdEK10")
                    clave_ek10 = (item.get("ClaveEK10") or "").strip()
                    nombre_ek10 = (item.get("NombreEK10") or "").strip()
                    id_enk_raw = item.get("idENK")
                    id_enk = str(id_enk_raw).strip() if id_enk_raw is not None and str(id_enk_raw).strip() not in ("", "None", "0") else None
                    
                    if id_enk:
                        con_enk += 1
                        info_enk = enk_info_map.get(id_enk) or item.get("NombreENK") or item.get("ClaveENK") or ""
                    else:
                        info_enk = ""

                    registro = {
                        "id_mapeo": item.get("ID"),
                        "compania_clave": cia_cve,
                        "compania_nombre": cia_nom,
                        "id_ek10": id_ek10,
                        "clave_ek10": clave_ek10,
                        "nombre_ek10": nombre_ek10,
                        "id_enk": id_enk,
                        "informacion_enk": info_enk,
                        "version": item.get("Version")
                    }
                    registros_totales.append(registro)

                resumen_companias[cia_cve] = {
                    "nombre": cia_nom,
                    "total_registros": len(raw_items),
                    "con_id_enk": con_enk,
                    "sin_id_enk": len(raw_items) - con_enk
                }
            else:
                print(f"  -> Error HTTP {resp.status_code}: {resp.text[:200]}")
                resumen_companias[cia_cve] = {"error": f"HTTP {resp.status_code}", "total_registros": 0}
        except Exception as err:
            print(f"  -> Error extrayendo Cia {cia_cve}: {err}")
            resumen_companias[cia_cve] = {"error": str(err), "total_registros": 0}

    print("\n" + "=" * 70)
    print(f"TOTAL GENERAL EXTRAÍDO: {len(registros_totales):,} registros de Ubicaciones")
    print("=" * 70)

    # 3. Guardar en JSON estructurado
    print(f"\n1. Guardando archivo JSON en: {JSON_OUT}")
    json_data = {
        "fecha_extraccion": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_registros": len(registros_totales),
        "resumen_companias": resumen_companias,
        "registros": registros_totales
    }
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # 4. Guardar en SQLite estructurado
    print(f"2. Guardando base de datos SQLite en: {SQLITE_OUT}")
    if os.path.exists(SQLITE_OUT):
        os.remove(SQLITE_OUT)

    conn_sqlite = sqlite3.connect(SQLITE_OUT)
    cur_sqlite = conn_sqlite.cursor()

    cur_sqlite.execute("""
    CREATE TABLE homologacion_ubicaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_mapeo INTEGER,
        compania_clave TEXT,
        compania_nombre TEXT,
        id_ek10 INTEGER,
        clave_ek10 TEXT,
        nombre_ek10 TEXT,
        id_enk TEXT,
        informacion_enk TEXT,
        version TEXT
    )
    """)

    cur_sqlite.execute("CREATE INDEX idx_id_ek10 ON homologacion_ubicaciones(id_ek10)")
    cur_sqlite.execute("CREATE INDEX idx_clave_ek10 ON homologacion_ubicaciones(clave_ek10)")
    cur_sqlite.execute("CREATE INDEX idx_id_enk ON homologacion_ubicaciones(id_enk)")
    cur_sqlite.execute("CREATE INDEX idx_cia ON homologacion_ubicaciones(compania_clave)")
    cur_sqlite.execute("CREATE INDEX idx_nom_ek10 ON homologacion_ubicaciones(nombre_ek10)")

    cur_sqlite.executemany("""
    INSERT INTO homologacion_ubicaciones (
        id_mapeo, compania_clave, compania_nombre, id_ek10, clave_ek10, nombre_ek10, id_enk, informacion_enk, version
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            r["id_mapeo"],
            r["compania_clave"],
            r["compania_nombre"],
            r["id_ek10"],
            r["clave_ek10"],
            r["nombre_ek10"],
            r["id_enk"],
            r["informacion_enk"],
            r["version"]
        ) for r in registros_totales
    ])
    conn_sqlite.commit()
    conn_sqlite.close()

    # 5. Guardar en CSV para consulta inmediata en Excel
    print(f"3. Guardando archivo CSV en: {CSV_OUT}")
    with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID_MAPEO", "COMPANIA_CLAVE", "COMPANIA_NOMBRE", "ID_EK10", "CLAVE_EK10", "NOMBRE_EK10", "ID_ENK", "INFORMACION_ENK"])
        for r in registros_totales:
            writer.writerow([
                r["id_mapeo"],
                r["compania_clave"],
                r["compania_nombre"],
                r["id_ek10"],
                r["clave_ek10"],
                r["nombre_ek10"],
                r["id_enk"] or "",
                r["informacion_enk"] or ""
            ])

    print("\n¡EXTRACCIÓN Y GUARDADO COMPLETADOS CON ÉXITO!")
    for cve, res in resumen_companias.items():
        print(f" - Cia {cve} ({res.get('nombre')}): {res.get('total_registros', 0):,} ubicaciones (Mapeadas a ENK: {res.get('con_id_enk', 0):,})")

if __name__ == "__main__":
    extraer_todas_las_ubicaciones()
