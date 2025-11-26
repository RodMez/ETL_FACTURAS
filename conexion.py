import mysql.connector
import os

def create_connection():
    # Cargar variables de entorno (requiere archivo .env)
    host = os.getenv('DB_HOST')
    database = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    if not all([host, database, user, password]):
        raise ValueError("Faltan variables de entorno. Por favor, configura el archivo .env")
    
    connection = mysql.connector.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )
    return connection

def create_tables(conn):
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS Facturas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(50),
            nombre VARCHAR(255),
            fecha DATE,
            gas DECIMAL(10,2),
            credito DECIMAL(10,2),
            total DECIMAL(10,2),
            consumo_m3 DECIMAL(10,2)
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS Detalles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            factura_id INT,
            concepto VARCHAR(255),
            valor_pagar DECIMAL(10,2),
            FOREIGN KEY(factura_id) REFERENCES Facturas(id)
        )""")
        conn.commit()
    finally:
        cursor.close()

def init_tables(conn):
    create_tables(conn)

def insert_factura(conn, filename, nombre, fecha, gas, credito, total, consumo_m3):
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("INSERT INTO Facturas VALUES (NULL, %s, %s, %s, %s, %s, %s, %s)",
                       (filename, nombre, fecha, gas, credito, total, consumo_m3))
        factura_id = cursor.lastrowid
        conn.commit()
        return factura_id
    finally:
        cursor.close()

def insert_detalles(conn, factura_id, concepto, valor_pagar):
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("INSERT INTO Detalles VALUES (NULL, %s, %s, %s)",
                       (factura_id, concepto, valor_pagar))
        conn.commit()
    finally:
        cursor.close()

def get_factura_id_by_filename(conn, filename):
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("SELECT id FROM Facturas WHERE filename = %s", (filename,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()

def check_detalle_exists(conn, factura_id, concepto, valor_pagar):
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute("SELECT id FROM Detalles WHERE factura_id = %s AND concepto = %s AND valor_pagar = %s", 
                       (factura_id, concepto, valor_pagar))
        result = cursor.fetchone()
        return result is not None
    finally:
        cursor.close()