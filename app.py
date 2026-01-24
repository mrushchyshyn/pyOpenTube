import http.server
import socketserver
import os
import json
import uuid
import random
import sys
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# ==========================================
#               CONFIGURATION
# ==========================================
PORT = 8000
UPLOAD_FOLDER = 'static/videos'
DB_FILE = 'videos.json'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB Limit
VIDEOS_PER_PAGE = 12

# Ensure necessary directories exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ==========================================
#           DATABASE HELPERS
# ==========================================
def get_db():
    """Reads the JSON database and returns a list of videos."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_db(videos):
    """Writes the list of videos back to the JSON file."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=4)

# ==========================================
#           CSS & STYLING
# ==========================================
CSS = """
<style>
    /* --- VARIABLES (Dark/Light Mode) --- */
    :root {
        --primary: #cc0000;
        --bg: #f9f9f9;
        --nav: #ffffff;
        --card: #ffffff;
        --text: #0f0f0f;
        --text-sec: #606060;
        --border: #e5e5e5;
        --hover: #f2f2f2;
        --inp: #ffffff;
        --desc: #f2f2f2;
    }
    
    body.dark-theme {
        --primary: #ff4d4d;
        --bg: #181818;
        --nav: #202020;
        --card: #202020;
        --text: #ffffff;
        --text-sec: #aaaaaa;
        --border: #383838;
        --hover: #383838;
        --inp: #121212;
        --desc: #383838;
    }

    /* --- GLOBAL RESET --- */
    body {
        font-family: "Roboto", Arial, sans-serif;
        background: var(--bg);
        margin: 0;
        padding: 0;
        color: var(--text);
        padding-top: 60px; /* Space for fixed navbar */
        transition: background 0.2s, color 0.2s;
    }

    /* --- NAVBAR --- */
    nav {
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 56px;
        background: var(--nav);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        z-index: 1000;
        border-bottom: 1px solid var(--border);
    }
    .logo {
        font-size: 1.2rem;
        font-weight: bold;
        color: var(--text);
        text-decoration: none;
        display: flex;
        align-items: center;
        letter-spacing: -1px;
    }
    .logo span.icon {
        color: white;
        background: #cc0000;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 4px;
        display: inline-block;
        height: 20px;
        line-height: 20px;
        font-size: 0.9rem;
        position: relative;
        top: -1px;
    }
    
    /* Hide text on mobile, keep icon */
    @media (max-width: 600px) { 
        .logo-text { display: none; } 
    }

    /* --- SEARCH BAR --- */
    .search-form {
        flex: 1;
        max-width: 600px;
        margin: 0 20px;
        display: flex;
    }
    .search-form input {
        width: 100%;
        padding: 8px 15px;
        border: 1px solid var(--border);
        background: var(--inp);
        color: var(--text);
        border-radius: 20px 0 0 20px;
        font-size: 1rem;
        outline: none;
    }
    .search-form button {
        padding: 8px 20px;
        background: var(--hover);
        border: 1px solid var(--border);
        border-left: none;
        border-radius: 0 20px 20px 0;
        cursor: pointer;
        color: var(--text);
    }

    /* --- BUTTONS --- */
    .action-btn {
        background: var(--hover);
        color: var(--text);
        padding: 8px 15px;
        text-decoration: none;
        border-radius: 18px;
        font-weight: 500;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 5px;
        border: none;
        cursor: pointer;
    }
    .action-btn:hover { background: var(--border); }

    .btn-primary {
        background: #cc0000;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 2px;
        cursor: pointer;
        font-weight: 500;
    }

    /* --- LAYOUT --- */
    .main-container {
        padding: 20px;
        display: flex;
        gap: 20px;
    }
    .sidebar {
        width: 240px;
        display: none; /* Hidden on mobile */
        flex-direction: column;
        gap: 5px;
        position: fixed;
        top: 70px;
        bottom: 0;
        left: 0;
        padding: 0 10px;
        overflow-y: auto;
    }
    .content {
        flex: 1;
        min-height: 80vh;
    }

    @media (min-width: 1000px) {
        .sidebar { display: flex; }
        .content { margin-left: 240px; }
    }

    /* --- SIDEBAR LINKS --- */
    .sidebar a {
        padding: 10px 20px;
        text-decoration: none;
        color: var(--text);
        border-radius: 10px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .sidebar a:hover { background: var(--hover); }
    .sidebar a.active { background: var(--hover); font-weight: bold; }

    /* --- MOBILE BOTTOM NAV --- */
    .mobile-nav {
        display: none;
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: var(--nav);
        border-top: 1px solid var(--border);
        height: 60px;
        z-index: 1000;
        justify-content: space-around;
        align-items: center;
    }
    .mobile-nav a {
        flex: 1;
        text-align: center;
        text-decoration: none;
        color: var(--text-sec);
        font-size: 0.75rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .mobile-nav a span { font-size: 1.2rem; margin-bottom: 4px; }
    .mobile-nav a.active { color: var(--text); font-weight: bold; }

    @media (max-width: 1000px) {
        .mobile-nav { display: flex; }
        body { padding-bottom: 70px; }
    }

    /* --- VIDEO GRID --- */
    .video-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
    }
    .video-card {
        cursor: pointer;
        text-decoration: none;
        color: inherit;
        display: block;
    }
    .thumbnail-container {
        width: 100%;
        aspect-ratio: 16/9;
        background: black;
        border-radius: 12px;
        overflow: hidden;
        position: relative;
    }
    .home-video {
        width: 100%;
        height: 100%;
        object-fit: cover;
        pointer-events: none;
    }
    .video-info { margin-top: 10px; }
    
    /* Truncate Titles */
    .details .title {
        font-weight: bold;
        font-size: 1rem;
        line-height: 1.4;
        margin-bottom: 4px;
        color: var(--text);
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: break-word;
    }
    .meta-text { font-size: 0.85rem; color: var(--text-sec); }

    /* --- LOAD MORE BUTTON --- */
    .load-more-container { text-align: center; margin-top: 40px; margin-bottom: 40px; }
    .load-more-btn {
        padding: 10px 30px;
        background: var(--card);
        border: 1px solid var(--border);
        color: var(--primary);
        font-weight: bold;
        border-radius: 24px;
        cursor: pointer;
        font-size: 1rem;
        transition: 0.2s;
    }
    .load-more-btn:hover { background: var(--hover); }

    /* --- WATCH PAGE --- */
    .watch-container {
        max-width: 1280px;
        margin: 0 auto;
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        padding: 0 20px;
    }
    .primary-col { flex: 1; min-width: 60%; }
    .secondary-col { width: 350px; flex-shrink: 0; }
    
    @media (max-width: 1000px) {
        .watch-container { flex-direction: column; }
        .secondary-col { width: 100%; }
    }

    .video-player-large {
        width: 100%;
        aspect-ratio: 16/9;
        background: black;
        display: block;
        border-radius: 12px;
    }
    .watch-meta { margin-top: 15px; }
    .watch-header { display: flex; justify-content: space-between; align-items: flex-start; }
    .watch-title { font-size: 1.25rem; font-weight: bold; margin-bottom: 10px; margin-top: 0; }
    .watch-desc-box {
        background: var(--desc);
        padding: 12px;
        border-radius: 12px;
        font-size: 0.9rem;
        margin-top: 15px;
    }
    .watch-stats { font-weight: bold; margin-bottom: 8px; color: var(--text); font-size: 0.9rem; }
    .watch-text { white-space: pre-wrap; color: var(--text); line-height: 1.4; }

    /* --- SUGGESTIONS --- */
    .suggested-card {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
        text-decoration: none;
        color: inherit;
    }
    .suggested-thumb {
        width: 168px;
        height: 94px;
        background: black;
        border-radius: 8px;
        flex-shrink: 0;
        overflow: hidden;
    }
    .suggested-thumb video { width: 100%; height: 100%; object-fit: cover; pointer-events: none; }
    .suggested-details h4 {
        margin: 0 0 4px 0;
        font-size: 0.9rem;
        line-height: 1.4;
        font-weight: 500;
        color: var(--text);
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        word-break: break-word;
    }

    /* --- UPLOAD & SETTINGS --- */
    .upload-container, .settings-section {
        max-width: 600px;
        margin: 40px auto;
        background: var(--card);
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .form-group { margin-bottom: 20px; }
    label { display: block; margin-bottom: 8px; font-weight: 500; color: var(--text); }
    input[type="text"], textarea {
        width: 100%;
        padding: 10px;
        border: 1px solid var(--border);
        border-radius: 4px;
        box-sizing: border-box;
        background: var(--inp);
        color: var(--text);
    }
    .setting-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 0;
        border-bottom: 1px solid var(--border);
    }
    /* --- COMMENTS SECTION --- */
    .comments-section { 
        margin-top: 24px; 
        border-top: 1px solid var(--border); 
        padding-top: 20px; 
    }
    .comment-form { 
        display: flex; 
        flex-direction: column; 
        gap: 10px; 
        margin-bottom: 30px; 
    }
    .comment-form textarea { 
        resize: none; 
        border-radius: 8px; 
        padding: 12px; 
    }
    .comment-item { 
        display: flex; 
        gap: 12px; 
        margin-bottom: 20px; 
    }
    .comment-avatar { 
        width: 40px; height: 40px; background: var(--primary); 
        color: white; border-radius: 50%; display: flex; 
        align-items: center; justify-content: center; font-weight: bold; 
    }
    .comment-content { 
        flex: 1; 
    }
    .comment-author { 
        font-size: 0.85rem; 
        font-weight: bold; 
        margin-bottom: 4px; 
    }
    .comment-text { 
        font-size: 0.95rem; 
        line-height: 1.4; 
    }
    .comment-date { 
        font-size: 0.8rem; 
        color: var(--text-sec); 
        margin-left: 8px; 
        font-weight: normal; 
    }
</style>

<script>
    /* --- THEME LOGIC --- */
    (function() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.documentElement.classList.add('dark-theme');
            window.addEventListener('DOMContentLoaded', () => {
                document.body.classList.add('dark-theme');
            });
        }
    })();

    function toggleTheme() {
        const isDark = document.body.classList.toggle('dark-theme');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        const btn = document.getElementById('theme-btn-text');
        if(btn) btn.innerText = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
</script>
"""

# ==========================================
#           HTML RENDERERS
# ==========================================

def render_base(content, path='/', query=''):
    """ Wraps content in the main HTML layout (Navbar + Sidebar + Mobile Nav) """
    active = lambda p: 'active' if path == p else ''
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>pyOpenTube</title>
    {CSS}
</head>
<body>
    <nav>
        <a href="/" class="logo">
            <span class="icon">▶</span> 
            <span class="logo-text">Tube</span>
        </a>
        
        <form action="/" method="GET" class="search-form">
            <input type="text" name="q" placeholder="Search" value="{query}">
            <button type="submit">🔍</button>
        </form>
        
        <a href="/upload" class="action-btn"><span>+</span> Create</a>
    </nav>

    <div class="main-container">
        <aside class="sidebar">
            <a href="/" class="{active('/')}">🏠 Home</a>
            <a href="/top" class="{active('/top')}">🔥 Top</a>
            <a href="/saved" class="{active('/saved')}">📂 Saved</a>
            <hr style="border:0; border-top:1px solid var(--border); width:90%;">
            <a href="/settings" class="{active('/settings')}">⚙️ Settings</a>
        </aside>

        <main class="content">
            {content}
        </main>
    </div>

    <div class="mobile-nav">
        <a href="/" class="{active('/')}"><span>🏠</span> Home</a>
        <a href="/top" class="{active('/top')}"><span>🔥</span> Top</a>
        <a href="/saved" class="{active('/saved')}"><span>📂</span> Saved</a>
        <a href="/settings" class="{active('/settings')}"><span>⚙️</span> Settings</a>
    </div>
</body>
</html>
"""

def render_card(v):
    """ Generates HTML for a single video card """
    views = v.get('views', 0)
    return f"""
    <a href="/watch/{v['id']}" class="video-card">
        <div class="thumbnail-container">
            <video class="home-video" preload="metadata">
                <source src="/static/videos/{v['filename']}#t=1">
            </video>
        </div>
        <div class="video-info">
            <div class="details">
                <div class="title">{v['title']}</div>
                <div class="meta-text">{views} views • {v['date']}</div>
            </div>
        </div>
    </a>
    """

def render_index(videos, page_title, has_next, sort_type, query):
    """ Renders the main grid (Home/Top/Search) """
    if videos:
        grid_html = "".join([render_card(v) for v in videos])
    else:
        grid_html = """
        <div style="grid-column: 1/-1; text-align: center; margin-top: 50px;">
            <h3>No videos found.</h3>
            <p><a href="/upload">Upload one</a> to get started.</p>
        </div>
        """
    
    load_btn = ""
    if has_next:
        load_btn = """
        <div class="load-more-container">
            <button id="load-more-btn" class="load-more-btn">Load More</button>
        </div>
        """
    
    script = f"""
    <script>
        let currentPage = 1;
        const currentSort = "{sort_type}";
        const currentQuery = "{query}";
        const loadBtn = document.getElementById('load-more-btn');
        const grid = document.getElementById('main-grid');

        if(loadBtn) {{
            loadBtn.addEventListener('click', function() {{
                currentPage++;
                fetch(`/api/load_more?page=${{currentPage}}&type=${{currentSort}}&q=${{currentQuery}}`)
                    .then(r => r.json())
                    .then(data => {{
                        if(data.length > 0) {{
                            data.forEach(v => {{
                                const html = `<a href="/watch/${{v.id}}" class="video-card">
                                    <div class="thumbnail-container">
                                        <video class="home-video" preload="metadata">
                                            <source src="/static/videos/${{v.filename}}#t=1">
                                        </video>
                                    </div>
                                    <div class="video-info"><div class="details">
                                        <div class="title">${{v.title}}</div>
                                        <div class="meta-text">${{v.views||0}} views • ${{v.date}}</div>
                                    </div></div>
                                </a>`;
                                grid.insertAdjacentHTML('beforeend', html);
                            }});
                            if(data.length < {VIDEOS_PER_PAGE}) loadBtn.style.display = 'none';
                        }} else {{ 
                            loadBtn.style.display = 'none'; 
                        }}
                    }});
            }});
        }}
    </script>
    """
    
    content = f"""
        <h2 style="margin-top:0; margin-bottom:20px;">{page_title}</h2>
        <div id="main-grid" class="video-grid">{grid_html}</div>
        {load_btn}
        {script}
    """
    path = '/' if sort_type == 'latest' else '/top'
    return render_base(content, path=path, query=query)

def render_watch(video, suggestions):
    """ Renders the Watch page with Comments """
    recs_html = "".join([f"""
        <a href="/watch/{v['id']}" class="suggested-card">
            <div class="suggested-thumb">
                <video preload="metadata"><source src="/static/videos/{v['filename']}#t=1"></video>
            </div>
            <div class="suggested-details">
                <h4>{v['title']}</h4>
                <div class="meta-text">{v.get('views',0)} views • {v['date']}</div>
            </div>
        </a>""" for v in suggestions])

    # Генерація списку коментарів
    comments_list = video.get('comments', [])
    comments_html = "".join([f"""
        <div class="comment-item">
            <div class="comment-avatar">{c['author'][0].upper()}</div>
            <div class="comment-content">
                <div class="comment-author">{c['author']} <span class="comment-date">{c['date']}</span></div>
                <div class="comment-text">{c['text']}</div>
            </div>
        </div>""" for c in reversed(comments_list)])

    content = f"""
    <div class="watch-container">
        <div class="primary-col">
            <video class="video-player-large" controls autoplay>
                <source src="/static/videos/{video['filename']}" type="video/mp4">
            </video>
            <div class="watch-meta">
                <div class="watch-header">
                    <h1 class="watch-title">{video['title']}</h1>
                    <button id="save-btn" class="action-btn" onclick="toggleSave('{video['id']}')">🔖 Save</button>
                </div>
                <div class="watch-desc-box">
                    <div class="watch-stats">{video.get('views', 0)} views • {video['date']}</div>
                    <div class="watch-text">{video['description']}</div>
                </div>
            </div>

            <div class="comments-section">
                <h3>{len(comments_list)} Comments</h3>
                <div class="comment-form">
                    <input type="text" id="comment-author" placeholder="Your name" style="margin-bottom:10px; width:200px;">
                    <textarea id="comment-text" rows="3" placeholder="Add a comment..."></textarea>
                    <button class="btn-primary" style="align-self: flex-end; margin-top:10px;" onclick="submitComment('{video['id']}')">Comment</button>
                </div>
                <div id="comments-container">{comments_html}</div>
            </div>
        </div>
        <div class="secondary-col">
            <h3 style="margin-top: 0;">Recommended</h3>
            {recs_html}
        </div>
    </div>
    <script>
        function submitComment(videoId) {{
            const author = document.getElementById('comment-author').value || "Anonymous";
            const text = document.getElementById('comment-text').value;
            if(!text) return;

            fetch('/api/comment', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ video_id: videoId, author: author, text: text }})
            }}).then(r => r.json()).then(data => {{
                if(data.success) location.reload(); 
            }});
        }}
        
        function checkSaveStatus(id) {{
            const saved = JSON.parse(localStorage.getItem('savedVideos')||'[]');
            const btn = document.getElementById('save-btn');
            if(saved.includes(id)) {{ 
                btn.innerHTML='✅ Saved'; btn.style.background='var(--border)'; 
            }}
        }}
        checkSaveStatus('{video['id']}');
    </script>
    """
    return render_base(content, path='/watch')

def render_upload():
    content = """
    <div class="upload-container">
        <h2>Upload Video</h2>
        <form method="POST" enctype="multipart/form-data" action="/upload">
            <div class="form-group">
                <label>Title</label>
                <input type="text" name="title" required>
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="description" rows="5"></textarea>
            </div>
            <div class="form-group">
                <label>File</label>
                <input type="file" name="file" accept="video/*" required>
            </div>
            <button type="submit" class="btn-primary">Publish</button>
        </form>
    </div>
    """
    return render_base(content, path='/upload')

def render_saved():
    """ Renders Saved Videos with Client-Side Pagination (Load More) """
    content = """
    <h2 style="margin-top:0; margin-bottom:20px;">Saved Videos</h2>
    <div id="saved-grid" class="video-grid"></div>
    
    <div class="load-more-container" style="display:none;" id="saved-load-container">
        <button id="saved-load-btn" class="load-more-btn">Load More</button>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const VIDEOS_PER_PAGE = 12;
            let currentPage = 1;
            let allSavedIds = [];

            const container = document.getElementById('saved-grid');
            const loadContainer = document.getElementById('saved-load-container');
            const loadBtn = document.getElementById('saved-load-btn');

            // 1. Load all IDs from storage and REVERSE them (Newest first)
            allSavedIds = JSON.parse(localStorage.getItem('savedVideos')||'[]').reverse();

            if(allSavedIds.length === 0) { 
                container.innerHTML='<p>No videos saved.</p>'; 
                return; 
            }

            // Function to load a specific batch
            function loadBatch(page) {
                const start = (page - 1) * VIDEOS_PER_PAGE;
                const end = start + VIDEOS_PER_PAGE;
                const batchIds = allSavedIds.slice(start, end);

                if (batchIds.length === 0) {
                    loadContainer.style.display = 'none';
                    return;
                }

                fetch('/api/videos?ids=' + batchIds.join(','))
                    .then(r => r.json())
                    .then(videos => {
                        // Map for preserving order
                        const videoMap = new Map(videos.map(v => [v.id, v]));
                        
                        let html = '';
                        batchIds.forEach(id => {
                            const v = videoMap.get(id);
                            if (v) {
                                html += `<a href="/watch/${v.id}" class="video-card">
                                    <div class="thumbnail-container">
                                        <video class="home-video" preload="metadata">
                                            <source src="/static/videos/${v.filename}#t=1">
                                        </video>
                                    </div>
                                    <div class="video-info">
                                        <div class="details">
                                            <div class="title">${v.title}</div>
                                            <div class="meta-text">${v.views||0} views • ${v.date}</div>
                                        </div>
                                    </div>
                                </a>`;
                            }
                        });

                        // Append to grid
                        container.insertAdjacentHTML('beforeend', html);

                        // Check if we need the button
                        if (end < allSavedIds.length) {
                            loadContainer.style.display = 'block';
                        } else {
                            loadContainer.style.display = 'none';
                        }
                    });
            }

            // Initial Load
            loadBatch(1);

            // Button Click Event
            loadBtn.addEventListener('click', function() {
                currentPage++;
                loadBatch(currentPage);
            });
        });
    </script>
    """
    return render_base(content, path='/saved')

def render_settings():
    content = """
    <div class="settings-section">
        <h2 style="border-bottom:1px solid var(--border); padding-bottom:10px;">Settings</h2>
        
        <div class="setting-item">
            <div>
                <strong>Appearance</strong>
                <p style="margin:5px 0; font-size:0.9rem; color:var(--text-sec);">Toggle Light/Dark theme</p>
            </div>
            <button class="action-btn" onclick="toggleTheme()">
                <span id="theme-btn-text">Switch Theme</span>
            </button>
        </div>

        <div class="setting-item">
            <div>
                <strong>Data</strong>
                <p style="margin:5px 0; font-size:0.9rem; color:var(--text-sec);">Clear saved videos</p>
            </div>
            <button class="action-btn" style="color:#cc0000;" onclick="localStorage.removeItem('savedVideos'); alert('Cleared!'); location.reload();">
                Clear Data
            </button>
        </div>
    </div>
    <script>
        const isDark = document.body.classList.contains('dark-theme');
        document.getElementById('theme-btn-text').innerText = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    </script>
    """
    return render_base(content, path='/settings')

# ==========================================
#           HTTP REQUEST HANDLER
# ==========================================

class VideoHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """ Handle GET requests (Pages, API, Static Files) """
        url = urlparse(self.path)
        path = url.path
        query = parse_qs(url.query)
        q_str = query.get('q', [''])[0]

        # 1. Serve Static Files (Videos)
        if path.startswith('/static/'):
            self.path = path.lstrip('/') 
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        # 2. API: Load More Videos (Server Side)
        if path == '/api/load_more':
            page = int(query.get('page', [1])[0])
            sort_type = query.get('type', ['latest'])[0]
            
            videos = get_db()
            # Filter
            if q_str: videos = [v for v in videos if q_str.lower() in v['title'].lower()]
            # Sort
            if sort_type == 'top': videos.sort(key=lambda x: x.get('views', 0), reverse=True)
            
            # Slice
            start = (page - 1) * VIDEOS_PER_PAGE
            end = start + VIDEOS_PER_PAGE
            chunk = videos[start:end]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(chunk).encode())
            return

        # 3. API: Get Specific Videos (for Saved page)
        if path == '/api/videos':
            ids = query.get('ids', [''])[0].split(',')
            all_videos = get_db()
            selected = [v for v in all_videos if v['id'] in ids]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(selected).encode())
            return

        # 4. Page Routes
        html_content = ""
        
        if path == '/' or path == '/index':
            videos = get_db()
            if q_str: videos = [v for v in videos if q_str.lower() in v['title'].lower()]
            has_next = len(videos) > VIDEOS_PER_PAGE
            chunk = videos[:VIDEOS_PER_PAGE]
            title = f"Search results for '{q_str}'" if q_str else "Latest Videos"
            html_content = render_index(chunk, title, has_next, 'latest', q_str)

        elif path == '/top':
            videos = get_db()
            videos.sort(key=lambda x: x.get('views', 0), reverse=True)
            chunk = videos[:50] # Only show top 50
            html_content = render_index(chunk, "Top 50 Videos", False, 'top', q_str)

        elif path == '/saved':
            html_content = render_saved()

        elif path == '/settings':
            html_content = render_settings()

        elif path == '/upload':
            html_content = render_upload()

        elif path.startswith('/watch/'):
            vid_id = path.split('/')[-1]
            all_videos = get_db()
            video = next((v for v in all_videos if v['id'] == vid_id), None)
            
            if video:
                # Increment Views
                video['views'] = video.get('views', 0) + 1
                save_db(all_videos)
                
                # Random Recommendations
                others = [v for v in all_videos if v['id'] != vid_id]
                suggestions = random.sample(others, min(len(others), 10)) if others else []
                html_content = render_watch(video, suggestions)
            else:
                html_content = "<h1>Video not found</h1>"
        else:
            self.send_error(404, "Page Not Found")
            return

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode())

    def do_POST(self):
        """ Handle File Uploads manually (since http.server is basic) """
        if self.path == '/upload':
            content_type = self.headers['Content-Type']
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Bad Request")
                return

            # Parse Boundary and Content Length
            boundary = content_type.split("boundary=")[1].encode()
            remain_bytes = int(self.headers['Content-Length'])
            
            # Read first boundary line
            line = self.rfile.readline()
            remain_bytes -= len(line)
            if not boundary in line:
                self.send_error(400, "Content does not begin with boundary")
                return

            form_data = {'title': '', 'description': '', 'filename': ''}
            
            # Loop through parts
            while remain_bytes > 0:
                line = self.rfile.readline()
                remain_bytes -= len(line)
                if boundary in line: break
                
                # Read Headers
                part_headers = {}
                while True:
                    h_line = line.decode().strip()
                    if not h_line: break
                    if ':' in h_line:
                        k, v = h_line.split(':', 1)
                        part_headers[k.lower()] = v.strip()
                    line = self.rfile.readline()
                    remain_bytes -= len(line)

                disp = part_headers.get('content-disposition', '')
                name_match = re.search(r'name="([^"]+)"', disp)
                filename_match = re.search(r'filename="([^"]+)"', disp)
                
                name = name_match.group(1) if name_match else None
                filename = filename_match.group(1) if filename_match else None

                # Read Body Data
                data = bytearray()
                while True:
                    line = self.rfile.readline()
                    remain_bytes -= len(line)
                    if boundary in line:
                        # Remove trailing CRLF
                        if data.endswith(b'\r\n'): data = data[:-2]
                        elif data.endswith(b'\n'): data = data[:-1]
                        break
                    data.extend(line)

                # Process Data
                if filename and name == 'file':
                    ext = filename.rsplit('.', 1)[-1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        unique_name = f"{uuid.uuid4()}.{ext}"
                        with open(os.path.join(UPLOAD_FOLDER, unique_name), 'wb') as f:
                            f.write(data)
                        form_data['filename'] = unique_name
                elif name:
                    form_data[name] = data.decode('utf-8')

            # Save to DB
            if form_data['filename']:
                new_video = {
                    'id': str(uuid.uuid4()),
                    'title': form_data['title'],
                    'description': form_data['description'],
                    'filename': form_data['filename'],
                    'date': datetime.now().strftime("%b %d, %Y"),
                    'views': 0
                }
                videos = get_db()
                videos.insert(0, new_video)
                save_db(videos)

            # Redirect
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        # comments post request
        if self.path == '/api/comment':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            videos = get_db()
            for v in videos:
                if v['id'] == data['video_id']:
                    if 'comments' not in v: v['comments'] = []
                    v['comments'].append({
                        'author': data['author'],
                        'text': data['text'],
                        'date': datetime.now().strftime("%b %d, %Y")
                    })
                    break
            save_db(videos)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
            return

# ==========================================
#           SERVER STARTUP
# ==========================================
class ThreadingSimpleServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

if __name__ == '__main__':
    HOST = '0.0.0.0'
    print("="*40)
    print(f"🚀 pyOpenTube Server Running!")
    print(f"🏠 Local:   http://127.0.0.1:{PORT}")
    print("="*40)
    
    server = ThreadingSimpleServer((HOST, PORT), VideoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
