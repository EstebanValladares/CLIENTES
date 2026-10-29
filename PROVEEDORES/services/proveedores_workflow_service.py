"""
Servicio de aplicación que orquesta el flujo completo de creación y registro
de proveedores en Aryve desde el Dashboard v2.
Integra telemetría con NUCLEO y streaming de logs en tiempo real.
"""
import time
import traceback
from typing import Any, Callable, Iterable, Mapping, Optional, Tuple, Union

from selenium.webdriver.remote.webdriver import WebDriver

from automation.browser import crear_driver
from automation.logger import ProveedorLogger
from automation.pages.login_page import LoginPage
from automation.pages.proveedor_page import ProveedorPage
from automation.telemetry import finalizar_telemetria, registrar_navegador, rep
from config.settings import (
    PAUSA_PANEL,
    RUTA_DATOS_CSV,
    RUTA_LOG,
    URL_BASE_ARYVE,
    obtener_credenciales,
)
from domain.models import ProveedorData
from repositories.proveedores_repo import leer_cola_csv, registrar_proveedor_json


class ProveedoresWorkflowService:
    """
    Orquestador del dominio de alta de proveedores en Aryve para Dashboard v2
    (`ProveedoresService` / `BotRunnerService`).
    """

    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        ruta_log: str = RUTA_LOG,
    ):
        self.logger = ProveedorLogger(ruta_log=ruta_log, callback_log=log_callback)

    def procesar_un_proveedor(
        self,
        driver: WebDriver,
        datos_proveedor: Union[ProveedorData, Mapping[str, Any]],
    ) -> Tuple[bool, str]:
        """
        Llena y guarda un proveedor completo en Aryve usando el `driver` ya autenticado.
        Persiste el ID generado y la clave en `registro_proveedores.json`.
        """
        prov = (
            datos_proveedor
            if isinstance(datos_proveedor, ProveedorData)
            else ProveedorData.from_dict(datos_proveedor)
        )
        proveedor_page = ProveedorPage(driver, self.logger)

        id_generado, _url_generada = proveedor_page.llenar_y_guardar_proveedor(prov)
        id_final = id_generado if id_generado else "Pendiente"

        self.logger.info(f"[ID] ID obtenido para '{prov.clave}': {id_final}")
        registrar_proveedor_json(prov.clave, id_final)

        ok_id = bool(id_generado and id_generado != "Pendiente")
        rep().verificar(
            f"Alta proveedor {prov.clave}",
            "ID numérico en URL",
            id_final,
            ok=ok_id,
            critica=False,
        )

        self.logger.info(
            f"[OK] Proveedor '{prov.nombre}' ({prov.clave}) guardado con éxito. ID: {id_final}"
        )
        return True, id_final

    def procesar_cola(
        self,
        lista_proveedores: Iterable[Union[ProveedorData, Mapping[str, Any]]],
    ) -> Tuple[bool, str]:
        """
        Procesa secuencialmente una lista/cola de proveedores en una sola sesión de navegador.
        """
        self.logger.iniciar_sesion_log()
        cola = [
            p if isinstance(p, ProveedorData) else ProveedorData.from_dict(p)
            for p in (lista_proveedores or [])
        ]

        if not cola:
            self.logger.aviso("No hay proveedores en la lista para procesar.")
            return False, "Cola vacía"

        try:
            usuario, password = obtener_credenciales()
        except Exception as err_cred:
            msg = f"Credenciales Aryve no disponibles: {err_cred}"
            self.logger.error(msg)
            return False, msg

        driver = crear_driver()
        registrar_navegador(driver, "PROVEEDORES")

        try:
            login_page = LoginPage(driver, self.logger)
            login_page.iniciar_sesion(usuario, password, url_portal=URL_BASE_ARYVE)

            total = len(cola)
            procesados_ok = 0

            for idx, prov in enumerate(cola, 1):
                nom = prov.nombre or f"Proveedor {idx}"
                self.logger.info("\n=======================================================")
                self.logger.info(
                    f" PROCESANDO [{idx}/{total}]: {nom} ({prov.tipo_persona})"
                )
                self.logger.info("=======================================================")
                ok_prov, _id_final = self.procesar_un_proveedor(driver, prov)
                if ok_prov:
                    procesados_ok += 1
                if idx < total:
                    time.sleep(PAUSA_PANEL)

            rep().verificar(
                "Proveedores procesados",
                total,
                procesados_ok,
                ok=(procesados_ok == total),
                critica=True,
            )
            self.logger.info(
                "\n[EXITO] ¡Todos los proveedores de la lista fueron llenados con éxito!"
            )
            return True, "Proceso completado exitosamente"

        except Exception as err:
            msg_err = f"[ERROR EN EJECUCIÓN]: {err}"
            self.logger.info(f"\n{msg_err}")
            traceback.print_exc()
            try:
                rep().registrar_excepcion()
                rep().capturar(motivo="Excepción durante procesamiento de cola PROVEEDORES")
            except Exception:
                pass
            return False, str(err)

        finally:
            try:
                finalizar_telemetria()
            except Exception:
                pass
            time.sleep(PAUSA_PANEL)
            try:
                driver.quit()
            except Exception:
                pass

    def ejecutar_cola_desde_csv(self, ruta_csv: str = RUTA_DATOS_CSV) -> Tuple[bool, str]:
        """
        Lee todos los proveedores pendientes en `datos.csv` y los procesa en lote.
        """
        cola = leer_cola_csv(ruta_csv)
        if not cola:
            self.logger.aviso(
                f"El archivo '{ruta_csv}' no contiene proveedores pendientes para procesar."
            )
            return False, "Sin registros en datos.csv"
        return self.procesar_cola(cola)
