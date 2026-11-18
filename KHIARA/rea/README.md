# 🔍 Módulo de Escaneo e Ingeniería Inversa Web (REA + DOM X-Ray)

Esta carpeta contiene las herramientas para radiografiar cualquier pantalla de **Aryve / Enkontrol** en vivo, sin tener que copiar HTML ni tomar capturas manualmente.

---

## 🚀 Cómo Usarlo en 2 Clics

### 1. Abrir Aryve conectado al escáner
Haz doble clic en **`1_abrir_aryve_rea.bat`**.
- Abrirá Chrome habilitando el puerto `9222` (Chrome DevTools Protocol).
- Iniciará sesión automáticamente en Aryve con las credenciales de tu `.env`.
- **Navega dentro de ese Chrome** hasta la pantalla, formulario, tabla o modal que quieras automatizar.

### 2. Escanear la pantalla actual
Cuando estés frente a la pantalla que quieres analizar, haz doble clic en **`2_escanear_pantalla.bat`**.
- Detecta automáticamente el `TARGET_ID` de la pestaña de Aryve.
- Extrae todos los `inputs`, desplegables `Select2`, tablas `DevExtreme`, botones, paneles y XPaths exactos.
- Ejecuta `rea-agents` (`inspect-web-page` y `analyze-web-bundle`) para mapear eventos, scripts y endpoints internos.
- Guarda todo en **`REA/reportes/`**:
  - `ultimo_escaneo_dom.json` (Mapa estructurado de selectores, IDs y XPaths)
  - `ultimo_dom.html` (Snapshot completo del DOM renderizado)
  - `rea_inspect.json` (Telemetría de página de REA)
  - `rea_bundle.json` (Rutas y bundles JS analizados por REA)

### 3. Pedir la automatización en el Chat
Una vez terminado el escaneo, solo dime en el chat:
> *"Ya escaneé la pantalla, ayúdame a automatizar..."*

Yo leeré directamente `REA/reportes/` y programaré el módulo de Selenium con los selectores y eventos exactos.

