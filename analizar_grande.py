# -*- coding: utf-8 -*-
"""
RADIOGRAFIA DE UN PDF GRANDE
Uso:
    python analizar_grande.py "C:\\ruta\\al\\archivo.pdf"

Muestra, pagina por pagina, que tipo de documento parece ser y propone
donde cortar para separar cada documento.
"""
import os
import sys
import csv
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import inteligencia as intel


def main():
    if len(sys.argv) < 2:
        print("Uso: python analizar_grande.py \"ruta\\al\\pdf.pdf\"")
        return
    ruta = sys.argv[1]
    if not os.path.isfile(ruta):
        print("No existe el archivo:", ruta)
        return

    print("Analizando:", os.path.basename(ruta))
    print("Esto puede tardar si el PDF es escaneado (se aplica OCR).\n")

    def progreso(i, total):
        print(f"\r  Leyendo pagina {i}/{total}...", end="", flush=True)

    paginas = intel.analizar_pdf_paginas(ruta, progreso=progreso)
    print("\n")

    print("=" * 78)
    print(f"{'Pag':>4} | {'Tipo detectado':<30} | {'Conf':<6} | Inicio")
    print("=" * 78)
    for p in paginas:
        tipo = p["tipo"] or "(sin identificar)"
        print(f"{p['pagina']:>4} | {tipo:<30} | {p['conf']:<6} | {p['inicio'][:34]}")

    grupos = intel.agrupar_paginas(paginas)
    print("\n" + "=" * 78)
    print("CORTES PROPUESTOS (cada bloque = 1 documento)")
    print("=" * 78)
    for i, g in enumerate(grupos, 1):
        rango = f"pag {g['paginas'][0]}" if len(g["paginas"]) == 1 else f"pag {g['paginas'][0]}-{g['paginas'][-1]}"
        print(f"  {i:>2}. [{rango:<10}] {g['tipo'] or 'SIN_IDENTIFICAR':<30} ({g['conf'] or '-'})")

    salida = os.path.splitext(ruta)[0] + "_radiografia.csv"
    with open(salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Pagina", "Tipo", "Confianza", "Inicio", "Grupo"])
        grupo_de = {}
        for gi, g in enumerate(grupos, 1):
            for n in g["paginas"]:
                grupo_de[n] = gi
        for p in paginas:
            w.writerow([p["pagina"], p["tipo"], p["conf"], p["inicio"], grupo_de.get(p["pagina"], "")])
    print(f"\nReporte guardado en: {salida}")


if __name__ == "__main__":
    main()
