"""Paso 3: texto literal con OCR. PaddleOCR (principal) y EasyOCR (alternativa)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from extraer_inputs import config
from extraer_inputs.logging_config import obtener_logger

log = obtener_logger(__name__)


@dataclass(frozen=True)
class LineaOCR:
    texto: str
    caja: tuple[float, float, float, float]  # x0, y0, x1, y1 en pixeles de la imagen para OCR
    confianza: float

    @property
    def centro_y(self) -> float:
        return (self.caja[1] + self.caja[3]) / 2


class MotorOCR:
    """Carga el motor una sola vez (los modelos tardan) y lo reutiliza en todo el lote."""

    def __init__(self, preferido: str = config.MOTOR_OCR) -> None:
        self.nombre = ""
        self._motor = None
        if preferido == "paddle":
            try:
                self._cargar_paddle()
                return
            except Exception as e:  # paddlepaddle sin rueda para este Python, DLL faltante, etc.
                log.warning("PaddleOCR no esta disponible (%s); se usa EasyOCR.", e)
        self._cargar_easyocr()

    def _cargar_paddle(self) -> None:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        # Las capturas ya vienen derechas (exif_transpose): sin clasificadores de orientacion.
        # enable_mkldnn=False: en CPU, Paddle 3.x con oneDNN falla al predecir
        # ("ConvertPirAttribute2RuntimeAttribute not support ...").
        self._motor = PaddleOCR(lang=config.IDIOMA_OCR, use_doc_orientation_classify=False,
                                use_doc_unwarping=False, use_textline_orientation=False,
                                enable_mkldnn=False)
        self.nombre = "PaddleOCR"
        log.info("Motor OCR: PaddleOCR (lang=%s).", config.IDIOMA_OCR)

    def _cargar_easyocr(self) -> None:
        import easyocr
        self._motor = easyocr.Reader([config.IDIOMA_OCR], gpu=False, verbose=False)
        self.nombre = "EasyOCR"
        log.info("Motor OCR: EasyOCR (lang=%s, CPU).", config.IDIOMA_OCR)

    def leer(self, imagen: Path) -> list[LineaOCR]:
        """Lineas de texto con su caja y confianza, en orden de lectura."""
        lineas = self._leer_paddle(imagen) if self.nombre == "PaddleOCR" else self._leer_easyocr(imagen)
        lineas.sort(key=lambda l: (round(l.centro_y / 12), l.caja[0]))
        return lineas

    def _leer_paddle(self, imagen: Path) -> list[LineaOCR]:
        lineas = []
        for resultado in self._motor.predict(str(imagen)):
            textos, scores = resultado["rec_texts"], resultado["rec_scores"]
            cajas = resultado["rec_boxes"]
            for texto, score, caja in zip(textos, scores, cajas):
                if str(texto).strip():
                    x0, y0, x1, y1 = (float(v) for v in caja)
                    lineas.append(LineaOCR(str(texto).strip(), (x0, y0, x1, y1), float(score)))
        return lineas

    def _leer_easyocr(self, imagen: Path) -> list[LineaOCR]:
        lineas = []
        for puntos, texto, confianza in self._motor.readtext(str(imagen)):
            xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
            if str(texto).strip():
                lineas.append(LineaOCR(str(texto).strip(), (min(xs), min(ys), max(xs), max(ys)), float(confianza)))
        return lineas
