# -*- coding: utf-8 -*-
"""
MOTOR DE LECTURA Y CLASIFICACION DE DOCUMENTOS
Lee PDF (capa de texto u OCR local) e identifica que tipo de documento es.
100% local: no envia datos a internet.
"""
import os
import re
import sys
import glob
import shutil
import tempfile
import subprocess
import unicodedata
import urllib.request
from collections import Counter

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

# ----------------------------------------------------------------------
# Rutas de Tesseract (OCR local, funciona en Windows y Linux)
# ----------------------------------------------------------------------
def _buscar_tesseract():
    ruta_env = os.environ.get("TESSERACT_CMD")
    if ruta_env and os.path.isfile(ruta_env):
        return ruta_env
    if os.name == "nt":
        for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                  r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")):
            if os.path.isfile(p):
                return p
    else:
        for p in ("/usr/bin/tesseract", "/usr/local/bin/tesseract"):
            if os.path.isfile(p):
                return p
    return shutil.which("tesseract") or "tesseract"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TESS_EXE = _buscar_tesseract()
TMP = os.path.join(tempfile.gettempdir(), "docunova_tmp")

URL_IDIOMA = "https://github.com/tesseract-ocr/tessdata_best/raw/main/spa.traineddata"

EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
EXT_PDF = {".pdf"}


# ----------------------------------------------------------------------
# Localizacion del directorio "tessdata" con el idioma espanol.
# Puede estar en varias rutas: la del proyecto, la del sistema (apt:
# tesseract-ocr-spa) o la del instalador de Windows.
# ----------------------------------------------------------------------
def _candidatos_tessdata():
    cands = []
    env = os.environ.get("TESSDATA_PREFIX")
    if env:
        cands.append(env)
    cands.append(os.path.join(BASE_DIR, "tessdata"))          # proyecto
    if os.name == "nt":
        cands += [r"C:\Program Files\Tesseract-OCR\tessdata",
                  r"C:\Program Files (x86)\Tesseract-OCR\tessdata"]
    else:
        cands += sorted(glob.glob("/usr/share/tesseract-ocr/*/tessdata"), reverse=True)
        cands += ["/usr/share/tesseract-ocr/tessdata", "/usr/share/tessdata",
                  "/usr/local/share/tessdata"]
    return [c for c in cands if c]


def _dir_tessdata():
    """Devuelve el primer directorio que tenga spa.traineddata, o None."""
    for d in _candidatos_tessdata():
        if os.path.isfile(os.path.join(d, "spa.traineddata")):
            return d
    return None


def _dir_descarga():
    """Carpeta local donde se descarga el idioma si falta en el sistema."""
    return os.path.join(BASE_DIR, "tessdata")


# Compatibilidad con codigo que lea intel.TESSDATA
TESSDATA = _dir_tessdata() or _dir_descarga()


def idioma_instalado():
    return _dir_tessdata() is not None


def asegurar_idioma():
    """Descarga spa.traineddata si falta en cualquier ubicacion conocida."""
    if idioma_instalado():
        return True
    try:
        destino_dir = _dir_descarga()
        os.makedirs(destino_dir, exist_ok=True)
        destino = os.path.join(destino_dir, "spa.traineddata")
        urllib.request.urlretrieve(URL_IDIOMA, destino)
        return os.path.isfile(destino)
    except Exception:
        return False


def _binario_ok():
    return os.path.isfile(TESS_EXE) or shutil.which(TESS_EXE) is not None


def _ocr_disponible():
    return _binario_ok() and idioma_instalado()


def ocr_estado():
    """Diagnostico del OCR (para /salud)."""
    d = _dir_tessdata()
    return {"binario": _binario_ok(), "spa": d is not None,
            "tessdata_dir": d, "exe": TESS_EXE,
            "local": _dir_descarga()}


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
        cmd = [TESS_EXE, ruta, "stdout", "-l", idioma]
        d = _dir_tessdata()
        if d:
            cmd += ["--tessdata-dir", d]
        cmd += ["--psm", psm]
        # 60 s por pagina: si Tesseract se colga, el trabajo sigue adelante
        # en lugar de bloquear el proceso completo durante 2 minutos.
        res = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60)
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


def separar_pdf(ruta, carpeta_salida, grupos, modo="upper", prefijo=None,
                progreso=None):
    """Crea un PDF por cada grupo. Devuelve la lista de archivos creados."""
    os.makedirs(carpeta_salida, exist_ok=True)
    doc = pymupdf.open(ruta)
    creados = []
    try:
        for i, g in enumerate(grupos, 1):
            if progreso:
                progreso(i, len(grupos))
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


# ----------------------------------------------------------------------
# DETECCION DE LA PERSONA (a quien pertenece cada documento)
# Es heuristica: intenta leer el numero de documento, el nombre y el correo.
# ----------------------------------------------------------------------
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Etiquetas de documentos tipo tabla (ej. certificado BDUA/ADRES): la
# etiqueta va en una linea y el valor en la siguiente.
RE_TIPO = re.compile(
    r"TIPO DE\s+IDENTIFICACI[OÓ]N\s*:?\s*([A-Za-z]{2,4})", re.I)
RE_DNI_ETQ = re.compile(
    r"N[ÚU]MERO DE\s+IDENTIFICACI[OÓ]N?\s*:?\s*([\d][\d.\s]{4,18}\d)", re.I)
RE_DNI_TOK = re.compile(
    r"\b(?:C\.?\s?C\.?|CEDULA(?:\s+DE\s+CIUDADAN[IÍ]A)?|T\.?\s?I\.?|"
    r"TARJETA DE IDENTIDAD|C\.?\s?E\.?|PASAPORTE|NIT)\b"
    r"[\s:.\-]*([\d][\d.\s]{4,18}\d)", re.I)

# Etiquetas que marcan el fin del valor de un nombre.
_FIN_ETQ = (
    r"(?:FECHA(?:\s+DE\s+NACIMIENTO)?|DEPARTAMENTO|MUNICIPIO|SEXO|"
    r"DIRECCI[OÓ]N|CORREO|E-?MAIL|TEL[EÉ]FONO|CELULAR|ESTADO|ENTIDAD|"
    r"R[EÉ]GIMEN|REGIMEN|TIPO DE|N[ÚU]MERO DE|NOMBRES?|APELLIDOS?|PERIODO|"
    r"DATOS|FECHA DE AFILIACI[OÓ]N|FECHA DE FINALIZACI[OÓ]N)"
)
RE_NOMBRES = re.compile(r"\bNOMBRES?\b\s*:?\s*(.*?)\s*(?=" + _FIN_ETQ + r"|$)", re.I)
RE_APELLIDOS = re.compile(r"\bAPELLIDOS?\b\s*:?\s*(.*?)\s*(?=" + _FIN_ETQ + r"|$)", re.I)

# Palabras que NO forman parte de un nombre (titulos, encabezados de
# entidad, lenguaje legal, etc.).
PALABRAS_PROHIBIDAS = {
    "acta", "compromiso", "compromisos", "documento", "documentos", "identidad",
    "certificado", "certificacion", "academico", "academica", "estudios", "grado",
    "eps", "tratamiento", "datos", "personales", "registro", "civil", "tutor",
    "legal", "representante", "acudiente", "cedula", "ciudadania", "tarjeta",
    "republica", "colombia", "registraduria", "nacional", "institucion", "educativa",
    "colegio", "secretaria", "educacion", "entidad", "promotora", "salud", "sisben",
    "autorizacion", "notaria", "numero", "fecha", "nacimiento", "nombres", "apellidos",
    "nombre", "firma", "codigo", "pagina", "senor", "senora", "adjunto", "anexo",
    "afiliado", "cotizante", "regimen", "subsidiado", "contributivo", "diploma",
    "bachiller", "jornada", "media", "acta", "clausulas", "partes", "habeas",
    # etiquetas de formulario y conectivos
    "nombre", "nombres", "apellido", "apellidos", "senor", "senora", "señor", "señora",
    "sr", "sra",
    "de", "la", "el", "los", "las", "del", "al", "y", "en", "con", "por", "para",
    "que", "se", "un", "una", "cc", "ti", "ce", "rc", "pp", "nit", "ci", "dv",
    # encabezados de entidad y lenguaje legal (certificado BDUA/ADRES, etc.)
    "administradora", "recursos", "sistema", "general", "seguridad", "social",
    "ministerio", "proteccion", "adres", "bdua", "afiliados", "unica", "unico",
    "resolucion", "resoluciones", "normativa", "anexo", "tecnico", "tecnicos",
    "lineamientos", "especificaciones", "operativas", "prestadores", "usuarios",
    "servicio", "servicios", "calidad", "informacion", "reportada", "fuente",
    "base", "bases", "afiliacion", "consulta", "resultados", "columnas",
    "tipo", "estado", "regimen", "departamento", "municipio", "nueva", "nuevo",
    "cabeza", "familia", "efectiva", "finalizacion", "periodo", "impresion",
    "estacion", "origen", "ventana", "imprimir", "cerrar", "responsable",
    "corresponde", "directamente", "cumplimiento", "marco", "definido", "nunca",
    "motivo", "denegar", "prestacion", "necesite", "retirarse", "trasladarse",
    "modificar", "actualizaciones", "dependen", "netamente", "solicitud",
    "escalada", "presenta", "vinculado", "genera", "aclara", "contenido",
    "reflejo", "reportado", "entidades", "adopta", "lineamiento",
}


def _limpiar_valor(v):
    v = (v or "").strip()
    v = re.sub(r"^[:\-\.\s]+", "", v)
    v = re.sub(r"[:\-\.\s]+$", "", v)
    v = re.sub(r"\s{2,}", " ", v)
    return v.strip()


# Token de tipo de documento que puede colarse al final del nombre.
_RE_TOKEN_ID = re.compile(
    r"(?:C\.?\s?C|T\.?\s?I|C\.?\s?E|P\.?\s?P|R\.?\s?C|N\.?\s?I\.?\s?T|"
    r"CEDULA|CIUDADANIA|IDENTIFICACION|PASAPORTE|EXTRA NJERIA|EXTRANJERIA)\.?",
    re.I)


def _limpiar_valor_nombre(v):
    v = _limpiar_valor(v)
    v = re.split(r"\d", v)[0]        # corta si empieza un numero (cedula, fecha, ...)
    toks = v.split()
    while toks and _RE_TOKEN_ID.fullmatch(toks[-1]):
        toks.pop()
    return _limpiar_valor(" ".join(toks))


def _nombre_etiquetado(plano):
    """Extrae NOMBRES + APELLIDOS de documentos con etiquetas."""
    partes = []
    for rx in (RE_NOMBRES, RE_APELLIDOS):
        m = rx.search(plano)
        if not m:
            continue
        v = _limpiar_valor_nombre(m.group(1))
        if v:
            partes.append(v)
    nombre = re.sub(r"\s{2,}", " ", " ".join(partes)).strip()
    if not nombre or re.search(r"\d", nombre):
        return None
    palabras = nombre.split()
    if 2 <= len(palabras) <= 6:
        return " ".join(palabras)
    return None


def _dni_desde_etiqueta(plano):
    for rx in (RE_DNI_ETQ, RE_DNI_TOK):
        m = rx.search(plano)
        if m:
            d = re.sub(r"\D", "", m.group(1))
            if 6 <= len(d) <= 12:
                return d
    return None


def _dni_generico(texto):
    """Numero de documento sin etiqueta: evita mezclar fechas o IPs."""
    m = re.search(r"\b\d{1,3}(?:\.\d{3}){1,4}\b", texto)
    if m:
        d = m.group(0).replace(".", "")
        if 6 <= len(d) <= 12:
            return d
    cands = re.findall(r"\b\d{6,11}\b", texto)
    if cands:
        return Counter(cands).most_common(1)[0][0]
    return None


def _detectar_nombre(texto):
    """Devuelve el nombre de la persona detectado en el texto.

    Ignora etiquetas (NOMBRE, APELLIDO, SENOR, C.C., ...) y conectivos
    (DE, LA, DEL, ...). Prefiere lineas 100% en mayusculas (como en las
    cedulas) y luego lineas Capitalizadas.
    """
    if not texto:
        return None
    fuertes = Counter()   # todas las palabras en MAYUSCULA
    debiles = Counter()   # palabras Capitalizadas
    for linea in texto.splitlines():
        linea = linea.strip()
        if not (4 <= len(linea) <= 90):
            continue
        tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", linea)
        limpios = []
        for p in tokens:
            if len(p) < 2 or p.lower() in PALABRAS_PROHIBIDAS:
                continue
            if p[0].isupper() or p.isupper():
                limpios.append(p)
        if not (2 <= len(limpios) <= 4):
            continue
        clave = " ".join(limpios)
        if all(p.isupper() for p in limpios):
            fuertes[clave] += 1
        else:
            debiles[clave] += 1
    if fuertes:
        return fuertes.most_common(1)[0][0]
    if debiles:
        return debiles.most_common(1)[0][0]
    return None


def _nombre_desde_archivo(nombre):
    """Intenta sacar el nombre de la persona desde el nombre del archivo."""
    base = os.path.splitext(os.path.basename(nombre or ""))[0]
    base = re.sub(r"[_\-\.\d]+", " ", base)
    palabras = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,}", base)
    sel = [p for p in palabras if p.lower() not in PALABRAS_PROHIBIDAS]
    if len(sel) >= 2:
        return " ".join(sel[:4])
    return None


def detectar_tipo_documento(texto):
    """Detecta el tipo de documento de identidad (CC, TI, CE, RC, PP, NIT)."""
    if not texto:
        return None
    # 1) etiqueta explicita: "TIPO DE IDENTIFICACION: CC"
    plano = re.sub(r"\s+", " ", texto)
    mt = RE_TIPO.search(plano)
    if mt:
        tok = mt.group(1).upper()
        if tok in ("CC", "TI", "CE", "RC", "PP", "NIT"):
            return tok
    # 2) palabras clave (cedula de ciudadania, tarjeta de identidad, ...)
    t = normalizar(texto)
    claves = [
        ("CC", [("cedula de ciudadania", 6), ("cedula ciudadania", 6)]),
        ("TI", [("tarjeta de identidad", 6)]),
        ("CE", [("cedula de extranjeria", 6), ("cedula de extranjero", 6)]),
        ("RC", [("registro civil", 5)]),
        ("PP", [("pasaporte", 5)]),
        ("NIT", [(" nit", 3)]),
    ]
    puntaje = {}
    for tipo, alternativas in claves:
        s = sum(peso for palabra, peso in alternativas if palabra in t)
        if s:
            puntaje[tipo] = s
    if puntaje:
        return max(puntaje, key=puntaje.get)
    # 3) token suelto (con o sin puntos): CC, C.C., TI, T.I., CE, C.E., ...
    patrones = [
        ("CC", r"C\.?\s?C\.?"),
        ("TI", r"T\.?\s?I\.?"),
        ("CE", r"C\.?\s?E\.?"),
        ("PP", r"P\.?\s?P\.?"),
        ("RC", r"R\.?\s?C\.?"),
        ("NIT", r"N\.?\s?I\.?\s?T\.?"),
    ]
    for tok, pat in patrones:
        if re.search(r"(?<![A-Za-z])" + pat + r"(?![A-Za-z])", texto):
            return tok
    return None


def detectar_persona(texto, nombre_archivo=""):
    """Devuelve {'nombre','dni','tipo','email'} o None si no reconoce a la persona."""
    info = {"nombre": None, "dni": None, "tipo": None, "email": None}
    texto = texto or ""
    plano = re.sub(r"\s+", " ", texto)

    m = RE_EMAIL.search(texto)
    if m:
        info["email"] = m.group(0).lower()

    info["tipo"] = detectar_tipo_documento(texto)
    info["dni"] = _dni_desde_etiqueta(plano) or _dni_generico(texto)
    info["nombre"] = (_nombre_etiquetado(plano)
                      or _detectar_nombre(texto)
                      or _nombre_desde_archivo(nombre_archivo))

    if not (info["nombre"] or info["dni"] or info["email"]):
        return None
    return info


def clave_persona(info):
    """Clave de agrupacion: prioriza el numero de documento."""
    if not info:
        return "sin_identificar"
    if info.get("dni"):
        return "dni_" + info["dni"]
    if info.get("nombre"):
        return "nom_" + normalizar(info["nombre"]).replace(" ", "_")
    if info.get("email"):
        return "mail_" + info["email"]
    return "sin_identificar"
