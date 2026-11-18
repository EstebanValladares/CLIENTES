"""
Punto de Entrada Principal de KHIARA.
Modo Consola:  python run.py
Modo Servidor: python run.py --server
"""

import sys

def main():
    if "--server" in sys.argv:
        import uvicorn
        port = 8001
        print(f"\n🚀 Iniciando Microservicio de KHIARA en http://localhost:{port}...")
        uvicorn.run("khiara.api.server:app", host="0.0.0.0", port=port, reload=False)
    else:
        from khiara.cli.consola import iniciar_consola_interactiva
        iniciar_consola_interactiva()

if __name__ == "__main__":
    main()
