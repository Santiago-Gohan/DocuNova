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
import json
import uuid
import zipfile
import shutil
import secrets
import functools
import threading
import time
from datetime import datetime, timedelta

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
import trabajos

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
app.config["SESSION_COOKIE_HTTPONLY"] = True
# La sesion se cierra sola tras este tiempo sin actividad (ademas de
# cerrarse al cerrar el navegador, por ser cookie de sesion no permanente).
MINUTOS_INACTIVIDAD = 30
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=MINUTOS_INACTIVIDAD)

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


@app.before_request
def _control_inactividad():
    """Cierra la sesion si pasa demasiado tiempo sin actividad."""
    if not session.get("uid"):
        return None
    ahora = time.time()
    ultimo = session.get("_ultimo", ahora)
    if ahora - ultimo > MINUTOS_INACTIVIDAD * 60:
        limpiar_trabajo()
        session.clear()
        if request.endpoint not in ("login", "registro", "salud", "static"):
            flash("Tu sesión se cerró por inactividad. Vuelve a entrar.", "aviso")
            return redirect(url_for("login"))
        return None
    session["_ultimo"] = ahora
    return None


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


def zip_de_carpeta(carpeta, nombre_zip, base=None):
    """Comprime `carpeta`. `base` evita usar la sesion dentro de hilos."""
    ruta_zip = os.path.join(base or trabajo_dir(), nombre_zip)
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _dirs, archivos in os.walk(carpeta):
            for a in archivos:
                completo = os.path.join(raiz, a)
                rel = os.path.relpath(completo, carpeta)
                z.write(completo, rel)
    return ruta_zip


def zip_de_archivos(lista_rutas, nombre_zip, base=None):
    ruta_zip = os.path.join(base or trabajo_dir(), nombre_zip)
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for r in lista_rutas:
            if os.path.isfile(r):
                z.write(r, os.path.basename(r))
    return ruta_zip


def leer_json(ruta, defecto=None):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 - archivo ausente o a medias
        return defecto


def escribir_json(ruta, datos):
    """Escritura atomica: la pagina de resultados nunca lee un archivo a medias."""
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def borrar_de(d, *nombres):
    for n in nombres:
        try:
            os.remove(os.path.join(d, n))
        except OSError:
            pass


def resumen_grupos(grupos):
    filas = []
    for i, g in enumerate(grupos, 1):
        rango = (f"pág {g['paginas'][0]}" if len(g["paginas"]) == 1
                 else f"pág {g['paginas'][0]}-{g['paginas'][-1]}")
        filas.append({"n": i, "rango": rango,
                      "tipo": g["tipo"] or "SIN IDENTIFICAR",
                      "conf": g["conf"] or "-"})
    return filas


def es_ajax():
    return request.headers.get("X-Trabajo") == "1"


def error_ajax(mensaje):
    return jsonify({"error": mensaje}), 400


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
    if usuario_actual():
        return redirect(url_for("dashboard"))
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
    if usuario_actual():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip()
        clave = request.form.get("clave") or ""
        u = db.verificar(usuario, clave)
        if u:
            session.clear()
            session["uid"] = u["id"]
            session["_ultimo"] = time.time()
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
            edad = "menor" if menor else "mayor"
            for num, nombre_doc in nomen.documentos_de(edad):
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
@app.route("/trabajo/<tid>")
@login_required
def estado_trabajo(tid):
    """Consulta de progreso: cada llamada dura milisegundos (nunca la corta Render)."""
    t = trabajos.obtener(tid, uid=session.get("uid"))
    if not t:
        abort(404)
    return jsonify({"id": t["id"], "estado": t["estado"], "pct": t["pct"],
                    "fase": t["fase"], "error": t["error"]})


def _procesar_clasificacion(progreso, d, entrada, subidos, modo, uid, usuario):
    """Hilo: clasifica cada archivo, arma el ZIP y guarda los resultados."""
    total = len(subidos)
    resultados = []
    salidas = []
    # Pase 1: leer el texto de cada archivo (para deducir la edad del grupo).
    textos = []
    for i, (ruta, original) in enumerate(subidos, 1):
        progreso(int((i - 1) * 45 / total),
                 f"Leyendo {i} de {total}: {original}")
        try:
            textos.append(intel.texto_de_archivo(ruta))
        except Exception:  # noqa: BLE001 - archivo ilegible, va sin clasificar
            textos.append("")
    edad = intel.detectar_edad("\n".join(textos))
    # Pase 2: clasificar (la edad decide si el ICFES es 005 o 008).
    for i, ((ruta, original), texto) in enumerate(zip(subidos, textos), 1):
        nombre = os.path.basename(ruta)
        progreso(int(45 + (i - 1) * 45 / total),
                 f"Clasificando {i} de {total}: {original}")
        res = (intel.clasificar(texto, edad)
               or intel.clasificar_desde_nombre(original, edad))
        ext = os.path.splitext(nombre)[1]
        if res:
            num, nom, conf, _ = res
            nuevo = nomen.nombre_documento(num, nom, modo, ext)
            resultados.append({"archivo": original, "tipo": f"{num}_{nom}",
                               "conf": conf, "nuevo": nuevo, "ok": True})
        else:
            nuevo = nombre
            resultados.append({"archivo": original, "tipo": "no identificado",
                               "conf": "-", "nuevo": nombre, "ok": False})
        destino = os.path.join(entrada, nuevo)
        base, e2 = os.path.splitext(destino)
        k = 2
        while os.path.exists(destino):
            destino = f"{base}_{k}{e2}"
            k += 1
        os.replace(ruta, destino)
        salidas.append(destino)
    progreso(94, "Comprimiendo el ZIP...")
    zip_de_archivos(salidas, "documentos_clasificados.zip", base=d)
    escribir_json(os.path.join(d, "clasificar_resultados.json"), resultados)
    try:
        db.registrar_actividad(uid, usuario, "clasificar", f"{total} archivos")
    except Exception:  # noqa: BLE001
        pass
    return {"total": total}


@app.route("/herramientas/clasificar", methods=["GET", "POST"])
@login_required
def herramienta_clasificar():
    d = trabajo_dir()
    if request.method == "POST":
        archivos = [a for a in request.files.getlist("documentos") if a and a.filename]
        modo = request.form.get("modo", "upper")
        if not archivos:
            if es_ajax():
                return error_ajax("Sube uno o varios documentos (PDF o imágenes).")
            flash("Sube uno o varios documentos (PDF o imágenes).", "error")
            return redirect(url_for("herramienta_clasificar"))
        entrada = os.path.join(d, "clasificar")
        shutil.rmtree(entrada, ignore_errors=True)
        os.makedirs(entrada, exist_ok=True)
        subidos = []
        for a in archivos:
            ruta = os.path.join(entrada, secure_filename(a.filename))
            a.save(ruta)
            subidos.append((ruta, a.filename))
        borrar_de(d, "clasificar_resultados.json", "documentos_clasificados.zip")
        tid = trabajos.crear(session["uid"], "Clasificando documentos",
                             _procesar_clasificacion, d, entrada, subidos, modo,
                             session["uid"], usuario_actual()["usuario"])
        return jsonify({"trabajo": tid, "total": len(subidos)})

    if request.args.get("nuevo"):
        borrar_de(d, "clasificar_resultados.json", "documentos_clasificados.zip")
    resultados = leer_json(os.path.join(d, "clasificar_resultados.json"))
    zip_listo = os.path.isfile(os.path.join(d, "documentos_clasificados.zip"))
    return render_template("clasificar.html", resultados=resultados,
                           zip_listo=zip_listo and bool(resultados))


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


def _procesar_organizacion(progreso, d, entrada, modo, uid, usuario):
    """Hilo: lee y clasifica cada documento para armar el plan de carpetas."""
    subidos = []
    for raiz, _dirs, archivos in os.walk(entrada):
        for a in archivos:
            if os.path.splitext(a)[1].lower() in EXT_DOC:
                subidos.append(os.path.join(raiz, a))
    if not subidos:
        raise ValueError("No se encontraron documentos PDF o imágenes "
                         "dentro de la carpeta o el ZIP.")
    personas = {}
    orden = []
    total = 0
    n_total = len(subidos)
    # ---- Pase 1: leer el texto y agrupar los documentos por persona ----
    for i, ruta in enumerate(subidos, 1):
        a = os.path.basename(ruta)
        rel = os.path.relpath(ruta, entrada)
        sub = os.path.dirname(rel)
        ext = os.path.splitext(a)[1].lower()
        progreso(int((i - 1) * 45 / n_total),
                 f"Leyendo {i} de {n_total}: {a}")
        try:
            texto = intel.texto_de_archivo(ruta)
        except Exception:  # noqa: BLE001
            texto = ""
        info = intel.detectar_persona(texto, a)
        # pista: si la carpeta ya venia con una subcarpeta por persona
        if not info and sub and sub != ".":
            cand = os.path.basename(sub).replace("_", " ").strip()
            if cand:
                info = {"nombre": cand}
        clave = intel.clave_persona(info)
        if clave not in personas:
            personas[clave] = {"clave": clave,
                               "carpeta": _carpeta_persona(info, modo),
                               "info": info or {}, "docs": []}
            orden.append(clave)
        personas[clave]["docs"].append({"rel": rel, "original": a,
                                        "ext": ext, "texto": texto})
        total += 1

    # ---- Pase 2: clasificar. La edad de cada persona decide el ICFES ----
    n_personas = len(orden)
    for j, clave in enumerate(orden, 1):
        p = personas[clave]
        edad = intel.detectar_edad("\n".join(doc["texto"] for doc in p["docs"]))
        for doc in p["docs"]:
            res = (intel.clasificar(doc["texto"], edad)
                   or intel.clasificar_desde_nombre(doc["original"], edad))
            if res:
                num, nom, conf, _ = res
                doc["nuevo"] = nomen.nombre_documento(num, nom, modo, doc["ext"])
                doc["tipo"] = f"{num}_{nom}"
                doc["conf"] = conf
                doc["ok"] = True
            else:
                doc["nuevo"] = nomen.formatear(doc["original"], modo)
                doc["tipo"] = "no identificado"
                doc["conf"] = "-"
                doc["ok"] = False
            doc.pop("ext", None)
            doc.pop("texto", None)
        progreso(int(45 + j * 50 / n_personas) if n_personas else 95,
                 f"Clasificando grupo {j} de {n_personas}...")

    plan = {"modo": modo, "total": total,
            "personas": [personas[k] for k in orden]}
    escribir_json(os.path.join(d, "organizar_plan.json"), plan)
    borrar_de(d, "organizar_listo.json", "organizado_por_persona.zip")
    try:
        db.registrar_actividad(uid, usuario, "organizar",
                               f"{total} documentos, {len(orden)} personas")
    except Exception:  # noqa: BLE001
        pass
    return {"total": total, "personas": len(orden)}


def _procesar_generacion(progreso, d, plan, uid, usuario):
    """Hilo: crea una carpeta por persona y comprime el resultado."""
    entrada = os.path.join(d, "organizar_entrada")
    salida = os.path.join(d, "organizar_salida")
    shutil.rmtree(salida, ignore_errors=True)
    os.makedirs(salida, exist_ok=True)
    n_p = max(1, len(plan["personas"]))
    for i, p in enumerate(plan["personas"], 1):
        progreso(int((i - 1) * 85 / n_p),
                 f"Creando carpeta {i} de {n_p}: {p['carpeta']}")
        carpeta_p = os.path.join(salida, p["carpeta"])
        os.makedirs(carpeta_p, exist_ok=True)
        for doc in p["docs"]:
            origen = os.path.join(entrada, doc["rel"])
            if not os.path.isfile(origen):
                continue
            destino = os.path.join(carpeta_p, doc["nuevo"])
            base, e2 = os.path.splitext(destino)
            k = 2
            while os.path.exists(destino):
                destino = f"{base}_{k}{e2}"
                k += 1
            shutil.copy2(origen, destino)
    progreso(90, "Comprimiendo el ZIP...")
    zip_de_carpeta(salida, "organizado_por_persona.zip", base=d)
    escribir_json(os.path.join(d, "organizar_listo.json"), plan)
    try:
        db.registrar_actividad(uid, usuario, "organizar",
                               f"{plan['total']} documentos, "
                               f"{len(plan['personas'])} personas")
    except Exception:  # noqa: BLE001
        pass
    return {"total": plan["total"], "personas": len(plan["personas"])}


@app.route("/herramientas/organizar", methods=["GET", "POST"])
@login_required
def herramienta_organizar():
    d = trabajo_dir()
    if request.method == "POST":
        accion = request.form.get("accion", "analizar")

        # ---------- FASE 1: analizar el ZIP o la carpeta y detectar personas ----------
        if accion == "analizar":
            archivo = request.files.get("carpeta")
            docs = [f for f in request.files.getlist("documentos") if f and f.filename]
            modo = request.form.get("modo", "upper")

            entrada = os.path.join(d, "organizar_entrada")
            shutil.rmtree(entrada, ignore_errors=True)
            os.makedirs(entrada, exist_ok=True)

            if archivo and archivo.filename:
                if not archivo.filename.lower().endswith(".zip"):
                    if es_ajax():
                        return error_ajax("El archivo debe ser un ZIP (.zip).")
                    flash("El archivo debe ser un ZIP (.zip).", "error")
                    return redirect(url_for("herramienta_organizar"))
                zip_in = os.path.join(d, "organizar.zip")
                archivo.save(zip_in)
                try:
                    with zipfile.ZipFile(zip_in) as z:
                        z.extractall(entrada)
                except zipfile.BadZipFile:
                    if es_ajax():
                        return error_ajax("El archivo no es un ZIP válido.")
                    flash("El archivo no es un ZIP válido.", "error")
                    return redirect(url_for("herramienta_organizar"))
            elif docs:
                # Carpeta subida directamente: se conservan las subcarpetas
                for f in docs:
                    rel = (f.filename or "").replace("\\", "/")
                    partes: list[str] = []
                    for p in rel.split("/"):
                        if not p or p in ("..", "."):
                            continue
                        partes.append(secure_filename(p) or "archivo")
                    if not partes:
                        continue
                    destino = os.path.join(entrada, *partes)
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    f.save(destino)
            else:
                if es_ajax():
                    return error_ajax("Elige una carpeta o sube un ZIP.")
                flash("Elige una carpeta o sube un ZIP.", "error")
                return redirect(url_for("herramienta_organizar"))

            borrar_de(d, "organizar_plan.json", "organizar_listo.json",
                      "organizado_por_persona.zip")
            tid = trabajos.crear(session["uid"], "Analizando documentos",
                                 _procesar_organizacion, d, entrada, modo,
                                 session["uid"], usuario_actual()["usuario"])
            return jsonify({"trabajo": tid})

        # ---------- FASE 2: generar el ZIP con los nombres editados ----------
        if accion == "generar":
            plan = leer_json(os.path.join(d, "organizar_plan.json"))
            if not plan:
                if es_ajax():
                    return error_ajax("Primero sube una carpeta o un ZIP para analizarlo.")
                flash("Primero sube una carpeta o un ZIP para analizarlo.", "error")
                return redirect(url_for("herramienta_organizar"))
            for p in plan["personas"]:
                carpeta = (request.form.get("carpeta_" + p["clave"]) or p["carpeta"]).strip()
                p["carpeta"] = re.sub(r'[\\/:*?"<>|]+', "_", carpeta or "SIN_IDENTIFICAR")
            tid = trabajos.crear(session["uid"], "Generando el ZIP",
                                 _procesar_generacion, d, plan,
                                 session["uid"], usuario_actual()["usuario"])
            return jsonify({"trabajo": tid})

    # ---------- GET: el estado se reconstruye desde los archivos en disco ----------
    if request.args.get("nuevo"):
        borrar_de(d, "organizar_plan.json", "organizar_listo.json",
                  "organizado_por_persona.zip")
    listo = leer_json(os.path.join(d, "organizar_listo.json"))
    if listo and os.path.isfile(os.path.join(d, "organizado_por_persona.zip")):
        return render_template("organizar.html", resumen=listo["personas"],
                               total=listo["total"],
                               n_personas=len(listo["personas"]),
                               fase="listo", zip_listo=True)
    plan = leer_json(os.path.join(d, "organizar_plan.json"))
    if plan:
        return render_template("organizar.html", resumen=plan["personas"],
                               total=plan["total"],
                               n_personas=len(plan["personas"]), fase="revision")
    return render_template("organizar.html", resumen=None)


# ----------------------------------------------------------------------
# Herramienta: separar PDF grande
# ----------------------------------------------------------------------
def _procesar_analisis_pdf(progreso, d, uid, usuario):
    """Hilo: analiza el PDF página por página (OCR solo si no tiene texto)."""
    ruta = os.path.join(d, "grande.pdf")
    if not os.path.isfile(ruta):
        raise ValueError("El PDF ya no está disponible. Súbelo de nuevo.")

    def al_avanzar(i, total):
        progreso(int(i * 95 / total) if total else 95,
                 f"Analizando página {i} de {total}")

    paginas = intel.analizar_pdf_paginas(ruta, progreso=al_avanzar)
    if not paginas:
        raise ValueError("No se pudieron leer las páginas del PDF.")
    progreso(97, "Guardando el análisis...")
    escribir_json(os.path.join(d, "separar_paginas.json"), paginas)
    borrar_de(d, "separados.zip")
    grupos = intel.agrupar_paginas(paginas)
    try:
        db.registrar_actividad(uid, usuario, "separar_analizar",
                               f"{len(paginas)} páginas")
    except Exception:  # noqa: BLE001
        pass
    return {"paginas": len(paginas), "grupos": len(grupos)}


def _procesar_cortes(progreso, d, modo, uid, usuario):
    """Hilo: extrae cada grupo de páginas en su propio PDF y arma el ZIP."""
    ruta = os.path.join(d, "grande.pdf")
    paginas = leer_json(os.path.join(d, "separar_paginas.json"))
    if not os.path.isfile(ruta) or not paginas:
        raise ValueError("Primero analiza un PDF.")
    grupos = intel.agrupar_paginas(paginas)
    destino = os.path.join(d, "separados")
    shutil.rmtree(destino, ignore_errors=True)

    def al_crear(i, total):
        progreso(int(i * 88 / total) if total else 88,
                 f"Extrayendo documento {i} de {total}")

    creados = intel.separar_pdf(ruta, destino, grupos, modo=modo,
                                progreso=al_crear)
    progreso(92, "Comprimiendo el ZIP...")
    zip_de_carpeta(destino, "separados.zip", base=d)
    try:
        db.registrar_actividad(uid, usuario, "separar_pdf",
                               f"{len(creados)} documentos")
    except Exception:  # noqa: BLE001
        pass
    return {"documentos": len(creados)}


@app.route("/herramientas/separar", methods=["GET", "POST"])
@login_required
def herramienta_separar():
    d = trabajo_dir()
    if request.method == "POST":
        accion = request.form.get("accion", "analizar")

        if accion == "analizar":
            archivo = request.files.get("pdf")
            if not archivo or not archivo.filename.lower().endswith(".pdf"):
                if es_ajax():
                    return error_ajax("Sube un archivo PDF.")
                flash("Sube un archivo PDF.", "error")
                return redirect(url_for("herramienta_separar"))
            borrar_de(d, "separar_paginas.json", "separados.zip")
            archivo.save(os.path.join(d, "grande.pdf"))
            tid = trabajos.crear(session["uid"], "Analizando el PDF",
                                 _procesar_analisis_pdf, d, session["uid"],
                                 usuario_actual()["usuario"])
            return jsonify({"trabajo": tid})

        elif accion == "separar":
            modo = request.form.get("modo", "upper")
            if not (os.path.isfile(os.path.join(d, "grande.pdf")) and
                    os.path.isfile(os.path.join(d, "separar_paginas.json"))):
                if es_ajax():
                    return error_ajax("Primero analiza un PDF.")
                flash("Primero analiza un PDF.", "error")
                return redirect(url_for("herramienta_separar"))
            tid = trabajos.crear(session["uid"], "Separando el PDF",
                                 _procesar_cortes, d, modo, session["uid"],
                                 usuario_actual()["usuario"])
            return jsonify({"trabajo": tid})

    # ---------- GET: los resultados se leen de lo que dejó el trabajo ----------
    if request.args.get("nuevo"):
        borrar_de(d, "grande.pdf", "separar_paginas.json", "separados.zip")
    paginas = leer_json(os.path.join(d, "separar_paginas.json"))
    if paginas:
        grupos = intel.agrupar_paginas(paginas)
        return render_template("separar.html", paginas=paginas,
                               grupos=resumen_grupos(grupos),
                               total_pag=len(paginas), analizado=True,
                               zip_listo=os.path.isfile(
                                   os.path.join(d, "separados.zip")))
    return render_template("separar.html", paginas=None, grupos=None,
                           analizado=False, zip_listo=False)


@app.route("/descargas/<nombre>")
@login_required
def descargar(nombre):
    permitidos = {"documentos_clasificados.zip",
                  "organizado_por_persona.zip", "separados.zip"}
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
