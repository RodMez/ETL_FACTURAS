"""
Aplicación Web para Gestión de Facturas
Servidor Flask simple con Bootstrap
"""

from flask import Flask, render_template, request, jsonify
import os
import sys
from werkzeug.utils import secure_filename

# Agregar el directorio padre al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conexion import create_connection

app = Flask(__name__)

# Configuración
FACTURAS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Facturas')
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Verificar si el archivo tiene extensión PDF"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/facturas', methods=['GET'])
def get_facturas():
    """Obtener todas las facturas de la base de datos"""
    try:
        conn = create_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # Consultar todas las facturas
        cursor.execute("""
            SELECT id, filename, nombre, fecha, gas, credito, total, consumo_m3 
            FROM Facturas 
            ORDER BY fecha DESC
        """)
        
        facturas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convertir fecha a string para JSON
        for factura in facturas:
            if factura['fecha']:
                factura['fecha'] = factura['fecha'].strftime('%Y-%m-%d')
        
        return jsonify({'success': True, 'facturas': facturas})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/facturas/<int:factura_id>/detalles', methods=['GET'])
def get_detalles(factura_id):
    """Obtener detalles específicos de una factura"""
    try:
        conn = create_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # Consultar detalles de la factura
        cursor.execute("""
            SELECT id, concepto, valor_pagar 
            FROM Detalles 
            WHERE factura_id = %s
            ORDER BY id
        """, (factura_id,))
        
        detalles = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'detalles': detalles})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_factura():
    """Subir una factura PDF a la carpeta Facturas"""
    try:
        # Verificar si se envió un archivo
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        
        # Verificar si se seleccionó un archivo
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        # Verificar extensión
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Solo se permiten archivos PDF'}), 400
        
        # Guardar archivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(FACTURAS_FOLDER, filename)
        
        # Verificar si el archivo ya existe
        if os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Ya existe una factura con ese nombre'}), 400
        
        file.save(filepath)
        
        return jsonify({
            'success': True, 
            'message': f'Factura {filename} subida correctamente. Ejecuta el procesador ETL para cargarla a la BD.',
            'filename': filename
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Aplicación Web de Gestión de Facturas")
    print("=" * 60)
    print(f"📁 Carpeta de facturas: {FACTURAS_FOLDER}")
    print(f"🌐 Abre tu navegador en: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
