import os, time
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 公開時にデータが消えない設定（Render用）
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(base_dir, 'study_final_v18.db'))
db = SQLAlchemy(app)

# --- DB定義 ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20))
    post_type = db.Column(db.String(20))
    content = db.Column(db.Text)
    answer = db.Column(db.Text)
    image_file = db.Column(db.Text)
    author = db.Column(db.String(50))
    likes = db.Column(db.Integer, default=0)
    is_help = db.Column(db.Boolean, default=False)
    date_posted = db.Column(db.DateTime, default=datetime.now)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(50))
    date_posted = db.Column(db.DateTime, default=datetime.now)

class AppUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    is_approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

class AdminConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(100), default='admin123')

with app.app_context():
    db.create_all()
    if not AdminConfig.query.first(): db.session.add(AdminConfig()); db.session.commit()

@app.route('/uploads/<filename>')
def uploaded_file(filename): return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

HTML_CODE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>StudyHub | Final</title>
    <style>
        :root { --bg: #0b1120; --side: #0f172a; --card: rgba(30, 41, 59, 0.7); --accent: #38bdf8; --text: #f1f5f9; --help: #facc15; --pink: #f472b6; --green: #10b981; }
        * { box-sizing: border-box; transition: all 0.3s ease; }
        body { font-family: sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        #gate { position: fixed; inset: 0; background: var(--bg); z-index: 5000; display: flex; align-items: center; justify-content: center; }
        .gate-box { background: var(--side); padding: 40px; border-radius: 30px; width: 400px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }

        .sidebar { width: 260px; background: #0f172a; border-right: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; }
        .sidebar-header { padding: 25px; color: var(--accent); font-weight: 900; font-size: 1.5em; text-align: center; }
        .nav-item { padding: 12px 20px; cursor: pointer; color: #94a3b8; font-weight: 600; border-radius: 12px; margin: 4px 15px; display: flex; align-items: center; gap: 10px; }
        .nav-item.active { background: rgba(56, 189, 248, 0.15); color: var(--accent); }
        .sub-menu { overflow: hidden; max-height: 0; padding-left: 15px; }
        .sub-menu.open { max-height: 300px; }
        .sub-item { padding: 10px 20px; cursor: pointer; font-size: 0.9em; color: #64748b; }

        .main { flex: 1; display: flex; flex-direction: column; background: radial-gradient(circle at top right, #1e293b, #050b18); position: relative; }
        .top-bar { padding: 20px 40px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
        .content-area { flex: 1; overflow-y: auto; padding: 30px 60px 150px; scroll-behavior: smooth; }

        .card { background: var(--card); border: 1px solid rgba(255,255,255,0.1); padding: 25px; border-radius: 25px; margin-bottom: 25px; backdrop-filter: blur(10px); }
        .btn { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 0.85em; font-weight: 600; }
        
        input, textarea, select { width: 100%; background: rgba(0,0,0,0.2); border: 1px solid #334155; color: white; padding: 15px; border-radius: 15px; margin-bottom: 10px; outline: none; }
        .hidden { display: none !important; }
        #modal, #post-modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center; backdrop-filter: blur(10px); }
    </style>
</head>
<body>
    <div id="gate">
        <div class="gate-box">
            <h2 id="g-msg">StudyHub ゲート</h2>
            <div id="g-form">
                <p style="font-size: 0.8em; color: #94a3b8;">名前を入力してください</p>
                <input type="text" id="g-name" placeholder="あなたの名前">
                <p style="font-size: 0.8em; color: #94a3b8; margin-top: 10px;">管理者のみ合言葉を入力（友達は空欄）</p>
                <input type="password" id="g-pass" placeholder="管理者パスワード">
                <button onclick="requestJoin()" class="btn" style="width:100%; background:var(--accent); color:var(--bg); padding:15px; margin-top:10px; font-weight: bold;">入室を申請する</button>
            </div>
            <p id="g-wait" class="hidden" style="color:var(--help); margin-top:20px;">申請を送りました。<br>管理者に承認してもらうまで、この画面で待機してね！</p>
        </div>
    </div>

    <div class="sidebar">
        <div class="sidebar-header">STUDYHUB</div>
        <div class="nav-item active" id="nav-home" onclick="showHome()">🏠 ホーム画面</div>
        {% for cat in ["数学", "英語", "理科", "社会", "国語"] %}
        <div class="nav-item" onclick="toggleMenu('{{ cat }}', this)">📂 {{ cat }}</div>
        <div class="sub-menu" id="sub-{{ cat }}">
            <div class="sub-item" onclick="view('{{ cat }}', 'Q', this)">🌟 良問リスト</div>
            <div class="sub-item" onclick="view('{{ cat }}', 'NOTE', this)">📝 授業ノート</div>
            <div class="sub-item" onclick="view('{{ cat }}', 'EXAM', this)">🎯 テスト予想</div>
        </div>
        {% endfor %}
        <div class="nav-item" onclick="view('CHAT', 'CHAT', this)" style="margin-top:auto; background:var(--green); color:white; justify-content:center; margin-bottom:20px;">💬 チャット</div>
    </div>

    <div class="main">
        <div class="top-bar">
            <h2 id="top-title" style="font-weight:900;">Home</h2>
            <div>
                <span id="admin-label" style="display:none; color:var(--help); margin-right:15px; font-weight:bold;">🛡️ ADMIN</span>
                <button onclick="document.getElementById('modal').style.display='flex'" style="background:none; border:none; color:white; cursor:pointer; font-size:1.5em;">⚙️</button>
            </div>
        </div>
        <div class="content-area" id="area"></div>
        <div id="chat-bar" style="display:none; padding:15px; background:var(--side);"><textarea id="chat-txt" placeholder="メッセージ..."></textarea><button onclick="sendChat()" class="btn" style="background:var(--green); color:white;">送信</button></div>
    </div>

    <button class="fab" id="fab" style="position:fixed; bottom:40px; right:40px; width:70px; height:70px; background:var(--accent); border-radius:50%; border:none; font-size:32px; color:var(--bg); cursor:pointer; z-index:100;" onclick="document.getElementById('post-modal').style.display='flex'">＋</button>

    <div id="post-modal"><div class="modal-body"><h2>NEW POST</h2><textarea id="p-content" class="round-input" rows="4"></textarea><input type="text" id="p-ans" class="round-input" placeholder="答え（任意）"><input type="file" id="p-file" class="hidden"><label for="p-file" style="cursor:pointer; color:var(--accent);">📸 画像を選択</label><button onclick="submitPost()" class="btn" style="width:100%; background:var(--accent); color:var(--bg); margin-top:20px;">送信</button><button onclick="document.getElementById('post-modal').style.display='none'" class="btn" style="width:100%; background:none; border:none; margin-top:10px;">閉じる</button></div></div>
    
    <div id="modal"><div class="modal-body"><h2>SETTINGS</h2><p id="my-name-display"></p><div id="admin-tools" class="hidden"><input type="password" id="new-pw" placeholder="新パスワード"><button onclick="changePw()" class="btn">保存</button></div><button onclick="document.getElementById('modal').style.display='none'" class="btn" style="width:100%; margin-top:20px;">閉じる</button></div></div>

    <script>
        let curC='HOME', curT='', isAdmin=false;
        const getMyName = () => localStorage.getItem('hub_name_v18');

        async function checkStatus() {
            const name = getMyName(); if(!name) return;
            const res = await fetch('/api/check?name='+name); const d = await res.json();
            if(d.approved) { 
                document.getElementById('gate').style.display='none'; 
                isAdmin = d.admin;
                if(isAdmin) { document.getElementById('admin-label').style.display='inline'; document.getElementById('admin-tools').classList.remove('hidden'); }
                document.getElementById('my-name-display').innerText = "名前: " + name;
                showHome(); 
            } else { document.getElementById('g-form').classList.add('hidden'); document.getElementById('g-wait').classList.remove('hidden'); }
        }

        async function requestJoin() {
            const name = document.getElementById('g-name').value;
            const pass = document.getElementById('g-pass').value;
            if(!name) return;
            localStorage.setItem('hub_name_v18', name);
            await fetch('/api/join', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name, pass}) });
            checkStatus();
        }

        setInterval(() => { if(document.getElementById('gate').style.display!=='none') checkStatus(); }, 3000);

        function toggleMenu(c, el) {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            el.classList.add('active');
            document.querySelectorAll('.sub-menu').forEach(m => m.id==='sub-'+c ? m.classList.toggle('open') : m.classList.remove('open'));
        }

        async function view(c, t, el) {
            curC=c; curT=t;
            document.querySelectorAll('.sub-item, .nav-item').forEach(i => i.classList.remove('active'));
            if(el) el.classList.add('active');
            document.getElementById('top-title').innerText = t==='CHAT'?"Chat":c+" / "+t;
            document.getElementById('chat-bar').style.display = t==='CHAT'?'block':'none';
            render();
        }

        async function render() {
            const res = await fetch('/api/posts'); const posts = await res.json();
            const a = document.getElementById('area'); a.innerHTML = "";
            if(curC==='HOME') {
                if(isAdmin) {
                    const users = await (await fetch('/api/pending')).json();
                    if(users.length>0) {
                        a.innerHTML += `<h3>👥 承認待ち</h3>`;
                        users.forEach(u => a.innerHTML += `<div class="card" style="display:flex; justify-content:space-between;"><span>${u}</span><button class="btn" onclick="approve('${u}')">承認</button></div>`);
                    }
                }
                a.innerHTML += `<h1>SOS Request</h1>`;
                posts.filter(p=>p.is_help).forEach(p=>a.innerHTML += `<div class="card"><b>${p.author}</b> が ${p.category} で困っています<br><button class="btn" onclick="view('${p.category}','${p.post_type}',null)">助ける</button></div>`);
                return;
            }
            posts.filter(p=>p.category===(curC==='CHAT'?'CHAT':curC) && (curC==='CHAT'||p.post_type===curT)).forEach(p=>{
                let h = `<div class="card"><small>${p.author} • ${p.time}</small><div>${p.content}</div>`;
                if(p.image_file) h += `<img src="/uploads/${p.image_file}" style="width:100%; border-radius:20px; margin-top:15px;">`;
                h += `<div style="margin-top:20px; display:flex; gap:10px;"><button class="btn">👍 ${p.likes}</button>`;
                if(isAdmin) h += `<button onclick="delP(${p.id})" class="btn" style="border-color:var(--pink);">🗑️ 削除</button>`;
                h += `</div></div>`; a.innerHTML += h;
            });
        }

        async function approve(n) { await fetch('/api/approve', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:n})}); render(); }
        async function delP(id) { if(confirm('消すよ？')) { await fetch('/api/del/'+id, {method:'POST'}); render(); } }
        async function submitPost() {
            const f = new FormData(); f.append('category', curC); f.append('post_type', curT); f.append('content', document.getElementById('p-content').value); f.append('author', getMyName());
            const file = document.getElementById('p-file').files[0]; if(file) f.append('file', file);
            await fetch('/api/post', { method:'POST', body:f }); document.getElementById('post-modal').style.display='none'; render();
        }
        function showHome() { curC='HOME'; document.getElementById('top-title').innerText="Home"; render(); }
        window.onload = checkStatus;
    </script>
</body>
</html>
"""

# --- API ---
@app.route('/')
def index(): return render_template_string(HTML_CODE)

@app.route('/api/join', methods=['POST'])
def join():
    d = request.get_json(); n = d.get('name'); p = d.get('pass')
    conf = AdminConfig.query.first()
    user = AppUser.query.filter_by(name=n).first()
    if not user:
        is_adm = (p == conf.password)
        db.session.add(AppUser(name=n, is_approved=is_adm, is_admin=is_adm))
        db.session.commit()
    return jsonify({'s':'ok'})

@app.route('/api/check')
def check():
    u = AppUser.query.filter_by(name=request.args.get('name')).first()
    return jsonify({'approved':u.is_approved if u else False, 'admin':u.is_admin if u else False})

@app.route('/api/pending')
def pending():
    return jsonify([u.name for u in AppUser.query.filter_by(is_approved=False).all()])

@app.route('/api/approve', methods=['POST'])
def approve():
    u = AppUser.query.filter_by(name=request.get_json().get('name')).first()
    if u: u.is_approved = True; db.session.commit()
    return jsonify({'s':'ok'})

@app.route('/api/posts')
def get_posts():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return jsonify([{'id':p.id,'category':p.category,'post_type':p.post_type,'content':p.content,'author':p.author,'likes':p.likes,'is_help':p.is_help,'time':p.date_posted.strftime('%H:%M'),'image_file':p.image_file} for p in posts])

@app.route('/api/post', methods=['POST'])
def post():
    file = request.files.get('file')
    fn = secure_filename(f"{time.time()}_{file.filename}") if file else None
    if file: file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
    db.session.add(Post(category=request.form.get('category'), post_type=request.form.get('post_type'), content=request.form.get('content'), author=request.form.get('author'), image_file=fn))
    db.session.commit(); return jsonify({'s':'ok'})

@app.route('/api/del/<int:id>', methods=['POST'])
def del_p(id):
    p = Post.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return jsonify({'s':'ok'})

if __name__ == '__main__':
    # 公開サーバー（Renderなど）で動かすためのPort設定
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
