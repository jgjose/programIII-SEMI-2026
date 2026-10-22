from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pymysql, hashlib

app = Flask(__name__)
app.secret_key = "clave_secreta_parcial"


TABLA = "usuarios_usss7625"


def conexion():
    return pymysql.connect(host="localhost", user="root", password="",
                           database="db_academica", charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor)

def md5(txt):
    return hashlib.md5(txt.encode()).hexdigest()


@app.route("/")
def inicio():
    if "usuario" in session:
        return redirect(url_for("usuarios"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    d = request.get_json()
    con = conexion()
    try:
        with con.cursor() as cur:
            cur.execute(f"SELECT * FROM {TABLA} WHERE usuario=%s AND clave=%s",
                        (d["usuario"], md5(d["clave"])))
            u = cur.fetchone()
    finally:
        con.close()
    if u:
        session["usuario"] = u["usuario"]
        return jsonify(ok=True)
    return jsonify(ok=False, msg="Usuario o clave incorrectos. Acceso denegado.")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("inicio"))


@app.route("/usuarios")
def usuarios():
    if "usuario" not in session:
        return redirect(url_for("inicio"))
    return render_template("usuarios.html", activo=session["usuario"])


@app.route("/crud_usuarios_usss7625", methods=["POST"])
def crud_usuarios_usss7625():
    if "usuario" not in session:
        return jsonify(ok=False, msg="No autorizado")
    d = request.get_json()
    accion = d.get("accion")
    con = conexion()
    try:
        with con.cursor() as cur:
            if accion == "nuevo":
                cur.execute(f"INSERT INTO {TABLA} (usuario,clave,nombre,direccion,telefono) VALUES (%s,%s,%s,%s,%s)",
                            (d["usuario"], md5(d["clave"]), d["nombre"], d["direccion"], d["telefono"]))
                msg = "Usuario registrado correctamente"
            elif accion == "modificar":
                if d.get("clave"):   
                    cur.execute(f"UPDATE {TABLA} SET usuario=%s,clave=%s,nombre=%s,direccion=%s,telefono=%s WHERE idUsuario=%s",
                                (d["usuario"], md5(d["clave"]), d["nombre"], d["direccion"], d["telefono"], d["idUsuario"]))
                else:
                    cur.execute(f"UPDATE {TABLA} SET usuario=%s,nombre=%s,direccion=%s,telefono=%s WHERE idUsuario=%s",
                                (d["usuario"], d["nombre"], d["direccion"], d["telefono"], d["idUsuario"]))
                msg = "Usuario modificado correctamente"
            elif accion == "eliminar":
                cur.execute(f"DELETE FROM {TABLA} WHERE idUsuario=%s", (d["idUsuario"],))
                msg = "Usuario eliminado correctamente"
            elif accion == "buscar":
                like = f"%{d.get('valor','')}%"
                cur.execute(f"SELECT idUsuario,usuario,nombre,direccion,telefono FROM {TABLA} "
                            "WHERE usuario LIKE %s OR nombre LIKE %s OR telefono LIKE %s ORDER BY idUsuario",
                            (like, like, like))
                return jsonify(ok=True, datos=cur.fetchall())
            else:
                return jsonify(ok=False, msg="Acción no válida")
        con.commit()
        return jsonify(ok=True, msg=msg)
    except Exception as e:
        return jsonify(ok=False, msg=str(e))
    finally:
        con.close()

if __name__ == "__main__":
    app.run(debug=True)
