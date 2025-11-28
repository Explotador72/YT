from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
from pathlib import Path
import os
import time
import re

# Inicialización de la aplicación Flask
app = Flask(__name__)
# Habilitar CORS para permitir peticiones desde cualquier origen (necesario para el frontend)
CORS(app)

# --- Configuración de Archivos ---
# Directorio donde se guardarán los videos descargados
DOWNLOADS_DIR = Path('Downloads').resolve()
# Crear el directorio si no existe
DOWNLOADS_DIR.mkdir(exist_ok=True)
print(f"📁 Directorio de descargas configurado en: {DOWNLOADS_DIR}")

# --- Funciones Auxiliares ---

def sanitize_filename(title: str) -> str:
    """Sanea el título para usarlo en la búsqueda de archivos, reemplazando caracteres no seguros."""
    # Eliminar caracteres inválidos en rutas de archivo y reemplazarlos por '_' o eliminarlos
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title)
    # Reemplazar espacios por guiones para una mejor búsqueda, si se desea
    # safe_title = safe_title.replace(' ', '_')
    return safe_title.strip()

def download_video(video_url: str):
    """
    Descarga SOLO video (sin conversión que requiera FFmpeg).
    Retorna un diccionario con el resultado.
    """
    print(f"🎬 Iniciando descarga de: {video_url}")
    
    try:
        # 1. Obtener información primero para determinar el título y extensión
        with YoutubeDL({'quiet': True, 'noprogress': True}) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                video_title = info.get('title', 'video_descargado')
                
                # Sanear el título para buscar el archivo después
                sanitized_title = sanitize_filename(video_title)
                
                print(f"📝 Título original: {video_title}")
                print(f"📝 Título saneado: {sanitized_title}")

            except Exception as e:
                print(f"💥 Error obteniendo info: {str(e)}")
                return {'success': False, 'error': f'Error obteniendo info de YouTube: {str(e)}'}

        # 2. Configuración para descargar
        # Usamos el título saneado en el outtmpl para una búsqueda más precisa
        output_template = str(DOWNLOADS_DIR / f'{sanitized_title}.%(ext)s')
        
        ydl_opts = {
            'outtmpl': output_template,
            'format': 'best[height<=720]',  # Descargar el mejor video hasta 720p
            'quiet': False,
            # Importante: Deshabilitar post-procesamiento para evitar dependencia de FFmpeg
            'postprocessors': [], 
            'nooverwrites': False, # Permitir sobrescribir para reintentos
            'noplaylist': True, # Solo descargar videos individuales
        }

        # 3. Descargar
        print("⬇️ Iniciando descarga...")
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 4. Buscar archivo descargado
        # Buscamos archivos que comiencen con el título saneado
        time.sleep(1) # Pequeña espera para asegurar que el sistema de archivos termine la operación
        
        # El glob busca cualquier extensión que siga al título saneado
        downloaded_files = list(DOWNLOADS_DIR.glob(f'{sanitized_title}.*'))
        
        print(f"🔍 Buscando archivos con: {sanitized_title}.*")
        print(f"📁 Archivos encontrados: {[f.name for f in downloaded_files]}")
        
        if downloaded_files:
            downloaded_file = downloaded_files[0]
            return {
                'success': True,
                'file_path': str(downloaded_file),
                'filename': downloaded_file.name,
                'title': video_title # Retornar el título original sin sanear para la respuesta
            }
        else:
            print("❌ No se encontró el archivo descargado después de la operación.")
            return {'success': False, 'error': 'No se encontró el archivo descargado'}
                
    except Exception as e:
        print(f"💥 Error en download_video: {str(e)}")
        return {'success': False, 'error': f'Error en la descarga: {str(e)}'}

# --- Rutas API ---

@app.route('/api/download', methods=['POST'])
def api_download():
    """
    Endpoint principal para iniciar la descarga de un video.
    Espera un JSON con 'url'.
    Retorna JSON con el nombre del archivo y la URL de descarga.
    """
    try:
        # Asegurarse de que el Content-Type es application/json
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type debe ser application/json'}), 415
            
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'La URL del video es requerida en el cuerpo de la solicitud JSON'}), 400
        
        video_url = data['url']
        print(f"📨 Solicitud POST recibida - URL: {video_url}")
        
        result = download_video(video_url)
        
        if result['success']:
            # Devolver los metadatos para que el cliente sepa qué descargar
            json = jsonify({
                'success': True,
                'title': result['title'],
                'filename': result['filename'],
                'download_url': f"/api/file/{result['filename']}"
            })
            print(json, "aqui")
            return json
            
        else:
            return jsonify({'success': False, 'error': result['error']}), 500
            
    except Exception as e:
        print(f"💥 Error en api_download: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/api/file/<filename>', methods=['GET'])
def serve_file(filename):
    """
    Endpoint para servir (enviar) el archivo descargado.
    El cliente puede usar esta URL para iniciar la descarga.
    """
    try:
        file_path = DOWNLOADS_DIR / filename
        print(f"📤 Solicitud GET recibida para servir archivo: {filename}")
        
        if file_path.exists():
            # Usar send_file con as_attachment=True para forzar la descarga en el cliente
            return send_file(
                file_path, 
                as_attachment=True, 
                download_name=filename, 
                # Sugerencia para el tipo MIME si es conocido (opcional)
                mimetype='video/mp4' 
            )
        else:
            print(f"❌ Archivo no encontrado en el servidor: {file_path}")
            return jsonify({'error': f'Archivo no encontrado: {filename}'}), 404
    except Exception as e:
        print(f"💥 Error en serve_file: {str(e)}")
        return jsonify({'error': f'Error al servir el archivo: {str(e)}'}), 500

@app.route('/', methods=['GET'])
def root_status():
    """Endpoint raíz simple para verificar que el backend está corriendo."""
    return jsonify({
        'status': 'Backend API activo',
        'message': 'Usa /api/download (POST) para iniciar descargas.'
    })


# --- Ejecución del Servidor ---

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask API...")
    # Ejecutar en modo de desarrollo. En producción, usa WSGI como Gunicorn.
    app.run(host='0.0.0.0', port=5000, debug=True)