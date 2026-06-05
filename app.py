from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import re
import subprocess

app = Flask(__name__)
CORS(app)

# Configuration
DOWNLOAD_FOLDER = './downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Check if FFmpeg is available
def check_ffmpeg():
    try:
        # Check current directory first
        if os.path.exists('./ffmpeg.exe'):
            return True
        # Check system PATH
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()

# Store download status
download_status = {}

# Quality options with their format selectors
QUALITY_OPTIONS = {
    '360p': {
        'name': '360p',
        'format': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]',
        'description': 'Good for mobile & slow internet'
    },
    '480p': {
        'name': '480p',
        'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
        'description': 'Standard DVD quality'
    },
    '720p': {
        'name': '720p',
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
        'description': 'HD quality - Recommended'
    },
    '1080p': {
        'name': '1080p',
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
        'description': 'Full HD - Requires FFmpeg',
        'requires_ffmpeg': True
    }
}

def download_video_thread(url, download_id, quality):
    """Background thread for downloading video"""
    try:
        # Clean URL (remove playlist parameters)
        clean_url = re.sub(r'[&?]list=[^&]+', '', url)
        clean_url = re.sub(r'&index=\d+', '', clean_url)
        
        quality_info = QUALITY_OPTIONS.get(quality, QUALITY_OPTIONS['720p'])
        format_option = quality_info['format']
        
        # Check FFmpeg requirement for 1080p
        if quality_info.get('requires_ffmpeg', False) and not FFMPEG_AVAILABLE:
            download_status[download_id] = {
                'status': 'error',
                'error': 'FFmpeg is required for 1080p. Please install FFmpeg or select 720p.',
                'message': '1080p requires FFmpeg'
            }
            return
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{quality}_%(id)s.%(ext)s',
            'format': format_option,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'geo_bypass': True,
            'retries': 10,
            'fragment_retries': 10,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        # Add merge option if FFmpeg is available
        if FFMPEG_AVAILABLE:
            ydl_opts['merge_output_format'] = 'mp4'
        
        # Update status
        download_status[download_id] = {
            'status': 'downloading',
            'message': f'Downloading {quality} video...',
            'progress': 0
        }
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            
            if info:
                # Get the filename
                filename = ydl.prepare_filename(info)
                
                # Check for actual file
                if not os.path.exists(filename):
                    # Try with .mp4 extension
                    mp4_file = filename.rsplit('.', 1)[0] + '.mp4'
                    if os.path.exists(mp4_file):
                        filename = mp4_file
                
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename) / (1024 * 1024)  # Size in MB
                    
                    download_status[download_id] = {
                        'status': 'completed',
                        'filename': os.path.basename(filename),
                        'title': info.get('title', 'video'),
                        'quality': quality,
                        'size_mb': round(file_size, 2),
                        'message': f'Download completed! ({quality} - {round(file_size, 2)} MB)'
                    }
                    return
            
            raise Exception("File not found after download")
            
    except Exception as e:
        error_msg = str(e)
        download_status[download_id] = {
            'status': 'error',
            'error': error_msg,
            'message': f'Download failed: {error_msg[:150]}'
        }

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDownTloader | Professional YouTube Downloader</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #0f0f1a 50%, #1a0b2e 100%);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        /* Animated Background */
        .bg-gradient {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
        }
        
        .bg-gradient::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 20% 50%, rgba(255, 0, 0, 0.15), transparent 50%);
            animation: rotate 20s linear infinite;
        }
        
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* Floating particles */
        .particle {
            position: fixed;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 50%;
            pointer-events: none;
            z-index: 0;
        }
        
        .container {
            position: relative;
            z-index: 1;
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Main Card */
        .main-card {
            background: rgba(15, 15, 25, 0.85);
            backdrop-filter: blur(20px);
            border-radius: 48px;
            border: 1px solid rgba(255, 0, 0, 0.2);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 0, 0, 0.1);
            overflow: hidden;
            width: 100%;
            animation: slideUp 0.6s cubic-bezier(0.2, 0.9, 0.4, 1.1);
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, rgba(255, 0, 0, 0.15), rgba(139, 92, 246, 0.1));
            padding: 45px 40px;
            text-align: center;
            border-bottom: 1px solid rgba(255, 0, 0, 0.2);
            position: relative;
        }
        
        .logo {
            font-size: 4.5rem;
            background: linear-gradient(135deg, #ff0000, #8b5cf6);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            display: inline-block;
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        h1 {
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, #ffffff, #ff0000, #8b5cf6);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin: 10px 0 5px;
            letter-spacing: -1px;
        }
        
        .tagline {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.9rem;
        }
        
        .ffmpeg-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 15px;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid {{ '#10b981' if ffmpeg_available else '#ef4444' }};
            color: {{ '#10b981' if ffmpeg_available else '#ef4444' }};
        }
        
        /* Content */
        .content {
            padding: 40px;
        }
        
        /* URL Input */
        .url-input-wrapper {
            background: rgba(0, 0, 0, 0.5);
            border-radius: 60px;
            padding: 6px;
            display: flex;
            align-items: center;
            border: 2px solid rgba(255, 0, 0, 0.3);
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }
        
        .url-input-wrapper:focus-within {
            border-color: #ff0000;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
            transform: scale(1.01);
        }
        
        .url-icon {
            padding: 18px 20px;
            color: #ff0000;
            font-size: 1.2rem;
        }
        
        #videoUrl {
            flex: 1;
            background: transparent;
            border: none;
            padding: 18px 0;
            font-size: 1rem;
            color: #fff;
            font-family: 'Inter', monospace;
            outline: none;
        }
        
        #videoUrl::placeholder {
            color: rgba(255, 255, 255, 0.3);
        }
        
        /* Quality Selection */
        .quality-section {
            margin-bottom: 30px;
        }
        
        .section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .section-title i {
            color: #ff0000;
        }
        
        .quality-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }
        
        .quality-card {
            position: relative;
            cursor: pointer;
        }
        
        .quality-card input {
            position: absolute;
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .quality-label {
            display: block;
            padding: 15px 10px;
            background: rgba(255, 255, 255, 0.03);
            border: 2px solid rgba(255, 0, 0, 0.2);
            border-radius: 20px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .quality-card input:checked + .quality-label {
            background: linear-gradient(135deg, rgba(255, 0, 0, 0.2), rgba(139, 92, 246, 0.2));
            border-color: #ff0000;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.2);
            transform: translateY(-2px);
        }
        
        .quality-label:hover {
            background: rgba(255, 0, 0, 0.1);
            transform: translateY(-2px);
        }
        
        .quality-name {
            font-size: 1.1rem;
            font-weight: 700;
            color: #fff;
        }
        
        .quality-desc {
            font-size: 0.7rem;
            color: rgba(255, 255, 255, 0.5);
            margin-top: 5px;
        }
        
        .badge-ffmpeg {
            display: inline-block;
            background: rgba(239, 68, 68, 0.2);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.6rem;
            color: #ef4444;
            margin-top: 5px;
        }
        
        /* Download Button */
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
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: all 0.3s ease;
            margin-bottom: 25px;
            position: relative;
            overflow: hidden;
        }
        
        .download-btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }
        
        .download-btn:hover::before {
            width: 300px;
            height: 300px;
        }
        
        .download-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(255, 0, 0, 0.4);
        }
        
        .download-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        /* Status Card */
        .status-card {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 24px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #ff0000;
            transition: all 0.3s;
        }
        
        .status-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            font-weight: 600;
            color: #ff6b6b;
        }
        
        .status-message {
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        
        .status-detail {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.75rem;
            font-family: monospace;
        }
        
        /* Progress Bar */
        .progress-container {
            margin-top: 15px;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #ff0000, #8b5cf6);
            width: 0%;
            transition: width 0.3s ease;
            animation: shimmer 1s infinite;
        }
        
        @keyframes shimmer {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        /* Features */
        .features {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }
        
        .feature {
            background: rgba(255, 255, 255, 0.03);
            padding: 15px;
            border-radius: 20px;
            text-align: center;
            transition: all 0.3s;
        }
        
        .feature:hover {
            background: rgba(255, 0, 0, 0.1);
            transform: translateY(-3px);
        }
        
        .feature i {
            font-size: 1.8rem;
            background: linear-gradient(135deg, #ff0000, #8b5cf6);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 8px;
            display: inline-block;
        }
        
        .feature h4 {
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 4px;
            color: #fff;
        }
        
        .feature p {
            font-size: 0.65rem;
            color: rgba(255, 255, 255, 0.5);
        }
        
        /* Footer */
        .footer {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            text-align: center;
            font-size: 0.7rem;
            color: rgba(255, 255, 255, 0.4);
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .quality-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
            .features { grid-template-columns: repeat(2, 1fr); }
            .header { padding: 30px 20px; }
            .content { padding: 25px; }
            h1 { font-size: 2rem; }
            .logo { font-size: 3rem; }
        }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    
    <div class="container">
        <div class="main-card">
            <div class="header">
                <i class="fas fa-download logo"></i>
                <h1>TDownTloader</h1>
                <p class="tagline">Professional YouTube Video Downloader</p>
                <div class="ffmpeg-status">
                    <i class="fas fa-{{ 'check-circle' if ffmpeg_available else 'exclamation-triangle' }}"></i>
                    FFmpeg: {{ 'Available' if ffmpeg_available else 'Missing' }}
                </div>
            </div>
            
            <div class="content">
                <div class="url-input-wrapper">
                    <div class="url-icon"><i class="fab fa-youtube"></i></div>
                    <input type="text" id="videoUrl" placeholder="Paste YouTube URL here...">
                </div>
                
                <div class="quality-section">
                    <div class="section-title">
                        <i class="fas fa-hd"></i>
                        <span>Select Quality</span>
                    </div>
                    <div class="quality-grid">
                        <div class="quality-card">
                            <input type="radio" name="quality" id="q360" value="360p">
                            <label for="q360" class="quality-label">
                                <div class="quality-name">360p</div>
                                <div class="quality-desc">Small file</div>
                            </label>
                        </div>
                        <div class="quality-card">
                            <input type="radio" name="quality" id="q480" value="480p">
                            <label for="q480" class="quality-label">
                                <div class="quality-name">480p</div>
                                <div class="quality-desc">Standard</div>
                            </label>
                        </div>
                        <div class="quality-card">
                            <input type="radio" name="quality" id="q720" value="720p" checked>
                            <label for="q720" class="quality-label">
                                <div class="quality-name">720p</div>
                                <div class="quality-desc">HD</div>
                            </label>
                        </div>
                        <div class="quality-card">
                            <input type="radio" name="quality" id="q1080" value="1080p" {{ 'disabled' if not ffmpeg_available else '' }}>
                            <label for="q1080" class="quality-label" style="{{ 'opacity: 0.5;' if not ffmpeg_available else '' }}">
                                <div class="quality-name">1080p</div>
                                <div class="quality-desc">Full HD</div>
                                {% if not ffmpeg_available %}
                                <div class="badge-ffmpeg">Requires FFmpeg</div>
                                {% endif %}
                            </label>
                        </div>
                    </div>
                </div>
                
                <button class="download-btn" id="downloadBtn">
                    <i class="fas fa-download"></i> Download Video
                </button>
                
                <div class="status-card" id="statusCard">
                    <div class="status-header">
                        <i class="fas fa-info-circle"></i>
                        <span>Status</span>
                    </div>
                    <div class="status-message" id="statusMessage">
                        Ready to download
                    </div>
                    <div class="status-detail" id="statusDetail">
                        Paste a YouTube URL and select quality
                    </div>
                    <div class="progress-container" id="progressContainer">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                    </div>
                </div>
                
                <div class="features">
                    <div class="feature">
                        <i class="fas fa-video"></i>
                        <h4>Multiple Qualities</h4>
                        <p>360p to 1080p</p>
                    </div>
                    <div class="feature">
                        <i class="fas fa-bolt"></i>
                        <h4>Fast Download</h4>
                        <p>Optimized speed</p>
                    </div>
                    <div class="feature">
                        <i class="fas fa-shield-alt"></i>
                        <h4>Secure</h4>
                        <p>No registration</p>
                    </div>
                    <div class="feature">
                        <i class="fas fa-save"></i>
                        <h4>MP4 Format</h4>
                        <p>Universal</p>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <i class="fas fa-copyright"></i> TDownTloader • High Quality YouTube Downloader
            </div>
        </div>
    </div>
    
    <script>
        // Create particles
        function createParticles() {
            for (let i = 0; i < 50; i++) {
                const particle = document.createElement('div');
                particle.classList.add('particle');
                const size = Math.random() * 4 + 1;
                particle.style.width = size + 'px';
                particle.style.height = size + 'px';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.top = Math.random() * 100 + '%';
                particle.style.animation = `float ${Math.random() * 10 + 10}s linear infinite`;
                document.body.appendChild(particle);
            }
        }
        createParticles();
        
        let currentDownloadId = null;
        let statusInterval = null;
        
        const statusMessage = document.getElementById('statusMessage');
        const statusDetail = document.getElementById('statusDetail');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const downloadBtn = document.getElementById('downloadBtn');
        const videoUrlInput = document.getElementById('videoUrl');
        
        function updateStatus(type, message, detail) {
            statusMessage.innerHTML = message;
            if (detail) statusDetail.innerHTML = detail;
        }
        
        function showProgress(show) {
            if (show) {
                progressContainer.style.display = 'block';
                let width = 0;
                const interval = setInterval(() => {
                    if (width < 90) {
                        width += Math.random() * 8;
                        progressFill.style.width = Math.min(width, 90) + '%';
                    } else {
                        clearInterval(interval);
                    }
                }, 800);
            } else {
                progressContainer.style.display = 'none';
                progressFill.style.width = '0%';
            }
        }
        
        async function checkStatus() {
            if (!currentDownloadId) return;
            try {
                const response = await fetch(`/api/status/${currentDownloadId}`);
                const data = await response.json();
                if (data.status === 'completed') {
                    clearInterval(statusInterval);
                    showProgress(false);
                    updateStatus('✅ Download Complete!', `Downloading: ${data.filename}`);
                    setTimeout(() => {
                        window.location.href = `/downloads/${encodeURIComponent(data.filename)}`;
                        setTimeout(() => {
                            updateStatus('Ready to download', 'Paste another URL');
                            downloadBtn.disabled = false;
                            downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Video';
                            currentDownloadId = null;
                        }, 2000);
                    }, 1000);
                } else if (data.status === 'error') {
                    clearInterval(statusInterval);
                    showProgress(false);
                    updateStatus('❌ ' + data.message, data.error || 'Try a different quality');
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Video';
                    currentDownloadId = null;
                } else if (data.status === 'downloading') {
                    statusDetail.innerHTML = '⏳ ' + data.message;
                }
            } catch (error) {
                console.error('Status error:', error);
            }
        }
        
        async function downloadVideo(url, quality) {
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, quality: quality })
                });
                const data = await response.json();
                if (data.success) {
                    currentDownloadId = data.download_id;
                    updateStatus(`⏳ Downloading ${quality}...`, 'Processing, please wait');
                    showProgress(true);
                    statusInterval = setInterval(checkStatus, 2000);
                } else {
                    throw new Error(data.error || 'Download failed');
                }
            } catch (error) {
                updateStatus('❌ Connection Error', 'Make sure server is running: python app.py');
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Video';
                showProgress(false);
            }
        }
        
        downloadBtn.addEventListener('click', () => {
            const url = videoUrlInput.value.trim();
            const quality = document.querySelector('input[name="quality"]:checked').value;
            if (!url) { updateStatus('❌ Enter a URL', ''); return; }
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<div class="spinner"></div> Processing...';
            downloadVideo(url, quality);
        });
        
        videoUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') downloadBtn.click();
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, ffmpeg_available=FFMPEG_AVAILABLE)

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '720p')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    download_id = str(uuid.uuid4())
    thread = threading.Thread(target=download_video_thread, args=(url, download_id, quality))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'download_id': download_id})

@app.route('/api/status/<download_id>', methods=['GET'])
def get_status(download_id):
    status = download_status.get(download_id)
    if not status:
        return jsonify({'status': 'pending'})
    return jsonify(status)

@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    print("=" * 60)
    print("   🎬 TDownTloader - YouTube Downloader")
    print("=" * 60)
    print(f"\n✅ Server running at: http://localhost:5000")
    print(f"📁 Downloads folder: {os.path.abspath(DOWNLOAD_FOLDER)}")
    print(f"\n🔧 FFmpeg: {'✅ Available (1080p works!)' if FFMPEG_AVAILABLE else '❌ Missing (1080p disabled)'}")
    if not FFMPEG_AVAILABLE:
        print("\n⚠️  To enable 1080p:")
        print("   1. Copy ffmpeg.exe to this folder")
        print("   2. Restart the server")
    print("\n🌐 Open: http://localhost:5000")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)