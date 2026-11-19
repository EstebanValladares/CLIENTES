"""
Asistente Conversacional Instantáneo de Alta de Usuarios y Posiciones para KHIARA.
Maneja la entrevista paso a paso en memoria local (< 50 ms) sin depender de la latencia
de APIs externas y ejecuta directamente UserCreationService / UserPositionService.
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

BASE_DASHBOARD = Path(__file__).resolve().parent.parent.parent.parent
ARCHIVO_PUESTOS = BASE_DASHBOARD / "USUARIOS" / "data" / "puestos.json"

# Estado de flujo aislado por session_id
_ESTADOS_SESION: Dict[str, Dict[str, Any]] = {}


def limpiar_flujo_sesion(session_id: str):
    _ESTADOS_SESION.pop(session_id, None)


def tiene_flujo_activo(session_id: str) -> bool:
    return session_id in _ESTADOS_SESION


def _cargar_puestos() -> Dict[str, Any]:
    if not ARCHIVO_PUESTOS.exists():
        return {}
    try:
        data = json.loads(ARCHIVO_PUESTOS.read_text(encoding="utf-8"))
        return data.get("puestos", {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _buscar_puesto(termino: str) -> List[Tuple[str, str]]:
    """Busca puestos coincidentes por nombre o clave POS-XXXX. Retorna [(nombre, clave), ...]."""
    puestos = _cargar_puestos()
    t = termino.strip().upper()
    if not t:
        return []

    exactos = []
    parciales = []
    palabras = [p for p in re.split(r"\s+", t) if len(p) >= 2]

    for nombre, info in puestos.items():
        n_up = nombre.upper()
        clave = str(info.get("clave_posicion_cloud", "")).upper()
        if t == n_up or (clave and t == clave):
            exactos.append((nombre, clave))
        elif t in n_up or (clave and t in clave):
            parciales.append((nombre, clave))
        elif palabras and all(p in n_up for p in palabras):
            parciales.append((nombre, clave))

    return exactos if exactos else parciales[:5]


def _separar_nombre_apellidos(texto: str) -> Tuple[str, str]:
    """Separa un nombre completo en (nombre, apellidos) de forma inteligente."""
    limpio = re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ\s]", " ", texto).strip()
    partes = [p for p in limpio.split() if p]
    if len(partes) == 0:
        return "", ""
    if len(partes) == 1:
        return partes[0].upper(), ""
    if len(partes) == 2:
        return partes[0].upper(), partes[1].upper()
    if len(partes) == 3:
        return partes[0].upper(), " ".join(partes[1:]).upper()
    # 4 o más palabras: últimos 2 son apellidos, el resto nombres
    return " ".join(partes[:-2]).upper(), " ".join(partes[-2:]).upper()


def _extraer_correo(texto: str) -> Optional[str]:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texto)
    return m.group(0).lower() if m else None


def _es_intencion_alta_usuario(msg_low: str) -> bool:
    disparadores = [
        "dar de alta", "alta de usuario", "alta de un usuario", "alta a un usuario",
        "crear usuario", "crear un usuario", "crea un usuario", "nuevo usuario",
        "registrar usuario", "alta de colaborador", "nuevo colaborador",
        "llenar usuario", "alta usuario"
    ]
    return any(d in msg_low for d in disparadores)


def _es_cancelacion(msg_low: str) -> bool:
    return msg_low.strip() in {
        "cancelar", "cancela", "salir", "detener", "olvídalo", "olvidalo", "no gracias", "abortar"
    }


def _es_confirmacion(msg_low: str) -> Tuple[bool, bool]:
    """Retorna (es_confirmacion, guardar_en_produccion)."""
    limpio = msg_low.strip().replace("í", "i")
    guardar = any(k in limpio for k in ["guardar", "produccion", "definitivo", "directo"])
    afirmativos = ["si", "adelante", "confirmo", "dale", "inicia", "crear", "llena", "procede", "ok", "va"]
    es_si = any(limpio == a or limpio.startswith(a + " ") for a in afirmativos)
    return es_si, guardar


def _sugerir_correo(nombre: str, apellidos: str) -> str:
    n = nombre.split()[0].lower() if nombre else "usuario"
    a = apellidos.split()[0].lower() if apellidos else "velas"
    # Quitar acentos básicos
    for orig, rep in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        n = n.replace(orig, rep)
        a = a.replace(orig, rep)
    return f"{n}.{a}@grupovelas.com"


def _construir_siguiente_paso(session_id: str, estado: Dict[str, Any]) -> str:
    # 1. Falta nombre o apellidos
    if not estado.get("nombre") or not estado.get("apellidos"):
        return (
            "¡Con gusto te ayudo a dar de alta al nuevo usuario! 🚀\n"
            "Dime su **Nombre y Apellidos completos** (o envíame nombre, correo y puesto juntos)."
        )

    # 2. Falta correo
    if not estado.get("correo"):
        sug = _sugerir_correo(estado["nombre"], estado["apellidos"])
        return (
            f"Perfecto, anoté a **{estado['nombre']} {estado['apellidos']}**.\n"
            f"Ahora dime su **correo corporativo** (ej. `{sug}`)."
        )

    # 3. Falta puesto
    if not estado.get("puesto"):
        return (
            f"Anotado el correo `{estado['correo']}`.\n"
            f"¿Qué **Puesto o Posición** ocupará? (Puedes escribir el nombre o clave `POS-XXXX`, ej. *Asesor de Venta Tampico*)."
        )

    # 4. Todos los datos completos -> Pedir confirmación
    estado["esperando_confirmacion"] = True
    return (
        "📋 **Confirma los datos para iniciar el llenado en Aryve:**\n"
        f"• **Nombre:** {estado['nombre']}\n"
        f"• **Apellidos:** {estado['apellidos']}\n"
        f"• **Correo:** `{estado['correo']}`\n"
        f"• **Puesto:** {estado['puesto']}\n\n"
        "Responde **\"sí\"** para abrir el navegador y llenar el formulario (revisión), "
        "**\"sí guardar\"** para guardar definitivo, o **\"cancelar\"**."
    )


def procesar_flujo_alta(session_id: str, mensaje: str) -> Optional[str]:
    """
    Intercepta y resuelve de forma instantánea (<50ms) el flujo de alta de usuarios.
    Retorna la respuesta lista para enviar al widget, o None si el mensaje no pertenece al flujo.
    """
    msg = mensaje.strip()
    msg_low = msg.lower()

    # A. Si ya hay un flujo activo para esta sesión
    if session_id in _ESTADOS_SESION:
        estado = _ESTADOS_SESION[session_id]

        if _es_cancelacion(msg_low):
            limpiar_flujo_sesion(session_id)
            return "Entendido, cancelé el proceso de alta de usuario. ¿En qué más puedo apoyarte?"

        # Si está esperando confirmación final
        if estado.get("esperando_confirmacion"):
            es_si, guardar = _es_confirmacion(msg_low)
            if es_si:
                from khiara.herramientas.explorador import tool_iniciar_creacion_usuario
                datos = dict(estado)
                limpiar_flujo_sesion(session_id)
                return tool_iniciar_creacion_usuario(
                    nombre=datos["nombre"],
                    apellidos=datos["apellidos"],
                    correo=datos["correo"],
                    puesto=datos["puesto"],
                    guardar_en_produccion=guardar
                )
            elif msg_low in {"no", "corregir", "cambiar"}:
                estado["esperando_confirmacion"] = False
                return "¿Qué dato deseas corregir? (Escribe el nuevo correo, puesto o nombre completo)."

        # Extraer correo si viene en el mensaje
        correo_det = _extraer_correo(msg)
        if correo_det:
            estado["correo"] = correo_det

        # Si faltaba nombre y apellidos
        if not estado.get("nombre") or not estado.get("apellidos"):
            sin_correo = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "", msg).strip()
            nom, ape = _separar_nombre_apellidos(sin_correo)
            if nom and ape:
                estado["nombre"] = nom
                estado["apellidos"] = ape
            elif nom and not ape:
                estado["nombre"] = nom
                return f"Anoté el nombre **{nom}**. ¿Cuáles son sus **apellidos**?"
            return _construir_siguiente_paso(session_id, estado)

        # Si ya tenía nombre y correo, este mensaje es el puesto
        if estado.get("correo") and not estado.get("puesto"):
            # Evitar tomar el correo recién enviado como puesto
            sin_correo = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "", msg).strip()
            if sin_correo:
                coincidencias = _buscar_puesto(sin_correo)
                if len(coincidencias) == 1:
                    estado["puesto"] = coincidencias[0][0]
                elif len(coincidencias) > 1:
                    # Si el usuario escribió exacto o casi exacto, o mostrar opciones rápidas
                    primero = coincidencias[0][0]
                    if sin_correo.upper() == primero.upper() or sin_correo.upper() == coincidencias[0][1]:
                        estado["puesto"] = primero
                    else:
                        opts = "\n".join(f"• **{n}** (`{c}`)" if c else f"• **{n}**" for n, c in coincidencias[:5])
                        return (
                            f"Encontré estos puestos parecidos a *\"{sin_correo}\"*:\n{opts}\n\n"
                            "Escribe el nombre exacto o clave `POS-XXXX` que deseas asignar."
                        )
                else:
                    # Aceptar el texto tal cual si es un puesto personalizado
                    estado["puesto"] = sin_correo.upper()
            return _construir_siguiente_paso(session_id, estado)

        # Si faltaba correo pero no trajo '@'
        if not estado.get("correo"):
            return "No detecté un correo válido. Por favor escríbelo con `@` (ej. `nombre.apellido@grupovelas.com`)."

        return _construir_siguiente_paso(session_id, estado)

    # B. Si NO hay flujo activo, verificar si el usuario quiere iniciar un alta de usuario
    if _es_intencion_alta_usuario(msg_low):
        estado = {
            "tipo": "usuario",
            "nombre": "",
            "apellidos": "",
            "correo": "",
            "puesto": "",
            "esperando_confirmacion": False
        }
        # Intentar extraer correo si ya viene en el primer mensaje
        correo_det = _extraer_correo(msg)
        if correo_det:
            estado["correo"] = correo_det

        # Intentar extraer nombre si dice "llamado X" o "a X"
        m_nom = re.search(r"(?:llamado|llamada|alta a)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:,|correo|puesto|$)", msg, re.IGNORECASE)
        if m_nom:
            nom, ape = _separar_nombre_apellidos(m_nom.group(1))
            if nom and ape:
                estado["nombre"] = nom
                estado["apellidos"] = ape

        _ESTADOS_SESION[session_id] = estado
        return _construir_siguiente_paso(session_id, estado)

    return None
