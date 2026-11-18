# 🍞 Módulo ASISTENTE CENTINELA (Toastie - OMFG Hello Toast)
**Ecosistema Dashboard EK10 - Grupo Velas**

---

## 📌 ¿Qué es este Módulo?
El Asistente Centinela es un agente proactivo que vive en la esquina de la pantalla.
A diferencia de los chatbots convencionales donde el usuario debe abrir una ventana para interactuar, **Toastie "habla" de inmediato** sacando un globo de diálogo flotante en cuanto detecta un evento relevante en el sistema.

### 🎯 Icono y Personaje
* Basado en la icónica tostada animada de **OMFG - Hello**.
* Imagen transparente en alta definición ubicada en: `assets/toast.png` (y servida en `/static/img/toast.png`).
* Animación suave en reposo (`animate-toast-idle`) y bote alegre al hablar o interactuar (`animate-toast-bounce`).

---

## ⚡ Capacidades Proactivas en Tiempo Real

1. **Monitoreo de Chat de Equipo & DMs:**
   * En cuanto un compañero envía un mensaje en `chat_equipo.db`, Toastie saca un bocadillo en la esquina:
     > 💬 *"Esteban, Carlos te acaba de escribir: '¿Tienes la clave del lote 12?'"*
   * Incluye botón directo `[Ver en Chat]` para responder sin rodeos.

2. **Monitoreo de Escalatorias de Precios (SOC Enkontrol):**
   * Al autorizarse nuevas escalatorias en `escalatorias.db`, Toastie notifica:
     > 📈 *"Nueva escalatoria autorizada en DQA con 12 insumos nuevos."*
   * Incluye botón directo `[Ver Escalatoria]`.

3. **Saludo Proactivo al Iniciar Sesión:**
   * Detecta la hora del día (Buenos días / tardes / noches) y el nombre del usuario activo.
   * Hace un resumen instantáneo del estado del sistema y mensajes pendientes.

4. **Autodescarte y Cero Molestias:**
   * El globo de diálogo cuenta con una barra de progreso inferior de 8 a 10 segundos.
   * Si el usuario no lo toca, se desvanece suavemente para no estorbar en pantalla.
   * Si el usuario pone el mouse encima (`hover`), la cuenta regresiva se pausa para que pueda leer con calma.
   * Cuenta con historial desplegable de los últimos avisos al hacer clic en el avatar.

5. **Efectos de Sonido Web Audio API:**
   * Genera un pop suave sintetizado en tiempo real sin requerir archivos mp3 externos ni consumir ancho de banda.

---

## 📂 Estructura de Archivos del Ecosistema

```
ASISTENTE/
├── assets/
│   ├── toast.png         # Icono oficial de la tostada con fondo transparente
│   └── toast_raw.png     # Imagen original
├── asistente_service.py  # Lógica de dominio backend (detección de eventos y cola)
├── asistente_widget.html # Componente visual modular del widget flotante
├── asistente.js          # Módulo Vue 3 con loop de polling reactivo
└── README.md             # Esta documentación técnica
```

---

## 🔌 Endpoints de la API REST

* `GET /api/asistente/estado?usuario_id=<id>&nombre=<nombre>`:  
  Devuelve si hay nuevos globos para hablar, métricas de DMs no leídos y el historial reciente.
* `GET /api/asistente/saludo?nombre=<nombre>`:  
  Genera el saludo proactivo inicial de bienvenida.
* `POST /api/asistente/hablar`:  
  Permite que cualquier subproceso, bot RPA o servicio backend dispare un globo de diálogo en la esquina.
  ```json
  {
    "titulo": "Alerta de Orden de Compra",
    "mensaje": "Se detectó un ajuste en la requisición JA2-00000266",
    "tipo": "alerta",
    "accion": ""
  }
  ```
