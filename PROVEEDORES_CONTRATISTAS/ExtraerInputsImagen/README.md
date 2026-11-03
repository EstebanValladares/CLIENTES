# ExtraerInputsImagen

Extrae los datos de los inputs (campos de formulario y tablas) de capturas de pantalla **PNG/JPG**
compartidas por correo, chat o carpeta, y los deja en **CSV**. Todo corre en el equipo: ninguna
imagen sale de el. No usa Selenium ni el navegador.

## Pipeline

1. **Preprocesado** (Pillow): corrige la orientacion EXIF (JPG de celular), convierte a RGB,
   escala x2 (LANCZOS) si el ancho es < 1500 px y mejora contraste/nitidez solo para el OCR.
   Las imagenes de trabajo van a `temp\`; la original no se toca.
2. **Estructura**: modelo de vision local `qwen2.5vl:7b` en Ollama (`format: json`, `temperature: 0`)
   devuelve `campos` (etiqueta, valor, tipo) y `tablas`.
3. **Texto literal**: OCR **PaddleOCR** (`lang="es"`); si no esta disponible, **EasyOCR**.
4. **Validacion cruzada** (rapidfuzz + regex):
   - similitud >= 0.9 con una linea del OCR -> se usa el texto del OCR (caracter por caracter);
   - menor -> se conserva el valor del modelo y `revisar = true`;
   - campos criticos validados con regex; si fallan -> `revisar = true`;
   - valor `null` del modelo -> se recupera del OCR por posicion (derecha o debajo de la etiqueta)
     y `revisar = true`;
   - campo critico que el modelo no devolvio -> se agrega desde el OCR con `revisar = true`.

**Campos criticos**: PROVEEDOR, NOMBRE (o razon social), DIRECCION (o domicilio),
CODIGO POSTAL (o C.P., 5 digitos) y RFC (3-4 letras + 6 digitos + 3 caracteres).
Se configuran en `src\extraer_inputs\config.py` (`CAMPOS_CRITICOS`).

## Salida

En `<carpeta de las imagenes>\resultados_extraccion\` (o la indicada con `--salida`):

- `<imagen>_<ext>.csv`: un archivo por imagen.
- `<imagen>_<ext>_tablas.csv`: si la imagen tiene tablas.
- `consolidado.csv`: todas las imagenes, con la columna `archivo_origen`.

Columnas: `etiqueta, valor, tipo, valor_modelo, valor_ocr, similitud, revisar, critico, motivo`.
Codificacion `utf-8-sig` (Excel muestra bien acentos y ñ). Filtre `revisar = true` para ver lo que
hay que confirmar a mano.

## Instalacion (una vez)

1. **Ollama para Windows**: https://ollama.com/download o `winget install Ollama.Ollama`.
   Deje la aplicacion abierta (icono en la bandeja) o ejecute `ollama serve`.
2. Descargar el modelo (~6 GB): `ollama pull qwen2.5vl:7b`
3. **Microsoft Visual C++ Redistributable x64** (PaddlePaddle necesita `vcomp140.dll`; sin ella
   falla con "DLL load failed while importing libpaddle"):
   `winget install Microsoft.VCRedist.2015+.x64`
4. Entorno de Python **3.13** (PaddlePaddle aun no publica ruedas para 3.14):
   ```
   py -3.13 -m venv .venv
   .venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   La primera ejecucion de PaddleOCR / EasyOCR descarga sus modelos de OCR (requiere internet una vez;
   quedan en `%USERPROFILE%\.paddlex` y `%USERPROFILE%\.EasyOCR`).

## Uso

- Arrastrar una **carpeta** o una **imagen** sobre `ejecutar.bat`, o:
  `ejecutar.bat "C:\capturas"` / `ejecutar.bat a.png b.jpg --salida "C:\resultados"`
- Al iniciar comprueba que Ollama corre (`GET /api/tags`) y que el modelo esta descargado; si no,
  indica como solucionarlo y termina con codigo 2.
- Codigos de salida: 0 ok, 1 alguna imagen con error, 2 Ollama/modelo no disponible,
  3 sin imagenes validas.
- Log: `logs\extraer_inputs.log`. Al final muestra imagenes procesadas, con error y campos a revisar.
- Si Ollama falla o devuelve un JSON invalido se reintenta una vez; despues se registra y se sigue
  con la siguiente imagen. Una imagen corrupta no detiene el lote.
- **Formulario conocido** (modo JSON para otros programas):
  `python -m extraer_inputs.json_cli captura.png --campos "Proveedor|Nombre|R.F.C.|..."`.
  Solo pide esas etiquetas en un JSON plano `{etiqueta: valor}` (salida estructurada de Ollama), sin
  tipos ni tablas: la respuesta pasa de ~1000 a ~250 tokens y la captura EK9 baja de ~11 a ~5 min.
  El log registra por imagen los tokens y segundos de Ollama (lectura de imagen vs respuesta).
- Variables opcionales: `EXTRAER_OCR=easyocr` (forzar EasyOCR), `EXTRAER_MODELO`,
  `EXTRAER_OLLAMA_URL`, `EXTRAER_TIMEOUT_OLLAMA` (seg).

**Rendimiento**: sin GPU NVIDIA el modelo corre en CPU. Medido en este equipo (Intel UHD, 16 GB):
3 min (JPG de 760 px), 8 min (1200 px) y 9.5 min (PNG de 1600 px) por imagen; el OCR tarda segundos.

**Notas tecnicas**: PaddleOCR se crea con `enable_mkldnn=False` porque en CPU Paddle 3.x con oneDNN
falla al predecir. En campos criticos, si el OCR y el modelo difieren aunque la similitud sea >= 0.9,
se usa el texto del OCR pero se marca `revisar = true` (con EasyOCR se vio "MAGO10203K64" vs
"MAG010203K64" y una direccion sin puntos).

## Pruebas

```
.venv\Scripts\python.exe tests\fixtures\crear_fixtures.py   (genera las 3 imagenes de ejemplo)
.venv\Scripts\python.exe -m pytest
```

- `test_validacion.py` y `test_preprocesado.py` no necesitan Ollama.
- `test_extraccion.py` procesa un PNG nitido, un JPG comprimido y un JPG girado y compara los
  campos criticos con `*.esperado.json` (deben coincidir o quedar `revisar = true`; en el nitido,
  coincidir). Si Ollama no esta corriendo se salta y lo indica.

## Empaquetado

Se deja como script `.py` con su `.venv` (no `.exe`): torch/paddle y los modelos de OCR harian un
ejecutable de mas de 1 GB. Si se llegara a empaquetar con PyInstaller harian falta
`--collect-all paddleocr --collect-all paddlex --collect-all paddle --collect-all easyocr`,
`--hidden-import ollama` y llevar los modelos de `%USERPROFILE%\.paddlex\official_models`
y `%USERPROFILE%\.EasyOCR\model` junto al ejecutable.
