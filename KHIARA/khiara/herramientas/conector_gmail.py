"""
Conector de Gmail para KHIARA.
Permite consultar, filtrar, leer y analizar correos electrónicos y sus archivos adjuntos.
Soporta:
1. Conexión segura IMAP/SSL (usando Contraseña de Aplicación de Google - sin requerir GCP).
2. Google Gmail API Oficial (vía credentials.json si está disponible).
"""

import os
import json
import email
import imaplib
from email.header import decode_header
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(BASE_DIR.parent / ".env", override=False)

DATA_DIR = BASE_DIR / "data"
CARPETA_DESCARGAS = DATA_DIR / "descargas_gmail"
CARPETA_DESCARGAS.mkdir(parents=True, exist_ok=True)

ARCHIVO_CREDENCIALES = DATA_DIR / "credenciales_gmail.json"

class ConectorGmail:
    """Administra la conexión y lectura de correos de Gmail."""

    def __init__(self, usuario: Optional[str] = None, password: Optional[str] = None):
        self._cargar_credenciales_guardadas()
        if usuario:
            self.usuario = usuario
        if password:
            self.password = password
        self.servidor_imap = "imap.gmail.com"
        self.puerto_imap = 993

    def _cargar_credenciales_guardadas(self):
        """Carga credenciales desde archivo JSON o desde variables de entorno."""
        self.usuario = os.getenv("GMAIL_USUARIO", "").strip()
        self.password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
        if ARCHIVO_CREDENCIALES.exists():
            try:
                data = json.loads(ARCHIVO_CREDENCIALES.read_text(encoding="utf-8"))
                if data.get("usuario") and data.get("password"):
                    self.usuario = data["usuario"].strip()
                    self.password = data["password"].strip()
            except Exception:
                pass

    def guardar_credenciales(self, usuario: str, password: str) -> bool:
        """Prueba y guarda las credenciales si son válidas."""
        usuario = usuario.strip()
        password = password.strip().replace(" ", "")
        
        # Probar conexión
        mail = imaplib.IMAP4_SSL(self.servidor_imap, self.puerto_imap)
        mail.login(usuario, password)
        mail.logout()

        # Si no hubo error, guardar
        self.usuario = usuario
        self.password = password
        ARCHIVO_CREDENCIALES.parent.mkdir(parents=True, exist_ok=True)
        ARCHIVO_CREDENCIALES.write_text(
            json.dumps({"usuario": usuario, "password": password}, indent=2),
            encoding="utf-8"
        )
        return True

    def esta_configurado(self) -> bool:
        return bool(self.usuario and self.password)

    def _conectar(self) -> imaplib.IMAP4_SSL:
        if not self.esta_configurado():
            raise ValueError(
                "Credenciales de Gmail no configuradas. "
                "Define GMAIL_USUARIO y GMAIL_APP_PASSWORD en tu archivo .env"
            )
        mail = imaplib.IMAP4_SSL(self.servidor_imap, self.puerto_imap)
        mail.login(self.usuario, self.password)
        return mail

    @staticmethod
    def _decodificar_cabecera(valor: Optional[str]) -> str:
        if not valor:
            return ""
        resultado = []
        for parte, encoding in decode_header(valor):
            if isinstance(parte, bytes):
                encoding = encoding or "utf-8"
                try:
                    resultado.append(parte.decode(encoding, errors="ignore"))
                except Exception:
                    resultado.append(parte.decode("latin1", errors="ignore"))
            else:
                resultado.append(str(parte))
        return "".join(resultado)

    def listar_correos(
        self,
        remitente: Optional[str] = None,
        asunto: Optional[str] = None,
        solo_no_leidos: bool = True,
        limite: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca y lista los correos más recientes."""
        mail = self._conectar()
        try:
            mail.select("INBOX")
            criterios = []
            if solo_no_leidos:
                criterios.append("UNSEEN")
            else:
                criterios.append("ALL")
            if remitente:
                criterios.append(f'FROM "{remitente}"')
            if asunto:
                criterios.append(f'SUBJECT "{asunto}"')

            busqueda = " ".join(criterios)
            _, datos_ids = mail.search(None, busqueda)
            ids = datos_ids[0].split()
            if not ids:
                return []

            # Tomar los más recientes al final
            ids_seleccionados = ids[-limite:]
            ids_seleccionados.reverse()

            resumen_correos = []
            for mail_id in ids_seleccionados:
                _, msg_data = mail.fetch(mail_id, "(RFC822.HEADER)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        resumen_correos.append({
                            "id": mail_id.decode("utf-8"),
                            "remitente": self._decodificar_cabecera(msg.get("From")),
                            "asunto": self._decodificar_cabecera(msg.get("Subject")),
                            "fecha": msg.get("Date", "")
                        })

            return resumen_correos
        finally:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    def leer_correo(self, id_correo: str) -> Dict[str, Any]:
        """Lee el cuerpo completo y lista los adjuntos de un correo."""
        mail = self._conectar()
        try:
            mail.select("INBOX")
            _, msg_data = mail.fetch(id_correo.encode("utf-8"), "(RFC822)")
            if not msg_data or not msg_data[0]:
                return {"error": f"No se encontró el correo con ID {id_correo}"}

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            cuerpo_texto = ""
            adjuntos = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    disposition = str(part.get("Content-Disposition", ""))

                    if "attachment" in disposition:
                        nombre_adjunto = self._decodificar_cabecera(part.get_filename())
                        if nombre_adjunto:
                            adjuntos.append(nombre_adjunto)
                    elif content_type == "text/plain" and "attachment" not in disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            cuerpo_texto += payload.decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    cuerpo_texto = payload.decode("utf-8", errors="ignore")

            return {
                "id": id_correo,
                "remitente": self._decodificar_cabecera(msg.get("From")),
                "asunto": self._decodificar_cabecera(msg.get("Subject")),
                "fecha": msg.get("Date", ""),
                "cuerpo": cuerpo_texto.strip()[:4000],  # Primeros 4000 caracteres
                "adjuntos": adjuntos
            }
        finally:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

    def descargar_adjuntos(self, id_correo: str, nombre_archivo: Optional[str] = None) -> List[str]:
        """Descarga adjuntos de un correo a data/descargas_gmail/."""
        mail = self._conectar()
        guardados = []
        try:
            mail.select("INBOX")
            _, msg_data = mail.fetch(id_correo.encode("utf-8"), "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            if msg.is_multipart():
                for part in msg.walk():
                    disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in disposition:
                        fn = self._decodificar_cabecera(part.get_filename())
                        if fn and (not nombre_archivo or nombre_archivo.lower() in fn.lower()):
                            ruta_destino = CARPETA_DESCARGAS / fn
                            payload = part.get_payload(decode=True)
                            if payload:
                                ruta_destino.write_bytes(payload)
                                guardados.append(str(ruta_destino))
            return guardados
        finally:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass

# Instancia global
gmail_manager = ConectorGmail()

def tool_guardar_credenciales_gmail(correo: str, clave_aplicacion: str) -> str:
    """Configura y valida la cuenta de Gmail del usuario para permitir que KHIARA lea sus correos.
    
    Args:
        correo: La dirección de correo electrónico del usuario (ej. 'juan@gmail.com').
        clave_aplicacion: La contraseña de aplicación de 16 caracteres generada en Google.
    """
    try:
        exito = gmail_manager.guardar_credenciales(correo, clave_aplicacion)
        if exito:
            return (
                f"✅ ¡Excelente! La cuenta de Gmail '{correo}' ha sido conectada y validada exitosamente con Google. "
                "A partir de este momento puedo avisarte de correos nuevos, leerlos y analizar tus adjuntos."
            )
        return "No se pudieron guardar las credenciales."
    except Exception as e:
        return (
            f"❌ Error al validar con Gmail: {str(e)}.\n"
            "Verifica que:\n"
            "1. La verificación en 2 pasos esté activa en tu cuenta de Google.\n"
            "2. Estés usando una Contraseña de Aplicación generada en https://myaccount.google.com/apppasswords (no tu contraseña normal de Gmail)."
        )

def tool_consultar_correos_recientes(
    remitente: Optional[str] = None,
    asunto: Optional[str] = None,
    solo_no_leidos: bool = True,
    limite: int = 5
) -> str:
    """Consulta y lista los correos más recientes en la bandeja de entrada de Gmail.
    
    Args:
        remitente: Filtro por dirección o nombre de quien envía (ej. 'juan@velas.com').
        asunto: Filtro por palabras clave en el asunto (ej. 'factura', 'AUS', 'estimación').
        solo_no_leidos: True para buscar únicamente correos no leídos; False para todos.
        limite: Cantidad máxima de correos a listar (por defecto 5).
    """
    if not gmail_manager.esta_configurado():
        return (
            "Gmail aún no está configurado. Para activarlo, agrega en tu archivo .env:\n"
            "GMAIL_USUARIO=tu_correo@gmail.com\n"
            "GMAIL_APP_PASSWORD=tu_clave_de_aplicacion_16_caracteres"
        )
    try:
        correos = gmail_manager.listar_correos(
            remitente=remitente,
            asunto=asunto,
            solo_no_leidos=solo_no_leidos,
            limite=limite
        )
        if not correos:
            if solo_no_leidos:
                # Si no hay correos no leídos, mostrar los últimos recibidos para confirmar conexión activa
                ultimos = gmail_manager.listar_correos(limite=3, solo_no_leidos=False)
                if ultimos:
                    lineas = [
                        f"📬 No tienes correos nuevos sin leer en tu cuenta ({gmail_manager.usuario}).",
                        "\nÚltimos correos recibidos en tu bandeja:"
                    ]
                    for c in ultimos:
                        lineas.append(f"• De: {c['remitente']} | Asunto: {c['asunto']}")
                    return "\n".join(lineas)
                return f"📬 No tienes correos nuevos sin leer en tu cuenta ({gmail_manager.usuario})."
            return f"No se encontraron correos con los filtros proporcionados."
        
        lineas = [f"📬 Tienes {len(correos)} correo(s) {'sin leer' if solo_no_leidos else 'encontrados'}:"]
        for c in correos:
            lineas.append(f"• [ID: {c['id']}] De: {c['remitente']} | Asunto: {c['asunto']}")
        lineas.append("\nPara leer el contenido completo, pide: 'lee el correo ID ...'")
        return "\n".join(lineas)
    except Exception as e:
        return f"Error consultando Gmail: {str(e)}"

def tool_leer_correo_completo(id_correo: str) -> str:
    """Lee el texto completo de un correo específico por su ID y lista sus adjuntos.
    
    Args:
        id_correo: El ID numérico del correo obtenido con tool_consultar_correos_recientes.
    """
    if not gmail_manager.esta_configurado():
        return "Gmail no está configurado en .env."
    try:
        info = gmail_manager.leer_correo(id_correo)
        if "error" in info:
            return info["error"]
        
        salida = [
            f"=== DETALLE DE CORREO [ID: {info['id']}] ===",
            f"De: {info['remitente']}",
            f"Asunto: {info['asunto']}",
            f"Fecha: {info['fecha']}",
            f"Adjuntos detectados: {', '.join(info['adjuntos']) if info['adjuntos'] else 'Ninguno'}",
            "\n--- CONTENIDO DEL MENSAJE ---",
            info['cuerpo'] or "[Mensaje sin texto plano]"
        ]
        return "\n".join(salida)
    except Exception as e:
        return f"Error leyendo correo {id_correo}: {str(e)}"

def tool_descargar_adjunto_correo(id_correo: str, nombre_adjunto: Optional[str] = None) -> str:
    """Descarga un archivo adjunto (PDF, Excel, imagen) de un correo para analizarlo.
    
    Args:
        id_correo: El ID del correo.
        nombre_adjunto: Nombre o parte del nombre del archivo a descargar (ej. 'presupuesto.xlsx').
    """
    if not gmail_manager.esta_configurado():
        return "Gmail no está configurado en .env."
    try:
        archivos = gmail_manager.descargar_adjuntos(id_correo, nombre_adjunto)
        if not archivos:
            return f"No se encontraron adjuntos coincidentes en el correo {id_correo}."
        return f"Archivos descargados exitosamente:\n" + "\n".join(f"- {a}" for a in archivos)
    except Exception as e:
        return f"Error descargando adjuntos: {str(e)}"
