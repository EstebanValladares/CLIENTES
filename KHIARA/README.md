# KHIARA 🧠
**Agente Autónomo de Inteligencia, Análisis de Proyectos y Grafos de Conocimiento**

KHIARA es un asistente de ingeniería diseñado para comprender proyectos enteros, mapear su arquitectura en **Grafos de Conocimiento (NetworkX)**, consultar bases de datos en vivo y realizar cálculos matemáticos precisos sin alucinaciones numéricas, impulsado por **Agno** y **Google Gemini**.

---

## 🚀 Características Principales

* 🌐 **Motor de Grafos (GraphRAG):** Mapea proyectos en nodos y aristas (Carpetas, Archivos, Tablas SQLite, Funciones, Clases, Esquemas JSON).
* 🦆 **Motor Analítico DuckDB:** Consultas SQL ultrarrápidas directamente sobre CSV, Excel, Parquet y JSON locales sin base de datos intermedia.
* 🏢 **Conector a Bases de Datos Empresariales:** Conexión en modo lectura a SQL Server (Enkontrol), MySQL o PostgreSQL mediante SQLAlchemy.
* 🧠 **Memoria Vectorial Semántica:** RAG vectorial local y persistente con embeddings y similitud de coseno (NumPy + Gemini Embeddings).
* 🔍 **Autoaprendizaje de Proyectos (`/aprender`):** Analiza cualquier repositorio o carpeta local en segundos y memoriza su estructura.
* 🔬 **Módulo REA (DOM X-Ray):** Radiografía profunda de pantallas web en Chrome (Select2, DevExtreme, botones, inputs y XPaths).
* 🗄️ **Inspector de Bases de Datos:** Ejecuta consultas `SELECT` en vivo sobre bases de datos SQLite del proyecto para responder con datos reales.
* 📐 **Cálculos Exactos:** Motor analítico basado en NumPy/Pandas para variaciones, porcentajes y fórmulas sin errores.
* ⚡ **Arquitectura Probada:** Construido sobre el framework `agno` con tipado estricto `pydantic`.

---

## 🛠️ Instalación

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/EstebanValladares/KHIARA.git
   cd KHIARA
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configurar tu clave de API:
   Crea un archivo `.env` basándote en `.env.example`:
   ```env
   GEMINI_API_KEY=tu_api_key_aqui
   DEFAULT_MODEL=gemini-2.5-flash
   ```

---

## 💻 Uso

Inicia la consola interactiva:
```bash
python run.py
```

### Comandos de Consola:
* `/aprender <ruta>`: Analiza e indexa cualquier proyecto local en el grafo.
* `/api <url|ruta>`: Ingiere automáticamente la especificación OpenAPI/Swagger de FastAPI.
* `/ontologia [termino]`: Consulta la "Llave Maestra" (Glosario Semántico de Grupo Velas).
* `/cruzar`: Analiza e interconecta tablas y módulos compartidos entre múltiples repos (GraphRAG).
* `/repomap`: Muestra el mapa compacto de todos los proyectos y firmas (Estilo Aider).
* `/reglas [tema]`: Consulta las reglas y preferencias de negocio aprendidas (Estilo Mem0).
* `/centinela [on|off]`: Activa o desactiva la vigilancia proactiva en segundo plano de tus proyectos.
* `/grafo`: Inspecciona el tamaño y desglose del grafo de conocimiento.
* `/duck <sql>`: Ejecuta consultas analíticas SQL en DuckDB sobre CSVs, Parquet o JSONs.
* `/memoria <texto>`: Búsqueda semántica de conceptos, notas y hechos en la memoria vectorial.
* `/tablas`: Conecta e inspecciona el catálogo de tablas en el servidor externo (SQL Server / MySQL).
* `/run <codigo>`: Ejecuta código Python seguro en el sandbox con captura de stdout/stderr.
* `/rea [termino]`: Inspecciona reportes y busca selectores, inputs y XPaths extraídos por REA.
* `/escanear`: Lanza el escáner de REA sobre la pestaña activa en Chrome (puerto 9222).
* Preguntas libres: Pregunta en lenguaje natural sobre cualquier proyecto aprendido o automatizaciones web.
