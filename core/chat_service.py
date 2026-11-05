"""
Core Domain: Servicio de Chat Interno para Equipo y Torre de Control.
Soporta:
1. Canal Grupal (#equipo / #general)
2. Mensajes Directos 1 a 1 entre compañeros (canales privados generados por pares de IDs)
3. Persistencia en SQLite local (O(1) lectura/escritura, cero dependencias externas)
4. Detección de presencia / compañeros en línea
"""
import os
import sqlite3
import datetime
import threading
from typing import List, Dict, Any, Optional
import requests

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "chat_equipo.db")

def _es_modo_master() -> bool:
    """Verifica si este proceso se ejecuta en la Torre de Control (Master)"""
    publisher_script = os.path.join(BASE_DIR, "publicar_version_equipo.py")
    return os.path.exists(publisher_script)

# Dirección de la Torre de Control central en la red interna de Grupo Velas
TORRE_CHAT_HOST = os.getenv("TORRE_CHAT_HOST", "10.10.200.147")
TORRE_CHAT_PORT = os.getenv("TORRE_CHAT_PORT", "8000")
TORRE_URL = os.getenv("TORRE_CHAT_URL", f"http://{TORRE_CHAT_HOST}:{TORRE_CHAT_PORT}").rstrip("/")

class ChatService:
    _lock = threading.Lock()
    _initialized = False

    @classmethod
    def proxy_torre_get(cls, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        En versión Cliente (clon de compañero), consulta a la Torre central de Esteban en la red.
        Si la Torre no responde o timeout (>2.5s), retorna None para fallback a SQLite local.
        """
        if _es_modo_master():
            return None
        url = f"{TORRE_URL}{path}"
        try:
            r = requests.get(url, params=params, timeout=2.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @classmethod
    def proxy_torre_post(cls, path: str, json_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        En versión Cliente, envía el mensaje/presencia/leído a la Torre central en la red.
        Si la Torre no responde o timeout (>2.5s), retorna None para fallback local.
        """
        if _es_modo_master():
            return None
        url = f"{TORRE_URL}{path}"
        try:
            r = requests.post(url, json=json_data, timeout=2.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @classmethod
    def obtener_identidad_local(cls) -> Dict[str, Any]:
        """
        Determina de forma automática quién es el usuario de esta computadora:
        1. En Master: Siempre Esteban (Torre).
        2. En Cliente: Lee .env (EK10_USER) y resuelve automáticamente el ID y Nombre oficial de Usuarios.json.
        """
        if _es_modo_master():
            return {
                "ok": True,
                "es_master": True,
                "encontrado": True,
                "usuario": {
                    "id": "1",
                    "nombre": "Esteban (Torre)",
                    "puesto": "Administrador Master",
                    "area": "Sistemas",
                    "correo": os.getenv("EK10_USER", "esteban@torre"),
                    "es_torre": True
                }
            }

        # Modo Cliente: buscar correo en .env
        correo_env = (os.getenv("EK10_USER") or os.getenv("EK9_USER") or "").strip().lower()
        if not correo_env:
            env_file = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("EK10_USER=") or line.startswith("EK9_USER="):
                                correo_env = line.split("=", 1)[1].strip().lower()
                                if correo_env:
                                    break
                except Exception:
                    pass

        if correo_env:
            try:
                from core.user_service import UserService
                catalogo = UserService.obtener_usuarios()
                user_match = None

                # 1. Búsqueda exacta por email o clave
                for u in catalogo:
                    u_mail = str(u.get("correo") or u.get("email") or "").strip().lower()
                    u_cve = str(u.get("clave") or "").strip().lower()
                    if correo_env in (u_mail, u_cve):
                        user_match = u
                        break

                # 2. Búsqueda por prefijo antes del @
                if not user_match and "@" in correo_env:
                    prefix = correo_env.split("@")[0].strip().lower()
                    for u in catalogo:
                        u_mail = str(u.get("correo") or u.get("email") or "").strip().lower()
                        u_cve = str(u.get("clave") or "").strip().lower()
                        if prefix == u_mail.split("@")[0] or prefix == u_cve.split("@")[0]:
                            user_match = u
                            break

                if user_match:
                    return {
                        "ok": True,
                        "es_master": False,
                        "encontrado": True,
                        "usuario": {
                            "id": str(user_match.get("id")),
                            "nombre": user_match.get("nombre_completo") or user_match.get("nombre"),
                            "puesto": user_match.get("puesto") or "Colaborador",
                            "area": user_match.get("area_organizacion") or "General",
                            "correo": correo_env,
                            "es_torre": False
                        }
                    }
            except Exception as e:
                print(f"[ChatService] Error resolviendo identidad desde Usuarios.json: {e}")

        return {
            "ok": True,
            "es_master": False,
            "encontrado": False,
            "usuario": None
        }

    @classmethod
    def _init_db(cls):
        with cls._lock:
            if cls._initialized:
                return
            os.makedirs(DATA_DIR, exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Tabla de mensajes
            cur.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canal TEXT NOT NULL,
                remitente_id TEXT NOT NULL,
                remitente_nombre TEXT NOT NULL,
                remitente_rol TEXT DEFAULT 'Colaborador',
                remitente_avatar TEXT DEFAULT '',
                destinatario_id TEXT DEFAULT '',
                destinatario_nombre TEXT DEFAULT '',
                texto TEXT NOT NULL,
                timestamp REAL NOT NULL,
                fecha_hora TEXT NOT NULL,
                leido INTEGER DEFAULT 0
            )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_canal_time ON mensajes(canal, timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_destinatario ON mensajes(destinatario_id, leido)")

            # Tabla de usuarios y presencia (Quién está en línea)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_presencia (
                usuario_id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                puesto TEXT DEFAULT '',
                area TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                es_torre INTEGER DEFAULT 0,
                ultima_actividad REAL NOT NULL,
                fecha_conexion TEXT NOT NULL
            )
            """)
            conn.commit()
            conn.close()
            cls._initialized = True

    @classmethod
    def canal_directo_id(cls, user1: str, user2: str) -> str:
        """Genera un ID canónico determinista para un chat 1 a 1 entre dos usuarios."""
        u1 = str(user1).strip().lower()
        u2 = str(user2).strip().lower()
        return f"dm_{min(u1, u2)}__{max(u1, u2)}"

    @classmethod
    def registrar_presencia(
        cls, 
        usuario_id: str, 
        nombre: str, 
        puesto: str = "", 
        area: str = "", 
        avatar: str = "", 
        es_torre: bool = False
    ) -> Dict[str, Any]:
        cls._init_db()
        ahora_ts = datetime.datetime.now().timestamp()
        ahora_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uid = str(usuario_id).strip()
        nom = str(nombre).strip() or "Usuario"

        with cls._lock:
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("""
                INSERT INTO usuarios_presencia (usuario_id, nombre, puesto, area, avatar, es_torre, ultima_actividad, fecha_conexion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(usuario_id) DO UPDATE SET
                    nombre = excluded.nombre,
                    puesto = excluded.puesto,
                    area = excluded.area,
                    avatar = excluded.avatar,
                    es_torre = excluded.es_torre,
                    ultima_actividad = excluded.ultima_actividad,
                    fecha_conexion = excluded.fecha_conexion
                """, (uid, nom, puesto, area, avatar, 1 if es_torre else 0, ahora_ts, ahora_str))
                conn.commit()
                conn.close()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}

    @classmethod
    def obtener_usuarios_presencia(cls, usuario_actual_id: str = "") -> List[Dict[str, Any]]:
        cls._init_db()
        ahora_ts = datetime.datetime.now().timestamp()
        # Se considera en línea si tuvo actividad en los últimos 2 minutos (120s)
        umbral_online = ahora_ts - 120

        with cls._lock:
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM usuarios_presencia ORDER BY es_torre DESC, nombre ASC")
                filas = cur.fetchall()
                conn.close()

                res = []
                for f in filas:
                    en_linea = f["ultima_actividad"] >= umbral_online
                    res.append({
                        "usuario_id": f["usuario_id"],
                        "nombre": f["nombre"],
                        "puesto": f["puesto"],
                        "area": f["area"],
                        "avatar": f["avatar"],
                        "es_torre": bool(f["es_torre"]),
                        "en_linea": en_linea,
                        "ultima_actividad": f["fecha_conexion"]
                    })
                return res
            except Exception as e:
                print(f"[ChatService] Error obteniendo usuarios: {e}")
                return []

    @classmethod
    def enviar_mensaje(
        cls,
        canal: str,
        remitente_id: str,
        remitente_nombre: str,
        texto: str,
        remitente_rol: str = "Colaborador",
        remitente_avatar: str = "",
        destinatario_id: str = "",
        destinatario_nombre: str = ""
    ) -> Dict[str, Any]:
        cls._init_db()
        texto = texto.strip()
        if not texto:
            return {"ok": False, "error": "El mensaje no puede estar vacío."}

        ahora = datetime.datetime.now()
        timestamp = ahora.timestamp()
        fecha_hora = ahora.strftime("%Y-%m-%d %H:%M:%S")
        hora_corta = ahora.strftime("%I:%M %p").lstrip("0")

        canal_limpio = canal.strip().lower() or "general"
        # Si es un mensaje 1 a 1 y no viene formateado el canal, formatearlo
        if destinatario_id and not canal_limpio.startswith("dm_"):
            canal_limpio = cls.canal_directo_id(remitente_id, destinatario_id)

        with cls._lock:
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("""
                INSERT INTO mensajes (
                    canal, remitente_id, remitente_nombre, remitente_rol, remitente_avatar,
                    destinatario_id, destinatario_nombre, texto, timestamp, fecha_hora, leido
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    canal_limpio, str(remitente_id), str(remitente_nombre), str(remitente_rol),
                    str(remitente_avatar), str(destinatario_id), str(destinatario_nombre),
                    texto, timestamp, fecha_hora
                ))
                msg_id = cur.lastrowid
                conn.commit()
                conn.close()

                return {
                    "ok": True,
                    "mensaje": {
                        "id": msg_id,
                        "canal": canal_limpio,
                        "remitente_id": str(remitente_id),
                        "remitente_nombre": str(remitente_nombre),
                        "remitente_rol": str(remitente_rol),
                        "remitente_avatar": str(remitente_avatar),
                        "destinatario_id": str(destinatario_id),
                        "destinatario_nombre": str(destinatario_nombre),
                        "texto": texto,
                        "timestamp": timestamp,
                        "fecha_hora": fecha_hora,
                        "hora_corta": hora_corta,
                        "leido": 0
                    }
                }
            except Exception as e:
                return {"ok": False, "error": f"Error guardando mensaje: {str(e)}"}

    @classmethod
    def obtener_mensajes(cls, canal: str, limite: int = 80, desde_id: int = 0) -> List[Dict[str, Any]]:
        cls._init_db()
        canal_limpio = canal.strip().lower() or "general"
        with cls._lock:
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                
                if desde_id > 0:
                    cur.execute("""
                    SELECT * FROM mensajes
                    WHERE canal = ? AND id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """, (canal_limpio, desde_id, limite))
                else:
                    cur.execute("""
                    SELECT * FROM (
                        SELECT * FROM mensajes
                        WHERE canal = ?
                        ORDER BY id DESC
                        LIMIT ?
                    ) ORDER BY id ASC
                    """, (canal_limpio, limite))
                
                filas = cur.fetchall()
                conn.close()

                mensajes = []
                for f in filas:
                    dt = datetime.datetime.fromtimestamp(f["timestamp"])
                    mensajes.append({
                        "id": f["id"],
                        "canal": f["canal"],
                        "remitente_id": f["remitente_id"],
                        "remitente_nombre": f["remitente_nombre"],
                        "remitente_rol": f["remitente_rol"],
                        "remitente_avatar": f["remitente_avatar"],
                        "destinatario_id": f["destinatario_id"],
                        "destinatario_nombre": f["destinatario_nombre"],
                        "texto": f["texto"],
                        "timestamp": f["timestamp"],
                        "fecha_hora": f["fecha_hora"],
                        "hora_corta": dt.strftime("%I:%M %p").lstrip("0"),
                        "leido": bool(f["leido"])
                    })
                return mensajes
            except Exception as e:
                print(f"[ChatService] Error consultando mensajes: {e}")
                return []

    @classmethod
    def marcar_como_leidos(cls, canal: str, usuario_id: str) -> bool:
        cls._init_db()
        canal_limpio = canal.strip().lower()
        with cls._lock:
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("""
                UPDATE mensajes 
                SET leido = 1 
                WHERE canal = ? AND remitente_id != ? AND leido = 0
                """, (canal_limpio, str(usuario_id)))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"[ChatService] Error marcando leidos: {e}")
                return False

    @classmethod
    def obtener_resumen_canales(cls, usuario_id: str) -> Dict[str, Any]:
        """Retorna el estado de no leídos para el canal general y para cada contacto directo."""
        cls._init_db()
        uid = str(usuario_id).strip().lower()
        with cls._lock:
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                # No leídos en General
                cur.execute("""
                SELECT COUNT(*) as no_leidos 
                FROM mensajes 
                WHERE canal = 'general' AND remitente_id != ? AND leido = 0
                """, (uid,))
                row_gen = cur.fetchone()
                no_leidos_general = row_gen["no_leidos"] if row_gen else 0

                # No leídos en DMs donde yo soy el destinatario
                cur.execute("""
                SELECT canal, remitente_id, COUNT(*) as no_leidos
                FROM mensajes
                WHERE destinatario_id = ? AND leido = 0
                GROUP BY canal, remitente_id
                """, (uid,))
                filas_dms = cur.fetchall()
                dms_no_leidos = {f["remitente_id"]: f["no_leidos"] for f in filas_dms}

                # Último mensaje de general
                cur.execute("SELECT texto, remitente_nombre, timestamp FROM mensajes WHERE canal = 'general' ORDER BY id DESC LIMIT 1")
                row_last = cur.fetchone()
                ultimo_general = dict(row_last) if row_last else None

                conn.close()
                return {
                    "general": {
                        "no_leidos": no_leidos_general,
                        "ultimo_mensaje": ultimo_general
                    },
                    "dms_no_leidos": dms_no_leidos
                }
            except Exception as e:
                print(f"[ChatService] Error en resumen de canales: {e}")
                return {"general": {"no_leidos": 0, "ultimo_mensaje": None}, "dms_no_leidos": {}}

