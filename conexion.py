import mysql.connector
from mysql.connector import Error


class Conexion:
    def _conectar(self):
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="nombre_bd"
        )

    def consultar(self, sql, datos=None):
        try:
            cnx = self._conectar()
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(sql, datos)
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

    def consultar_dict(self, sql, valores=()):
        cnx = self._conectar()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute(sql, valores)
        filas = cursor.fetchall()
        cursor.close()
        cnx.close()
        return filas

    def ejecutar_varios(self, operaciones):
        cnx = None
        try:
            cnx = self._conectar()
            cursor = cnx.cursor()
            for sql, datos in operaciones:
                cursor.execute(sql, datos)
            cnx.commit()
            cursor.close()
            cnx.close()
            return 'ok'
        except Error as e:
            if cnx:
                cnx.rollback()
                cnx.close()
            print(f"Error en transacción: {e}")
            return f'Error: {e}'