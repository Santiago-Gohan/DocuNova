# -*- coding: utf-8 -*-
"""
DocuNova - Quitar el fondo de las imagenes del tour.

Toma imagenes (JPG/PNG) con fondo claro/uniforme y genera PNG con fondo
transparente, usando relleno (flood fill) desde los bordes con tolerancia.

Uso:
    python quitar_fondo.py <carpeta_origen> <carpeta_destino> [tolerancia]

Ejemplo:
    python quitar_fondo.py "C:\\...\\imagenes de guiador" "webapp\\static\\tour" 38

Notas:
- Funciona bien cuando el fondo es (casi) de un solo color y el personaje
  NO toca los bordes de la imagen.
- Si el fondo es un escenario complejo, el resultado sera imperfecto: en ese
  caso conviene regenerar la imagen con fondo transparente.
"""
import os
import sys

import cv2
import numpy as np

# Nombres "bonitos" para los archivos (ajusta a tu gusto)
MAPA = {
    "1. goku": "1_goku",
    "2. vegueta": "2_vegeta",
    "3. vulma": "3_bulma",
    "4. krillin": "4_krillin",
    "5. gohan": "5_gohan",
    "6.": "6_personaje",
}

# Tolerancias especiales: algunas imagenes (con contenido pegado a los bordes)
# necesitan un valor mas alto para que el fondo se quede limpio.
TOLERANCIA_ESPECIAL = {
    "1. goku": 120,
}


def limpiar_nombre(base):
    """Devuelve un nombre seguro para web a partir del nombre del archivo."""
    clave = base.lower().replace(".jpg", "").replace(".jpeg", "").replace(".png", "")
    if clave in MAPA:
        return MAPA[clave]
    seguro = "".join(c if c.isalnum() else "_" for c in clave).strip("_")
    return seguro or "personaje"


def quitar_fondo(ruta, tolerancia=38, desvanecer=2):
    """Devuelve una imagen RGBA con el fondo (conectado a los bordes) transparente."""
    img = cv2.imread(ruta, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]

    # Mascara donde flood fill marcara el fondo. Es (h+2, w+2) por exigencia de OpenCV.
    relleno = np.zeros((h + 2, w + 2), np.uint8)
    tol = (tolerancia, tolerancia, tolerancia)
    flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE

    semillas = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for sx, sy in semillas:
        if relleno[sy + 1, sx + 1] == 0:
            cv2.floodFill(img, relleno, (sx, sy), 0, tol, tol, flags)

    fondo = relleno[1:-1, 1:-1] > 0  # True = fondo

    # Alpha: 0 en el fondo, 255 en el personaje
    alpha = np.where(fondo, 0, 255).astype(np.uint8)

    # Suaviza el borde para que no quede "cortado" (antialias)
    if desvanecer > 0:
        alpha = cv2.GaussianBlur(alpha, (0, 0), desvanecer)

    b, g, r = cv2.split(img)
    rgba = cv2.merge([b, g, r, alpha])
    return rgba, float(fondo.mean()) * 100.0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    origen = sys.argv[1]
    destino = sys.argv[2]
    tol = int(sys.argv[3]) if len(sys.argv) > 3 else 38
    os.makedirs(destino, exist_ok=True)

    for nombre in sorted(os.listdir(origen)):
        if not nombre.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        ruta = os.path.join(origen, nombre)
        clave = nombre.lower().replace(".jpg", "").replace(".jpeg", "").replace(".png", "")
        tol_usar = TOLERANCIA_ESPECIAL.get(clave, tol)
        res = quitar_fondo(ruta, tol_usar)
        if res is None:
            print("  ! no se pudo leer:", nombre)
            continue
        rgba, pct = res
        salida = limpiar_nombre(nombre) + ".png"
        cv2.imwrite(os.path.join(destino, salida), rgba)
        print("  {0:20s} -> {1:16s} fondo quitado: {2:5.1f}%  (tol {3})".format(
            nombre, salida, pct, tol_usar))
    print("Listo. Revisa las imagenes: si el fondo no quedo limpio, sube/baja la tolerancia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
