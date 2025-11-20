import os
import re
import csv


def parse_resultado_y_guardar_especifico(prueba_path: str = 'Facturas', txt_nombre: str = 'resultado.txt', csv_nombre: str = 'facturas_especificas.csv') -> str:
    """Lee `prueba_path/txt_nombre`, extrae los ítems (desde la línea 9 de cada factura)
    y escribe un CSV con columnas: `filename, ID, Concepto, ValorPagar`.

    Es heurístico: detecta líneas que comienzan con un índice seguido de un ID
    y dos o más montos; toma el segundo monto como `ValorPagar`.
    """
    txt_path = os.path.join(prueba_path, txt_nombre)
    csv_path = os.path.join(prueba_path, csv_nombre)

    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"No existe el archivo de texto: {txt_path}")

    with open(txt_path, 'r', encoding='utf-8') as f:
        full = f.read()

    # separar bloques por separadores ----- filename -----
    matches = list(re.finditer(r'^-----\s*(.+?)\s*-----\s*$', full, flags=re.MULTILINE))
    if not matches:
        blocks = [(None, full)]
    else:
        blocks = []
        for i, m in enumerate(matches):
            name = m.group(1).strip()
            start = m.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(full)
            block = full[start:end].strip()
            blocks.append((name, block))

    # regex tentativa para línea de item: índice (1-2 dígitos), ID (3-4 dígitos o 'N'), concepto..., valorF, ValorPagar, pendiente (opcional)
    # restringimos el ID para evitar capturar líneas no relacionadas (ej. índices muy grandes o montos)
    item_re = re.compile(r'^\s*(\d{1,2})\s+([0-9]{3,4}|N)\s+(.+?)\s+([0-9\.,-]+)\s+([0-9\.,-]+)(?:\s+([0-9\.,-]+))?', re.I)

    rows = []
    for filename, block in blocks:
        lines = [ln.rstrip() for ln in block.splitlines() if ln.strip() != '']

        # Buscar el inicio de los ítems: la primera línea que comienza con '1 ' seguido de algo
        start_idx = None
        for i, ln in enumerate(lines):
            if re.match(r'^\s*1\s+\S+', ln):
                start_idx = i
                break

        # Si no encontramos '1 ...', usar heurística alternativa: buscar primera línea que contenga patrón de ítem (índice seguido de ID)
        if start_idx is None:
            for i, ln in enumerate(lines):
                if re.match(r'^\s*\d+\s+\S+', ln):
                    start_idx = i
                    break

        # Si aún no hay start_idx, fallback: empezar desde 0
        if start_idx is None:
            start_idx = 0

        for ln in lines[start_idx:]:
            # detenerse cuando la línea ya no parece un ítem (no comienza por número índice de 1-2 dígitos)
            if not re.match(r'^\s*\d{1,2}\s+', ln):
                break
            ln_strip = ln.strip()
            if not ln_strip:
                continue

            m = item_re.match(ln_strip)
            if m:
                # evitar índices absurdamente grandes (p.ej. 2005 que no son ítems)
                try:
                    idx_val = int(m.group(1))
                    if idx_val > 99:
                        break
                except Exception:
                    pass
                # grupos: m.group(2)=ID (puede ser N), concepto aproximado en group(3)
                id_ = m.group(2).strip()

                # Construir resto de la línea después de índice e ID para localizar montos
                # eliminar el prefijo "<idx> <id> "
                prefix_re = re.compile(r'^\s*' + re.escape(m.group(1)) + r'\s+' + re.escape(m.group(2)))
                rest = prefix_re.sub('', ln_strip, count=1).strip()

                # encontrar todos los tokens numéricos en rest (montos y cantidades)
                num_tokens = re.findall(r'-?[0-9][0-9\.,]*', rest)

                # Concepto: texto antes del primer número en rest
                concepto = ''
                first_num_match = re.search(r'-?[0-9][0-9\.,]*', rest)
                if first_num_match:
                    concepto = rest[:first_num_match.start()].strip()
                else:
                    # fallback a group(3)
                    concepto = (m.group(3) or '').strip()

                # Determinar ValorPagar: preferir segundo número si existe (valorF, ValorPagar).
                # Si el segundo es 0 pero el primero es distinto de 0 (p.ej. subsidio -36,156 0),
                # usar el absoluto del primero (36,156). Si no hay números, '0'.
                valorp_raw = '0'
                if len(num_tokens) >= 2:
                    # tomar segundo por defecto
                    valorp_raw = num_tokens[1]
                    # si segundo es cero pero primero no, usar absoluto del primero
                    first_clean = re.sub(r'[^0-9]', '', num_tokens[0]) if num_tokens[0] else ''
                    second_clean = re.sub(r'[^0-9]', '', valorp_raw) if valorp_raw else ''
                    if (second_clean == '' or int(second_clean or 0) == 0) and first_clean and int(first_clean) != 0:
                        # usar absoluto del primer token (elimina signo)
                        valorp_raw = num_tokens[0]
                elif len(num_tokens) == 1:
                    valorp_raw = num_tokens[0]

                # normalizar valor: eliminar puntos, comas y signos; tomar absoluto
                valorp_clean = re.sub(r'[^0-9]', '', valorp_raw)
                if valorp_clean == '':
                    valorp_clean = '0'

                rows.append({'filename': filename or '', 'ID': id_, 'Concepto': concepto, 'ValorPagar': valorp_clean})
                continue

            # Si no matchea, intentar heurística alternativa:
            parts = ln_strip.split()
            if len(parts) >= 6 and parts[0].isdigit() and parts[1].isdigit():
                # buscar tokens que parezcan montos (contienen dígitos y , o .)
                amount_positions = [i for i, t in enumerate(parts) if re.search(r'[0-9][\.,]?[0-9]', t)]
                if len(amount_positions) >= 2:
                    # ID está en parts[1]
                    id_ = parts[1]
                    # concepto: desde parts[2] hasta antes de primer monto
                    first_amt_pos = amount_positions[0]
                    concepto = ' '.join(parts[2:first_amt_pos])
                    # valor a pagar: segundo monto
                    valorp = parts[amount_positions[1]]
                    valorp_clean = re.sub(r'[^0-9]', '', valorp)
                    rows.append({'filename': filename or '', 'ID': id_, 'Concepto': concepto, 'ValorPagar': valorp_clean})
                    continue

            # si se llega aquí, la línea no parece ser un item; continuar

    # escribir CSV
    fieldnames = ['filename', 'ID', 'Concepto', 'ValorPagar']
    with open(csv_path, 'w', encoding='utf-8', newline='') as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return csv_path


if __name__ == '__main__':
    try:
        ruta = parse_resultado_y_guardar_especifico('Facturas')
        print(f"CSV específico generado en: {ruta}")
    except Exception as e:
        print(f"Error: {e}")
