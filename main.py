from funciones import leer_pdfs_y_guardar_txt
from funciones import parse_resultado_y_guardar_csv

if __name__ == '__main__':
	try:
		ruta = leer_pdfs_y_guardar_txt('Facturas')
		print(f"Salida guardada en: {ruta}")
		try:
			csv_ruta = parse_resultado_y_guardar_csv('facturas')
			print(f"CSV generado en: {csv_ruta}")
		except Exception as ex:
			print(f"No se pudo generar el CSV: {ex}")
	except Exception as e:
		print(f"Error: {e}")
