"""main.py (formerly agregar_facturas.py)

Monitorea la carpeta `Facturas` y, al detectar PDFs nuevos, regenera
`resultado.txt` y actualiza los CSVs `datos_generales.csv` y
`datos_especificos.csv` llamando a las funciones existentes.

OPTIMIZADO: Solo carga a la BD las facturas que no existen, comparando
los filenames normalizados entre la BD y el CSV.

Incluye un modo `--once` para ejecutar una sola iteración (útil para pruebas).
"""

import os
import time
import csv
import argparse
from analisis_general import leer_pdfs_y_guardar_txt, parse_resultado_y_guardar_csv
from analisis_especifico import parse_resultado_y_guardar_especifico
from corregir_cargar import create_connection, init_tables, process_generales, process_especificos


# Directorio y nombres
CARPETA_FACTURAS = 'Facturas'
RESULTADO_NOMBRE = 'resultado.txt'
CSV_GENERAL = 'datos_generales.csv'
CSV_ESPECIFICO = 'datos_especificos.csv'


def asegurar_csvs_existen() -> None:
    """Asegura que los CSVs existan. Si no existen, los crea ejecutando el proceso de extracción."""
    csv_gral = os.path.join(CARPETA_FACTURAS, CSV_GENERAL)
    csv_esp = os.path.join(CARPETA_FACTURAS, CSV_ESPECIFICO)
    
    # Si ambos CSVs existen, no hacer nada
    if os.path.exists(csv_gral) and os.path.exists(csv_esp):
        print(f"[{time.ctime()}] CSVs ya existen, continuando...")
        return
    
    print(f"[{time.ctime()}] CSVs no encontrados, creándolos...")
    
    try:
        # Extraer texto de todos los PDFs de la carpeta
        ruta_txt = leer_pdfs_y_guardar_txt(CARPETA_FACTURAS, salida_nombre=RESULTADO_NOMBRE)
        
        # Generar CSV general y específico
        csv_g = parse_resultado_y_guardar_csv(CARPETA_FACTURAS, txt_nombre=RESULTADO_NOMBRE, csv_nombre=CSV_GENERAL)
        csv_e = parse_resultado_y_guardar_especifico(CARPETA_FACTURAS, txt_nombre=RESULTADO_NOMBRE, csv_nombre=CSV_ESPECIFICO)
        
        print(f"[{time.ctime()}] ✓ CSVs creados: {csv_g}, {csv_e}")
    except Exception as e:
        print(f"[{time.ctime()}] Error al crear CSVs: {e}")
        raise


def load_processed() -> set:
    """Carga nombres de archivos ya procesados desde `datos_generales.csv` (si existe)."""
    s = set()
    p = os.path.join(CARPETA_FACTURAS, CSV_GENERAL)
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    fn = r.get('filename')
                    if fn:
                        s.add(fn)
        except Exception:
            pass
    return s


def cargar_datos_existentes_a_bd() -> None:
    """Carga a la BD solo las facturas nuevas que no existen en la BD.
    
    OPTIMIZADO: Usa las funciones optimizadas de process_generales y 
    process_especificos que filtran antes de intentar cargar.
    """
    print(f"\n[{time.ctime()}] === Iniciando carga optimizada a base de datos ===")
    try:
        conn = create_connection()
        init_tables(conn) # Asegurar que las tablas existan
        
        csv_gral = os.path.join(CARPETA_FACTURAS, CSV_GENERAL)
        csv_esp = os.path.join(CARPETA_FACTURAS, CSV_ESPECIFICO)

        if os.path.exists(csv_gral):
            print(f"[{time.ctime()}] Procesando datos generales...")
            process_generales(conn, csv_gral)
        else:
            print(f"[{time.ctime()}] ADVERTENCIA: {CSV_GENERAL} no encontrado")
        
        if os.path.exists(csv_esp):
            print(f"[{time.ctime()}] Procesando datos específicos...")
            process_especificos(conn, csv_esp)
        else:
            print(f"[{time.ctime()}] ADVERTENCIA: {CSV_ESPECIFICO} no encontrado")
            
        conn.close()
        print(f"[{time.ctime()}] === Carga a base de datos completada ===\n")
    except Exception as db_err:
        print(f"[{time.ctime()}] ERROR cargando a base de datos: {db_err}")


def procesar_y_actualizar(nuevos_archivos: list) -> None:
    """Regenera `resultado.txt` y los CSVs para la carpeta `Facturas`.

    Esta estrategia regenera los CSVs completos (sobrescribe), que es más
    robusta frente a variaciones de extracción. Después marca como procesados
    los archivos en `nuevos_archivos`.
    """
    try:
        # Extraer texto de todos los PDFs de la carpeta y escribir resultado.txt
        ruta_txt = leer_pdfs_y_guardar_txt(CARPETA_FACTURAS, salida_nombre=RESULTADO_NOMBRE)

        # Generar CSV general y específico usando el resultado recién creado
        csv_g = parse_resultado_y_guardar_csv(CARPETA_FACTURAS, txt_nombre=RESULTADO_NOMBRE, csv_nombre=CSV_GENERAL)
        csv_e = parse_resultado_y_guardar_especifico(CARPETA_FACTURAS, txt_nombre=RESULTADO_NOMBRE, csv_nombre=CSV_ESPECIFICO)

        print(f"[{time.ctime()}] CSVs actualizados: {csv_g}, {csv_e}")

        # Cargar a la base de datos (solo las facturas nuevas)
        cargar_datos_existentes_a_bd()

    except Exception as e:
        print(f"[{time.ctime()}] Error al regenerar CSVs: {e}")


def detectar_nuevas_facturas_loop(interval: int = 30):
    ARCHIVOS_PROCESADOS = load_processed()
    print(f"[{time.ctime()}] Procesados inicialmente: {len(ARCHIVOS_PROCESADOS)} archivos")

    while True:
        archivos_pdf = [f for f in os.listdir(CARPETA_FACTURAS) if f.lower().endswith('.pdf')]
        nuevos = [f for f in archivos_pdf if f not in ARCHIVOS_PROCESADOS]

        if nuevos:
            print(f"[{time.ctime()}] Se detectaron {len(nuevos)} facturas nuevas: {nuevos}")
            procesar_y_actualizar(nuevos)
            # marcar todos los PDFs actuales como procesados para no repetir
            ARCHIVOS_PROCESADOS.update(archivos_pdf)

        time.sleep(interval)


def detectar_nuevas_facturas_once() -> None:
    """Una única iteración: detecta nuevos PDFs, procesa y sale (útil para pruebas)."""
    ARCHIVOS_PROCESADOS = load_processed()
    archivos_pdf = [f for f in os.listdir(CARPETA_FACTURAS) if f.lower().endswith('.pdf')]
    nuevos = [f for f in archivos_pdf if f not in ARCHIVOS_PROCESADOS]

    if nuevos:
        print(f"[{time.ctime()}] Se detectaron {len(nuevos)} facturas nuevas: {nuevos}")
        procesar_y_actualizar(nuevos)
    else:
        print(f"[{time.ctime()}] No hay facturas nuevas. Procesados: {len(ARCHIVOS_PROCESADOS)}")


def main():
    parser = argparse.ArgumentParser(description='Monitorea carpeta Facturas y actualiza CSVs')
    parser.add_argument('--once', action='store_true', help='Ejecutar una sola iteración y salir')
    parser.add_argument('--interval', type=int, default=30, help='Intervalo en segundos para el modo loop')
    args = parser.parse_args()

    if not os.path.isdir(CARPETA_FACTURAS):
        print(f"Carpeta no encontrada: {CARPETA_FACTURAS}")
        return

    # ASEGURAR que los CSVs existan antes de arrancar
    # Si no existen, los crea automáticamente
    asegurar_csvs_existen()

    # SIEMPRE intentar cargar lo que ya exista en los CSVs al arrancar
    # Esto cubre el caso de que existan CSVs pero la BD esté vacía o desactualizada
    # La función optimizada solo cargará las facturas que faltan en la BD
    cargar_datos_existentes_a_bd()

    if args.once:
        detectar_nuevas_facturas_once()
    else:
        print(f"[{time.ctime()}] Iniciando monitoreo de facturas en {CARPETA_FACTURAS}...")
        detectar_nuevas_facturas_loop(interval=args.interval)


if __name__ == '__main__':
    main()