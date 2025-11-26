import mysql.connector
import os
from dotenv import load_dotenv
import subprocess
import sys

load_dotenv()

def get_counts():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Facturas")
    facturas_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Detalles")
    detalles_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return facturas_count, detalles_count

def run_etl():
    print("Running ETL script...")
    result = subprocess.run([sys.executable, "corregir_cargar.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode

def main():
    print("Initial counts:")
    f1, d1 = get_counts()
    print(f"Facturas: {f1}, Detalles: {d1}")

    print("\n--- First Run ---")
    if run_etl() != 0:
        print("ETL failed!")
        return

    print("Counts after first run:")
    f2, d2 = get_counts()
    print(f"Facturas: {f2}, Detalles: {d2}")

    print("\n--- Second Run (Idempotency Check) ---")
    if run_etl() != 0:
        print("ETL failed!")
        return

    print("Counts after second run:")
    f3, d3 = get_counts()
    print(f"Facturas: {f3}, Detalles: {d3}")

    if f2 == f3 and d2 == d3:
        print("\nSUCCESS: Counts remained the same. Idempotency verified.")
    else:
        print("\nFAILURE: Counts changed between runs.")

if __name__ == "__main__":
    main()
