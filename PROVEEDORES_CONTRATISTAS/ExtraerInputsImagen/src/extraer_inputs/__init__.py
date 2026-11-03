"""Extraccion local de los datos de los inputs de capturas de pantalla (PNG/JPG).

Pipeline: preprocesado (Pillow) -> estructura (Ollama qwen2.5vl) -> texto literal (OCR)
-> validacion cruzada (rapidfuzz + regex) -> CSV. Todo se ejecuta en el equipo; ninguna
imagen sale de el. No depende de Selenium ni del navegador.
"""

__version__ = "1.0.0"
