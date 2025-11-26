"""main.py (formerly agregar_facturas.py)

Monitorea la carpeta `Facturas` y, al detectar PDFs nuevos, regenera
`resultado.txt` y actualiza los CSVs `facturas.csv` y
`facturas_especificas.csv` llamando a las funciones existentes.

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


def load_processed() -> set:
    """Carga nombres de archivos ya procesados desde `facturas.csv` (si existe)."""
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

        # Cargar a la base de datos
        print(f"[{time.ctime()}] Iniciando carga a base de datos...")
        try:
            conn = create_connection()
            init_tables(conn) # Asegurar que las tablas existan
            process_generales(conn, os.path.join(CARPETA_FACTURAS, CSV_GENERAL))
            process_especificos(conn, os.path.join(CARPETA_FACTURAS, CSV_ESPECIFICO))
            conn.close()
            print(f"[{time.ctime()}] Carga a base de datos completada.")
        except Exception as db_err:
            print(f"[{time.ctime()}] Error cargando a base de datos: {db_err}")

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

    if args.once:
        detectar_nuevas_facturas_once()
    else:
        print(f"[{time.ctime()}] Iniciando monitoreo de facturas en {CARPETA_FACTURAS}...")
        detectar_nuevas_facturas_loop(interval=args.interval)


if __name__ == '__main__':
    main()