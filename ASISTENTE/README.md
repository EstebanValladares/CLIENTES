# 🍞 Ecosistema Modular ASISTENTE CENTINELA (OMFG Hello Toast)
**Dashboard EK10 - Grupo Velas**

---

## 📌 ¿Qué es este Módulo?
El **Asistente Centinela** es un agente proactivo y ligero que acompaña al usuario desde la esquina inferior de la pantalla.
A diferencia de los chatbots convencionales donde el usuario debe abrir una ventana para interactuar, el Asistente **"habla" de inmediato** desplegando un globo de diálogo flotante con sonido suave en cuanto detecta un evento relevante en el sistema.

### 🎯 Icono y Personaje
* Basado en la icónica tostada animada de **OMFG - Hello**.
* Imagen transparente en alta definición ubicada en: `assets/toast.png` (y servida en `/static/img/toast.png`).
* **Diseño limpio y estático:** Sin animaciones de mareo, con flotación suave solo al pasar el cursor (`hover:scale-105`).

### 💬 Experiencia de Usuario:
1. **Saludo Inicial Flotante:**  
   Al arrancar el Dashboard, muestra un bocadillo limpio que saluda directamente al usuario en sesión:  
   *`"¡Hola, Esteban! Soy Chilaquil. Haz clic en mí en cualquier momento si quieres platicar..."`*  
   Se desvanece solo a los 9 segundos o al hacer clic.
2. **Ventana de Chat Interactivo al Dar Clic:**  
   Al hacer clic en la tostada, se despliega una ventana de chat completa:  
   * Conversación interactiva bidireccional (usuario ➔ asistente).  
   * Búsqueda en la plantilla de 1,104 colaboradores, obras, lotes y escalatorias.  
   * Chips de preguntas rápidas sugeridas.  
   * Botón de limpiar historial y cerrar.

---

## 🏗️ Arquitectura Modular y Escalable

La carpeta `ASISTENTE/` está diseñada bajo principios de arquitectura limpia para crecer exponencialmente sin desorden:

```
ASISTENTE/
├── assets/
│   ├── toast.png                  # Avatar oficial HD recortado y con fondo transparente
│   ├── toast_hd_raw.png           # Original de alta resolución
│   └── toast_raw.png              # Imagen base
├── config.py                      # Constantes globales, rutas de base de datos y timeouts
├── database.py                    # Persistencia SQLite (data/asistente.db: config y memoria)
├── asistente_service.py           # Fachada / Orquestador principal de eventos y servicios
├── dialogos/
│   ├── __init__.py
│   └── banco_frases.py            # Personalidad, saludos contextuales, frases y bautizo
├── monitores/
│   ├── __init__.py                # Exportación de monitores pluggables
│   ├── chat_monitor.py            # Listener de mensajes de chat y DMs de equipo
│   ├── escalatorias_monitor.py    # Listener de escalatorias de precios en Enkontrol
│   └── sistema_monitor.py         # Monitor de salud e integridad de lotes y base de datos
├── views/
│   └── asistente_widget.html      # Plantilla visual (Globo, Modal Bautizo, Historial y Avatar)
├── modules/
│   └── asistente.js               # Lógica Vue 3 reactiva, Web Audio sintetizado y ciclo de vida
└── README.md                      # Esta documentación técnica
```

---

## ⚡ Bautizo y Saludo Inicial (Sin Sobrecarga)

### 1. ¿Es pesado el saludo al iniciar el Dashboard?
**No, es extremadamente ligero (sub-milisegundo, 0ms de retraso):**
- No consulta modelos LLM externos ni hace peticiones pesadas por red.
- La lógica contextual (hora del día, usuario y mensajes pendientes) se procesa localmente en Python/SQLite en menos de 2 milisegundos.
- Se renderiza al vuelo en Vue 3 con una suave animación y un blip sintetizado mediante Web Audio API.

### 2. Experiencia de Bautizo (Nombre Personalizado la Primera y Única Vez):
- **Detección Automática:** Cuando el usuario entra por primera vez, el sistema detecta que `primer_inicio_completado` no está registrado.
- **Card de Bautizo:** El asistente despliega una elegante tarjeta de bienvenida encima de la tostada con el texto:
  > *"¡OMFG HELLO! Bienvenido. Seré tu centinela en pantalla. ¿Cómo te gustaría llamarme?"*
  > Sugerencias rápidas: `[Toastie]` `[Pancho]` `[Ary]` `[VelasBot]` `[Centinela]`
- **Guardado Permanente:** Al guardar, se almacena en `localStorage` (para disponibilidad instantánea en el navegador) y en la tabla `asistente_config` de `data/asistente.db`.
- **Nunca Vuelve a Preguntar:** En futuros accesos, Toastie ya conoce su nombre y saluda directamente:
  > *"👋 ¡Buenos días, Esteban! Soy Pancho. Todo tranquilo por aquí: cero alertas críticas..."*
- **Edición Disponible:** Si el usuario desea cambiarle el nombre más adelante, puede presionar el pequeño lápiz ✏️ en el panel de historial.

---

## 🔌 Monitores Proactivos en Tiempo Real

1. **ChatMonitor (`monitores/chat_monitor.py`):**
   - Vigila `chat_equipo.db`. Si un compañero envía un mensaje o DM, el asistente saca un globo:
     > 💬 *"Carlos te escribió: '¿Tienes la clave del lote 12?'"* con botón `[Ver en Chat]`.

2. **EscalatoriasMonitor (`monitores/escalatorias_monitor.py`):**
   - Vigila `escalatorias.db`. Al autorizarse precios nuevos:
     > 📈 *"Nueva escalatoria autorizada en DQA con 12 insumos nuevos."* con botón `[Ver Escalatoria]`.

3. **SistemaMonitor (`monitores/sistema_monitor.py`):**
   - Vigila el estado de Mapeo de Lotes, centros de costos y salud del servidor.

---

## 🛠️ Endpoints API

* `GET /api/asistente/estado?usuario_id=...&nombre=...`: Estado, métricas y nuevos avisos pendientes.
* `GET /api/asistente/saludo?usuario_id=...&nombre=...`: Saludo contextual instantáneo.
* `GET /api/asistente/reaccion-clic?usuario_id=...`: Frases dinámicas al interactuar con el avatar.
* `POST /api/asistente/configurar-nombre`: Bautiza y persiste el nombre del asistente (`{"usuario_id": "...", "nombre_asistente": "..."}`).
* `POST /api/asistente/hablar`: Permite a cualquier módulo o script hacer hablar al asistente.
