"""Genera las 3 imagenes de prueba y su JSON esperado (ejecutar una vez):

    .venv\\Scripts\\python.exe tests\\fixtures\\crear_fixtures.py

- proveedor_nitido.png      formulario limpio, 1600 px de ancho
- proveedor_comprimido.jpg  reducido a 760 px y JPG calidad 35 (como llega por chat)
- proveedor_girado.jpg      pixeles girados + EXIF Orientation=6 (como un JPG de celular)
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARPETA = Path(__file__).resolve().parent
FUENTE = r"C:\Windows\Fonts\arial.ttf"
FUENTE_NEGRITA = r"C:\Windows\Fonts\arialbd.ttf"

CAMPOS = [
    # (etiqueta, valor, tipo)  en orden visual
    ("PROVEEDOR", "PRV-004512", "texto"),
    ("NOMBRE", "MATERIALES Y ACEROS DEL GOLFO SA DE CV", "texto"),
    ("DIRECCION", "AV. HIDALGO 1520 COL. AGUILA, TAMPICO, TAMPS.", "texto"),
    ("CODIGO POSTAL", "89230", "numero"),
    ("RFC", "MAG010203K64", "texto"),
    ("TELEFONO", "833 214 5566", "texto"),
    ("CORREO", "", "vacio"),
    ("TIPO PERSONA", "MORAL", "select"),
]
CRITICOS = ["PROVEEDOR", "NOMBRE", "DIRECCION", "CODIGO POSTAL", "RFC"]


def dibujar() -> Image.Image:
    ancho, alto = 1600, 1180
    img = Image.new("RGBA", (ancho, alto), (255, 255, 255, 255))  # RGBA: el preprocesado debe quitar el alfa
    d = ImageDraw.Draw(img)
    titulo = ImageFont.truetype(FUENTE_NEGRITA, 40)
    etiqueta = ImageFont.truetype(FUENTE_NEGRITA, 24)
    valor = ImageFont.truetype(FUENTE, 30)
    d.rectangle([0, 0, ancho, 90], fill=(37, 99, 235))
    d.text((40, 22), "ALTA DE PROVEEDOR", font=titulo, fill="white")
    y = 130
    for nombre, texto, tipo in CAMPOS:
        d.text((60, y), nombre, font=etiqueta, fill=(55, 65, 81))
        caja = [60, y + 34, ancho - 60, y + 94]
        d.rounded_rectangle(caja, radius=6, outline=(156, 163, 175), width=2, fill=(249, 250, 251))
        d.text((78, y + 47), texto, font=valor, fill=(17, 24, 39))
        if tipo == "select":
            d.polygon([(ancho - 100, y + 56), (ancho - 80, y + 56), (ancho - 90, y + 70)], fill=(75, 85, 99))
        y += 120
    # checkbox marcado
    d.rectangle([60, y + 6, 92, y + 38], outline=(55, 65, 81), width=3, fill=(37, 99, 235))
    d.line([(66, y + 22), (75, y + 31), (88, y + 12)], fill="white", width=4)
    d.text((108, y + 8), "ACTIVO", font=etiqueta, fill=(55, 65, 81))
    # botones que el modelo NO debe devolver como campos
    d.rounded_rectangle([ancho - 420, alto - 90, ancho - 250, alto - 40], radius=8, fill=(22, 163, 74))
    d.text((ancho - 385, alto - 80), "Guardar", font=valor, fill="white")
    d.rounded_rectangle([ancho - 230, alto - 90, ancho - 60, alto - 40], radius=8, fill=(220, 38, 38))
    d.text((ancho - 200, alto - 80), "Cancelar", font=valor, fill="white")
    return img


def main() -> None:
    img = dibujar()
    img.save(CARPETA / "proveedor_nitido.png")

    rgb = img.convert("RGB")
    chica = rgb.resize((760, int(rgb.height * 760 / rgb.width)), Image.Resampling.BILINEAR)
    chica.save(CARPETA / "proveedor_comprimido.jpg", quality=35)

    # Pixeles girados 90 grados (antihorario) + Orientation=6: el visor (y exif_transpose) la endereza
    girada = rgb.resize((1200, int(rgb.height * 1200 / rgb.width))).rotate(90, expand=True)
    exif = Image.Exif()
    exif[0x0112] = 6
    girada.save(CARPETA / "proveedor_girado.jpg", quality=85, exif=exif)

    esperado = {"criticos": {n: v for n, v, _ in CAMPOS if n in CRITICOS},
                "campos": [{"etiqueta": n, "valor": v, "tipo": t} for n, v, t in CAMPOS]
                + [{"etiqueta": "ACTIVO", "valor": "true", "tipo": "checkbox"}]}
    for nombre in ("proveedor_nitido.png", "proveedor_comprimido.jpg", "proveedor_girado.jpg"):
        (CARPETA / f"{Path(nombre).stem}.esperado.json").write_text(
            json.dumps(esperado, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
