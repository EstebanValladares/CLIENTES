"""
Ejecutor de Scripts Python en Entorno Controlado (Sandbox) para KHIARA.
Permite a KHIARA generar, probar y ejecutar código Python de forma segura,
con límites de tiempo, captura de errores, auto-depuración y generación
de gráficos o reportes.
"""

import os
import sys
import uuid
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from khiara.core.config import SANDBOX_DIR, GRAFICAS_DIR, BASE_DIR


class SandboxPython:
    def __init__(self, tiempo_limite_segundos: int = 30):
        self.tiempo_limite = tiempo_limite_segundos
        self.dir_sandbox = SANDBOX_DIR
        self.dir_graficas = GRAFICAS_DIR
        self.dir_workspace = BASE_DIR

    def ejecutar_codigo(self, codigo_python: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Ejecuta un fragmento de código Python en un subproceso aislado.
        Captura stdout, stderr, tiempo de ejecución y detecta gráficos generados.
        """
        limite = timeout or self.tiempo_limite
        id_ejecucion = uuid.uuid4().hex[:8]
        archivo_temp = self.dir_sandbox / f"temp_run_{id_ejecucion}.py"

        # Inyectar cabecera para backend gráfico headless (Agg) y rutas seguras
        codigo_enriquecido = f"""# -*- coding: utf-8 -*-
import sys, os
from pathlib import Path

# Configurar matplotlib headless para evitar bloquear la ejecución en terminal
os.environ['MPLBACKEND'] = 'Agg'

# Permitir importar módulos del workspace
dir_ws = r'{str(self.dir_workspace)}'
dir_graf = r'{str(self.dir_graficas)}'
if dir_ws not in sys.path:
    sys.path.insert(0, dir_ws)

{codigo_python}
"""

        try:
            with open(archivo_temp, "w", encoding="utf-8") as f:
                f.write(codigo_enriquecido)

            tiempo_inicio = time.time()
            
            # Ejecutar con el mismo intérprete de Python
            proc = subprocess.run(
                [sys.executable, str(archivo_temp)],
                cwd=str(self.dir_sandbox),
                capture_output=True,
                text=True,
                timeout=limite,
                encoding="utf-8",
                errors="replace"
            )
            tiempo_total = round(time.time() - tiempo_inicio, 3)

            salida_stdout = proc.stdout.strip()
            salida_stderr = proc.stderr.strip()

            # Detectar si se guardaron gráficos en el directorio de gráficas recientemente
            graficas_generadas = []
            ahora = time.time()
            for g in self.dir_graficas.glob("*.*"):
                if g.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"} and (ahora - g.stat().st_mtime) < 60:
                    graficas_generadas.append(str(g))

            return {
                "ok": proc.returncode == 0,
                "codigo_salida": proc.returncode,
                "tiempo_segundos": tiempo_total,
                "stdout": salida_stdout,
                "stderr": salida_stderr,
                "graficas_generadas": graficas_generadas
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Tiempo de ejecución excedido (Timeout de {limite} segundos). Posible bucle infinito.",
                "tiempo_segundos": limite
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Error del sandbox: {str(e)}"
            }
        finally:
            if archivo_temp.exists():
                try:
                    archivo_temp.unlink()
                except Exception:
                    pass

    def crear_o_actualizar_archivo(self, ruta_relativa: str, contenido: str) -> Dict[str, Any]:
        """
        Crea o actualiza un archivo de código dentro del workspace o sandbox.
        Protegido contra directory traversal fuera del repositorio.
        """
        try:
            ruta_destino = (self.dir_workspace / ruta_relativa).resolve()
            # Verificar que quede dentro del workspace
            if not str(ruta_destino).startswith(str(self.dir_workspace)):
                return {"ok": False, "error": "Acceso denegado: No se puede escribir fuera del workspace."}

            ruta_destino.parent.mkdir(parents=True, exist_ok=True)
            with open(ruta_destino, "w", encoding="utf-8") as f:
                f.write(contenido)

            return {
                "ok": True,
                "archivo": str(ruta_destino.relative_to(self.dir_workspace)),
                "bytes_escritos": len(contenido.encode("utf-8"))
            }
        except Exception as e:
            return {"ok": False, "error": f"Error guardando archivo: {str(e)}"}
