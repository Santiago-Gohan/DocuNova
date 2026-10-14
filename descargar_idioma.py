# -*- coding: utf-8 -*-
"""
Descarga el idioma espanol (spa.traineddata) para el OCR de Tesseract.
Ejecuta:  python descargar_idioma.py
"""
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(BASE, "tessdata")
URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/spa.traineddata"


def main():
    os.makedirs(DESTINO, exist_ok=True)
    salida = os.path.join(DESTINO, "spa.traineddata")
    if os.path.isfile(salida):
        print("Ya existe:", salida)
        return
    print("Descargando idioma espanol (spa.traineddata, ~13 MB)...")
    try:
        urllib.request.urlretrieve(URL, salida)
        print("Listo:", salida)
    except Exception as e:
        print("No se pudo descargar:", e)
        print("Descargalo manualmente desde:")
        print("  https://github.com/tesseract-ocr/tessdata_best/raw/main/spa.traineddata")
        print("y guardalo en:", DESTINO)


if __name__ == "__main__":
    main()
