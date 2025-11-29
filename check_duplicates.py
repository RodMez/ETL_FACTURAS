import os
import csv

# PDFs en carpeta
pdfs = sorted([f for f in os.listdir('Facturas') if f.lower().endswith('.pdf')])
print(f"PDFs en carpeta Facturas: {len(pdfs)}")
for p in pdfs:
    print(f"  {p}")

print("\n" + "="*60)

# Facturas en CSV
with open('Facturas/datos_generales.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    csv_files = [row['filename'] for row in reader if row['filename']]

print(f"\nFacturas en datos_generales.csv: {len(csv_files)}")
for f in csv_files:
    print(f"  {f}")

print("\n" + "="*60)

# Analizar normalización
print("\nAnálisis de normalización (últimos 7 caracteres):")
normalized_map = {}
for filename in csv_files:
    base_name = filename.rsplit('.', 1)[0]
    norm_key = base_name[-7:]
    
    if norm_key not in normalized_map:
        normalized_map[norm_key] = []
    normalized_map[norm_key].append(filename)

print(f"\nFilenames únicos normalizados: {len(normalized_map)}")
for norm, files in sorted(normalized_map.items()):
    if len(files) > 1:
        print(f"\n⚠️  '{norm}' -> {len(files)} archivos (DUPLICADOS):")
        for f in files:
            print(f"      - {f}")
    else:
        print(f"✓ '{norm}' -> {files[0]}")

dup_count = sum(1 for files in normalized_map.values() if len(files) > 1)
print(f"\n{'='*60}")
print(f"Resumen:")
print(f"  PDFs en carpeta: {len(pdfs)}")
print(f"  Facturas en CSV: {len(csv_files)}")
print(f"  Claves normalizadas únicas: {len(normalized_map)}")
print(f"  Grupos con duplicados: {dup_count}")
