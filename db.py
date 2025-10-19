import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "BaguiraLluvia23",        # pon tu contraseña si tienes
    "database": "gestion_matricula",
    "port": 3306
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print("ERROR: No se pudo conectar a la BD:", e)
        raise
