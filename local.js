const statusElement = document.getElementById('status');
const downloadButton = document.getElementById('downloadButton');
const apiUrlInput = document.getElementById('apiUrl');
const videoUrlInput = document.getElementById('videoUrl');

downloadButton.addEventListener("click", startProcess);

     
// Función para mostrar mensajes de estado con color
function showStatus(message, type = 'info') {
    let bgColor, textColor;
    if (type === 'success') {
        bgColor = 'bg-green-100';
        textColor = 'text-green-800';
    } else if (type === 'error') {
        bgColor = 'bg-red-100';
        textColor = 'text-red-800';
    } else if (type === 'loading') {
        bgColor = 'bg-yellow-100';
        textColor = 'text-yellow-800';
    } else {
        bgColor = 'bg-gray-100';
        textColor = 'text-gray-800';
    }
    statusElement.className = `mt-4 p-4 rounded-lg text-sm transition-all duration-300 ${bgColor} ${textColor}`;
    statusElement.innerHTML = message;
}

// --- Lógica Principal del Proceso ---
// CORRECCIÓN DE RECARGA: La función ahora recibe el evento (event)
async function startProcess(event) {
    event.preventDefault();
    event.stopPropagation();
    // CORRECCIÓN CRUCIAL: Detenemos la acción por defecto del botón (submit/recarga)
    if (event && event.preventDefault) {
        event.preventDefault(); 
    }

    const LOCAL_API_URL = apiUrlInput.value.trim();
    const videoUrl = videoUrlInput.value.trim();

    if (!videoUrl) {
        showStatus('❌ Ingresa la URL de un video de YouTube.', 'error');
        return;
    }
    
    downloadButton.disabled = true;
    downloadButton.innerHTML = '<span class="animate-spin mr-2">⚙️</span> Procesando... (Puede tardar hasta 30s)';
    
    showStatus(`⏳ Paso 1/2: Solicitando descarga a ${LOCAL_API_URL}...`, 'loading');
    
    try {
        // Paso 1: Llamar al endpoint /api/download para iniciar la descarga en el backend
        const downloadResponse = await fetch(`${LOCAL_API_URL}/api/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: videoUrl })
        });

        // DEPURACIÓN AVANZADA: Leemos la respuesta como texto para evitar fallo en .json()
        if (!downloadResponse.ok) {
            const errorText = await downloadResponse.text();
            showStatus(`❌ Error HTTP (${downloadResponse.status}). Ver consola para detalles.`, 'error');
            console.error("Respuesta HTTP fallida:", downloadResponse.status, errorText);
            return;
        }

        const responseText = await downloadResponse.text();
        
        console.log('--- Contenido recibido del servidor (DEBE ser JSON) ---');
        console.log(responseText);
        console.log('--------------------------------------------------');

        let downloadData;
        try {
            // Intentamos parsear el texto a JSON
            downloadData = JSON.parse(responseText);
        } catch (e) {
            // Si falla, el contenido no era JSON (HTML, texto de error, etc.)
            showStatus(`❌ Error de SINTAXIS JSON. El servidor no devolvió JSON válido. Ver consola.`, 'error');
            console.error("Error al parsear JSON:", e.message);
            return;
        }
        
        // Si el JSON es válido, verificamos el campo 'success'
        if (!downloadData.success) {
            const errorMsg = downloadData.error || `Error desconocido en el backend`;
            showStatus(`❌ Error en el backend (Paso 1): ${errorMsg}`, 'error');
            return;
        }

        console.log('✅ Backend: Descarga completada. Iniciando descarga en cliente...');

        const filename = downloadData.filename;
        const downloadUrlRelative = downloadData.download_url;
        const fileUrl = `${LOCAL_API_URL}${downloadUrlRelative}`;

        showStatus(`✅ Paso 1/2 Completado. Video "${downloadData.title}" descargado en el servidor. <br> ⏳ Paso 2/2: Iniciando descarga del archivo...`, 'loading');

        // Paso 2: Usar un enlace invisible para la descarga (NO RECARGA LA PÁGINA)
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = fileUrl;
        a.download = filename;

        document.body.appendChild(a);
        a.click(); 
        document.body.removeChild(a);

        showStatus(`🎉 Éxito! El archivo "${filename}" se está descargando en tu navegador. Revisa tu carpeta de descargas.`, 'success');

    } catch (error) {
        showStatus(`❌ Error de conexión o fatal. Asegúrate de que el servidor Flask está corriendo en http://localhost:5000. Mensaje: ${error.message}`, 'error');
        console.error("Error fatal en el fetch/proceso:", error);
    } finally {
        downloadButton.disabled = false;
        downloadButton.innerHTML = '🚀 Iniciar Descarga Local';
    }
}