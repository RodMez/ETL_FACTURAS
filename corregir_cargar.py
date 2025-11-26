import csv
import datetime
from dotenv import load_dotenv
from conexion import *  

# Cargar variables de entorno desde .env
load_dotenv()

# Crear conexión y tablas antes de procesar
conn = create_connection()
print("Creando tablas en la base de datos...")
init_tables(conn)
print("Tablas creadas exitosamente!")

def process_generales(conn, file_path):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_filename = row['filename']
            base_name = original_filename.rsplit('.', 1)[0]
            new_filename = base_name[-7:]
            # Update filename in row
            row['filename'] = new_filename
            
            # Limitar nombre a solo 2 palabras
            nombre_completo = row['Nombre']
            palabras = nombre_completo.split()
            if len(palabras) > 2:
                nombre_corto = ' '.join(palabras[:2])
            else:
                nombre_corto = nombre_completo
            
            # Insert into Facturas using conexion.py's functions
            factura_id = insert_factura(conn, row['filename'], nombre_corto, datetime.datetime.strptime(row['Fecha'], '%d/%m/%Y').strftime('%Y-%m-%d'), row['Gas'], row['credito'], row['Total'], row['Consumo_m3'])
            print(f"Insertada factura {factura_id} con filename {new_filename} y nombre {nombre_corto}")

def process_especificos(conn, file_path):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row['Concepto'].strip():
                continue
            original_filename = row['filename']
            base_name = original_filename.rsplit('.', 1)[0]
            new_filename = base_name[-7:]
            row['filename'] = new_filename
            
            # Buscar el ID de la factura correspondiente
            factura_id = get_factura_id_by_filename(conn, new_filename)
            if factura_id:
                insert_detalles(conn, factura_id, row['Concepto'], row['ValorPagar'])
                print(f"Insertado detalle para factura {factura_id}: {row['Concepto']}")
            else:
                print(f"No se encontró factura con filename {new_filename}")

# Run processing
process_generales(conn, 'Facturas/datos_generales.csv')
process_especificos(conn, 'Facturas/datos_especificos.csv')