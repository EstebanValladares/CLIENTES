import os, sys

print("=" * 65)
print("       CENTRO DE INTELIGENCIA OPERATIVA - GRUPO VELAS")
print("=" * 65)
print()

# 1. Asegurar ruta base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# 2. Verificar o crear .env
env_file = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_file):
    print("=" * 65)
    print("         CONFIGURACION INICIAL DE CREDENCIALES ARYVE")
    print("=" * 65)
    print("[!] Es la primera vez que inicias el sistema en este equipo.")
    print("Por favor ingresa tus credenciales oficiales de Grupo Velas:\n")
    try:
        user = input(">> Correo de Grupo Velas: ").strip()
        pwd = input(">> Contrasena de Aryve: ").strip()
    except Exception:
        user = ""
        pwd = ""
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"EK10_USER={user}\nEK10_PASS={pwd}\nEK9_USER={user}\nEK9_PASS={pwd}\n")
    print("\n[OK] Credenciales guardadas en .env.")
else:
    print("[OK] Credenciales personales detectadas (.env cargado).")

# 3. Lanzar servidor
print("\n[INFO] Iniciando servidor en http://127.0.0.1:8000 ...")
print("[INFO] Presiona CTRL+C para detener el sistema.\n")

import webbrowser
try:
    webbrowser.open("http://127.0.0.1:8000")
except Exception:
    pass

import uvicorn
try:
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, log_level="info")
except Exception as e:
    print(f"\n[ERROR]: Fallo al iniciar el servidor: {e}")
    input("\nPresiona ENTER para salir...")
