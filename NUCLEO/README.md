# NUCLEO — ecosistema de automatización VELAS

Infraestructura compartida (solo librería estándar, funciona dentro de cualquier `.venv`).

## Idea central
El veredicto de una ejecución **no sale de lo que imprime la consola**, sale de
**verificaciones de negocio** (¿el dato quedó realmente en pantalla?).

| Veredicto | Significado |
|---|---|
| `OK` | Todo verificado, sin incidencias |
| `ADVERTENCIA` | Pasos fallidos o líneas sospechosas en consola, sin verificación crítica caída |
| `FALLO_SILENCIOSO` | exit code 0 **pero** una verificación crítica falló (la consola "mentía") |
| `FALLO` | Excepción no controlada, exit code ≠ 0, o abortó en pre-flight |

## Uso diario
```
python main.py                                   # menú: los bots pasan solos por el orquestador; 8 = salud
python NUCLEO/orquestador.py ejecutar CREACION_USUARIOS
python NUCLEO/orquestador.py salud               # pre-flight de todos + grafo + historial
python NUCLEO/orquestador.py historial 20
python -m NUCLEO.grafo impacto select2-formControl_Grupo-container   # ¿qué proyectos se rompen si esto cambia?
python -m NUCLEO.grafo compartidos               # acoplamientos entre proyectos
python -m NUCLEO.grafo calientes                 # componentes que más fallan
```

## Cuando algo falla
1. Banner con el veredicto real en consola + popup de Windows (FALLO / FALLO_SILENCIOSO).
2. `NUCLEO/ULTIMO_DIAGNOSTICO.md`: qué falló, evidencia, captura, HTML, proyectos afectados.
   Pásaselo al agente: *"Analiza NUCLEO/ULTIMO_DIAGNOSTICO.md y corrígelo"*.
3. `NUCLEO/capturas/` y `NUCLEO/reportes/` (JSON por ejecución + `historial.jsonl`).

## Activar notificaciones y visión (opcional)
Copia `config.ejemplo.json` a `config.json` (está en `.gitignore`) y llena:
- `telegram_token` + `telegram_chat_id` → alerta con captura al celular.
- `gemini_api_key` (+ `pip install -U google-genai` en el venv del bot) → Gemini analiza la captura del fallo.

También funcionan variables de entorno: `VELAS_TELEGRAM_TOKEN`, `VELAS_TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`.
`VELAS_SIN_POPUP=1` desactiva el popup (pruebas).

## Conectar otro proyecto (3 pasos)
1. Está en `proyectos.json` (archivos requeridos para el pre-flight). Ya cubre los 6 actuales.
2. **Sin tocar su código** ya obtiene: pre-flight, vigilancia de consola, excepciones, captura automática.
3. Para detectar fallos silenciosos, copia el patrón de `CREACION_USUARIOS/funciones_rh.py`:
   - `rep().paso(nombre, ok, componente=<id del selector>)` en cada acción.
   - `rep().verificar(nombre, esperado, obtenido, critica=True, componente=...)` leyendo el estado REAL de la página.
   - `finalizar_telemetria()` antes de la pausa final del navegador.

## Archivos
`telemetria.py` reportes/verificaciones · `notificador.py` alertas · `vision.py` Gemini ·
`grafo.py` grafo de conocimiento (se reconstruye solo desde el código; `grafo.mmd` es el diagrama Mermaid) ·
`lanzador.py` envoltura transparente · `orquestador.py` punto de entrada.

