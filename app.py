# Parcial II - Programacion III | Codigo de estudiante: usss007625
# Sin frameworks: solo libreria estandar de Python + mysql-connector-python
# Ejecutar:  python app.py   ->   http://127.0.0.1:8080
import os, json, hashlib, secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http import cookies
from urllib.parse import urlparse, parse_qs
import mysql.connector

CODIGO = "usss007625"
TABLA = f"usuarios_{CODIGO}"
BD = "db_parcial2"
CFG = dict(host="localhost", port=3306, user="root", password="")
RAIZ = os.path.dirname(os.path.abspath(_file_))
PUBLIC = os.path.join(RAIZ, "public")
SESIONES = {}
MIME = {".html": "text/html", ".css": "text/css", ".js": "application/javascript"}


def cifrar(clave):
    return hashlib.md5(clave.encode("utf-8")).hexdigest()   # 32 caracteres, cabe en char(35)


class Usuarios:
    """Acceso a datos de la tabla usuarios_usss007625."""

    def conectar(self):
        return mysql.connector.connect(database=BD, **CFG)

    def preparar(self):
        # Crea la base de datos, la tabla y el usuario inicial si no existen
        con = mysql.connector.connect(**CFG)
        cur = con.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {BD} CHARACTER SET utf8mb4")
        cur.execute(f"USE {BD}")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {TABLA} (
            idUsuario INT(10) NOT NULL AUTO_INCREMENT,
            usuario   CHAR(35),
            clave     CHAR(35),
            nombre    CHAR(85),
            direccion CHAR(100),
            telefono  CHAR(9),
            PRIMARY KEY (idUsuario))""")
        cur.execute(f"SELECT idUsuario FROM {TABLA} WHERE usuario=%s", ("admin",))
        if cur.fetchone() is None:
            cur.execute(f"INSERT INTO {TABLA} (usuario, clave, nombre, direccion, telefono) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        ("admin", cifrar(CODIGO), "Administrador", "Usulutan", "7777-7777"))
        con.commit()
        cur.close(); con.close()

    def autenticar(self, usuario, clave):
        con = self.conectar()
        try:
            cur = con.cursor()
            cur.execute(f"SELECT idUsuario FROM {TABLA} WHERE usuario=%s AND clave=%s",
                        (usuario, cifrar(clave)))
            return cur.fetchone() is not None
        finally:
            con.close()

    def crud_usuarios_usss007625(self, accion, datos=None, idUsuario=None, q=""):
        """CRUD: listar | crear | actualizar | eliminar"""
        datos = datos or {}
        con = self.conectar()
        try:
            cur = con.cursor(dictionary=True)

            if accion == "listar":
                like = f"%{q.strip()}%"
                cur.execute(f"SELECT idUsuario, usuario, nombre, direccion, telefono FROM {TABLA} "
                            "WHERE usuario LIKE %s OR nombre LIKE %s OR direccion LIKE %s OR telefono LIKE %s "
                            "ORDER BY idUsuario DESC", (like, like, like, like))
                return {"ok": True, "datos": cur.fetchall()}

            if accion == "eliminar":
                cur.execute(f"DELETE FROM {TABLA} WHERE idUsuario=%s", (idUsuario,))
                con.commit()
                return {"ok": True, "msg": "Usuario eliminado"}

            if accion in ("crear", "actualizar"):
                usuario = str(datos.get("usuario", "")).strip()
                clave = str(datos.get("clave", ""))
                nombre = str(datos.get("nombre", "")).strip()
                direccion = str(datos.get("direccion", "")).strip()
                telefono = str(datos.get("telefono", "")).strip()

                if not usuario or not nombre or not direccion or not telefono:
                    return {"ok": False, "msg": "Complete todos los campos"}
                if len(usuario) > 35 or len(nombre) > 85 or len(direccion) > 100 or len(telefono) > 9:
                    return {"ok": False, "msg": "Algun campo supera la longitud permitida"}

                cur.execute(f"SELECT idUsuario FROM {TABLA} WHERE usuario=%s", (usuario,))
                otro = cur.fetchone()
                if otro and str(otro["idUsuario"]) != str(idUsuario or ""):
                    return {"ok": False, "msg": "Ese nombre de usuario ya existe"}

                if accion == "crear":
                    if not clave:
                        return {"ok": False, "msg": "La clave es obligatoria"}
                    cur.execute(f"INSERT INTO {TABLA} (usuario, clave, nombre, direccion, telefono) "
                                "VALUES (%s,%s,%s,%s,%s)",
                                (usuario, cifrar(clave), nombre, direccion, telefono))
                    con.commit()
                    return {"ok": True, "msg": "Usuario registrado correctamente"}

                if clave:
                    cur.execute(f"UPDATE {TABLA} SET usuario=%s, clave=%s, nombre=%s, direccion=%s, telefono=%s "
                                "WHERE idUsuario=%s",
                                (usuario, cifrar(clave), nombre, direccion, telefono, idUsuario))
                else:
                    cur.execute(f"UPDATE {TABLA} SET usuario=%s, nombre=%s, direccion=%s, telefono=%s "
                                "WHERE idUsuario=%s", (usuario, nombre, direccion, telefono, idUsuario))
                con.commit()
                return {"ok": True, "msg": "Usuario actualizado correctamente"}

            return {"ok": False, "msg": "Accion no valida"}
        except mysql.connector.Error as e:
            return {"ok": False, "msg": f"Error de base de datos: {e}"}
        finally:
            con.close()


db = Usuarios()


class Servidor(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def sid(self):
        c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return c["token"].value if "token" in c else None

    def usuario_actual(self):
        return SESIONES.get(self.sid())

    def enviar(self, codigo, cuerpo, tipo="application/json", cabeceras=None):
        datos = cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (cabeceras or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(datos)

    def json(self, obj, codigo=200, cabeceras=None):
        self.enviar(codigo, json.dumps(obj, default=str), cabeceras=cabeceras)

    def ir_a(self, destino):
        self.enviar(302, "", "text/plain", {"Location": destino})

    def pagina(self, nombre):
        ruta = os.path.join(PUBLIC, nombre)
        with open(ruta, "rb") as f:
            self.enviar(200, f.read(), MIME.get(os.path.splitext(nombre)[1], "text/plain"))

    def cuerpo(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n) or "{}")
        except ValueError:
            return {}

    def exigir_sesion(self):
        if not self.usuario_actual():
            self.json({"ok": False, "msg": "Sesion no valida", "login": True}, 401)
            return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        ruta = u.path
        if ruta == "/":
            return self.ir_a("/panel") if self.usuario_actual() else self.pagina("login.html")
        if ruta == "/panel":
            return self.pagina("panel.html") if self.usuario_actual() else self.ir_a("/")
        if ruta == "/api/sesion":
            return self.json({"ok": bool(self.usuario_actual()), "usuario": self.usuario_actual()})
        if ruta == "/api/usuarios":
            if not self.exigir_sesion():
                return
            q = parse_qs(u.query).get("q", [""])[0]
            return self.json(db.crud_usuarios_usss007625("listar", q=q))
        if ruta.startswith("/assets/"):
            nombre = os.path.normpath(ruta[1:]).replace("\\", "/")
            if nombre.startswith("assets/") and os.path.isfile(os.path.join(PUBLIC, nombre)):
                return self.pagina(nombre)
        self.enviar(404, "No encontrado", "text/plain")

    def do_POST(self):
        ruta = urlparse(self.path).path
        d = self.cuerpo()
        if ruta == "/api/login":
            usuario = str(d.get("usuario", "")).strip()
            clave = str(d.get("clave", ""))
            if not usuario or not clave:
                return self.json({"ok": False, "msg": "Escriba su usuario y clave"})
            try:
                valido = db.autenticar(usuario, clave)
            except mysql.connector.Error as e:
                return self.json({"ok": False, "msg": f"Error de base de datos: {e}"})
            if not valido:
                return self.json({"ok": False, "msg": "Acceso denegado: usuario o clave incorrectos"})
            token = secrets.token_hex(24)
            SESIONES[token] = usuario
            return self.json({"ok": True}, cabeceras={"Set-Cookie": f"token={token}; Path=/; HttpOnly"})
        if ruta == "/api/logout":
            SESIONES.pop(self.sid(), None)
            return self.json({"ok": True})
        if ruta == "/api/usuarios":
            if not self.exigir_sesion():
                return
            return self.json(db.crud_usuarios_usss007625("crear", datos=d))
        self.json({"ok": False, "msg": "Ruta no valida"}, 404)

    def do_PUT(self):
        ruta = urlparse(self.path).path
        if ruta.startswith("/api/usuarios/") and self.exigir_sesion():
            ident = ruta.rsplit("/", 1)[1]
            return self.json(db.crud_usuarios_usss007625("actualizar", datos=self.cuerpo(), idUsuario=ident))

    def do_DELETE(self):
        ruta = urlparse(self.path).path
        if ruta.startswith("/api/usuarios/") and self.exigir_sesion():
            ident = ruta.rsplit("/", 1)[1]
            return self.json(db.crud_usuarios_usss007625("eliminar", idUsuario=ident))


if _name_ == "_main_":
    try:
        db.preparar()
    except mysql.connector.Error as e:
        print("No se pudo conectar a MySQL. Encienda MySQL en XAMPP.\n", e)
        raise SystemExit(1)
    print("Servidor listo en http://127.0.0.1:8080   (Ctrl+C para detener)")
    print(f"Ingrese con -> Usuario: admin | Clave: {CODIGO}")
    ThreadingHTTPServer(("127.0.0.1", 8080), Servidor).serve_forever()