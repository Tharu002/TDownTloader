from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import re
import tempfile

app = Flask(__name__)
CORS(app)

# Use temporary directory for downloads
DOWNLOAD_FOLDER = tempfile.mkdtemp()

def download_video(url, quality):
    try:
        clean_url = re.sub(r'[&?]list=[^&]+', '', url)
        clean_url = re.sub(r'&index=\d+', '', clean_url)
        
        quality_map = {
            '360p': 'best[height<=360][ext=mp4]/best[height<=360]',
            '480p': 'best[height<=480][ext=mp4]/best[height<=480]',
            '720p': 'best[height<=720][ext=mp4]/best[height<=720]',
            '1080p': 'best[height<=1080][ext=mp4]/best[height<=1080]'
        }
        
        format_option = quality_map.get(quality, 'best[ext=mp4]')
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/video_{unique_id}.%(ext)s',
            'format': format_option,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                filename = filename.rsplit('.', 1)[0] + '.mp4'
            
            if not os.path.exists(filename):
                # Try to find any video file
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if f.endswith('.mp4') or f.endswith('.webm'):
                        filename = os.path.join(DOWNLOAD_FOLDER, f)
                        break
            
            return filename, info.get('title', 'video')
            
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

# HTML Template
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDownTloader | YouTube Downloader</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #0f0f1a 50%, #1a0b2e 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
        }
        .card {
            background: rgba(15, 15, 25, 0.85);
            backdrop-filter: blur(20px);
            border-radius: 48px;
            border: 1px solid rgba(255, 0, 0, 0.2);
            overflow: hidden;
            width: 100%;
        }
        .header {
            background: linear-gradient(135deg, rgba(255,0,0,0.15), rgba(139,92,246,0.1));
            padding: 40px;
            text-align: center;
            border-bottom: 1px solid rgba(255,0,0,0.2);
        }
        .logo { font-size: 4rem; background: linear-gradient(135deg, #ff0000, #8b5cf6); -webkit-background-clip: text; background-clip: text; color: transparent; }
        h1 { font-size: 2.5rem; font-weight: 900; background: linear-gradient(135deg, #fff, #ff0000, #8b5cf6); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .content { padding: 40px; }
        .url-input {
            background: rgba(0,0,0,0.5);
            border-radius: 60px;
            padding: 6px;
            display: flex;
            border: 2px solid rgba(255,0,0,0.3);
            margin-bottom: 30px;
        }
        .url-input:focus-within { border-color: #ff0000; box-shadow: 0 0 20px rgba(255,0,0,0.3); }
        .url-icon { padding: 18px 20px; color: #ff0000; }
        #videoUrl {
            flex: 1;
            background: transparent;
            border: none;
            padding: 18px 0;
            font-size: 1rem;
            color: #fff;
            outline: none;
        }
        .quality-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .quality-card input { display: none; }
        .quality-card label {
            display: block;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border: 2px solid rgba(255,0,0,0.2);
            border-radius: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
            color: rgba(255,255,255,0.7);
        }
        .quality-card input:checked + label {
            background: linear-gradient(135deg, rgba(255,0,0,0.3), rgba(139,92,246,0.3));
            border-color: #ff0000;
            color: white;
        }
        .download-btn {
            width: 100%;
            background: linear-gradient(135deg, #ff0000, #8b5cf6);
            border: none;
            padding: 18px;
            border-radius: 60px;
            font-size: 1.1rem;
            font-weight: 700;
            color: white;
            cursor: pointer;
            margin-bottom: 25px;
            transition: all 0.3s;
        }
        .download-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(255,0,0,0.4); }
        .download-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .status-card {
            background: rgba(0,0,0,0.5);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 25px;
            border-left: 4px solid #ff0000;
        }
        .status-message { color: rgba(255,255,255,0.9); margin-bottom: 8px; }
        .status-detail { color: rgba(255,255,255,0.5); font-size: 0.8rem; word-break: break-word; }
        .features {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }
        .feature {
            background: rgba(255,255,255,0.03);
            padding: 15px;
            border-radius: 15px;
            text-align: center;
        }
        .feature i { font-size: 1.5rem; color: #ff0000; margin-bottom: 8px; display: block; }
        .feature p { font-size: 0.7rem; color: rgba(255,255,255,0.5); }
        .footer {
            background: rgba(0,0,0,0.4);
            padding: 20px;
            text-align: center;
            font-size: 0.75rem;
            color: rgba(255,255,255,0.4);
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (max-width: 768px) {
            .quality-grid { grid-template-columns: repeat(2, 1fr); }
            .features { grid-template-columns: repeat(2, 1fr); }
            .header, .content { padding: 25px; }
            h1 { font-size: 1.8rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <i class="fas fa-download logo"></i>
                <h1>TDownTloader</h1>
                <p style="color: rgba(255,255,255,0.6);">YouTube Video Downloader</p>
            </div>
            <div class="content">
                <div class="url-input">
                    <div class="url-icon"><i class="fab fa-youtube"></i></div>
                    <input type="text" id="videoUrl" placeholder="Paste YouTube URL here...">
                </div>
                <div class="quality-grid">
                    <div class="quality-card"><input type="radio" name="quality" id="q360" value="360p"><label for="q360">360p</label></div>
                    <div class="quality-card"><input type="radio" name="quality" id="q480" value="480p"><label for="q480">480p</label></div>
                    <div class="quality-card"><input type="radio" name="quality" id="q720" value="720p" checked><label for="q720">720p</label></div>
                    <div class="quality-card"><input type="radio" name="quality" id="q1080" value="1080p"><label for="q1080">1080p</label></div>
                </div>
                <button class="download-btn" id="downloadBtn"><i class="fas fa-download"></i> Download Video</button>
                <div class="status-card" id="statusCard">
                    <div class="status-message" id="statusMessage">Ready to download</div>
                    <div class="status-detail" id="statusDetail">Paste a YouTube URL and select quality</div>
                </div>
                <div class="features">
                    <div class="feature"><i class="fas fa-video"></i><p>360p-1080p</p></div>
                    <div class="feature"><i class="fas fa-magic"></i><p>Easy to use</p></div>
                    <div class="feature"><i class="fas fa-rocket"></i><p>Fast</p></div>
                    <div class="feature"><i class="fas fa-save"></i><p>MP4 format</p></div>
                </div>
            </div>
            <div class="footer"><i class="fas fa-copyright"></i> TDownTloader • Made by Tharu002</div>
        </div>
    </div>
    <script>
        const downloadBtn = document.getElementById('downloadBtn');
        const videoUrlInput = document.getElementById('videoUrl');
        const statusMessage = document.getElementById('statusMessage');
        const statusDetail = document.getElementById('statusDetail');
        
        function updateStatus(message, detail) {
            statusMessage.innerHTML = message;
            if (detail) statusDetail.innerHTML = detail;
        }
        
        async function downloadVideo() {
            const url = videoUrlInput.value.trim();
            const quality = document.querySelector('input[name="quality"]:checked').value;
            
            if (!url) {
                updateStatus('❌ Please enter a URL', '');
                return;
            }
            
            if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
                updateStatus('❌ Invalid YouTube URL', 'Please enter a valid YouTube link');
                return;
            }
            
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<div class="spinner"></div> Processing...';
            updateStatus('⏳ Processing...', 'Downloading video, please wait (30-60 seconds)...');
            
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, quality: quality })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStatus('✅ Download Complete!', 'Starting download...');
                    window.location.href = data.download_url;
                    setTimeout(() => {
                        updateStatus('Ready to download', 'Paste another URL');
                        downloadBtn.disabled = false;
                        downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Video';
                    }, 3000);
                } else {
                    throw new Error(data.error || 'Download failed');
                }
            } catch (error) {
                updateStatus('❌ Download Failed', error.message);
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Video';
            }
        }
        
        downloadBtn.addEventListener('click', downloadVideo);
        videoUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') downloadVideo();
        });
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/download', methods=['POST'])
def api_download():
    try:
        data = request.json
        url = data.get('url')
        quality = data.get('quality', '720p')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        filename, title = download_video(url, quality)
        
        if os.path.exists(filename):
            return jsonify({
                'success': True,
                'download_url': f'/api/download_file/{os.path.basename(filename)}'
            })
        else:
            return jsonify({'error': 'File not found'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_file/<filename>')
def download_file(filename):
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

# This is for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
