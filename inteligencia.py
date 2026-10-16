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
import uuid
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            "local": _dir_descarga(), "workers": WORKERS_OCR}


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


def _render_pagina(page, dpi=200, indice=0):
    """Renderiza la pagina a PNG y devuelve la ruta del archivo temporal.

    PyMuPDF NO es seguro entre hilos, asi que el render se hace siempre en un
    solo hilo; el OCR (que es un subproceso) si se puede paralelizar.
    """
    os.makedirs(TMP, exist_ok=True)
    tmp = os.path.join(TMP, f"_pag_{os.getpid()}_{indice}_{uuid.uuid4().hex[:8]}.png")
    page.get_pixmap(dpi=dpi).save(tmp)
    return tmp


def _ocr_png(tmp):
    """OCR de un PNG ya renderizado, con reintento en modo automatico."""
    txt = _ocr_archivo(tmp)                     # modo bloque uniforme
    if len(txt.strip()) < 20:
        alt = _ocr_archivo(tmp, psm="3")        # modo automatico
        if len(alt.strip()) > len(txt.strip()):
            txt = alt
    return txt


def _ocr_tmp(tmp):
    """Aplica OCR a un PNG temporal y lo borra (seguro para usar en hilos)."""
    try:
        return _ocr_png(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _ocr_pagina(page, dpi=200):
    return _ocr_tmp(_render_pagina(page, dpi))


# Tesseract usa todos los nucleos en cada llamada; para paralelizar de verdad
# cada pagina se procesa en un hilo y se limita el lote al numero de nucleos.
# En entornos con poca memoria RAM (Render free) conviene bajarlo con la
# variable de entorno DOCUNOVA_OCR_WORKERS.
def _workers_ocr():
    v = os.environ.get("DOCUNOVA_OCR_WORKERS")
    if v and v.strip().isdigit():
        return max(1, int(v))
    return max(1, min(4, (os.cpu_count() or 1) - 1))


WORKERS_OCR = _workers_ocr()


def _ocr_paginas(pares, dpi=200, al_completar=None):
    """OCR de varias paginas: render secuencial + OCR en paralelo.

    pares: lista de (indice, page). Devuelve {indice: texto}. Las paginas se
    procesan en lotes pequenos para no llenar el disco con muchos PNG.
    `al_completar()` se llama una vez por pagina terminada (para el progreso).
    """
    resultados = {}
    if not pares:
        return resultados
    lote = max(WORKERS_OCR, 1)
    for inicio in range(0, len(pares), lote):
        grupo = pares[inicio:inicio + lote]
        temporales = {idx: _render_pagina(page, dpi, idx) for idx, page in grupo}
        if WORKERS_OCR <= 1 or len(grupo) == 1:
            for idx, _page in grupo:
                resultados[idx] = _ocr_tmp(temporales[idx])
                if al_completar:
                    al_completar()
        else:
            with ThreadPoolExecutor(max_workers=WORKERS_OCR) as ex:
                futuros = {ex.submit(_ocr_tmp, temporales[idx]): idx
                           for idx, _page in grupo}
                for fut in as_completed(futuros):
                    idx = futuros[fut]
                    resultados[idx] = fut.result()
                    if al_completar:
                        al_completar()
    return resultados


# ----------------------------------------------------------------------
# Refuerzo de OCR para paginas dificiles (fotos borrosas o con poco contraste)
# ----------------------------------------------------------------------
CONF_RANGO = {"": 0, "BAJA": 1, "MEDIA": 2, "ALTA": 3}
MAX_REFUERZO = 25


def _ocr_alternativo(tmp):
    """OCR de refuerzo: devuelve una lista de lecturas alternativas.

    Realza el contraste con Pillow (escala de grises) y prueba el modo
    automatico y una version binarizada. Cada variante se evalua por separado
    para no inventar coincidencias al mezclar textos.
    """
    variantes = []
    try:
        from PIL import Image, ImageOps
        im = Image.open(tmp).convert("L")
        realzada = ImageOps.autocontrast(im)
        g = tmp + ".g.png"
        realzada.save(g)
        variantes.append((g, "3"))
        b = tmp + ".b.png"
        realzada.point(lambda v: 255 if v > 160 else 0).save(b)
        variantes.append((b, "6"))
    except Exception:  # noqa: BLE001 - si Pillow falla, se sigue sin realce
        variantes = []

    lecturas = []
    for ruta_v, psm in variantes:
        try:
            t = _ocr_archivo(ruta_v, psm=psm)
            if t.strip():
                lecturas.append(t)
        finally:
            try:
                os.remove(ruta_v)
            except OSError:
                pass
    if not lecturas:
        t = _ocr_archivo(tmp, psm="3")
        if t.strip():
            lecturas.append(t)
    return lecturas


def _reforzar_ocr(ruta, paginas, edad, maximo=MAX_REFUERZO):
    """Segunda pasada de OCR solo para paginas dudosas.

    Las fotos borrosas que Tesseract no lee a la primera (paginas sin
    identificar o de confianza BAJA) se reprocesan a mayor resolucion con
    realce de contraste y se reclasifican con cada lectura por separado. Solo
    cuesta tiempo en esas paginas, asi que los escaneos limpios no pierden
    velocidad. Solo se acepta el resultado si queda MEDIA o ALTA, para no
    inventar un tipo equivocado en una foto ilegible.
    """
    dudosas = [i for i, p in enumerate(paginas)
               if (not p.get("num")) or p.get("conf") == "BAJA"]
    if not dudosas:
        return 0
    dudosas = dudosas[:maximo]
    try:
        doc = pymupdf.open(ruta)
    except Exception:  # noqa: BLE001
        return 0
    mejoras = 0
    try:
        for i in dudosas:
            tmp = _render_pagina(doc[i], dpi=300, indice=i)
            try:
                lecturas = _ocr_alternativo(tmp)
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            actual = CONF_RANGO.get(paginas[i].get("conf", ""), 0)
            mejor = None
            for t in lecturas:
                r = clasificar(t, edad)
                if not r:
                    continue
                clave = (CONF_RANGO.get(r[2], 0), len(r[3]))
                if mejor is None or clave > mejor[0]:
                    mejor = (clave, r, t)
            if mejor is None:
                continue
            clave, r, texto = mejor
            if r[2] == "BAJA":
                continue
            if paginas[i].get("num") and clave <= (actual, 0):
                continue
            paginas[i]["texto"] = texto
            paginas[i]["num"] = r[0]
            paginas[i]["tipo"] = f"{r[0]}_{r[1]}"
            paginas[i]["conf"] = r[2]
            primera = next((ln.strip() for ln in texto.splitlines()
                            if ln.strip()), "")
            paginas[i]["inicio"] = primera[:70]
            mejoras += 1
    finally:
        doc.close()
    return mejoras


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
    ("001", "ACTA DE COMPROMISO APRENDIZ", [
        ("acta de compromiso", 7), ("compromiso del aprendiz", 7),
        ("deberes del aprendiz", 7), ("compromisos como aprendiz", 7),
        ("acta de compromiso aprendiz", 7), ("compromiso aprendiz", 5),
        ("compromiso", 3), ("aprendiz", 2), ("sena", 2),
        ("clausulas", 2), ("acuerdan", 2), ("entre las partes", 2),
        ("obligaciones", 2),
    ]),
    ("002", "DOCUMENTO DE IDENTIDAD", [
        ("cedula de ciudadania", 7), ("tarjeta de identidad", 7),
        ("no. de ti", 5), ("no de ti", 5), ("numero de ti", 5),
        ("cedula de extranjeria", 7), ("permiso por proteccion temporal", 7),
        ("registraduria nacional", 4), ("documento de identidad", 4),
        ("cedula", 4), ("ppt", 3), ("nuip", 3),
        ("fecha de expedicion", 3), ("lugar de expedicion", 4),
        ("registrador nacional", 4), ("registrador", 3),
        ("republica de colombia", 2), ("fecha de nacimiento", 1),
        ("ciudadania", 3), ("ciudadana", 3),
    ]),
    ("003", "CERTIFICADO ACADEMICO", [
        ("certifica que", 6), ("curso y aprobo", 7), ("cursó y aprobó", 7),
        ("acta de grado", 6), ("certificado academico", 7),
        ("certificado de estudios", 6), ("institucion educativa", 5),
        ("bachiller", 5), ("titulo de", 4), ("diploma", 4),
        ("secretaria de educacion", 3), ("educacion media", 3),
        ("grado", 2), ("colegio", 2), ("jornada", 1),
    ]),
    ("004", "CERTIFICADO EPS", [
        ("entidad promotora de salud", 7), ("certificado de afiliacion", 7),
        ("certificado eps", 6), ("certificado de salud", 6),
        ("certificado medico", 5), ("eps", 4), ("sisben", 4),
        ("estado: activo", 4), ("estado activo", 3),
        ("regimen contributivo", 3), ("regimen subsidiado", 3),
        ("afiliacion", 3), ("cotizante", 3), ("afiliado", 3),
        ("promotora de salud", 3), ("fosyga", 2),
    ]),
    ("005", "TRATAMIENTO DE DATOS", [
        ("tratamiento de datos menor", 12), ("autorizacion de tratamiento", 8),
        ("tratamiento de datos", 8), ("consentimiento informado", 6),
        ("habeas data", 6), ("ley 1581", 6),
        ("finalidad del tratamiento", 5), ("datos personales", 5),
        ("autorizacion", 3), ("consentimiento", 3), ("autorizo", 3),
    ]),
    ("ICFES", "RESULTADOS ICFES", [
        ("icfes", 8), ("puntaje global", 7), ("saber 11", 7),
        ("prueba saber", 6), ("resultados de la aplicacion", 6),
        ("reporte de resultados", 5), ("resultados saber", 5),
    ]),
    ("006", "REGISTRO CIVIL", [
        ("registro civil de nacimiento", 8), ("registro civil", 8),
        ("indicativo serial", 5), ("oficina de registro", 5),
        ("datos del inscrito", 5), ("inscripcion de nacimiento", 5),
        ("nombre del padre", 4), ("nombre de la madre", 4),
        ("nacimiento", 3), ("notaria", 3),
    ]),
    ("007", "CEDULA TUTOR LEGAL", [
        ("tutor legal", 8), ("acudiente", 7), ("autorizacion del acudiente", 7),
        ("autorizacion del tutor", 7), ("representante legal", 6),
        ("padre de familia", 5), ("madre de familia", 5),
    ]),
]


def detectar_edad(texto):
    """Devuelve 'menor', 'mayor' o None segun el documento de identidad.

    Tarjeta de identidad / registro civil -> menor.
    Cedula de ciudadania / extranjeria / PPT -> mayor.
    """
    t = normalizar(texto or "")
    if not t:
        return None
    if any(p in t for p in ("tarjeta de identidad", "no. de ti", "no de ti",
                            "numero de ti", "registro civil")):
        return "menor"
    if any(p in t for p in ("cedula de ciudadania", "cedula de extranjeria",
                            "permiso por proteccion temporal")):
        return "mayor"
    return None


def numero_icfes(edad):
    """El ICFES es 008 para menores y 005 para mayores."""
    return "008" if edad == "menor" else "005"


def clasificar(texto, edad=None):
    """Devuelve (numero, nombre, confianza, coincidencias) o None.

    edad: 'menor' | 'mayor' | None -> se usa para ubicar el ICFES (008 o 005).
    """
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
            resultados.append([num, nombre, score, hits])
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
    num, nombre = mejor[0], mejor[1]
    if num == "ICFES":
        num = numero_icfes(edad)
    return num, nombre, conf, mejor[3]


def clasificar_desde_nombre(nombre, edad=None):
    """Clasifica un documento usando su NOMBRE de archivo como pista.

    Sirve cuando el PDF/imagen no tiene texto util (escaneo sin OCR) pero el
    archivo viene bien nombrado, p. ej. "CERTIFICADO_DE_SALUD_YEIMY.pdf".
    """
    base = os.path.splitext(os.path.basename(nombre or ""))[0]
    base = re.sub(r"[_\-\.]+", " ", base)
    return clasificar(base, edad)


def clasificar_archivo(ruta, edad=None):
    """Lee un archivo (PDF/imagen) y devuelve el texto y la clasificacion.

    Si el texto no alcanza para clasificar, se intenta con el nombre del
    archivo como segunda pista. Si no se pasa 'edad', se intenta deducir del
    propio texto (util para ubicar el ICFES en 005 o 008).
    """
    texto = texto_de_archivo(ruta)
    if edad is None:
        edad = detectar_edad(texto)
    res = clasificar(texto, edad)
    if not res:
        res = clasificar_desde_nombre(os.path.basename(ruta), edad)
    return texto, res


# ----------------------------------------------------------------------
# ANALISIS DE UN PDF GRANDE, PAGINA POR PAGINA
# ----------------------------------------------------------------------
def analizar_pdf_paginas(ruta, max_paginas=None, dpi=200, progreso=None, on_pagina=None):
    """Devuelve una lista con el tipo detectado en cada pagina del PDF.

    Primero se lee el texto de todas las paginas y se deduce la edad (menor o
    mayor) a partir del documento de identidad; eso decide si el ICFES va como
    008 (menor) o como 005 (mayor).
    """
    doc = pymupdf.open(ruta)
    total = len(doc)
    if max_paginas is not None:
        total = min(total, max_paginas)
    textos = [""] * total
    pendientes = []
    hechas = [0]
    candado = threading.Lock()

    def al_completar():
        with candado:
            hechas[0] += 1
            n = hechas[0]
        if progreso:
            progreso(n, total)

    try:
        for i in range(total):
            page = doc[i]
            t = page.get_text().strip()
            if len(t) < 20:
                pendientes.append((i, page))
            else:
                textos[i] = t
                al_completar()
        lecturas = _ocr_paginas(pendientes, dpi=dpi, al_completar=al_completar)
        for i, t in lecturas.items():
            textos[i] = t
    finally:
        doc.close()

    edad = detectar_edad("\n".join(textos))
    out = []
    for i, t in enumerate(textos):
        res = clasificar(t, edad)
        primera = next((ln.strip() for ln in t.splitlines() if ln.strip()), "")
        out.append({
            "pagina": i + 1,
            "texto": t,
            "num": res[0] if res else "",
            "tipo": f"{res[0]}_{res[1]}" if res else "",
            "conf": res[2] if res else "",
            "inicio": primera[:70],
        })

    # Fotos borrosas: reintenta el OCR en las paginas que quedaron dudosas.
    _reforzar_ocr(ruta, out, edad)

    for info in out:
        if on_pagina:
            on_pagina(info)
    marcar_tutor(out, edad)
    return out


def marcar_tutor(paginas, edad=None):
    """Marca como cedula del tutor (007) los documentos de identidad (002)
    adicionales. En un set de menor solo hay una identificacion propia; si
    aparece otra hoja de identidad, es del acudiente.

    Las paginas consecutivas del mismo documento cuentan como una sola.
    """
    if edad is None:
        edad = detectar_edad("\n".join(p.get("texto", "") for p in paginas))
    if edad == "mayor":
        return
    originales = [p.get("num") for p in paginas]
    identidades = 0
    for i, p in enumerate(paginas):
        if originales[i] != "002":
            continue
        if i == 0 or originales[i - 1] != "002":
            identidades += 1
        if identidades > 1:
            p["num"] = "007"
            p["tipo"] = "007_CEDULA TUTOR LEGAL"


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

    # Tutor legal: la cedula del acudiente que acompana los papeles de un menor.
    marcar_tutor(paginas)

    # Los grupos se construyen con el tipo de la primera pagina; si el tutor
    # reasigno numeros, hay que rehacerlos para que el nombre del archivo
    # coincida con el tipo corregido.
    for g in grupos:
        p0 = next((p for p in paginas if p["pagina"] == g["paginas"][0]), None)
        if p0 is not None:
            g["num"] = p0.get("num", "")
            g["tipo"] = p0.get("tipo", "") or "SIN_IDENTIFICAR"
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
    "icfes", "saber", "puntaje", "global", "prueba", "reporte", "aplicacion",
    "extranjeria", "temporal", "proteccion", "inscrito", "indicativo", "serial",
    "oficina", "madre", "padre", "ppt", "aprendiz", "deberes", "sena",
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
