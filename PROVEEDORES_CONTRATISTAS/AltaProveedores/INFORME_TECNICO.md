# AltaProveedores EK10 — Informe técnico

Sistema para **dar de alta proveedores (y contratistas) en el ERP suite.ekloud / ENKONTROL
(Aryve)** a partir de la captura de pantalla "Datos Generales" (EK9) de un proveedor, o
—modo recomendado— leyendo los datos directamente de la base de datos del ERP.

Dos piezas:

1. **Portal web local** (Flask, `portal.py`): se sube una captura, se obtiene el CSV del
   proveedor, se guarda en un historial y se dispara el bot. Corre en `http://localhost:5055`.
2. **Bot de automatización** (Selenium, `alta_proveedores.py` / `alta_contratistas.py`): abre
   Chrome, inicia sesión en el ERP y llena el formulario de alta.

Todo es local; ninguna captura ni dato sale del equipo (salvo que se use el lector Gemini/Claude).

---

## 1. Flujo general

```
   Captura EK9 (PNG/JPG)
          │  (se sube en el portal)
          ▼
   ┌──────────────┐     PORTAL_LECTOR decide cómo leer la captura
   │  portal.py   │────────────────────────────────────────────────┐
   └──────────────┘                                                 │
          │                                                         ▼
          │                         ┌───────── lectores de imagen ──────────┐
          │                         │ ocr    → ocr_ek9.py (OCR de Windows)   │
          │                         │ gemini → extraer_gemini.py (+ OCR)     │
          │                         │ claude → extraer_imagen.py (API)       │
          │                         │ local  → extraer_local.py (Ollama+Paddle)
          │                         │ db     → consulta_proveedor.py (SQL)  ◄── recomendado
          │                         └────────────────────────────────────────┘
          ▼
   CSV vertical "CAMPO,VALOR"  (Datos/csv/proveedor_<num>_<corto>.csv)
          │
          ▼
   Historial SQLite (Datos/historial.db)  + casillas Proveedor/Contratista
          │  (al confirmar en el portal)
          ▼
   ┌─────────────────────┐   Selenium + Chrome
   │ alta_proveedores.py │── login → busca RFC (evita duplicados) → wizard Tipo Persona
   │ alta_contratistas.py│──  → llena campos obligatorios → Guardar → escribe "ID EK10" en el CSV
   └─────────────────────┘
```

El CSV es el **contrato** entre el lector y el bot: formato vertical `CAMPO,VALOR`, UTF-8 con BOM,
un proveedor por archivo. Lo produce cualquier lector y lo consume el bot (`proveedor_csv.py`).

---

## 2. Lectores de imagen (`PORTAL_LECTOR`)

El portal elige el lector con la variable de entorno `PORTAL_LECTOR`. Cada lanzador `.bat` la fija:

| Valor   | Módulo                | Qué hace | Requisitos |
|---------|-----------------------|----------|------------|
| `db`    | `consulta_proveedor.py` | **Lee solo el número de proveedor** de la captura (OCR) y trae el resto de campos de la base de datos del ERP. Exacto y rápido (~3.5 s). | Acceso a la base (SQL Anywhere) |
| `ocr`   | `ocr_ek9.py`          | OCR 100 % local (API de Windows, WinRT + OpenCV). Lee todos los campos de la imagen. | Windows |
| `gemini`| `extraer_gemini.py`   | Gemini como lector principal + OCR de Windows en paralelo para comparar. | `GEMINI_API_KEY` |
| `claude`| `extraer_imagen.py`   | API de Anthropic. | `ANTHROPIC_API_KEY` |
| `local` | `extraer_local.py`    | Modelo de visión local (Ollama `qwen2.5vl` + PaddleOCR del proyecto `ExtraerInputsImagen`). Sin internet, pero ~5 min por imagen en CPU. | Ollama + proyecto aparte |

Por omisión: `gemini` si existe `GEMINI_API_KEY`, si no `ocr`.

**Recomendado: `db`.** El OCR de la captura comete errores (p. ej. leyó CP `89600`→`39600`,
RFC `...MZ5`→`...MZS`); la base da el dato exacto. En modo `db` el OCR solo se usa para el número
de proveedor (muy confiable) y, como respaldo, si la base no responde se cae al OCR completo
avisando que se revise todo.

---

## 3. Modo base de datos (`consulta_proveedor.py`) — lo más relevante

### Conexión (SAP SQL Anywhere 11, ODBC vía pyodbc)

- Servidor del ERP: `10.10.202.244`. En el puerto **2544** corre el engine **`especial_v9`**
  (se descubre con `dblocate.exe <host>` de SQL Anywhere). Base: `EK_ADM01_11`.
- **El driver v11 NO entiende `HOST=ip:port`** (eso es de v12+); da el error
  `-72 No database file specified`. Hay que usar la sintaxis de red de v11:

  ```
  DRIVER={SQL Anywhere 11};CommLinks=tcpip(HOST=10.10.202.244;PORT=2544);ENG=especial_v9;DBN=EK_ADM01_11;UID=...;PWD=...
  ```
  El `ENG` (nombre del engine) es obligatorio y se valida (sin él: `-832`; con uno inexistente: `-100`).

- Todo es configurable por variables de entorno: `EK_DB_HOST`, `EK_DB_PORT`, `EK_DB_NAME`,
  `EK_DB_USER`, `EK_DB_PASSWORD`, `EK_DB_SERVER`, `EK_DB_DRIVER`. **La contraseña nunca está en
  el código**; se toma de `EK_DB_PASSWORD`.

### Consulta y mapeo

`sp_proveedores` tiene 113 columnas. La consulta trae las que se usan y traduce tres códigos a
texto con JOIN a sus catálogos:

| Campo EK9 | Columna de `sp_proveedores` | Nota |
|-----------|------------------------------|------|
| Proveedor | `numpro` | |
| Persona Física | `persona_fisica` (`S`/`N`) | decide física vs moral |
| Nombre | `a_nombre` (física) / `nombre` (moral, razón social) | |
| A. Paterno / Materno | `a_paterno` / `a_materno` | solo física |
| Obliga CFDI / Filial / Factoraje | `obliga_cfd` (1/0) / `filial` / `bit_factoraje` (S/N) | → Sí/No |
| Dirección / Calle / Colonia / Deleg. ó Mpio. / Ciudad / C.P. | `direccion` / `calle` / `colonia` / `deleg` / `ciudad` / `cp` | |
| R.F.C. | `rfc` | sin guiones |
| Nombre Corto | `nomcorto` | |
| Tipo de Tercero | `tipo_tercero` (código) | JOIN `sp_tercero(id_tercero,desc_tercero)` → "Proveedor Nacional" |
| Tipo de Operación | `tipo_operacion` (código) | JOIN `sp_operacion(id_operacion,desc_operacion)` → "Otros" |
| Tipo de Proveedor | `tipo_prov` (código) | JOIN `sp_tipo_prov(tipo_prov,descripcion)` → "SERVICIOS" |
| Nac. ó Ext. | `prov_exterior` | `N`→Nacional, `E`→Extranjero (no existe columna `nacional`) |
| Estatus General | `cancelado` | `A`→Vigente, `C`→Cancelado, `P`→Habilitado por password (no es columna directa) |
| Empleado / Nacionalidad / ID Fiscal / Tipo Soc. / Clave ID | `num_empleado` / `nacionalidad` / `id_fiscal` / `tipo_soc` / `Clave_ID` | |

El resultado se entrega en el mismo formato `[(campo EK9, valor)]` que los demás lectores, así que
el resto del portal y el bot no cambian.

---

## 4. Worker de OCR persistente (rendimiento)

El OCR de Windows (WinRT) **no convive con Selenium/Flask en el mismo proceso** (tumbaba el portal
con código 139), así que corre en un proceso aparte. Antes se arrancaba el `.exe` onefile completo
por cada imagen (~13 s de desempaquetado + imports). Ahora:

- `portal.py` mantiene **un worker vivo** (`PortalProveedores.exe --ocr-server`) que carga el OCR
  una sola vez y atiende cada imagen por `stdin`/`stdout` (`_asegurar_worker` / `ocr_en_proceso_aparte`,
  bajo `_ocr_lock`; con timeout de 180 s y reinicio si el worker muere).
- Se **precalienta** al abrir el portal (`precalentar_ocr`, hilo daemon), así hasta la primera
  subida es rápida.
- Resultado: subidas de **~15 s → ~3.5 s**.

Nota: un `.exe` onefile en ejecución se ve como 3 procesos normales: bootstrap → portal
(escucha 5055) → worker `--ocr-server`.

---

## 5. Login con recarga (`explorar_formulario.py` → `iniciar_sesion`)

Si la página de login **no reacciona en 10 s** (no carga o no aparece el campo de usuario), se
recarga y se reintenta, hasta 6 veces. Se logra con `set_page_load_timeout(10)` para que
`driver.get` no se cuelgue, más una espera de 10 s por el campo `#username`. Tras enviar las
credenciales, si el dashboard no aparece, también recarga el login. Al terminar restaura el tiempo
de carga normal (300 s).

---

## 6. Módulos

| Archivo | Rol |
|---------|-----|
| `portal.py` | Portal Flask: subida, historial SQLite, selección de lector, worker de OCR, dispara el bot. |
| `consulta_proveedor.py` | **Modo `db`**: consulta el proveedor en la base del ERP y lo mapea a campos EK9. |
| `ocr_ek9.py` | OCR de Windows de la captura EK9 (WinRT + OpenCV, lectura campo por campo con votación). |
| `extraer_gemini.py` / `extraer_imagen.py` / `extraer_local.py` | Lectores alternos (Gemini / Anthropic / modelo local). |
| `proveedor_csv.py` | Lee/normaliza el CSV del proveedor; reglas de Clave, tipo de persona, etc. |
| `explorar_formulario.py` | Utilidades Selenium comunes: driver, **login**, waits, exploración del formulario. |
| `alta_proveedores.py` | Bot de alta de proveedores (wizard Tipo Persona, campos obligatorios, anti-duplicados por RFC). |
| `alta_contratistas.py` | Bot de alta de contratistas (requiere "ID EK10" en el CSV). |
| `explorar_contratistas.py` | Exploración del módulo de contratistas (apoyo al desarrollo). |
| `templates/portal.html` | UI del portal. |

---

## 7. Cómo ejecutar

### Opción A: con los `.exe` ya compilados (no incluidos en este ZIP por tamaño)
Lanzadores (`.bat`), cada uno fija el lector:

- `EjecutarPortalBase.bat` → portal en modo **base de datos** (recomendado).
- `EjecutarPortalLocal.bat` → portal en modo OCR de Windows.
- `EjecutarPortal.bat` / `AbrirPortal.bat` → portal (Gemini/Claude según configuración).
- `EjecutarAltaProveedores.bat` → bot directo desde CSV, sin portal.
- `CerrarPortal.bat` → detiene el portal.

Antes de usar el modo `db`, definir la contraseña una vez (no queda en archivos):
```
setx EK_DB_PASSWORD "la_contrasena"
```
Usuario (`user_write`), engine (`especial_v9`) y base ya van dentro de `EjecutarPortalBase.bat`.

### Opción B: desde el código (desarrollo)
```
pip install -r requirements.txt
set PORTAL_LECTOR=db
set EK_DB_USER=user_write
set EK_DB_SERVER=especial_v9
set EK_DB_NAME=EK_ADM01_11
set EK_DB_PASSWORD=...
set EKLOUD_USUARIO=...        (para que el bot haga login)
set EKLOUD_PASSWORD=...
python portal.py
```

### Compilar los `.exe`
```
CompilarAltaProveedores.bat    (requiere: pip install pyinstaller)
```
Genera `AltaProveedores.exe` (bot) y `PortalProveedores.exe` (portal). Ya incluye los
`--hidden-import` necesarios (`pyodbc`, `consulta_proveedor`, `extraer_local`, etc.).

---

## 8. Variables de entorno

| Variable | Para qué | Dónde |
|----------|----------|-------|
| `PORTAL_LECTOR` | Lector de imagen (`db`/`ocr`/`gemini`/`claude`/`local`) | portal |
| `EK_DB_HOST/PORT/NAME/USER/PASSWORD/SERVER/DRIVER` | Conexión a la base del ERP | modo `db` |
| `EKLOUD_USUARIO` / `EKLOUD_PASSWORD` | Login del bot al ERP | bot |
| `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | Lectores Gemini / Claude | opcional |
| `PORTAL_PUERTO` / `PORTAL_DATOS` | Puerto (5055) y carpeta de datos del portal | opcional |

**Ninguna contraseña está en el código ni en este ZIP.** Todas se leen de variables de entorno.

---

## 9. Datos y dependencias

- **`Datos/`** (no incluido en el ZIP): `historial.db` (SQLite), `csv/` y `imagenes/`. Se crea solo.
  Contiene datos reales de proveedores, por eso no se comparte.
- **Modo `local`** depende del proyecto aparte **`ExtraerInputsImagen`** (Ollama `qwen2.5vl:7b` +
  PaddleOCR, Python 3.13 con su propio `.venv`). **Se incluye en este paquete** (carpeta
  `ExtraerInputsImagen/`, con su propio `README.md`); no hace falta para los modos
  `db`/`ocr`/`gemini`/`claude`.
- **OCR de Windows** (`ocr_ek9.py`): usa WinRT (paquete `winrt`/`winsdk`), solo Windows.
- **Bot**: requiere Google Chrome instalado (Selenium Manager baja el driver).

---

## 10. Notas / pendientes

- El RFC de la base viene sin guiones; el bot limpia separadores de todas formas.
- En modo `db`, si la base no responde, el portal cae al OCR completo y marca todo para revisar.
- Credenciales de la base (`user_write`) y del ERP se gestionan por fuera; rotarlas es responsabilidad
  del área de IT.
