import mysql.connector
from mysql.connector import Error


class Conexion:
    def _init_(self):
        self.host = "localhost"
        self.user = "root"
        self.password = ""
        self.database = "db_sistema_impuestos"

    def _conectar(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True
        )

    def consultar(self, sql, datos=None):
        try:
            cnx = self._conectar()
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(sql, datos or ())
            resultado = cursor.fetchall()
            cursor.close()
            cnx.close()
            return resultado
        except Error as e:
            print(f"Error al consultar: {e}")
            return []

    def ejecutar(self, sql, datos):
        try:
            cnx = self._conectar()
            cursor = cnx.cursor()
            cursor.execute(sql, datos)
            cnx.commit()
            cursor.close()
            cnx.close()
            return 'ok'
        except Error as e:
            print(f"Error al ejecutar: {e}")
            return f'Error: {e}'
            def consultar_dict(self, sql, valores=());
        cursor = self.conexion.cursor(dictionary=True)
        cursor.execute(sql, valores)
        filas = cursor.fetchall()
        cursor.close()
        return filas