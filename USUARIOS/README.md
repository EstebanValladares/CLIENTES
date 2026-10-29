# Módulo de Usuarios (Arquitectura Limpia y Modular)

Este módulo gestiona la administración, automatización y sincronización de usuarios y perfiles para **Aryve (Enkontrol 10)**.

---

## 🏗️ Arquitectura del Módulo

El módulo ha sido simplificado y organizado para eliminar la sobre-fragmentación previa, manteniendo código limpio, mantenible y desacoplado:

```text
USUARIOS/
├── selectores.py         # Catálogo centralizado de selectores DOM (IDs, XPaths y URLs de Aryve)
├── puestos_service.py     # Lógica de dominio y reglas de negocio para puestos y clasificadores
├── puestos.json           # Matriz oficial de puestos con sus clasificadores correspondientes
├── automation/            # Automatización con Selenium WebDriver
│   ├── browser.py         # Ciclo de vida y creación del WebDriver de Chrome
│   ├── ui_helpers.py      # Interacciones atómicas con la UI de Aryve (menús, paneles, árboles)
│   ├── usuario_bot.py     # Flujos de negocio: Alta de Usuarios y Asignación de Clasificadores
│   └── telemetry.py       # Adaptador de telemetría y diagnósticos
└── logger/                # Registro y bitácora de auditoría
    ├── bitacora.py        # Registro de fallos en clasificadores y logs de ejecución
    └── fallos_clasificadores.jsonl
```

---

## ⚡ Capacidades Principales

1. **Búsqueda y Sincronización en Vivo**:
   - Conexión directa a la API Cloud de Aryve (`/Aryve/base/kontrol/usuarios/GetBP/GetUsuario`).
   - Sincronización instantánea en memoria, JSON y CSV sin requerir Selenium.

2. **Creación de Posiciones (Puestos)**:
   - Almacenamiento local en `puestos.json` con sincronización en la nube vía Google Firebase Firestore.

3. **Creación de Usuarios**:
   - Automatización Selenium de extremo a extremo: datos generales, niveles de acceso, grupos y asignación inicial de clasificadores según el puesto.

4. **Actualización de Clasificadores**:
   - Asignación incremental y corrección de clasificadores por ID de usuario.
   - Detección y registro de discrepancias o fallos en bitácora para auto-reparación.

---

## 🚀 Uso Rápido en Python

```python
from USUARIOS import (
    obtener_configuracion_puesto,
    ejecutar_alta_usuario,
    ejecutar_asignacion_clasificadores,
    cerrar_driver_activo
)

# 1. Obtener la matriz de un puesto
config = obtener_configuracion_puesto("ASESOR DE VENTA REYNOSA")
print(f"Total clasificadores: {config.total_clasificadores}")

# 2. Asignar clasificadores a un usuario por su ID
# ok, mensaje = ejecutar_asignacion_clasificadores("1234", config.clasificadores)
```
