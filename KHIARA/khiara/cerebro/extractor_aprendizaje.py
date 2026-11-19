"""
Extractor Controlado de Aprendizaje para KHIARA.
Solo persiste reglas globales cuando el usuario lo indica explícitamente
("aprende que...", "recuerda que...", "guarda que...", "ten en cuenta que..."),
evitando contaminar la memoria colectiva con conversaciones casuales.
"""

import re
import logging
from typing import Optional, Dict, Any
from khiara.cerebro.memoria_evolutiva import memoria_evolutiva_global

logger = logging.getLogger("khiara.aprendizaje")

PATRONES_ENSENANZA_EXPLICITA = [
    r"^(?:khiara[,\s]+)?(?:aprende|recuerda|guarda|memoriza|anota)\s+(?:que|esto:?)\s+(.+)$",
    r"^(?:khiara[,\s]+)?ten\s+en\s+cuenta\s+que\s+(.+)$",
    r"^(?:khiara[,\s]+)?guarda\s+(?:esta\s+)?regla:?\s+(.+)$",
]


def detectar_comando_aprendizaje(mensaje: str, usuario_id: str = "esteban") -> Optional[str]:
    """
    Comandos instantáneos (<10ms) para controlar explícitamente qué SÍ y qué NO aprende KHIARA:
    - 'aprende que ...' / 'recuerda que ...' / 'guarda regla: ...' -> Guarda permanentemente
    - 'qué has aprendido' / 'ver reglas' / 'lista tus aprendizajes' -> Lista reglas con su ID
    - 'olvida RULE_xxxx' / 'borra RULE_xxxx' -> Elimina la regla indicada
    """
    msg = mensaje.strip()
    msg_low = msg.lower()
    norm = msg_low.replace("é", "e").replace("á", "a").replace("í", "i").replace("ó", "o").replace("ú", "u")

    # 1. Borrar / Olvidar una regla específica (insensible a mayúsculas/minúsculas)
    m_del = re.match(r"^(?:olvida|borra|elimina)\s+(RULE_[a-zA-Z0-9]+)", msg, re.IGNORECASE)
    if m_del:
        id_buscado = m_del.group(1).lower()
        memoria_evolutiva_global._cargar_reglas()
        id_real = next((k for k in memoria_evolutiva_global.reglas.keys() if k.lower() == id_buscado), None)
        if id_real and memoria_evolutiva_global.eliminar_regla(id_real):
            return f"🗑️ Listo, eliminé permanentemente la regla **`{id_real}`** de mi memoria."
        return f"No encontré ninguna regla guardada con el ID `{m_del.group(1)}`."

    # 2. Listar aprendizajes guardados
    if any(k in norm for k in [
        "que has aprendido", "lista tus aprendizajes", "ver reglas",
        "tus reglas", "que reglas sabes", "que sabes guardado", "ver aprendizajes"
    ]):
        memoria_evolutiva_global._cargar_reglas()
        reglas = memoria_evolutiva_global.listar_todas()
        if not reglas:
            return "Aún no tengo reglas personalizadas guardadas. Puedes enseñarme diciendo: **\"aprende que ...\"**."
        lineas = [f"🧠 **Reglas aprendidas guardadas ({len(reglas)}):**"]
        for r in reglas[-15:]:
            lineas.append(f"• **`{r['id']}`** [{r['categoria']}]: {r['regla']}")
        lineas.append("\nPara borrar alguna, dime: `olvida RULE_xxxx`.")
        return "\n".join(lineas)

    # 3. Guardar nueva regla explícita
    for pat in PATRONES_ENSENANZA_EXPLICITA:
        m = re.match(pat, msg, re.IGNORECASE | re.DOTALL)
        if m:
            texto_regla = m.group(1).strip()
            if len(texto_regla) < 4:
                return "Dime qué dato o regla quieres que guarde (ej. *\"aprende que el insumo 1300001 va en compañía 20\"*)."
            res = memoria_evolutiva_global.registrar_regla(
                texto_regla=texto_regla,
                categoria="REGLA_NEGOCIO",
                proyecto_asociado=usuario_id
            )
            if res.get("ok"):
                rid = res["id"]
                return (
                    f"✅ **¡Aprendido y guardado permanentemente!** (`{rid}`)\n"
                    f"• *\"{texto_regla}\"*\n\n"
                    f"Ya quedó integrado en mi memoria. Si algún día deseas quitarlo, escribe `olvida {rid}`."
                )
    return None


def analizar_y_aprender_de_turno(
    mensaje_usuario: str,
    respuesta_khiara: str,
    usuario_id: str = "esteban"
) -> Optional[Dict[str, Any]]:
    """
    Se mantiene solo para registros explícitos; las charlas normales quedan
    únicamente en el historial privado (conversaciones.db) sin ensuciar reglas globales.
    """
    return None
