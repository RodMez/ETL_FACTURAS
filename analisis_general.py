import os
from typing import Optional


def leer_pdfs_y_guardar_txt(prueba_path: str = 'Facturas', salida_nombre: str = 'resultado.txt') -> str:
	"""Recorre la carpeta `prueba_path`, extrae texto de cada archivo PDF y guarda
	la salida concatenada en `<prueba_path>/<salida_nombre>`.

	Retorna la ruta del archivo generado.
	"""
	# Buscar archivos PDF (extensiones .pdf, mayúsc/minúsc)
	if not os.path.isdir(prueba_path):
		raise FileNotFoundError(f"La carpeta especificada no existe: {prueba_path}")

	pdf_files = [f for f in os.listdir(prueba_path) if f.lower().endswith('.pdf')]
	salida_path = os.path.join(prueba_path, salida_nombre)
	# Usaremos únicamente `pypdf` (PdfReader) de forma minimalista
	try:
		from pypdf import PdfReader

		def extractor(path: str) -> str:
			texts = []
			reader = PdfReader(path)
			for page in reader.pages:
				try:
					t = page.extract_text() or ''
				except Exception:
					t = ''
				texts.append(t)
			return "\n".join(texts)
	except Exception as e:
		# Si no está instalada, dejar extractor como None y se escribirá un error en el archivo
		extractor = None

	# Abrir archivo de salida y escribir resultados
	with open(salida_path, 'w', encoding='utf-8') as out_f:
		if not pdf_files:
			out_f.write(f"No se encontraron archivos PDF en '{prueba_path}'.\n")
			return salida_path

		for pdf_file in sorted(pdf_files):
			ruta = os.path.join(prueba_path, pdf_file)
			out_f.write(f"----- {pdf_file} -----\n")
			if extractor is None:
				out_f.write("ERROR: No hay librería disponible para extraer texto de PDFs.\n")
				continue

			try:
				texto = extractor(ruta)
				if not texto:
					out_f.write("(No se extrajo texto o está vacío)\n")
				else:
					out_f.write(texto)
					if not texto.endswith('\n'):
						out_f.write('\n')
			except Exception as e:
				out_f.write(f"ERROR al procesar {pdf_file}: {e}\n")

	return salida_path


if __name__ == '__main__':
	try:
		ruta = leer_pdfs_y_guardar_txt('Facturas')
		print(f"Salida guardada en: {ruta}")
	except Exception as ex:
		print(f"Error: {ex}")


def parse_resultado_y_guardar_csv(prueba_path: str = 'Facturas', txt_nombre: str = 'resultado.txt', csv_nombre: str = 'datos_generales.csv') -> str:
	"""Lee `prueba_path/txt_nombre`, extrae campos claves por factura y escribe un CSV

	Campos: `filename, Nombre, Fecha, Gas, credito, Total, Consumo_m3`.
	La función es heurística y trata de ser robusta ante pequeñas variaciones.
	Retorna la ruta del CSV generado.
	"""
	import re
	import csv

	txt_path = os.path.join(prueba_path, txt_nombre)
	csv_path = os.path.join(prueba_path, csv_nombre)

	if not os.path.isfile(txt_path):
		raise FileNotFoundError(f"No existe el archivo de texto: {txt_path}")

	with open(txt_path, 'r', encoding='utf-8') as f:
		full = f.read()

	# Buscar secciones delimitadas por: ----- filename.pdf -----
	matches = list(re.finditer(r'^-----\s*(.+?)\s*-----\s*$', full, flags=re.MULTILINE))
	entries = []

	if not matches:
		# Si no hay separadores, tratar todo como una sola factura
		blocks = [(None, full)]
	else:
		blocks = []
		for i, m in enumerate(matches):
			name = m.group(1).strip()
			start = m.end()
			end = matches[i+1].start() if i+1 < len(matches) else len(full)
			block = full[start:end].strip()
			blocks.append((name, block))


	# Helpers
	def clean_amount(a: str) -> str:
		# normaliza '$ 26,815' -> '26815' (solo dígitos)
		s = re.sub(r'[^0-9]', '', a)
		return s

	# detecta montos como $26,815 o $ 26.815
	amount_re = re.compile(r'\$\s*[\d\.,]+')
	date_re = re.compile(r'(\d{1,2}/\d{1,2}/\d{4})')
	standalone_int_re = re.compile(r'^\s*(\d{1,5})\s*$')
	total_keywords_re = re.compile(r'\b(total|valor a pagar|a pagar|valor a pagar:|importe)\b', re.IGNORECASE)
	# nombre: línea con mayúsculas, varias palabras, sin números, sin símbolos, sin palabras genéricas
	nombre_re = re.compile(r'^[A-ZÁÉÍÓÚÑ ]{8,}$')
	avoid_words = {'AL DÍA', 'FECHA', 'PAGO', 'SUSPENCIÓN', 'INMEDIATO', 'NO HAY NADA', 'IMPORTE', 'VALOR', 'DIRECCI', 'LOCALIDAD', 'ASUNTO', 'CARTAGENA', 'ESTIMADO', 'CONEXION', 'RESIDENCIAL', 'ESTRATO', 'KR', 'CL', 'BOTERO', 'SAN ROQUE', 'SINCELEJO', 'CREDITO', 'OTROS', 'CONSUMO', 'RECUPERADO', 'FACTURADO', 'MES', 'PRO', 'SEGURIDAD', 'VIDA', 'SUBSIDIO', 'INTERES', 'BRILLA', 'PLUS', 'UNIDAD', 'CLIENTE', 'ESTRATO', 'DIRECCIYN', 'LOCALIDAD', 'ASUNTO', 'RECUPERACI', 'CONSUMO', 'PERIODOS', 'ANTERIORES', 'USUARIO', 'FACTURA', 'ANEXA', 'COMUNICACI', 'INVESTIGACI', 'FACTURACIYN', 'KIT', 'NOMBRE', 'CONTRATO', 'DIRECCION', 'LOCALIDAD', 'ASUNTO', 'RECUPERACION', 'CONSUMO', 'PERIODOS', 'ANTERIORES', 'USUARIO', 'FACTURA', 'ANEXA', 'COMUNICACION', 'INVESTIGACION', 'FACTURACION', 'KIT'}
	# para separar nombre de fecha si están juntos
	fecha_re = re.compile(r'(\d{1,2}/\d{1,2}/\d{4})')

	for filename, block in blocks:
		# normalizar espacios no-break y limpiar bloque
		block = block.replace('\xa0', ' ') if isinstance(block, str) else block
		lines = [ln.strip() for ln in block.splitlines() if ln.strip()!='']
		# Busca Nombre: primera línea con letras (mínimo dos palabras) en las primeras 10 líneas
		nombre = ''
		fecha = ''
		gas = ''
		credito = ''
		total = ''
		consumo = ''


		# Nombre heurístico mejorado
		nombre = ''
		# 1. Buscar línea con mayúsculas, varias palabras, sin números ni símbolos, sin palabras genéricas
		for ln in lines[:16]:
			ln_clean = ln.strip().replace('  ', ' ')
			ln_upper = ln_clean.upper()
			if (
				len(ln_clean.split()) >= 2
				and not any(ch.isdigit() for ch in ln_clean)
				and not any(sym in ln_clean for sym in '"$%/.:,;')
				and nombre_re.match(ln_upper)
				and not any(w in ln_upper for w in avoid_words)
			):
				nombre = ln_clean
				break

		# 2. Si no se encontró, buscar línea con mínimo dos palabras, sin números, sin símbolos, y sin palabras genéricas
		if not nombre:
			for ln in lines[:16]:
				ln_clean = ln.strip().replace('  ', ' ')
				ln_upper = ln_clean.upper()
				if (
					len(ln_clean.split()) >= 2
					and not any(ch.isdigit() for ch in ln_clean)
					and not any(sym in ln_clean for sym in '"$%/.:,;')
					and not any(w in ln_upper for w in avoid_words)
				):
					nombre = ln_clean
					break

		# 3. Si el nombre contiene una fecha al final, separarla
		if nombre:
			m = fecha_re.search(nombre)
			if m:
				nombre = nombre[:m.start()].strip()

		# 4. Si sigue sin nombre, buscar línea con mínimo dos palabras, sin números, aunque tenga símbolos
		if not nombre:
			for ln in lines[:20]:
				ln_clean = ln.strip().replace('  ', ' ')
				ln_upper = ln_clean.upper()
				if (
					len(ln_clean.split()) >= 2
					and not any(ch.isdigit() for ch in ln_clean)
					and not any(w in ln_upper for w in avoid_words)
				):
					nombre = ln_clean
					break

		# 5. Si sigue sin nombre, fallback: primera línea con mínimo dos palabras
		if not nombre:
			for ln in lines[:20]:
				ln_clean = ln.strip().replace('  ', ' ')
				if len(ln_clean.split()) >= 2:
					nombre = ln_clean
					break

		# Fecha
		for ln in lines[:12]:
			m = date_re.search(ln)
			if m:
				fecha = m.group(1)
				break

		# Cantidades: preferimos encontrar la línea de cargos (varios montos juntos)
		header_lines = lines[:16]
		gas = credito = total = ''

		charges_line = None
		for ln in header_lines:
			ams = amount_re.findall(ln)
			if len(ams) >= 2:
				charges_line = ln
				ams_clean = [clean_amount(a) for a in ams]
				gas = ams_clean[0]
				credito = ams_clean[1] if len(ams_clean) >= 2 else ''
				break

		# Si no se encontró línea con varios montos, extraer montos del header en orden
		if not charges_line:
			header_text = '\n'.join(header_lines)
			amounts = amount_re.findall(header_text)
			amounts = [clean_amount(a) for a in amounts]
			if amounts:
				gas = amounts[0] if len(amounts) >= 1 else ''
				credito = amounts[1] if len(amounts) >= 2 else ''

		# Buscar Total: preferir línea que contenga palabra 'total' o línea independiente con un solo monto
		total_found = False
		for ln in header_lines:
			if total_keywords_re.search(ln):
				am = amount_re.findall(ln)
				if am:
					total = clean_amount(am[-1])
					total_found = True
					break

		if not total_found:
			# buscar línea independiente con único monto en todo bloque (desde header hasta 40 líneas)
			search_scope = lines[:40] if len(lines) > 40 else lines
			for ln in search_scope:
				am = amount_re.findall(ln)
				if len(am) == 1 and ln.strip().startswith('$'):
					total = clean_amount(am[0])
					total_found = True
					break

		if not total_found:
			# fallback: último monto del header
			if 'amounts' in locals() and amounts:
				total = amounts[-1]

		# Consumo_m3 heurístico: buscar el primer entero standalone plausible después del Total
		consumo = ''
		total_idx = None
		if total:
			for i, ln in enumerate(lines):
				# comparar montos encontrados en la línea con la forma normalizada del total
				ams = amount_re.findall(ln)
				matched = False
				for a in ams:
					if clean_amount(a) == total:
						total_idx = i
						matched = True
						break
				if matched:
					break
				# fallback: comparar con dígitos presentes en la línea
				if total in re.sub(r'[^0-9]', '', ln):
					total_idx = i
					break

		# buscar en un rango de líneas después del total (preferible) o desde el inicio
		if total_idx is not None:
			start = total_idx + 1
		else:
			start = 0

		end = min(len(lines), start + 80)
		for i in range(start, end):
			ln = lines[i]
			m = standalone_int_re.match(ln)
			if m:
				val = m.group(1)
				try:
					iv = int(val)
					if 1 <= iv <= 5000:
						consumo = val
						break
				except Exception:
					continue

		# fallback: buscar desde el final hacia atrás cualquier standalone plausible
		if not consumo:
			for ln in reversed(lines[-120:]):
				m = standalone_int_re.match(ln)
				if m:
					val = m.group(1)
					try:
						iv = int(val)
						if 1 <= iv <= 5000:
							consumo = val
							break
					except Exception:
						continue

		# Fallbacks: si no hay nombre, intentar una línea más arriba
		if not nombre:
			for ln in lines[:20]:
				if ln.strip() and not ln.strip().startswith('$') and len(ln.split())>=2:
					nombre = ln.strip()
					break

		entries.append({
			'filename': filename or '',
			'Nombre': nombre,
			'Fecha': fecha,
			'Gas': gas,
			'credito': credito,
			'Total': total,
			'Consumo_m3': consumo,
		})

	# Escribir CSV
	fieldnames = ['filename', 'Nombre', 'Fecha', 'Gas', 'credito', 'Total', 'Consumo_m3']
	with open(csv_path, 'w', encoding='utf-8', newline='') as cf:
		writer = csv.DictWriter(cf, fieldnames=fieldnames)
		writer.writeheader()
		for e in entries:
			writer.writerow(e)

	return csv_path


parse_resultado_y_guardar_csv('Facturas', 'resultado.txt', 'datos_generales.csv')  # Llama a la función para generar CSV

