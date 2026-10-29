"""NUCLEO: infraestructura compartida del ecosistema VELAS (solo librería estándar).

Módulos:
    config        -> configuración (config.json / variables de entorno)
    telemetria    -> reportes estructurados, verificaciones de negocio, capturas
    notificador   -> alertas (popup Windows, Telegram, bitácora)
    vision        -> análisis de capturas con Gemini (opcional)
    grafo         -> grafo de conocimiento del ecosistema + análisis de impacto
    lanzador      -> envoltura que ejecuta cualquier proyecto con telemetría automática
    orquestador   -> punto de entrada: ejecutar, salud, historial
"""

