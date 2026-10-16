# -*- coding: utf-8 -*-
"""
DocuNova - Nomenclatura y formato de nombres.
Logica pura (sin interfaz grafica): la usan tanto la app de escritorio
como la version web.
"""
import re

# (numero, nombre del documento, cuando)
# cuando: "todos" | "menor" | "mayor"
# Ojo: hay dos "005" a proposito. Para un MENOR, 005 es el tratamiento de
# datos y el ICFES es 008. Para un MAYOR, el ICFES ocupa el 005.
DOCS = [
    ("001", "ACTA DE COMPROMISO APRENDIZ", "todos"),
    ("002", "DOCUMENTO DE IDENTIDAD", "todos"),
    ("003", "CERTIFICADO ACADEMICO", "todos"),
    ("004", "CERTIFICADO EPS", "todos"),
    ("005", "TRATAMIENTO DE DATOS", "menor"),
    ("006", "REGISTRO CIVIL", "menor"),
    ("007", "CEDULA TUTOR LEGAL", "menor"),
    ("008", "RESULTADOS ICFES", "menor"),
    ("005", "RESULTADOS ICFES", "mayor"),
]


def documentos_de(edad):
    """Documentos que le corresponden a un aprendiz segun su edad.

    edad: "menor" | "mayor" | None. Si no se conoce la edad, devuelve solo
    los documentos comunes (001 a 004).
    """
    if edad == "menor":
        return [(n, nom) for n, nom, c in DOCS if c in ("todos", "menor")]
    if edad == "mayor":
        return [(n, nom) for n, nom, c in DOCS if c in ("todos", "mayor")]
    return [(n, nom) for n, nom, c in DOCS if c == "todos"]

# Tipos de documento (se guardan en MAYUSCULA siempre)
TIPOS = ["CC", "TI", "CE", "PP", "RC", "NIT"]

# Siglas que se mantienen en mayuscula al usar "Tipo Titulo"
SIGLAS = {"CC", "TI", "CE", "PP", "RC", "NIT", "EPS", "SISBEN", "PDF", "ID", "ICFES", "PPT"}

SEP = "_"


def formatear(texto, modo):
    """modo: 'upper' | 'lower' | 'title'. Respeta siglas en 'title'."""
    texto = texto.strip()
    if modo == "upper":
        return texto.upper()
    if modo == "lower":
        return texto.lower()
    partes = re.split(r"([ _])", texto)
    salida = []
    for p in partes:
        if p in (" ", "_") or p == "":
            salida.append(p)
        elif p.upper() in SIGLAS:
            salida.append(p.upper())
        else:
            salida.append(p.capitalize())
    return "".join(salida)


def limpiar_espacios(texto):
    texto = texto.strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def nombre_carpeta(nombre, tipo, numero, modo):
    """SANTIAGO_BARRERA_CC_1031649321"""
    nombre = limpiar_espacios(nombre)
    nombre = nombre.replace(" ", SEP)
    nombre = nombre.replace("-", SEP)
    nombre = re.sub(r"_+", SEP, nombre)
    tipo = tipo.upper().strip()
    numero = re.sub(r"[^0-9A-Za-z]", "", numero)
    base = SEP.join([nombre, tipo, numero])
    return formatear(base, modo)


def nombre_documento(numero, nombre_doc, modo, ext=""):
    nombre_doc = nombre_doc.replace(" ", SEP)
    base = SEP.join([numero, nombre_doc])
    return formatear(base, modo) + ext
