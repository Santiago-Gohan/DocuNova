# -*- coding: utf-8 -*-
"""
MOTOR DE LECTURA Y CLASIFICACION DE DOCUMENTOS
Lee PDF (capa de texto u OCR local) e identifica que tipo de documento es.
100% local: no envia datos a internet.
"""
import os
import re
import sys
import subprocess
import unicodedata

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

# ----------------------------------------------------------------------
# Rutas de Tesseract (OCR local)
# ----------------------------------------------------------------------
TESS_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tessdata")
TMP = os.path.join(os.environ.get("TEMP", "."), "clasificador_tmp")

EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
EXT_PDF = {".pdf"}


def _ocr_disponible():
    return os.path.isfile(TESS_EXE) and os.path.isfile(os.path.join(TESSDATA, "spa.traineddata"))


# ----------------------------------------------------------------------
# Normalizacion de texto
# ----------------------------------------------------------------------
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9ñ ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


# ----------------------------------------------------------------------
# Formato de nombres (igual criterio que el organizador)
# ----------------------------------------------------------------------
SIGLAS = {"CC", "TI", "CE", "PP", "RC", "NIT", "EPS", "SISBEN", "PDF", "ID"}


def _formatear(texto, modo):
    texto = texto.strip()
    if modo == "upper":
        return texto.upper()
    if modo == "lower":
        return texto.lower()
    salida = []
    for p in re.split(r"([ _])", texto):
        if p in (" ", "_") or p == "":
            salida.append(p)
        elif p.upper() in SIGLAS:
            salida.append(p.upper())
        else:
            salida.append(p.capitalize())
    return "".join(salida)


# ----------------------------------------------------------------------
# OCR
# ----------------------------------------------------------------------
def _ocr_archivo(ruta, idioma="spa", psm="6"):
    if not _ocr_disponible():
        return ""
    os.makedirs(TMP, exist_ok=True)
    try:
        res = subprocess.run(
            [TESS_EXE, ruta, "stdout", "-l", idioma,
             "--tessdata-dir", TESSDATA, "--psm", psm],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        return res.stdout or ""
    except Exception:
        return ""


def _ocr_pagina(page, dpi=200):
    os.makedirs(TMP, exist_ok=True)
    tmp = os.path.join(TMP, f"_pag_{os.getpid()}_{id(page) % 100000}.png")
    pix = page.get_pixmap(dpi=dpi)
    pix.save(tmp)
    txt = _ocr_archivo(tmp)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return txt


# ----------------------------------------------------------------------
# Lectura de archivos
# ----------------------------------------------------------------------
def texto_de_pdf(ruta, max_paginas=2, dpi=200):
    """Devuelve el texto del PDF. Usa la capa de texto; si no hay, aplica OCR."""
    partes = []
    doc = pymupdf.open(ruta)
    try:
        for i, page in enumerate(doc):
            if i >= max_paginas:
                break
            t = page.get_text().strip()
            if len(t) < 20:
                t = _ocr_pagina(page, dpi)
            partes.append(t)
    finally:
        doc.close()
    return "\n".join(partes).strip()


def texto_de_archivo(ruta, max_paginas=2, dpi=200):
    ext = os.path.splitext(ruta)[1].lower()
    if ext in EXT_PDF:
        return texto_de_pdf(ruta, max_paginas, dpi)
    if ext in EXT_IMAGEN:
        return _ocr_archivo(ruta)
    return ""


# ----------------------------------------------------------------------
# REGLAS DE CLASIFICACION
# (numero, nombre, [(palabra clave, peso), ...])
# ----------------------------------------------------------------------
REGLAS = [
    ("001", "ACTA DE COMPROMISO", [
        ("acta de compromiso", 6), ("acta de compromisos", 6),
        ("compromiso", 3), ("clausulas", 2), ("acuerdan", 2),
        ("entre las partes", 2), ("obligaciones", 2),
    ]),
    ("002", "DOCUMENTO DE IDENTIDAD", [
        ("cedula de ciudadania", 7), ("cedula", 4), ("tarjeta de identidad", 6),
        ("registraduria nacional", 4), ("documento de identidad", 4),
        ("nuip", 3), ("numero de identificacion", 3), ("republica de colombia", 2),
        ("fecha de nacimiento", 1),
    ]),
    ("003", "CERTIFICADO ACADEMICO", [
        ("certificado academico", 7), ("acta de grado", 6), ("certificado de estudios", 6),
        ("institucion educativa", 4), ("diploma", 4), ("bachiller", 3),
        ("secretaria de educacion", 3), ("grado", 2), ("colegio", 2),
        ("certifica que", 3), ("educacion media", 3), ("jornada", 1),
    ]),
    ("004", "CERTIFICADO EPS", [
        ("entidad promotora de salud", 7), ("certificado eps", 6), ("eps", 4),
        ("afiliacion", 4), ("sisben", 4), ("regimen subsidiado", 3),
        ("regimen contributivo", 3), ("cotizante", 3), ("afiliado", 3),
        ("promotora de salud", 3), ("fosyga", 2),
    ]),
    ("005", "TRATAMIENTO DE DATOS", [
        ("tratamiento de datos", 7), ("datos personales", 4), ("habeas data", 6),
        ("autorizacion", 3), ("ley 1581", 5), ("consentimiento", 3),
        ("autorizo", 3), ("finalidad del tratamiento", 5),
    ]),
    ("006", "REGISTRO CIVIL", [
        ("registro civil", 8), ("registro civil de nacimiento", 8),
        ("notaria", 3), ("indicativo serial", 4), ("nacimiento", 3),
        ("inscripcion de nacimiento", 5),
    ]),
    ("007", "DOCUMENTO TUTOR LEGAL", [
        ("tutor legal", 7), ("representante legal", 5), ("acudiente", 6),
        ("autorizacion del acudiente", 6), ("padre de familia", 3),
        ("autorizacion del tutor", 6),
    ]),
]


def clasificar(texto):
    """Devuelve (numero, nombre, confianza, coincidencias) o None."""
    t = normalizar(texto)
    if len(t) < 8:
        return None
    resultados = []
    for num, nombre, claves in REGLAS:
        score = 0
        hits = []
        for palabra, peso in claves:
            if palabra in t:
                score += peso
                hits.append(palabra)
        if score > 0:
            resultados.append((num, nombre, score, hits))
    if not resultados:
        return None
    resultados.sort(key=lambda r: r[2], reverse=True)
    mejor = resultados[0]
    segundo = resultados[1][2] if len(resultados) > 1 else 0
    score = mejor[2]
    if score >= 6 and score >= segundo * 1.5:
        conf = "ALTA"
    elif score >= 4 and score > segundo:
        conf = "MEDIA"
    else:
        conf = "BAJA"
    return mejor[0], mejor[1], conf, mejor[3]


def clasificar_archivo(ruta):
    """Lee un archivo (PDF/imagen) y devuelve el texto y la clasificacion."""
    texto = texto_de_archivo(ruta)
    return texto, clasificar(texto)


# ----------------------------------------------------------------------
# ANALISIS DE UN PDF GRANDE, PAGINA POR PAGINA
# ----------------------------------------------------------------------
def analizar_pdf_paginas(ruta, max_paginas=None, dpi=200, progreso=None, on_pagina=None):
    """Devuelve una lista con el tipo detectado en cada pagina del PDF."""
    doc = pymupdf.open(ruta)
    total = len(doc)
    out = []
    try:
        for i, page in enumerate(doc):
            if max_paginas is not None and i >= max_paginas:
                break
            if progreso:
                progreso(i + 1, total)
            t = page.get_text().strip()
            if len(t) < 20:
                t = _ocr_pagina(page, dpi)
            res = clasificar(t)
            primera = next((ln.strip() for ln in t.splitlines() if ln.strip()), "")
            info = {
                "pagina": i + 1,
                "texto": t,
                "num": res[0] if res else "",
                "tipo": f"{res[0]}_{res[1]}" if res else "",
                "conf": res[2] if res else "",
                "inicio": primera[:70],
            }
            out.append(info)
            if on_pagina:
                on_pagina(info)
    finally:
        doc.close()
    return out


def agrupar_paginas(paginas):
    """Agrupa paginas consecutivas del mismo tipo. Cada grupo = un documento."""
    grupos = []
    actual = None
    for p in paginas:
        tipo = p["tipo"] or "SIN_IDENTIFICAR"
        if actual is None or tipo != actual["tipo"]:
            if actual:
                grupos.append(actual)
            actual = {"paginas": [p["pagina"]], "tipo": tipo, "num": p["num"],
                      "conf": p["conf"], "inicio": p["inicio"]}
        else:
            actual["paginas"].append(p["pagina"])
    if actual:
        grupos.append(actual)
    return grupos


def separar_pdf(ruta, carpeta_salida, grupos, modo="upper", prefijo=None):
    """Crea un PDF por cada grupo. Devuelve la lista de archivos creados."""
    os.makedirs(carpeta_salida, exist_ok=True)
    doc = pymupdf.open(ruta)
    creados = []
    try:
        for g in grupos:
            nuevo = pymupdf.open()
            for n in g["paginas"]:
                nuevo.insert_pdf(doc, from_page=n - 1, to_page=n - 1)
            if "_" in (g["tipo"] or ""):
                num, _, nom = g["tipo"].partition("_")
                base = f"{num}_{nom.replace(' ', '_')}"
            else:
                base = f"sin_identificar_pag{g['paginas'][0]:03d}"
            nombre = _formatear(base, modo) + ".pdf"
            if prefijo:
                nombre = prefijo + "_" + nombre
            destino = os.path.join(carpeta_salida, nombre)
            raiz, ext = os.path.splitext(destino)
            k = 2
            while os.path.exists(destino):
                destino = f"{raiz}_{k}{ext}"
                k += 1
            nuevo.save(destino)
            nuevo.close()
            creados.append(destino)
    finally:
        doc.close()
    return creados
