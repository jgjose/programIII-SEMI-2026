from mysql.connector.errors import Error
import conexion

db = conexion.Conexion()


class crud_clientes:
    def consultar(self, buscar):
        sql = "SELECT * FROM clientes WHERE nombre LIKE %s OR codigo LIKE %s"
        patron = f"%{buscar}%"
        return db.consultar(sql, (patron, patron))

    def administrar(self, datos):
        try:
            if datos['accion'] == 'nuevo':
                sql = """
                    INSERT INTO clientes(codigo,nombre,direccion,telefono,email,tipo)
                    VALUES(%s,%s,%s,%s,%s,%s)
                """
                valores = (datos['codigo'], datos['nombre'], datos['direccion'],
                           datos['telefono'], datos['email'], datos['tipo'])
            elif datos['accion'] == 'modificar':
                sql = """
                    UPDATE clientes SET codigo=%s,nombre=%s,direccion=%s,telefono=%s,email=%s,tipo=%s
                    WHERE idCliente=%s
                """
                valores = (datos['codigo'], datos['nombre'], datos['direccion'],
                           datos['telefono'], datos['email'], datos['tipo'], datos['idCliente'])
            else:
                sql = """
                    DELETE FROM clientes WHERE idCliente=%s
                """
                valores = (datos['idCliente'],)
            return db.ejecutar(sql, valores)
        except Error as e:
            return f"Error al guardar el cliente: {e}"