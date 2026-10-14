# -*- coding: utf-8 -*-
"""Base de datos de usuarios y actividad (SQLite)."""
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("ORGANIZADOR_DB") or os.path.join(BASE, "organizador.db")


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def inicializar():
    con = conectar()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario   TEXT UNIQUE NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            nombre    TEXT,
            clave     TEXT NOT NULL,
            rol       TEXT NOT NULL DEFAULT 'usuario',
            activo    INTEGER NOT NULL DEFAULT 1,
            creado    TEXT,
            ultimo_acceso TEXT
        );
        CREATE TABLE IF NOT EXISTS actividad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            usuario    TEXT,
            accion     TEXT,
            detalle    TEXT,
            fecha      TEXT
        );
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nombre     TEXT,
            guardado   TEXT,
            tipo       TEXT,
            conf       TEXT,
            tam        INTEGER,
            subido     TEXT
        );
    """)
    con.commit()
    con.close()


def hay_usuarios():
    con = conectar()
    n = con.execute("SELECT COUNT(*) c FROM usuarios").fetchone()["c"]
    con.close()
    return n > 0


def crear_usuario(usuario, email, clave, nombre=None, rol="usuario"):
    con = conectar()
    try:
        con.execute(
            "INSERT INTO usuarios (usuario, email, nombre, clave, rol, activo, creado) "
            "VALUES (?,?,?,?,?,1,?)",
            (usuario.strip(), email.strip().lower(), (nombre or usuario).strip(),
             generate_password_hash(clave), rol, ahora()))
        con.commit()
        uid = con.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario.strip(),)).fetchone()["id"]
        return uid
    except sqlite3.IntegrityError:
        return None
    finally:
        con.close()


def obtener_por_usuario(texto):
    con = conectar()
    fila = con.execute(
        "SELECT * FROM usuarios WHERE usuario=? OR email=?", (texto, texto.lower())).fetchone()
    con.close()
    return fila


def obtener_por_id(uid):
    con = conectar()
    fila = con.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
    con.close()
    return fila


def verificar(texto, clave):
    u = obtener_por_usuario(texto)
    if u and u["activo"] and check_password_hash(u["clave"], clave):
        return u
    return None


def listar_usuarios():
    con = conectar()
    filas = con.execute("SELECT * FROM usuarios ORDER BY rol DESC, usuario").fetchall()
    con.close()
    return filas


def cambiar_clave(uid, nueva):
    con = conectar()
    con.execute("UPDATE usuarios SET clave=? WHERE id=?", (generate_password_hash(nueva), uid))
    con.commit()
    con.close()


def actualizar_perfil(uid, nombre, email):
    con = conectar()
    try:
        con.execute("UPDATE usuarios SET nombre=?, email=? WHERE id=?",
                    (nombre.strip(), email.strip().lower(), uid))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()


def eliminar_usuario(uid):
    con = conectar()
    con.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    con.commit()
    con.close()


def set_rol(uid, rol):
    con = conectar()
    con.execute("UPDATE usuarios SET rol=? WHERE id=?", (rol, uid))
    con.commit()
    con.close()


def set_activo(uid, activo):
    con = conectar()
    con.execute("UPDATE usuarios SET activo=? WHERE id=?", (1 if activo else 0, uid))
    con.commit()
    con.close()


def marcar_acceso(uid):
    con = conectar()
    con.execute("UPDATE usuarios SET ultimo_acceso=? WHERE id=?", (ahora(), uid))
    con.commit()
    con.close()


def contar_admins():
    con = conectar()
    n = con.execute("SELECT COUNT(*) c FROM usuarios WHERE rol='admin'").fetchone()["c"]
    con.close()
    return n


def registrar_actividad(usuario_id, usuario, accion, detalle=""):
    con = conectar()
    con.execute("INSERT INTO actividad (usuario_id, usuario, accion, detalle, fecha) VALUES (?,?,?,?,?)",
                (usuario_id, usuario, accion, detalle, ahora()))
    con.commit()
    con.close()


def actividad_reciente(limite=40):
    con = conectar()
    filas = con.execute(
        "SELECT * FROM actividad ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    con.close()
    return filas


# ----------------------------------------------------------------------
# Documentos privados por usuario
# ----------------------------------------------------------------------
def agregar_documento(usuario_id, nombre, guardado, tipo, conf, tam):
    con = conectar()
    con.execute(
        "INSERT INTO documentos (usuario_id, nombre, guardado, tipo, conf, tam, subido) "
        "VALUES (?,?,?,?,?,?,?)",
        (usuario_id, nombre, guardado, tipo, conf, tam, ahora()))
    con.commit()
    con.close()


def listar_documentos(usuario_id):
    con = conectar()
    filas = con.execute(
        "SELECT * FROM documentos WHERE usuario_id=? ORDER BY id DESC", (usuario_id,)).fetchall()
    con.close()
    return filas


def obtener_documento(doc_id):
    con = conectar()
    fila = con.execute("SELECT * FROM documentos WHERE id=?", (doc_id,)).fetchone()
    con.close()
    return fila


def borrar_documento(doc_id):
    con = conectar()
    fila = con.execute("SELECT * FROM documentos WHERE id=?", (doc_id,)).fetchone()
    con.execute("DELETE FROM documentos WHERE id=?", (doc_id,))
    con.commit()
    con.close()
    return fila


def contar_documentos(usuario_id):
    con = conectar()
    n = con.execute("SELECT COUNT(*) c FROM documentos WHERE usuario_id=?", (usuario_id,)).fetchone()["c"]
    con.close()
    return n
