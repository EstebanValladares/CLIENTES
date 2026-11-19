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
# Recuerda el último puesto usado en un alta de usuario por sesión (para "crea su posicion")
_ULTIMO_PUESTO_SESION: Dict[str, str] = {}


def limpiar_flujo_sesion(session_id: str):
    _ESTADOS_SESION.pop(session_id, None)


def tiene_flujo_activo(session_id: str) -> bool:
    return session_id in _ESTADOS_SESION


def _cargar_json_puestos() -> Dict[str, Any]:
    if not ARCHIVO_PUESTOS.exists():
        return {}
    try:
        return json.loads(ARCHIVO_PUESTOS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cargar_puestos() -> Dict[str, Any]:
    data = _cargar_json_puestos()
    return data.get("puestos", {}) if isinstance(data, dict) else {}


def obtener_info_ultima_posicion() -> Dict[str, Any]:
    """Devuelve la última clave POS-XXXX registrada y sugiere la siguiente disponible."""
    data = _cargar_json_puestos()
    claves: List[Tuple[int, str, str]] = []

    for nombre, info in data.get("puestos", {}).items():
        c = str(info.get("clave_posicion_cloud", "")).strip()
        m = re.match(r"POS-(\d+)", c, re.IGNORECASE)
        if m:
            claves.append((int(m.group(1)), c.upper(), nombre))

    for reg in data.get("posiciones_registradas", []):
        c = str(reg.get("clave", "")).strip()
        m = re.match(r"POS-(\d+)", c, re.IGNORECASE)
        if m:
            claves.append((int(m.group(1)), c.upper(), reg.get("nombre", "")))

    claves.sort(key=lambda x: x[0], reverse=True)
    if not claves:
        return {
            "ultima_clave": "POS-1084",
            "ultimo_nombre": "N/A",
            "siguiente_clave": "POS-1085",
            "total": len(data.get("puestos", {}))
        }

    top_num, top_clave, top_nombre = claves[0]
    return {
        "ultima_clave": top_clave,
        "ultimo_nombre": top_nombre,
        "siguiente_clave": f"POS-{top_num + 1:04d}",
        "total": len(data.get("puestos", {}))
    }


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
    return " ".join(partes[:-2]).upper(), " ".join(partes[-2:]).upper()


def _extraer_correo(texto: str) -> Optional[str]:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texto)
    return m.group(0).lower() if m else None


def _extraer_clave_pos(texto: str) -> Optional[str]:
    m = re.search(r"\bPOS-\d{3,5}\b", texto, re.IGNORECASE)
    return m.group(0).upper() if m else None


def _es_intencion_alta_usuario(msg_low: str) -> bool:
    disparadores = [
        "dar de alta", "alta de usuario", "alta de un usuario", "alta a un usuario",
        "crear usuario", "crear un usuario", "crea un usuario", "nuevo usuario",
        "registrar usuario", "alta de colaborador", "nuevo colaborador",
        "llenar usuario", "alta usuario"
    ]
    if "posicion" in msg_low or "posición" in msg_low or "puesto" in msg_low:
        if "usuario" not in msg_low and "colaborador" not in msg_low:
            return False
    return any(d in msg_low for d in disparadores)


def _es_intencion_alta_posicion(msg_low: str) -> bool:
    norm = msg_low.replace("ó", "o")
    disparadores = [
        "crear posicion", "crea posicion", "crea la posicion", "crear la posicion",
        "crear su posicion", "crea su posicion", "nueva posicion", "alta de posicion",
        "alta posicion", "registrar posicion", "dar de alta posicion", "dar de alta una posicion",
        "crear puesto", "nuevo puesto", "alta de puesto", "alta puesto"
    ]
    return any(d in norm for d in disparadores)


def _es_consulta_ultima_clave_pos(msg_low: str) -> bool:
    norm = msg_low.replace("ó", "o").replace("ú", "u")
    tiene_pos = "posicion" in norm or "puesto" in norm or "pos-" in norm
    tiene_clave = any(k in norm for k in ["ultima clave", "ultimo pos", "siguiente clave", "clave mas alta", "ultima posicion", "ultimo numero"])
    return tiene_pos and tiene_clave


def _es_cancelacion(msg_low: str) -> bool:
    return msg_low.strip() in {
        "cancelar", "cancela", "salir", "detener", "olvídalo", "olvidalo", "no gracias", "abortar"
    }


def _es_confirmacion(msg_low: str) -> Tuple[bool, bool]:
    limpio = msg_low.strip().replace("í", "i").replace("ó", "o")
    guardar = any(k in limpio for k in ["guardar", "produccion", "definitivo", "directo"])
    afirmativos = ["si", "adelante", "confirmo", "dale", "inicia", "crear", "llena", "procede", "ok", "va"]
    es_si = any(limpio == a or limpio.startswith(a + " ") for a in afirmativos)
    return es_si, guardar


def _sugerir_correo(nombre: str, apellidos: str) -> str:
    n = nombre.split()[0].lower() if nombre else "usuario"
    a = apellidos.split()[0].lower() if apellidos else "velas"
    for orig, rep in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        n = n.replace(orig, rep)
        a = a.replace(orig, rep)
    return f"{n}.{a}@grupovelas.com"


def _construir_paso_usuario(estado: Dict[str, Any]) -> str:
    if not estado.get("nombre") or not estado.get("apellidos"):
        return (
            "¡Con gusto te ayudo a dar de alta al nuevo usuario! 🚀\n"
            "Dime su **Nombre y Apellidos completos** (o envíame nombre, correo y puesto juntos)."
        )
    if not estado.get("correo"):
        sug = _sugerir_correo(estado["nombre"], estado["apellidos"])
        return (
            f"Perfecto, anoté a **{estado['nombre']} {estado['apellidos']}**.\n"
            f"Ahora dime su **correo corporativo** (ej. `{sug}`)."
        )
    if not estado.get("puesto"):
        return (
            f"Anotado el correo `{estado['correo']}`.\n"
            f"¿Qué **Puesto o Posición** ocupará? (Puedes escribir el nombre o clave `POS-XXXX`, ej. *Asesor de Venta Tampico*)."
        )

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


def _construir_paso_posicion(estado: Dict[str, Any]) -> str:
    info_ult = obtener_info_ultima_posicion()
    if not estado.get("clave"):
        return (
            f"¡Con gusto te ayudo a crear la nueva posición! 🏗️\n"
            f"La última clave registrada es **`{info_ult['ultima_clave']}`** (*{info_ult['ultimo_nombre']}*).\n"
            f"¿Usamos la siguiente clave **`{info_ult['siguiente_clave']}`** o prefieres otra clave `POS-XXXX`?"
        )
    if not estado.get("nombre"):
        sug_puesto = estado.get("puesto_sugerido", "")
        extra = f" (o responde **\"mismo\"** para usar *{sug_puesto}*)" if sug_puesto else ""
        return (
            f"Anotada la clave **`{estado['clave']}`**.\n"
            f"¿Cuál es el **Nombre oficial del puesto/posición**?{extra}"
        )
    if not estado.get("categoria"):
        return (
            f"Anotado el puesto **{estado['nombre']}**.\n"
            f"¿Qué **Categoría** le asignamos? (ej. `VENTAS`, `OBRA`, `TITULACIÓN`, `SISTEMAS`, `ADMINISTRACION`)."
        )

    estado["esperando_confirmacion"] = True
    return (
        "📋 **Confirma los datos de la nueva Posición en Aryve:**\n"
        f"• **Clave:** `{estado['clave']}`\n"
        f"• **Nombre:** {estado['nombre']}\n"
        f"• **Categoría:** {estado['categoria']}\n"
        f"• **Puesto Superior:** {estado.get('padre') or 'N/A'}\n\n"
        "Responde **\"sí\"** para abrir Aryve y llenar la posición (revisión), "
        "**\"sí guardar\"** para guardar definitivo, o **\"cancelar\"**."
    )


def _parece_pregunta_o_consulta_sistema(msg: str) -> bool:
    """Detecta si el usuario está haciendo una pregunta o consultando otro módulo para no atraparlo como nombre de usuario."""
    m_low = msg.lower().strip()
    norm = m_low.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if "?" in m_low or "¿" in m_low:
        return True
    palabras_sistema = [
        "cuantas ", "cuantos ", "cual ", "cuales ", "como ", "donde ", "por que ", "porque ",
        "que es ", "que son ", "existe ", "busca ", "consulta ", "dime ", "muestra ",
        "orden de compra", "ordenes de compra", " base de datos", " db ", "ek9", "ek10",
        "escalatoria", "insumo", "obras", "presupuesto", "lote", "manzana", "correo nuevo",
        "correos", "gmail", "tipo 1", "tipo 2", "tipo 3", "tipo 4", "tipo 5", "grupo ",
        "reporte", "explosion", "tabla", "sql", "aprende que", "recuerda que"
    ]
    return any(p in f" {norm} " for p in palabras_sistema)


def procesar_flujo_alta(session_id: str, mensaje: str) -> Optional[str]:
    """
    Intercepta y resuelve de forma instantánea (<50ms) el flujo de alta de usuarios,
    creación de posiciones y consultas de última clave POS-XXXX.
    """
    msg = mensaje.strip()
    msg_low = msg.lower()

    # 0. Consulta directa de última clave POS-XXXX
    if _es_consulta_ultima_clave_pos(msg_low):
        info = obtener_info_ultima_posicion()
        return (
            f"🏷️ **Catálogo de Posiciones ({info['total']} registradas):**\n"
            f"• **Última clave registrada:** `{info['ultima_clave']}` (*{info['ultimo_nombre']}*)\n"
            f"• **Siguiente clave disponible:** **`{info['siguiente_clave']}`**\n\n"
            "Si deseas crearla ahora, dime **\"crea la posición\"**."
        )

    # 0.5 Si pregunta si puede crear un usuario sin guardar, responder sin bloquear la sesión
    if ("sin darle a guardar" in msg_low or "sin guardar" in msg_low) and ("usuario" in msg_low or "posicion" in msg_low or "posición" in msg_low):
        limpiar_flujo_sesion(session_id)
        return (
            "¡Sí! Por defecto lleno todos los campos en Aryve en **Modo Revisión (sin guardar)** "
            "para que tú verifiques en el navegador antes de confirmar.\n"
            "Cuando quieras iniciar el proceso, dime **\"dar de alta usuario\"** o **\"crea la posición\"**."
        )

    # A. Si ya hay un flujo activo para esta sesión
    if session_id in _ESTADOS_SESION:
        estado = _ESTADOS_SESION[session_id]

        if _es_cancelacion(msg_low):
            limpiar_flujo_sesion(session_id)
            return "Entendido, cancelé el proceso. ¿En qué más puedo apoyarte?"

        # Si el usuario cambió de tema y está haciendo una pregunta o consulta del sistema, salir del asistente
        if not estado.get("esperando_confirmacion") and _parece_pregunta_o_consulta_sistema(msg):
            limpiar_flujo_sesion(session_id)
            return None

        # ---- FLUJO ACTIVO: POSICIÓN ----
        if estado.get("tipo") == "posicion":
            if estado.get("esperando_confirmacion"):
                es_si, guardar = _es_confirmacion(msg_low)
                if es_si:
                    from khiara.herramientas.explorador import tool_iniciar_creacion_posicion
                    datos = dict(estado)
                    limpiar_flujo_sesion(session_id)
                    return tool_iniciar_creacion_posicion(
                        clave=datos["clave"],
                        nombre=datos["nombre"],
                        categoria=datos["categoria"],
                        puesto_padre=datos.get("padre", ""),
                        guardar_en_produccion=guardar
                    )
                elif msg_low in {"no", "corregir", "cambiar"}:
                    estado["esperando_confirmacion"] = False
                    return "¿Qué dato deseas corregir? (Escribe la nueva clave POS-XXXX, nombre o categoría)."

            if not estado.get("clave"):
                clave_det = _extraer_clave_pos(msg)
                if clave_det:
                    estado["clave"] = clave_det
                else:
                    es_si, _ = _es_confirmacion(msg_low)
                    if es_si or "siguiente" in msg_low or "esa" in msg_low:
                        estado["clave"] = obtener_info_ultima_posicion()["siguiente_clave"]
                    else:
                        # Si escribió directo el nombre del puesto, asignar siguiente clave y ese nombre
                        estado["clave"] = obtener_info_ultima_posicion()["siguiente_clave"]
                        estado["nombre"] = msg.upper()
                return _construir_paso_posicion(estado)

            if not estado.get("nombre"):
                if msg_low in {"mismo", "el mismo", "igual", "si", "sí"} and estado.get("puesto_sugerido"):
                    estado["nombre"] = estado["puesto_sugerido"]
                else:
                    estado["nombre"] = msg.upper()
                return _construir_paso_posicion(estado)

            if not estado.get("categoria"):
                estado["categoria"] = msg.upper()
                return _construir_paso_posicion(estado)

            return _construir_paso_posicion(estado)

        # ---- FLUJO ACTIVO: USUARIO ----
        if estado.get("esperando_confirmacion"):
            es_si, guardar = _es_confirmacion(msg_low)
            if es_si:
                from khiara.herramientas.explorador import tool_iniciar_creacion_usuario
                datos = dict(estado)
                _ULTIMO_PUESTO_SESION[session_id] = datos["puesto"]
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

        correo_det = _extraer_correo(msg)
        if correo_det:
            estado["correo"] = correo_det

        if not estado.get("nombre") or not estado.get("apellidos"):
            sin_correo = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "", msg).strip()
            nom, ape = _separar_nombre_apellidos(sin_correo)
            if nom and ape:
                estado["nombre"] = nom
                estado["apellidos"] = ape
            elif nom and not ape:
                estado["nombre"] = nom
                return f"Anoté el nombre **{nom}**. ¿Cuáles son sus **apellidos**?"
            return _construir_paso_usuario(estado)

        if estado.get("correo") and not estado.get("puesto"):
            sin_correo = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "", msg).strip()
            if sin_correo:
                coincidencias = _buscar_puesto(sin_correo)
                if len(coincidencias) == 1:
                    estado["puesto"] = coincidencias[0][0]
                elif len(coincidencias) > 1:
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
                    estado["puesto"] = sin_correo.upper()
            return _construir_paso_usuario(estado)

        if not estado.get("correo"):
            return "No detecté un correo válido. Por favor escríbelo con `@` (ej. `nombre.apellido@grupovelas.com`)."

        return _construir_paso_usuario(estado)

    # B. Iniciar flujo de CREACIÓN DE POSICIÓN
    if _es_intencion_alta_posicion(msg_low):
        clave_det = _extraer_clave_pos(msg) or ""
        estado = {
            "tipo": "posicion",
            "clave": clave_det,
            "nombre": "",
            "categoria": "",
            "padre": "",
            "puesto_sugerido": _ULTIMO_PUESTO_SESION.get(session_id, ""),
            "esperando_confirmacion": False
        }
        _ESTADOS_SESION[session_id] = estado
        return _construir_paso_posicion(estado)

    # C. Iniciar flujo de ALTA DE USUARIO
    if _es_intencion_alta_usuario(msg_low):
        estado = {
            "tipo": "usuario",
            "nombre": "",
            "apellidos": "",
            "correo": "",
            "puesto": "",
            "esperando_confirmacion": False
        }
        correo_det = _extraer_correo(msg)
        if correo_det:
            estado["correo"] = correo_det

        m_nom = re.search(r"(?:llamado|llamada|alta a)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:,|correo|puesto|$)", msg, re.IGNORECASE)
        if m_nom:
            nom, ape = _separar_nombre_apellidos(m_nom.group(1))
            if nom and ape:
                estado["nombre"] = nom
                estado["apellidos"] = ape

        _ESTADOS_SESION[session_id] = estado
        return _construir_paso_usuario(estado)

    return None
