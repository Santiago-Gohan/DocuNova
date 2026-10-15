# -*- coding: utf-8 -*-
"""
DocuNova - Organizador de documentos (version web)
Servidor Flask con usuarios, roles (admin/usuario) y herramientas de documentos.
Uso:  python app.py       ->  http://127.0.0.1:5000
"""
import os
import io
import re
import sys
import uuid
import zipfile
import shutil
import secrets
import functools
import threading
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, send_file, abort, jsonify)
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
PADRE = os.path.dirname(BASE)
sys.path.insert(0, PADRE)
sys.path.insert(0, BASE)

import db
import inteligencia as intel
import nomenclatura as nomen

# --- Entorno: en produccion se desactiva el acceso local a "Mi PC" ---
PRODUCCION = os.environ.get("ENTORNO", "").strip().lower() in ("produccion", "production", "prod")

TRABAJOS = os.environ.get("ORGANIZADOR_TRABAJOS") or os.path.join(BASE, "trabajos")
os.makedirs(TRABAJOS, exist_ok=True)
DATOS = os.environ.get("ORGANIZADOR_DATOS") or os.path.join(BASE, "datos")
os.makedirs(DATOS, exist_ok=True)

app = Flask(__name__)

# --- Clave secreta (env var en produccion; si no, archivo local) ---
_clave_env = os.environ.get("ORGANIZADOR_CLAVE")
if _clave_env:
    _clave = _clave_env
else:
    _clave_file = os.path.join(BASE, "clave_secreta.txt")
    if os.path.isfile(_clave_file):
        with open(_clave_file, "r", encoding="utf-8") as f:
            _clave = f.read().strip()
    else:
        _clave = secrets.token_hex(32)
        try:
            with open(_clave_file, "w", encoding="utf-8") as f:
                f.write(_clave)
        except OSError:
            pass
app.secret_key = _clave
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300 MB
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.inicializar()

# En servidores donde no haya idioma OCR, se intenta descargar en segundo
# plano (sin bloquear el arranque ni las peticiones web).
def _preparar_ocr():
    try:
        if not intel.idioma_instalado():
            intel.asegurar_idioma()
    except Exception:
        pass


threading.Thread(target=_preparar_ocr, daemon=True).start()


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def trabajo_dir():
    """Carpeta de trabajo aislada por sesion de navegador."""
    if "trabajo" not in session:
        session["trabajo"] = uuid.uuid4().hex
    ruta = os.path.join(TRABAJOS, session["trabajo"])
    os.makedirs(ruta, exist_ok=True)
    return ruta


def usuario_actual():
    uid = session.get("uid")
    if not uid:
        return None
    u = db.obtener_por_id(uid)
    if not u or not u["activo"]:
        session.clear()
        return None
    return u


@app.context_processor
def inyectar():
    return {"usuario": usuario_actual(), "produccion": PRODUCCION}


def login_required(f):
    @functools.wraps(f)
    def envoltura(*a, **k):
        if not usuario_actual():
            flash("Inicia sesión para continuar.", "aviso")
            return redirect(url_for("login", siguiente=request.path))
        return f(*a, **k)
    return envoltura


def admin_required(f):
    @functools.wraps(f)
    def envoltura(*a, **k):
        u = usuario_actual()
        if not u:
            flash("Inicia sesión para continuar.", "aviso")
            return redirect(url_for("login"))
        if u["rol"] != "admin":
            flash("Solo el administrador puede entrar aquí.", "error")
            return redirect(url_for("dashboard"))
        return f(*a, **k)
    return envoltura


def zip_de_carpeta(carpeta, nombre_zip):
    ruta_zip = os.path.join(trabajo_dir(), nombre_zip)
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _dirs, archivos in os.walk(carpeta):
            for a in archivos:
                completo = os.path.join(raiz, a)
                rel = os.path.relpath(completo, carpeta)
                z.write(completo, rel)
    return ruta_zip


def zip_de_archivos(lista_rutas, nombre_zip):
    ruta_zip = os.path.join(trabajo_dir(), nombre_zip)
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for r in lista_rutas:
            if os.path.isfile(r):
                z.write(r, os.path.basename(r))
    return ruta_zip


def limpiar_trabajo():
    d = os.path.join(TRABAJOS, session.get("trabajo", ""))
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def carpeta_usuario(uid):
    """Carpeta privada de cada usuario: webapp/datos/u_<id>/"""
    ruta = os.path.join(DATOS, f"u_{uid}")
    os.makedirs(ruta, exist_ok=True)
    return ruta


# ----------------------------------------------------------------------
# Autenticacion
# ----------------------------------------------------------------------
@app.route("/salud")
def salud():
    # Mantiene 200 para el healthcheck y ademas informa el estado del OCR.
    return jsonify({"estado": "ok", "ocr": intel.ocr_estado()}), 200


@app.route("/")
def index():
    if usuario_actual():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    primero = not db.hay_usuarios()
    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip()
        email = (request.form.get("email") or "").strip()
        clave = request.form.get("clave") or ""
        clave2 = request.form.get("clave2") or ""
        nombre = (request.form.get("nombre") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.\-]{3,30}", usuario):
            flash("El usuario debe tener 3-30 caracteres (letras, números, . _ -).", "error")
        elif "@" not in email or "." not in email:
            flash("Escribe un correo válido.", "error")
        elif len(clave) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        elif clave != clave2:
            flash("Las contraseñas no coinciden.", "error")
        else:
            rol = "admin" if primero else "usuario"
            uid = db.crear_usuario(usuario, email, clave, nombre, rol)
            if uid is None:
                flash("Ese usuario o correo ya existe.", "error")
            else:
                db.registrar_actividad(uid, usuario, "registro", f"rol={rol}")
                flash(f"¡Cuenta creada como {'ADMINISTRADOR' if rol == 'admin' else 'usuario'}! Ya puedes iniciar sesión.", "ok")
                return redirect(url_for("login"))
    return render_template("registro.html", primero=primero)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip()
        clave = request.form.get("clave") or ""
        u = db.verificar(usuario, clave)
        if u:
            session.clear()
            session["uid"] = u["id"]
            db.marcar_acceso(u["id"])
            db.registrar_actividad(u["id"], u["usuario"], "login")
            nxt = request.args.get("siguiente") or url_for("dashboard")
            return redirect(nxt)
        flash("Usuario o contraseña incorrectos (o cuenta desactivada).", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    u = usuario_actual()
    if u:
        db.registrar_actividad(u["id"], u["usuario"], "logout")
    limpiar_trabajo()
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("login"))


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    u = usuario_actual()
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "datos":
            if db.actualizar_perfil(u["id"], request.form.get("nombre") or u["usuario"],
                                    request.form.get("email") or u["email"]):
                flash("Datos actualizados.", "ok")
            else:
                flash("Ese correo ya está en uso.", "error")
        elif accion == "clave":
            actual = request.form.get("actual") or ""
            nueva = request.form.get("nueva") or ""
            if not db.verificar(u["usuario"], actual):
                flash("La contraseña actual no es correcta.", "error")
            elif len(nueva) < 6:
                flash("La nueva contraseña debe tener al menos 6 caracteres.", "error")
            else:
                db.cambiar_clave(u["id"], nueva)
                flash("Contraseña cambiada.", "ok")
        return redirect(url_for("perfil"))
    return render_template("perfil.html")


# ----------------------------------------------------------------------
# Panel de administrador
# ----------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html",
                           usuarios=db.listar_usuarios(),
                           actividad=db.actividad_reciente(30))


@app.route("/admin/crear", methods=["POST"])
@admin_required
def admin_crear():
    usuario = (request.form.get("usuario") or "").strip()
    email = (request.form.get("email") or "").strip()
    clave = request.form.get("clave") or ""
    nombre = (request.form.get("nombre") or "").strip()
    rol = request.form.get("rol") or "usuario"
    if len(usuario) < 3 or "@" not in email or len(clave) < 6:
        flash("Revisa los datos: usuario (3+), correo válido y clave (6+).", "error")
    else:
        uid = db.crear_usuario(usuario, email, clave, nombre, rol if rol in ("admin", "usuario") else "usuario")
        if uid is None:
            flash("Ese usuario o correo ya existe.", "error")
        else:
            db.registrar_actividad(session["uid"], "admin", "crear_usuario", usuario)
            flash(f"Usuario '{usuario}' creado.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/eliminar/<int:uid>", methods=["POST"])
@admin_required
def admin_eliminar(uid):
    if uid == session["uid"]:
        flash("No puedes eliminarte a ti mismo.", "error")
    else:
        objetivo = db.obtener_por_id(uid)
        if objetivo and objetivo["rol"] == "admin" and db.contar_admins() <= 1:
            flash("No puedes eliminar al único administrador.", "error")
        elif objetivo:
            db.eliminar_usuario(uid)
            db.registrar_actividad(session["uid"], "admin", "eliminar_usuario", objetivo["usuario"])
            flash(f"Usuario '{objetivo['usuario']}' eliminado.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/rol/<int:uid>", methods=["POST"])
@admin_required
def admin_rol(uid):
    objetivo = db.obtener_por_id(uid)
    if not objetivo:
        abort(404)
    if objetivo["id"] == session["uid"]:
        flash("No puedes cambiar tu propio rol.", "error")
    elif objetivo["rol"] == "admin" and db.contar_admins() <= 1:
        flash("Debe quedar al menos un administrador.", "error")
    else:
        nuevo = "usuario" if objetivo["rol"] == "admin" else "admin"
        db.set_rol(uid, nuevo)
        db.registrar_actividad(session["uid"], "admin", "cambiar_rol", f"{objetivo['usuario']}->{nuevo}")
        flash(f"Rol de '{objetivo['usuario']}' ahora es {nuevo}.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/activo/<int:uid>", methods=["POST"])
@admin_required
def admin_activo(uid):
    objetivo = db.obtener_por_id(uid)
    if not objetivo:
        abort(404)
    if objetivo["id"] == session["uid"]:
        flash("No puedes desactivar tu propia cuenta.", "error")
    else:
        db.set_activo(uid, not objetivo["activo"])
        db.registrar_actividad(session["uid"], "admin", "activar/desactivar", objetivo["usuario"])
        flash("Estado actualizado.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/clave/<int:uid>", methods=["POST"])
@admin_required
def admin_clave(uid):
    objetivo = db.obtener_por_id(uid)
    if not objetivo:
        abort(404)
    nueva = request.form.get("clave") or ""
    if len(nueva) < 6:
        flash("La contraseña debe tener al menos 6 caracteres.", "error")
    else:
        db.cambiar_clave(uid, nueva)
        db.registrar_actividad(session["uid"], "admin", "reset_clave", objetivo["usuario"])
        flash(f"Contraseña de '{objetivo['usuario']}' cambiada.", "ok")
    return redirect(url_for("admin"))


# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------
@app.route("/panel")
@login_required
def dashboard():
    return render_template("dashboard.html",
                           n_docs=len(nomen.DOCS),
                           ocr=intel._ocr_disponible())


# ----------------------------------------------------------------------
# Herramienta: convertir texto
# ----------------------------------------------------------------------
@app.route("/herramientas/convertir", methods=["GET", "POST"])
@login_required
def herramienta_convertir():
    resultado = None
    if request.method == "POST":
        texto = request.form.get("texto") or ""
        lineas = [l for l in texto.splitlines() if l.strip()]
        resultado = {"upper": [], "lower": [], "title": []}
        for l in lineas:
            limpio = l.rstrip(",").strip()
            for m in resultado:
                resultado[m].append({
                    "texto": nomen.formatear(limpio, m),
                    "token": nomen.formatear(limpio.replace(" ", "_"), m),
                })
    return render_template("convertir.html", resultado=resultado)


# ----------------------------------------------------------------------
# Herramienta: crear estructura (ZIP descargable)
# ----------------------------------------------------------------------
@app.route("/herramientas/crear", methods=["GET", "POST"])
@login_required
def herramienta_crear():
    if request.method == "POST":
        modo = request.form.get("modo", "upper")
        lineas = [l.strip() for l in (request.form.get("estudiantes") or "").splitlines() if l.strip()]
        d = trabajo_dir()
        carpeta = os.path.join(d, "estructura")
        shutil.rmtree(carpeta, ignore_errors=True)
        creados = 0
        for l in lineas:
            partes = [p.strip() for p in l.split(",")]
            nombre = partes[0] if partes else ""
            numero = partes[1] if len(partes) > 1 else "000000"
            menor = len(partes) > 2 and partes[2].strip().upper() in ("S", "SI", "SÍ")
            if not nombre:
                continue
            nom_carpeta = nomen.nombre_carpeta(nombre, "CC", numero, modo)
            ruta_est = os.path.join(carpeta, nom_carpeta)
            os.makedirs(ruta_est, exist_ok=True)
            for num, nombre_doc, solo_menores in nomen.DOCS:
                if solo_menores and not menor:
                    continue
                nombre_archivo = nomen.nombre_documento(num, nombre_doc, modo, ".pdf")
                with open(os.path.join(ruta_est, nombre_archivo), "wb") as f:
                    f.write(b"%PDF-1.4\n% documento de ejemplo\n")
            creados += 1
        if creados:
            zip_ruta = zip_de_carpeta(carpeta, "estructura_estudiantes.zip")
            return send_file(zip_ruta, as_attachment=True, download_name="estructura_estudiantes.zip")
        flash("No se creó nada: revisa el formato.", "error")
    return render_template("crear.html", docs=nomen.DOCS)


# ----------------------------------------------------------------------
# Herramienta: normalizar (subir ZIP -> ZIP normalizado)
# ----------------------------------------------------------------------
@app.route("/herramientas/normalizar", methods=["GET", "POST"])
@login_required
def herramienta_normalizar():
    if request.method == "POST":
        archivo = request.files.get("zip")
        modo = request.form.get("modo", "upper")
        if not archivo or not archivo.filename.lower().endswith(".zip"):
            flash("Sube un archivo .ZIP con las carpetas a normalizar.", "error")
            return redirect(url_for("herramienta_normalizar"))
        d = trabajo_dir()
        entrada = os.path.join(d, "entrada")
        shutil.rmtree(entrada, ignore_errors=True)
        os.makedirs(entrada, exist_ok=True)
        with zipfile.ZipFile(archivo) as z:
            z.extractall(entrada)
        cambios = 0
        for raiz, dirs, archivos in os.walk(entrada, topdown=False):
            for a in archivos:
                nuevo = nomen.formatear(a, modo)
                if nuevo != a:
                    try:
                        os.rename(os.path.join(raiz, a), os.path.join(raiz, nuevo))
                        cambios += 1
                    except OSError:
                        pass
            for dr in dirs:
                nuevo = nomen.formatear(dr, modo)
                if nuevo != dr:
                    try:
                        os.rename(os.path.join(raiz, dr), os.path.join(raiz, nuevo))
                        cambios += 1
                    except OSError:
                        pass
        zip_ruta = zip_de_carpeta(entrada, "normalizado.zip")
        db.registrar_actividad(session["uid"], usuario_actual()["usuario"], "normalizar", f"{cambios} cambios")
        return send_file(zip_ruta, as_attachment=True, download_name="normalizado.zip")
    return render_template("normalizar.html")


# ----------------------------------------------------------------------
# Herramienta: clasificar (subir archivos -> resultados + ZIP renombrado)
# ----------------------------------------------------------------------
@app.route("/herramientas/clasificar", methods=["GET", "POST"])
@login_required
def herramienta_clasificar():
    if request.method == "POST":
        archivos = request.files.getlist("documentos")
        modo = request.form.get("modo", "upper")
        archivos = [a for a in archivos if a and a.filename]
        if not archivos:
            flash("Sube uno o varios documentos (PDF o imágenes).", "error")
            return redirect(url_for("herramienta_clasificar"))
        d = trabajo_dir()
        entrada = os.path.join(d, "clasificar")
        shutil.rmtree(entrada, ignore_errors=True)
        os.makedirs(entrada, exist_ok=True)
        resultados = []
        salidas = []
        for a in archivos:
            nombre = secure_filename(a.filename)
            ruta = os.path.join(entrada, nombre)
            a.save(ruta)
            try:
                texto, res = intel.clasificar_archivo(ruta)
            except Exception as e:
                res = None
            ext = os.path.splitext(nombre)[1]
            if res:
                num, nom, conf, _ = res
                nuevo = nomen.nombre_documento(num, nom, modo, ext)
                resultados.append({"archivo": a.filename, "tipo": f"{num}_{nom}", "conf": conf,
                                   "nuevo": nuevo, "ok": True})
            else:
                nuevo = nombre
                resultados.append({"archivo": a.filename, "tipo": "no identificado",
                                   "conf": "-", "nuevo": nombre, "ok": False})
            destino = os.path.join(entrada, nuevo)
            base, e2 = os.path.splitext(destino)
            k = 2
            while os.path.exists(destino):
                destino = f"{base}_{k}{e2}"
                k += 1
            os.replace(ruta, destino)
            salidas.append(destino)
        zip_ruta = zip_de_archivos(salidas, "documentos_clasificados.zip")
        db.registrar_actividad(session["uid"], usuario_actual()["usuario"], "clasificar", f"{len(archivos)} archivos")
        # guarda la ruta del zip para descarga posterior
        session["zip_clasificar"] = os.path.basename(zip_ruta)
        return render_template("clasificar.html", resultados=resultados, zip_listo=True)
    return render_template("clasificar.html", resultados=None, zip_listo=False)


# ----------------------------------------------------------------------
# Herramienta: organizar por persona (subir carpeta/ZIP -> una carpeta
# por persona con cada documento ya clasificado)
# ----------------------------------------------------------------------
EXT_DOC = intel.EXT_PDF | intel.EXT_IMAGEN


def _carpeta_persona(info, modo):
    """Nombre de la carpeta de una persona. Estructura planeada:
    NOMBRE_APELLIDO_TIPO_NUMERO (ej. SANTIAGO_BARRERA_CC_1031649321)."""
    if not info:
        return "SIN_IDENTIFICAR"
    nombre = (info.get("nombre") or "").strip()
    dni = (info.get("dni") or "").strip()
    tipo = (info.get("tipo") or "").strip().upper()
    if nombre and tipo and dni:
        return nomen.nombre_carpeta(nombre, tipo, dni, modo)
    if nombre and dni:
        return nomen.formatear(f"{nombre.replace(' ', '_')}_{dni}", modo)
    if nombre and tipo:
        return nomen.formatear(f"{nombre.replace(' ', '_')}_{tipo}", modo)
    if nombre:
        return nomen.formatear(nombre.replace(" ", "_"), modo)
    if dni and tipo:
        return nomen.formatear(f"{tipo}_{dni}", modo)
    if dni:
        return nomen.formatear(f"DOC_{dni}", modo)
    if info.get("email"):
        return nomen.formatear(info["email"], modo)
    return "SIN_IDENTIFICAR"


@app.route("/herramientas/organizar", methods=["GET", "POST"])
@login_required
def herramienta_organizar():
    if request.method == "POST":
        archivo = request.files.get("carpeta")
        modo = request.form.get("modo", "upper")
        if not archivo or not archivo.filename:
            flash("Sube la carpeta de documentos comprimida en un ZIP.", "error")
            return redirect(url_for("herramienta_organizar"))
        if not archivo.filename.lower().endswith(".zip"):
            flash("Empaqueta la carpeta en un ZIP (.zip) y vuelve a subirla.", "error")
            return redirect(url_for("herramienta_organizar"))

        d = trabajo_dir()
        entrada = os.path.join(d, "organizar_entrada")
        salida = os.path.join(d, "organizar_salida")
        shutil.rmtree(entrada, ignore_errors=True)
        shutil.rmtree(salida, ignore_errors=True)
        os.makedirs(entrada, exist_ok=True)
        os.makedirs(salida, exist_ok=True)

        zip_in = os.path.join(d, "organizar.zip")
        archivo.save(zip_in)
        try:
            with zipfile.ZipFile(zip_in) as z:
                z.extractall(entrada)
        except zipfile.BadZipFile:
            flash("El archivo no es un ZIP válido.", "error")
            return redirect(url_for("herramienta_organizar"))

        personas = {}   # clave -> {"carpeta", "docs": [...], "sin_id": n}
        orden = []
        total = 0
        sin_id = 0
        for raiz, _dirs, archivos in os.walk(entrada):
            for a in archivos:
                ext = os.path.splitext(a)[1].lower()
                if ext not in EXT_DOC:
                    continue
                ruta = os.path.join(raiz, a)
                rel = os.path.relpath(ruta, entrada)
                sub = os.path.dirname(rel)
                try:
                    texto, res = intel.clasificar_archivo(ruta)
                except Exception:
                    texto, res = "", None
                info = intel.detectar_persona(texto, a)
                # pista: si el ZIP ya venía con una subcarpeta por persona
                if not info and sub and sub != ".":
                    cand = os.path.basename(sub).replace("_", " ").strip()
                    if cand:
                        info = {"nombre": cand, "dni": None, "email": None}
                clave = intel.clave_persona(info)
                if clave == "sin_identificar":
                    sin_id += 1
                if clave not in personas:
                    personas[clave] = {"carpeta": _carpeta_persona(info, modo),
                                       "info": info, "docs": []}
                    orden.append(clave)
                # nombre del documento clasificado
                if res:
                    num, nom, conf, _ = res
                    nuevo = nomen.nombre_documento(num, nom, modo, ext)
                    tipo = f"{num}_{nom}"
                else:
                    nuevo = nomen.formatear(a, modo)
                    tipo = "no identificado"
                    conf = "-"
                # carpeta destino + evitar colisiones
                carpeta_p = os.path.join(salida, personas[clave]["carpeta"])
                os.makedirs(carpeta_p, exist_ok=True)
                destino = os.path.join(carpeta_p, nuevo)
                base, e2 = os.path.splitext(destino)
                k = 2
                while os.path.exists(destino):
                    destino = f"{base}_{k}{e2}"
                    k += 1
                shutil.copy2(ruta, destino)
                personas[clave]["docs"].append({
                    "original": a, "nuevo": os.path.basename(destino),
                    "tipo": tipo, "conf": conf, "ok": bool(res),
                })
                total += 1

        if total == 0:
            flash("No se encontraron documentos PDF o imágenes dentro del ZIP.", "error")
            return redirect(url_for("herramienta_organizar"))

        zip_ruta = zip_de_carpeta(salida, "organizado_por_persona.zip")
        db.registrar_actividad(session["uid"], usuario_actual()["usuario"], "organizar",
                               f"{total} documentos, {len(personas)} personas")
        resumen = []
        for clave in orden:
            p = personas[clave]
            resumen.append({"carpeta": p["carpeta"], "docs": p["docs"],
                            "info": p["info"]})
        return render_template("organizar.html", resumen=resumen, total=total,
                               n_personas=len(personas), sin_id=sin_id,
                               zip_listo=True)
    return render_template("organizar.html", resumen=None)


# ----------------------------------------------------------------------
# Herramienta: separar PDF grande
# ----------------------------------------------------------------------
@app.route("/herramientas/separar", methods=["GET", "POST"])
@login_required
def herramienta_separar():
    if request.method == "POST":
        accion = request.form.get("accion", "analizar")
        d = trabajo_dir()
        if accion == "analizar":
            archivo = request.files.get("pdf")
            if not archivo or not archivo.filename.lower().endswith(".pdf"):
                flash("Sube un archivo PDF.", "error")
                return redirect(url_for("herramienta_separar"))
            ruta = os.path.join(d, "grande.pdf")
            archivo.save(ruta)
            progreso = []
            paginas = intel.analizar_pdf_paginas(ruta)
            grupos = intel.agrupar_paginas(paginas)
            for i, g in enumerate(grupos, 1):
                rango = (f"pág {g['paginas'][0]}" if len(g["paginas"]) == 1
                         else f"pág {g['paginas'][0]}-{g['paginas'][-1]}")
                progreso.append({"n": i, "rango": rango, "tipo": g["tipo"] or "SIN IDENTIFICAR", "conf": g["conf"] or "-"})
            return render_template("separar.html", paginas=paginas, grupos=progreso,
                                   total_pag=len(paginas), analizado=True)
        elif accion == "separar":
            modo = request.form.get("modo", "upper")
            ruta = os.path.join(d, "grande.pdf")
            if not os.path.isfile(ruta):
                flash("Primero analiza un PDF.", "error")
                return redirect(url_for("herramienta_separar"))
            destino = os.path.join(d, "separados")
            shutil.rmtree(destino, ignore_errors=True)
            paginas = intel.analizar_pdf_paginas(ruta)
            grupos = intel.agrupar_paginas(paginas)
            creados = intel.separar_pdf(ruta, destino, grupos, modo=modo)
            zip_ruta = zip_de_carpeta(destino, "separados.zip")
            db.registrar_actividad(session["uid"], usuario_actual()["usuario"], "separar_pdf", f"{len(creados)} documentos")
            return send_file(zip_ruta, as_attachment=True, download_name="documentos_separados.zip")
    return render_template("separar.html", paginas=None, grupos=None, analizado=False)


@app.route("/descargas/<nombre>")
@login_required
def descargar(nombre):
    permitidos = {session.get("zip_clasificar"), "documentos_clasificados.zip",
                  "organizado_por_persona.zip"}
    if nombre not in permitidos:
        abort(404)
    ruta = os.path.join(trabajo_dir(), nombre)
    if not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, as_attachment=True, download_name=nombre)


# ----------------------------------------------------------------------
# Mis documentos (carpeta privada de cada usuario)
# ----------------------------------------------------------------------
@app.route("/mis-documentos")
@login_required
def mis_documentos():
    u = usuario_actual()
    docs = db.listar_documentos(u["id"])
    return render_template("mis_documentos.html", docs=docs,
                           total=len(docs),
                           usado=sum(d["tam"] or 0 for d in docs))


@app.route("/mis-documentos/subir", methods=["POST"])
@login_required
def mis_documentos_subir():
    u = usuario_actual()
    archivos = [a for a in request.files.getlist("documentos") if a and a.filename]
    if not archivos:
        flash("Selecciona al menos un archivo.", "error")
        return redirect(url_for("mis_documentos"))
    carpeta = carpeta_usuario(u["id"])
    subidos = 0
    for a in archivos:
        nombre = secure_filename(a.filename) or "documento"
        destino = os.path.join(carpeta, nombre)
        raiz, ext = os.path.splitext(destino)
        k = 2
        while os.path.exists(destino):
            destino = f"{raiz}_{k}{ext}"
            k += 1
        a.save(destino)
        tipo, conf = "", ""
        try:
            _, res = intel.clasificar_archivo(destino)
            if res:
                tipo, conf = f"{res[0]}_{res[1]}", res[2]
        except Exception:
            pass
        db.agregar_documento(u["id"], a.filename, os.path.basename(destino),
                             tipo, conf, os.path.getsize(destino))
        subidos += 1
    db.registrar_actividad(u["id"], u["usuario"], "subir_documentos", f"{subidos} archivos")
    flash(f"{subidos} documento(s) guardado(s) en tu carpeta privada.", "ok")
    return redirect(url_for("mis_documentos"))


def _doc_autorizado(doc_id):
    """Devuelve (documento, es_admin) si el usuario puede acceder."""
    u = usuario_actual()
    d = db.obtener_documento(doc_id)
    if not d:
        return None, False
    if u["rol"] == "admin" or d["usuario_id"] == u["id"]:
        return d, u["rol"] == "admin"
    return None, False


@app.route("/mis-documentos/descargar/<int:doc_id>")
@login_required
def mis_documentos_descargar(doc_id):
    d, _ = _doc_autorizado(doc_id)
    if not d:
        abort(404)
    ruta = os.path.join(carpeta_usuario(d["usuario_id"]), d["guardado"])
    if not os.path.isfile(ruta):
        abort(404)
    return send_file(ruta, as_attachment=True, download_name=d["nombre"])


@app.route("/mis-documentos/borrar/<int:doc_id>", methods=["POST"])
@login_required
def mis_documentos_borrar(doc_id):
    d, _ = _doc_autorizado(doc_id)
    if not d:
        abort(404)
    ruta = os.path.join(carpeta_usuario(d["usuario_id"]), d["guardado"])
    if os.path.isfile(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass
    db.borrar_documento(doc_id)
    u = usuario_actual()
    db.registrar_actividad(u["id"], u["usuario"], "borrar_documento", d["nombre"])
    flash("Documento eliminado.", "ok")
    return redirect(request.referrer or url_for("mis_documentos"))


@app.route("/admin/documentos/<int:uid>")
@admin_required
def admin_documentos(uid):
    objetivo = db.obtener_por_id(uid)
    if not objetivo:
        abort(404)
    docs = db.listar_documentos(uid)
    return render_template("mis_documentos.html", docs=docs, total=len(docs),
                           usado=sum(d["tam"] or 0 for d in docs), objetivo=objetivo)


# ----------------------------------------------------------------------
# Acceso a carpetas locales (solo admin)
# ----------------------------------------------------------------------
@app.route("/local", methods=["GET", "POST"])
@admin_required
def local():
    if PRODUCCION:
        flash("El acceso a archivos locales está desactivado en el servidor.", "error")
        return redirect(url_for("dashboard"))
    ruta = request.form.get("ruta") or request.args.get("ruta") or ""
    entradas = []
    error = None
    if ruta:
        if os.path.isdir(ruta):
            try:
                for nombre in sorted(os.listdir(ruta)):
                    p = os.path.join(ruta, nombre)
                    entradas.append({"nombre": nombre, "dir": os.path.isdir(p),
                                     "tam": os.path.getsize(p) if os.path.isfile(p) else 0})
            except Exception as e:
                error = f"No se pudo leer: {e}"
        else:
            error = "Esa ruta no existe o no es una carpeta."
    return render_template("local.html", ruta=ruta, entradas=entradas, error=error)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("  DocuNova - Organizador de documentos (web)")
    print(f"  Abre en tu navegador:  http://127.0.0.1:{puerto}")
    print("  Para acceso desde internet usa un tunel (ver LEEME_WEB.txt)")
    print("=" * 60)
    app.run(host="0.0.0.0", port=puerto, debug=False)
