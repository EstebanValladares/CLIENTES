"""
Page Object para el inicio de sesión en la plataforma Aryve.
"""
import time
from automation.browser import BasePage
from config.selectors import LoginSelectors
from config.settings import PAUSA_ESTABILIZACION, TIMEOUT_LOGIN, URL_BASE_ARYVE


class LoginPage(BasePage):
    """Encapsula el flujo de autenticación en el portal Aryve."""

    def iniciar_sesion(
        self,
        usuario: str,
        password: str,
        url_portal: str = URL_BASE_ARYVE,
    ) -> None:
        self.logger.info("Iniciando sesión en Aryve...")
        self.driver.get(url_portal)

        user_input = self.esperar_clicable(LoginSelectors.INPUT_USERNAME, timeout=TIMEOUT_LOGIN)
        user_input.clear()
        user_input.send_keys(usuario)

        pass_input = self.esperar_presente(LoginSelectors.INPUT_PASSWORD, timeout=TIMEOUT_LOGIN)
        pass_input.clear()
        pass_input.send_keys(password)

        btn_submit = self.esperar_clicable(LoginSelectors.BTN_SUBMIT, timeout=TIMEOUT_LOGIN)
        btn_submit.click()

        # Esperar reactivamente a que desaparezca el formulario de login o cargue el body autenticado
        self.esperar_presente(LoginSelectors.BODY, timeout=TIMEOUT_LOGIN)
        self.esperar_fin_carga(timeout=TIMEOUT_LOGIN, pausa_extra=1.2)
        self.driver.refresh()
        self.esperar_presente(LoginSelectors.BODY, timeout=TIMEOUT_LOGIN)
        self.esperar_fin_carga(timeout=TIMEOUT_LOGIN, pausa_extra=PAUSA_ESTABILIZACION)
        self.logger.info("¡Logeo exitoso!")

