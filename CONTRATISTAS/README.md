# Módulo CONTRATISTAS - Dashboard EK10

Módulo integral y automatizado para el procesamiento, normalización, generación de gafetes de identificación (762 x 686 px) y carga desatendida mediante Selenium en **Aryve Suite (EnKontrol EK10)**.

---

## 🏗️ Arquitectura Modular del Proyecto

La estructura sigue el estándar de Arquitectura Limpia adoptado por `DASHBOARD_EK10`, desacoplando configuración, reglas de negocio y automatización:

```text
CONTRATISTAS/
├── .env                              # Credenciales seguras (EK10_USER, EK10_PASS)
├── main.py                           # CLI / Orquestador unificado (CLI, bots, API)
├── automatizacion_contratistas.py    # Ejecutor directo retrocompatible
├── contratista_mapeado.json          # Catálogo maestro estructurado y optimizado
├── requirements.txt                  # Dependencias del módulo
├── README.md                         # Documentación de uso
│
├── config/                           # Configuración y Parámetros
│   ├── __init__.py
│   └── settings.py                   # Rutas, canvas 762x686, URLs y credenciales
│
├── domain/                           # Reglas de Negocio y Dominio
│   ├── __init__.py
│   ├── text_processor.py             # Normalización, remoción de SA de CV y prefijos
│   ├── image_generator.py            # Motor gráfico PIL (gafetes centrados 762x686)
│   └── catalog_service.py            # Gestión del catálogo JSON e ingesta CSV
│
├── automation/                       # Automatización RPA Selenium
│   ├── __init__.py
│   ├── driver_factory.py             # Instanciación y optimización de ChromeDriver
│   └── contractor_bot.py             # Ciclo completo en Aryve (login, detección, edición, upload, guardar)
│
├── data/                             # Fuentes de datos
│   └── Contratistas (2)(Contratistas).csv
│
└── output/                           # Gafetes generados ({id}.png)
    ├── 222.png
    ├── 223.png
    └── ...
```

---

## 🚀 Comandos de Uso

### 1. Ejecutar Automatización en Aryve (EK10)
Carga secuencialmente fotos en Aryve para el rango especificado. Si el contratista ya tiene foto asignada en el servidor, **se omite automáticamente sin modificar nada**:

```bash
# Ejecutar rango (por defecto 223 al 229)
python CONTRATISTAS/main.py --desde 223 --hasta 229

# O usar el script de compatibilidad directa:
python CONTRATISTAS/automatizacion_contratistas.py --desde 223 --hasta 229

# Ejecutar un solo ID específico:
python CONTRATISTAS/main.py --id 229

# Ejecutar en segundo plano sin ventana gráfica (headless):
python CONTRATISTAS/main.py --desde 223 --hasta 229 --headless --no-pause
```

### 2. Generar Gafetes de Imagen
Genera las imágenes `{id}.png` de 762 x 686 píxeles con fondo blanco y texto centrado en `CONTRATISTAS/output/`:

```bash
# Generar para todos los contratistas desde ID >= 222
python CONTRATISTAS/main.py --generate-images --desde 222

# Generar para un ID individual
python CONTRATISTAS/main.py --generate-images --id 229
```

### 3. Reconstruir el Catálogo JSON Mapeado
Regenera `contratista_mapeado.json` a partir del archivo CSV fuente:

```bash
python CONTRATISTAS/main.py --build-catalog
```

---

## 📐 Especificaciones de los Gafetes

| Parámetro | Valor |
| :--- | :--- |
| **Ancho** | `762 px` |
| **Alto** | `686 px` |
| **Fondo** | Blanco puro (`#FFFFFF`) |
| **Texto** | Negro puro (`#000000`) |
| **Alineación** | Centrado horizontal y verticalmente |
| **Tipografía** | Sans-serif clara (`Segoe UI` / `Arial`) |
| **Nomenclatura** | `{id}.png` (ej. `223.png`, `229.png`) |

---

## 🔒 Manejo de Credenciales
Las credenciales de acceso a Aryve se resuelven en el siguiente orden:
1. Argumentos CLI: `--user` y `--password`.
2. Variables de entorno: `EK10_USER` y `EK10_PASS` (en `CONTRATISTAS/.env` o raíz `.env`).
3. Valores por defecto del sistema.

*Nota técnica*: Aryve (EK10) requiere la contraseña literal sin decodificación en Base64.
