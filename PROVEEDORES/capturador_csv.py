import csv
import os
from generador_nombres import (
    generar_clave_proveedor,
    generar_nombre_corto,
    generar_clave_persona_fisica,
    generar_nombre_corto_persona_fisica
)

COLUMNAS_CSV = [
    "TIPO PERSONA", "CLAVE", "NOMBRE", "PATERNO", "MATERNO",
    "RFC", "NOMBRE CORTO", "CALLE", "EXT", "COLONIA", "CP"
]


def capturar_datos_proveedor(ruta_csv="datos.csv"):
    print("\n" + "=" * 65)
    print("      [CAPTURA] CAPTURA DE DATOS PARA NUEVO PROVEEDOR")
    print("=" * 65)

    while True:
        # 1. Tipo de persona
        print("\nSeleccione el Tipo de Persona:")
        print("  [1] MORAL (por defecto)")
        print("  [2] FÍSICA")
        opc_tipo = input("Opción (1/2 o presione Enter para MORAL): ").strip()
        es_fisica = opc_tipo in ["2", "F", "FISICA", "FÍSICA"]
        tipo_persona = "FÍSICA" if es_fisica else "MORAL"

        paterno = ""
        materno = ""

        if es_fisica:
            print("\n--- DATOS DE PERSONA FÍSICA ---")
            nombre = input("1. Nombre(s): ").strip().upper()
            if not nombre:
                print("[AVISO] El nombre no puede estar vacío. Intenta de nuevo.")
                continue

            paterno = input("2. Apellido Paterno: ").strip().upper()
            materno = input("3. Apellido Materno (opcional): ").strip().upper()
            rfc = input("4. RFC: ").strip().upper()
            calle = input("5. Calle: ").strip().upper()
            ext = input("6. No. Exterior: ").strip().upper()
            colonia = input("7. Colonia / Asentamiento: ").strip().upper()
            cp = input("8. Código Postal (CP): ").strip().upper()

            # Generación automática para Persona Física
            clave = generar_clave_persona_fisica(nombre, paterno, max_chars=20).upper()
            nombre_corto = generar_nombre_corto_persona_fisica(nombre, paterno, max_chars=20).upper()

        else:
            print("\n--- DATOS DE PERSONA MORAL ---")
            nombre = input("1. Nombre completo / Razón Social: ").strip().upper()
            if not nombre:
                print("[AVISO] El nombre no puede estar vacío. Intenta de nuevo.")
                continue

            rfc = input("2. RFC: ").strip().upper()
            calle = input("3. Calle: ").strip().upper()
            ext = input("4. No. Exterior: ").strip().upper()
            colonia = input("5. Colonia / Asentamiento: ").strip().upper()
            cp = input("6. Código Postal (CP): ").strip().upper()

            # Generación automática para Persona Moral
            clave = generar_clave_proveedor(nombre, max_chars=20).upper()
            nombre_corto = generar_nombre_corto(nombre, max_chars=20).upper()

        # Resumen en pantalla
        print("\n" + "-" * 60)
        print(" [RESUMEN] RESUMEN DEL PROVEEDOR A GUARDAR:")
        print("-" * 60)
        print(f"  • TIPO PERSONA     : {tipo_persona}")
        print(f"  • NOMBRE           : {nombre}")
        if es_fisica:
            print(f"  • APELLIDO PATERNO : {paterno}")
            print(f"  • APELLIDO MATERNO : {materno}")
        print(f"  • CLAVE (Auto)     : {clave}")
        print(f"  • NOMBRE CORTO     : {nombre_corto}")
        print(f"  • RFC              : {rfc}")
        print(f"  • CALLE            : {calle}")
        print(f"  • NO. EXTERIOR     : {ext}")
        print(f"  • COLONIA          : {colonia}")
        print(f"  • CODIGO POSTAL    : {cp}")
        print("-" * 60)

        confirmacion = input("\n¿Los datos son correctos? (S/N): ").strip().upper()
        if confirmacion == 'S':
            registro_final = {
                "TIPO PERSONA": str(tipo_persona).strip().upper(),
                "CLAVE": str(clave).strip().upper(),
                "NOMBRE": str(nombre).strip().upper(),
                "PATERNO": str(paterno).strip().upper(),
                "MATERNO": str(materno).strip().upper(),
                "RFC": str(rfc).strip().upper(),
                "NOMBRE CORTO": str(nombre_corto).strip().upper(),
                "CALLE": str(calle).strip().upper(),
                "EXT": str(ext).strip().upper(),
                "COLONIA": str(colonia).strip().upper(),
                "CP": str(cp).strip().upper()
            }
            guardar_en_csv(ruta_csv, registro_final)
            return registro_final
        else:
            print("\nReiniciando captura...")


def guardar_en_csv(ruta_csv, registro):
    """Guarda o anexa el registro en el archivo CSV respetando la estructura."""
    existe_archivo = os.path.exists(ruta_csv)
    contenido_previo = ""
    
    if existe_archivo:
        with open(ruta_csv, mode="r", encoding="utf-8") as f:
            contenido_previo = f.read()

    with open(ruta_csv, mode="a", newline="\n", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
        
        # Escribir cabecera solo si el archivo es nuevo o está vacío
        if not existe_archivo or len(contenido_previo.strip()) == 0:
            escritor.writeheader()
        elif not contenido_previo.endswith("\n"):
            f.write("\n")

        escritor.writerow(registro)
        f.flush()
        os.fsync(f.fileno())

    print(f"\n[OK] Proveedor guardado con éxito en '{ruta_csv}'.")

