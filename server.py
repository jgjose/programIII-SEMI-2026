# -*- coding: utf-8 -*-
"""Parcial II - Programación Computacional III (UGB Usulután)
Servidor Python puro (http.server, sin Flask ni Django) + MySQL (XAMPP)."""
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mysql.connector

CODIGO = "usss007625"
BD = "db_academica"
TABLA = "usuarios_" + CODIGO
CONFIG = {"host": "localhost", "port": 3306, "user": "root", "password": ""}  # XAMPP por defecto
PUERTO = 8000

BASE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(BASE, "web")
SESIONES = {}  # sid -> nombre de usuario


# ---------------------------------------------------------------- Base de datos
def conectar(con_bd=True):
    cfg = dict(CONFIG)
    if con_bd:
        cfg["database"] = BD
    return mysql.connector.connect(**cfg)


def preparar_bd():
    """Crea db_academica, la tabla usuarios_<codigo> y el usuario inicial admin."""
    con = conectar(False)
    cur = con.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS " + BD + " CHARACTER SET utf8mb4")
    cur.execute("USE " + BD)
    cur.execute(
        "CREATE TABLE IF NOT EXISTS " + TABLA + " ("
        " idUsuario INT(10) NOT NULL AUTO_INCREMENT,"
        " usuario CHAR(35) NOT NULL,"
        " clave CHAR(35) NOT NULL,"
        " nombre CHAR(85) NOT NULL,"
        " direccion CHAR(100),"
        " telefono CHAR(9),"
        " PRIMARY KEY (idUsuario)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cur.execute("SELECT idUsuario FROM " + TABLA + " WHERE BINARY usuario=%s", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO " + TABLA + " (usuario, clave, nombre, direccion, telefono) "
            "VALUES (%s,%s,%s,%s,%s)",
            ("admin", CODIGO, "Administrador", "Usulután", "0000-0000"),
        )
    con.commit()
    cur.close()
    con.close()


def autenticar(usuario, clave):
    con = conectar()
    cur = con.cursor()
    cur.execute(
        "SELECT idUsuario FROM " + TABLA + " WHERE BINARY usuario=%s AND BINARY clave=%s LIMIT 1",
        (usuario, clave),
    )
    fila = cur.fetchone()
    cur.close()
    con.close()
    return fila is not None


def crud_usuarios_usss007625(accion, d):
    """Procesa los datos enviados por el cliente. accion: guardar | buscar | eliminar."""
    con = conectar()
    cur = con.cursor(dictionary=True)
    try:
        if accion == "guardar":
            id_ = str(d.get("idUsuario") or "").strip()
            usuario = (d.get("usuario") or "").strip()
            clave = (d.get("clave") or "").strip()
            nombre = (d.get("nombre") or "").strip()
            direccion = (d.get("direccion") or "").strip()
            telefono = (d.get("telefono") or "").strip()

            if not usuario or not clave or not nombre:
                return {"ok": False, "msg": "Usuario, clave y nombre son obligatorios."}
            if len(usuario) > 35 or len(clave) > 35 or len(nombre) > 85 \
                    or len(direccion) > 100 or len(telefono) > 9:
                return {"ok": False, "msg": "Algún campo excede la longitud permitida."}

            cur.execute(
                "SELECT idUsuario FROM " + TABLA + " WHERE BINARY usuario=%s AND idUsuario<>%s",
                (usuario, int(id_) if id_ else 0),
            )
            if cur.fetchone():
                return {"ok": False, "msg": "Ese nombre de usuario ya existe."}

            if id_:
                cur.execute(
                    "UPDATE " + TABLA + " SET usuario=%s, clave=%s, nombre=%s, direccion=%s, "
                    "telefono=%s WHERE idUsuario=%s",
                    (usuario, clave, nombre, direccion, telefono, int(id_)),
                )
                msg = "Usuario modificado correctamente."
            else:
                cur.execute(
                    "INSERT INTO " + TABLA + " (usuario, clave, nombre, direccion, telefono) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (usuario, clave, nombre, direccion, telefono),
                )
                msg = "Usuario registrado correctamente."
            con.commit()
            return {"ok": True, "msg": msg}

        if accion == "buscar":
            t = "%" + (d.get("termino") or "").strip() + "%"
            cur.execute(
                "SELECT idUsuario, usuario, clave, nombre, direccion, telefono FROM " + TABLA +
                " WHERE usuario LIKE %s OR nombre LIKE %s OR direccion LIKE %s OR telefono LIKE %s"
                " ORDER BY idUsuario",
                (t, t, t, t),
            )
            return {"ok": True, "datos": cur.fetchall()}

        if accion == "eliminar":
            cur.execute("DELETE FROM " + TABLA + " WHERE idUsuario=%s", (int(d.get("idUsuario")),))
            con.commit()
            return {"ok": True, "msg": "Usuario eliminado correctamente."}

        return {"ok": False, "msg": "Acción no válida."}
    except Exception as e:
        return {"ok": False, "msg": "Error: " + str(e)}
    finally:
        cur.close()
        con.close()


# ---------------------------------------------------------------- Servidor HTTP
TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "application/javascript; charset=utf-8"}


class Manejador(BaseHTTPRequestHandler):
    def _sid(self):
        for p in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = p.strip().partition("=")
            if k == "sid":
                return v
        return None

    def _autenticado(self):
        return self._sid() in SESIONES

    def _responder(self, codigo, cuerpo, tipo, extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo=200, extra=None):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self._responder(codigo, cuerpo, "application/json; charset=utf-8", extra)

    def _redirigir(self, destino):
        self._responder(302, b"", "text/plain", {"Location": destino})

    def _archivo(self, ruta_rel):
        ruta = os.path.realpath(os.path.join(WEB, ruta_rel))
        if not ruta.startswith(os.path.realpath(WEB)) or not os.path.isfile(ruta):
            return self._responder(404, "No encontrado".encode(), "text/plain; charset=utf-8")
        with open(ruta, "rb") as f:
            self._responder(200, f.read(), TIPOS.get(os.path.splitext(ruta)[1], "application/octet-stream"))

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta in ("/", "/login"):
            return self._archivo("login.html")          # el login es lo primero que se muestra
        if ruta == "/usuarios":
            if not self._autenticado():
                return self._redirigir("/")
            return self._archivo("usuarios.html")
        if ruta.startswith(("/css/", "/js/")):
            return self._archivo(ruta.lstrip("/"))
        self._responder(404, "No encontrado".encode(), "text/plain; charset=utf-8")

    def do_POST(self):
        try:
            largo = int(self.headers.get("Content-Length") or 0)
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except Exception:
            return self._json({"ok": False, "msg": "Solicitud inválida."}, 400)

        if self.path == "/api/login":
            usuario = (datos.get("usuario") or "").strip()
            clave = (datos.get("clave") or "").strip()
            try:
                valido = autenticar(usuario, clave)
            except Exception as e:
                return self._json({"ok": False, "msg": "Error de base de datos: " + str(e)}, 500)
            if not valido:
                return self._json({"ok": False, "msg": "Usuario o clave incorrectos. Acceso denegado."}, 401)
            sid = secrets.token_hex(16)
            SESIONES[sid] = usuario
            return self._json({"ok": True}, 200, {"Set-Cookie": "sid=" + sid + "; Path=/; HttpOnly"})

        if self.path == "/api/logout":
            SESIONES.pop(self._sid(), None)
            return self._json({"ok": True}, 200, {"Set-Cookie": "sid=; Path=/; Max-Age=0"})

        if self.path == "/api/usuarios":
            if not self._autenticado():
                return self._json({"ok": False, "msg": "Sesión no válida."}, 401)
            return self._json(crud_usuarios_usss007625(datos.get("accion"), datos.get("datos") or {}))

        self._json({"ok": False, "msg": "Ruta no encontrada."}, 404)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    preparar_bd()
    print("Base de datos lista. Servidor en http://localhost:%d  (Ctrl+C para detener)" % PUERTO)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador).serve_forever()