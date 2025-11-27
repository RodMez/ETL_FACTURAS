import csv
import datetime
from dotenv import load_dotenv
from conexion import *  

# Cargar variables de entorno desde .env
load_dotenv()


def process_generales(conn, file_path):
    """Procesa el CSV de datos generales y carga solo las facturas nuevas a la BD.
    
    Optimizado: Obtiene todos los filenames de la BD una sola vez y filtra
    el CSV para procesar solo las facturas que no existen en la BD.
    """
    # Obtener todos los filenames existentes en la BD (1 sola consulta)
    existing_filenames = get_all_filenames(conn)
    print(f"Facturas existentes en BD: {len(existing_filenames)}")
    
    facturas_procesadas = 0
    facturas_nuevas = 0
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_filename = row['filename']
            base_name = original_filename.rsplit('.', 1)[0]
            new_filename = base_name[-7:]
            
            # Si la factura ya existe en la BD, saltarla
            if new_filename in existing_filenames:
                facturas_procesadas += 1
                continue
            
            # Limitar nombre a solo 2 palabras
            nombre_completo = row['Nombre']
            palabras = nombre_completo.split()
            if len(palabras) > 2:
                nombre_corto = ' '.join(palabras[:2])
            else:
                nombre_corto = nombre_completo
            
            # Insertar factura nueva
            factura_id = insert_factura(
                conn, 
                new_filename, 
                nombre_corto, 
                datetime.datetime.strptime(row['Fecha'], '%d/%m/%Y').strftime('%Y-%m-%d'), 
                row['Gas'], 
                row['credito'], 
                row['Total'], 
                row['Consumo_m3']
            )
            print(f"✓ Insertada factura {factura_id} - {new_filename} ({nombre_corto})")
            facturas_nuevas += 1
    
    print(f"\n--- Resumen process_generales ---")
    print(f"Facturas ya existentes (saltadas): {facturas_procesadas}")
    print(f"Facturas nuevas insertadas: {facturas_nuevas}")


def process_especificos(conn, file_path):
    """Procesa el CSV de datos específicos y carga solo los detalles de facturas nuevas.
    
    Optimizado: Primero filtra para procesar solo detalles de facturas que
    existen en la BD, evitando consultas innecesarias.
    """
    # Obtener todos los filenames existentes en la BD
    existing_filenames = get_all_filenames(conn)
    
    # Crear diccionario para evitar consultas repetidas de factura_id
    filename_to_id = {}
    
    detalles_procesados = 0
    detalles_nuevos = 0
    detalles_saltados = 0
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Saltar filas vacías
            if not row['Concepto'].strip():
                continue
            
            original_filename = row['filename']
            base_name = original_filename.rsplit('.', 1)[0]
            new_filename = base_name[-7:]
            
            # Si la factura no existe en la BD, saltar este detalle
            if new_filename not in existing_filenames:
                detalles_saltados += 1
                continue
            
            # Obtener factura_id (usar caché para evitar consultas repetidas)
            if new_filename not in filename_to_id:
                factura_id = get_factura_id_by_filename(conn, new_filename)
                if factura_id:
                    filename_to_id[new_filename] = factura_id
                else:
                    detalles_saltados += 1
                    continue
            else:
                factura_id = filename_to_id[new_filename]
            
            # Verificar si el detalle ya existe
            if check_detalle_exists(conn, factura_id, row['Concepto'], row['ValorPagar']):
                detalles_procesados += 1
            else:
                insert_detalles(conn, factura_id, row['Concepto'], row['ValorPagar'])
                print(f"✓ Insertado detalle para factura {factura_id}: {row['Concepto']}")
                detalles_nuevos += 1
    
    print(f"\n--- Resumen process_especificos ---")
    print(f"Detalles ya existentes (saltados): {detalles_procesados}")
    print(f"Detalles nuevos insertados: {detalles_nuevos}")
    print(f"Detalles sin factura asociada (saltados): {detalles_saltados}")


def main():
    # Crear conexión y tablas antes de procesar
    conn = create_connection()
    print("Creando tablas en la base de datos...")
    init_tables(conn)
    print("Tablas creadas exitosamente!\n")

    # Run processing
    print("=== Procesando datos generales ===")
    process_generales(conn, 'Facturas/datos_generales.csv')
    
    print("\n=== Procesando datos específicos ===")
    process_especificos(conn, 'Facturas/datos_especificos.csv')
    
    conn.close()
    print("\n✓ Proceso completado exitosamente!")

if __name__ == "__main__":
    main()