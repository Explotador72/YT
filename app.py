from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
from pathlib import Path
import os
import tempfile
import time

app = Flask(__name__)
CORS(app)

# Configuración
DOWNLOADS_DIR = Path('Downloads').resolve()
DOWNLOADS_DIR.mkdir(exist_ok=True)

def download_video(video_url: str):
    """Descarga SOLO video (sin conversión que requiera FFmpeg)"""
    try:
        print(f"🎬 Iniciando descarga de: {video_url}")
        
        # Configuración para descargar video directamente sin post-procesamiento
        ydl_opts = {
            'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
            'format': 'best[height<=720]',  # Descargar el mejor video hasta 720p
            'quiet': False,
            # Deshabilitar post-procesamiento que requiere FFmpeg
            'postprocessors': [],  # ¡IMPORTANTE! Sin post-procesamiento
        }

        # Obtener información primero
        with YoutubeDL({'quiet': False}) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                video_title = info.get('title', 'video_descargado')
                original_ext = info.get('ext', 'mp4')
                print(f"📝 Título: {video_title}")
                print(f"📦 Formato original: {original_ext}")
            except Exception as e:
                return {'success': False, 'error': f'Error obteniendo info: {str(e)}'}

        # Descargar
        with YoutubeDL(ydl_opts) as ydl:
            print("⬇️ Iniciando descarga...")
            ydl.download([video_url])

        # Buscar archivo descargado
        time.sleep(2)
        
        # Buscar por el título
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        downloaded_files = list(DOWNLOADS_DIR.glob(f'*{safe_title}*'))
        
        print(f"🔍 Buscando archivos con: *{safe_title}*")
        print(f"📁 Archivos encontrados: {[f.name for f in downloaded_files]}")
        
        if downloaded_files:
            downloaded_file = downloaded_files[0]
            return {
                'success': True,
                'file_path': str(downloaded_file),
                'filename': downloaded_file.name,
                'title': video_title
            }
        else:
            return {'success': False, 'error': 'No se encontró el archivo descargado'}
                
    except Exception as e:
        print(f"💥 Error en download_video: {str(e)}")
        return {'success': False, 'error': f'Error en la descarga: {str(e)}'}

@app.route('/api/download', methods=['POST'])
def api_download():
    """Endpoint para descargar"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL requerida'}), 400
        
        video_url = data['url']
        
        print(f"📨 Solicitud recibida - URL: {video_url}")
        
        result = download_video(video_url)
        
        if result['success']:
            return jsonify({
                'success': True,
                'title': result['title'],
                'filename': result['filename'],
                'download_url': f"/api/file/{result['filename']}"
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 500
            
    except Exception as e:
        print(f"💥 Error en api_download: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/api/file/<filename>')
def serve_file(filename):
    """Sirve archivo descargado"""
    try:
        file_path = DOWNLOADS_DIR / filename
        print(f"📤 Intentando servir: {filename}")
        print(f"📁 Ruta: {file_path}")
        print(f"✅ Existe: {file_path.exists()}")
        
        if file_path.exists():
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': f'Archivo no encontrado: {filename}'}), 404
    except Exception as e:
        print(f"💥 Error en serve_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Sirve el frontend"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Downloader</title>
        <style>
            body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
            .container { background: #f8f9fa; padding: 30px; border-radius: 10px; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { padding: 12px 25px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .status { margin: 15px 0; padding: 15px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .loading { background: #fff3cd; color: #856404; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Descargador de Videos</h1>
            <p><strong>⚠️ Solo video (sin FFmpeg)</strong></p>
            <p>Prueba con: <code>https://www.youtube.com/watch?v=dQw4w9WgXcQ</code></p>
            <input type="text" id="videoUrl" placeholder="Pega URL de YouTube aquí" value="https://www.youtube.com/watch?v=dQw4w9WgXcQ">
            <div>
                <button onclick="download()">🎥 Descargar Video</button>
            </div>
            <div id="status"></div>
        </div>

        <script>
            function showStatus(message, type) {
                document.getElementById('status').innerHTML = '<div class="status ' + type + '">' + message + '</div>';
            }

            async function download() {
                const url = document.getElementById('videoUrl').value;
                
                if (!url) {
                    showStatus('❌ Ingresa una URL', 'error');
                    return;
                }

                try {
                    showStatus('⏳ Descargando video...', 'loading');
                    
                    const response = await fetch('/api/download', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    });

                    const data = await response.json();
                    console.log('Respuesta:', data);
                    
                    if (data.success) {
                        // Descargar automáticamente
                        window.location.href = data.download_url;
                        showStatus('✅ Video descargado!', 'success');
                    } else {
                        showStatus('❌ ' + data.error, 'error');
                    }
                    
                } catch (error) {
                    console.error('Error:', error);
                    showStatus('❌ Error: ' + error.message, 'error');
                }
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚀 Servidor iniciado en: http://localhost:5000")
    print("📁 Carpeta de descargas:", DOWNLOADS_DIR)
    print("⚠️  Modo: Solo video (sin FFmpeg)")
    app.run(host='0.0.0.0', port=5000, debug=True)