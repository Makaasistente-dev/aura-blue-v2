import os
# -*- coding: utf-8 -*-
# ============================================================
#  AURA BLUE - Asistente Personal con IA
#  Para ejecutar: python3 app.py
#  Luego abre: http://localhost:5000
# ============================================================

from flask import Flask, render_template_string, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re

try:
    from groq import Groq
    GROQ_OK = True
except ImportError:
    GROQ_OK = False

# ── App ──────────────────────────────────────────────────────
GROQ_KEY = os.environ.get('GROQ_KEY', '')
ELEVEN_KEY = os.environ.get('ELEVEN_KEY', '')
ELEVEN_VOICE = '21m00Tcm4TlvDq8ikWAM'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aura-blue-2026-definitivo'
db_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/aura.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Crear tablas automáticamente al iniciar
with app.app_context():
    try:
        db.create_all()
        print('✅ Tablas creadas')
    except Exception as e:
        print(f'❌ Error tablas: {e}')
login_manager = LoginManager(app)
login_manager.login_view = '/'

# ── Modelos ───────────────────────────────────────────────────
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id       = db.Column(db.Integer, primary_key=True)
    nombre   = db.Column(db.String(80))
    email    = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    api_key  = db.Column(db.String(300), default='')

class Gasto(db.Model):
    __tablename__ = 'gastos'
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    concepto   = db.Column(db.String(100), default='Gasto')
    monto      = db.Column(db.Float)
    fecha      = db.Column(db.DateTime, default=datetime.utcnow)

class Recordatorio(db.Model):
    __tablename__ = 'recordatorios'
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    texto      = db.Column(db.String(300))
    fecha_hora = db.Column(db.DateTime)
    hecho      = db.Column(db.Boolean, default=False)

class Familiar(db.Model):
    __tablename__ = 'familiares'
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    nombre     = db.Column(db.String(80))
    telefono   = db.Column(db.String(30))

class Historial(db.Model):
    __tablename__ = 'historial'
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    rol        = db.Column(db.String(20))
    contenido  = db.Column(db.Text)
    fecha      = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid):
    return db.session.get(Usuario, int(uid))

# ══════════════════════════════════════════════════════════════
#  PÁGINA LOGIN
# ══════════════════════════════════════════════════════════════
HTML_LOGIN = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aura Blue</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;
  background:#000918;
  min-height:100vh;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:24px;
  overflow:hidden;
}
/* Fondo animado */
.bg{position:fixed;inset:0;z-index:0;overflow:hidden}
.bg-orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:.35;animation:drift 12s ease-in-out infinite}
.bg-orb:nth-child(1){width:400px;height:400px;background:#0044ff;top:-100px;left:-100px;animation-delay:0s}
.bg-orb:nth-child(2){width:350px;height:350px;background:#7700ff;bottom:-80px;right:-80px;animation-delay:-5s}
.bg-orb:nth-child(3){width:250px;height:250px;background:#00aaff;top:50%;left:50%;animation-delay:-9s}
@keyframes drift{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(30px,-30px) scale(1.1)}}

/* Contenido */
.wrap{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;width:100%;max-width:360px}

/* Orb */
.orb{
  width:100px;height:100px;border-radius:50%;
  background:radial-gradient(circle at 35% 30%,#88ddff,#0055ff 50%,#8833ff);
  box-shadow:0 0 40px #0077ff55,0 0 80px #0044ff22;
  animation:pulse 4s ease-in-out infinite;
  margin-bottom:20px;cursor:pointer;
}
@keyframes pulse{0%,100%{transform:scale(1);box-shadow:0 0 40px #0077ff55}
                 50%{transform:scale(1.07);box-shadow:0 0 70px #0099ffaa}}

h1{font-size:26px;font-weight:300;letter-spacing:8px;color:#99ccff;margin-bottom:32px}

/* Card */
.card{
  background:rgba(0,20,60,0.6);
  border:1px solid rgba(0,180,255,0.2);
  border-radius:22px;padding:32px;width:100%;
  backdrop-filter:blur(20px);
}
input{
  display:block;width:100%;padding:14px 16px;margin:8px 0;
  border-radius:12px;border:1px solid rgba(0,150,255,0.25);
  background:rgba(0,0,0,0.35);color:#fff;font-size:16px;outline:none;
  transition:border-color .2s;
}
input:focus{border-color:#00aaff;background:rgba(0,100,255,0.1)}
input::placeholder{color:#3a6a9a}
.btn{
  width:100%;padding:15px;margin-top:14px;border:none;border-radius:14px;
  background:linear-gradient(135deg,#00aaff,#0055ff);
  color:#fff;font-size:16px;font-weight:600;cursor:pointer;
  letter-spacing:1px;transition:opacity .2s;
}
.btn:hover{opacity:.88}
.link{text-align:center;margin-top:18px;color:#5588bb;font-size:14px;cursor:pointer}
.link:hover{color:#00aaff}
.error{color:#ff6677;font-size:13px;text-align:center;margin-top:10px;min-height:18px}
</style>
</head>
<body>
<div class="bg">
  <div class="bg-orb"></div>
  <div class="bg-orb"></div>
  <div class="bg-orb"></div>
</div>
<div class="wrap">
  <div class="orb"></div>
  <h1>AURA BLUE</h1>

  <!-- LOGIN -->
  <div class="card" id="box-login">
    <input id="l-email" type="email" placeholder="Tu email">
    <input id="l-pass"  type="password" placeholder="Contraseña">
    <button class="btn" onclick="doLogin()">Entrar</button>
    <p class="link" onclick="show('reg')">¿Primera vez? Crear cuenta →</p>
    <div class="error" id="err-login"></div>
  </div>

  <!-- REGISTRO -->
  <div class="card" id="box-reg" style="display:none">
    <input id="r-nom"   type="text"     placeholder="Tu nombre">
    <input id="r-email" type="email"    placeholder="Tu email">
    <input id="r-pass"  type="password" placeholder="Crea una contraseña">
    <button class="btn" onclick="doRegistro()">Crear cuenta</button>
    <p class="link" onclick="show('login')">← Ya tengo cuenta</p>
    <div class="error" id="err-reg"></div>
  </div>
</div>

<script>
function show(t){
  document.getElementById('box-login').style.display = t==='login' ? 'block':'none';
  document.getElementById('box-reg').style.display   = t==='reg'   ? 'block':'none';
}
async function doLogin(){
  const email=document.getElementById('l-email').value.trim();
  const pass =document.getElementById('l-pass').value;
  const err  =document.getElementById('err-login');
  err.textContent='';
  if(!email||!pass){err.textContent='Rellena todos los campos';return}
  const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email,password:pass})});
  const d=await r.json();
  if(d.ok) location='/aura';
  else err.textContent=d.error||'Datos incorrectos';
}
async function doRegistro(){
  const nombre=document.getElementById('r-nom').value.trim();
  const email =document.getElementById('r-email').value.trim();
  const pass  =document.getElementById('r-pass').value;
  const err   =document.getElementById('err-reg');
  err.textContent='';
  if(!nombre||!email||!pass){err.textContent='Rellena todos los campos';return}
  const r=await fetch('/registro',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({nombre,email,password:pass})});
  const d=await r.json();
  if(d.ok) location='/aura';
  else err.textContent=d.error||'Error al crear cuenta';
}
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════
#  PÁGINA PRINCIPAL — AURA
# ══════════════════════════════════════════════════════════════
HTML_AURA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aura — {{ nombre }}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#000918;--navy:#001030;--cyan:#00aaff;--gold:#fbbf24;--purple:#a855f7}
body{
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;
  background:var(--bg);color:#fff;
  height:100vh;display:flex;flex-direction:column;overflow:hidden;
}

/* HEADER */
.hdr{
  padding:14px 18px;
  background:rgba(0,10,35,0.92);
  border-bottom:1px solid rgba(0,150,255,0.18);
  display:flex;justify-content:space-between;align-items:center;
  backdrop-filter:blur(16px);flex-shrink:0;
}
.orb{
  width:46px;height:46px;border-radius:50%;
  background:radial-gradient(circle at 35% 30%,#88ddff,#0055ff 50%,#8833ff);
  box-shadow:0 0 20px #0077ff44;
  animation:orbPulse 4s ease-in-out infinite;cursor:pointer;flex-shrink:0;
}
@keyframes orbPulse{0%,100%{box-shadow:0 0 20px #0077ff44}50%{box-shadow:0 0 40px #0099ff88}}
.hdr-info{display:flex;align-items:center;gap:12px}
.hdr-btns{display:flex;gap:8px;align-items:center}
.btn-small{
  padding:8px 13px;border-radius:18px;border:1px solid rgba(0,170,255,0.35);
  background:transparent;color:var(--cyan);font-size:13px;cursor:pointer;
  transition:background .2s;
}
.btn-small:hover{background:rgba(0,170,255,0.12)}
.btn-voz{
  padding:9px 17px;border-radius:18px;border:none;
  background:linear-gradient(135deg,#10b981,#047857);
  color:#fff;font-size:13px;font-weight:600;cursor:pointer;
  animation:vPulse 3s infinite;
}
.btn-voz.active{background:#374151;animation:none}
@keyframes vPulse{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,0.5)}
                  50%{box-shadow:0 0 0 8px rgba(16,185,129,0)}}
#status{font-size:12px;color:#3a6a9a;margin-top:2px}

/* CHAT */
.chat{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:12px;
      scrollbar-width:thin;scrollbar-color:#1a2a4a transparent}
.chat::-webkit-scrollbar{width:4px}
.chat::-webkit-scrollbar-thumb{background:#1a3a6a;border-radius:4px}

.msg{max-width:84%;padding:13px 17px;border-radius:20px;font-size:15px;
     line-height:1.55;animation:fadeUp .3s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.msg.aura{
  align-self:flex-start;
  background:rgba(255,255,255,0.07);
  border:1px solid rgba(0,150,255,0.18);
  border-bottom-left-radius:4px;
}
.msg.user{
  align-self:flex-end;
  background:linear-gradient(135deg,rgba(0,40,100,0.9),rgba(0,20,60,0.95));
  border:1px solid rgba(0,100,200,0.2);
  border-bottom-right-radius:4px;
}
.msg-label{font-size:12px;font-weight:600;margin-bottom:5px;opacity:.7}
.msg-time{font-size:11px;color:#2a5a8a;margin-top:6px}

/* Typing indicator */
.typing{align-self:flex-start;background:rgba(255,255,255,0.07);
        border:1px solid rgba(0,150,255,0.18);border-radius:20px;
        border-bottom-left-radius:4px;padding:14px 20px;display:none}
.typing span{display:inline-block;width:7px;height:7px;border-radius:50%;
             background:var(--cyan);animation:bounce 1.2s infinite;margin:0 2px}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-8px)}}

/* INPUT AREA */
.input-area{
  padding:14px 18px 18px;
  background:rgba(0,8,28,0.9);
  border-top:1px solid rgba(0,150,255,0.15);
  flex-shrink:0;
}
.tools{display:flex;gap:8px;margin-bottom:11px;overflow-x:auto;padding-bottom:2px}
.tools::-webkit-scrollbar{display:none}
.tool{
  padding:8px 14px;
  background:rgba(0,150,255,0.08);
  border:1px solid rgba(0,150,255,0.25);
  border-radius:18px;color:var(--cyan);
  font-size:13px;cursor:pointer;white-space:nowrap;
  transition:all .2s;flex-shrink:0;
}
.tool:hover{background:rgba(0,150,255,0.18);border-color:rgba(0,150,255,0.5)}
.input-row{
  display:flex;gap:9px;align-items:center;
  background:rgba(0,15,45,0.85);
  padding:7px;border-radius:28px;
  border:1px solid rgba(0,150,255,0.25);
  transition:border-color .2s;
}
.input-row:focus-within{border-color:rgba(0,150,255,0.55)}
.input-row input{
  flex:1;background:transparent;border:none;color:#fff;
  padding:11px 14px;font-size:16px;outline:none;
}
.input-row input::placeholder{color:#2a4a6a}
.btn-mic{
  width:44px;height:44px;border-radius:50%;border:none;flex-shrink:0;
  background:linear-gradient(135deg,var(--gold),#d97706);
  color:#000;font-size:18px;cursor:pointer;transition:transform .15s;
}
.btn-mic:active{transform:scale(.9)}
.btn-mic.listening{background:linear-gradient(135deg,#ef4444,#b91c1c);animation:listening 1s infinite}
@keyframes listening{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.5)}50%{box-shadow:0 0 0 10px rgba(239,68,68,0)}}
.btn-send{
  width:44px;height:44px;border-radius:50%;border:none;flex-shrink:0;
  background:linear-gradient(135deg,var(--cyan),#0066ff);
  color:#fff;font-size:18px;cursor:pointer;transition:transform .15s;
}
.btn-send:active{transform:scale(.9)}

/* PANEL API KEY */
.panel{
  position:fixed;inset:0;z-index:300;
  background:rgba(0,5,20,0.85);backdrop-filter:blur(12px);
  display:none;align-items:center;justify-content:center;padding:24px;
}
.panel.show{display:flex}
.panel-box{
  background:rgba(0,15,45,0.98);
  border:1px solid rgba(0,170,255,0.35);
  border-radius:22px;padding:28px;width:100%;max-width:420px;
}
.panel-box h3{color:var(--cyan);margin-bottom:8px;font-size:18px}
.panel-box p{color:#6a9aaa;font-size:14px;margin-bottom:18px;line-height:1.5}
.panel-box input{
  width:100%;padding:13px 15px;border-radius:12px;
  border:1px solid rgba(0,150,255,0.3);
  background:rgba(0,0,0,0.4);color:#fff;font-size:15px;
  outline:none;margin-bottom:10px;
}
.panel-box input:focus{border-color:var(--cyan)}
.panel-box .btn-save{
  width:100%;padding:13px;border:none;border-radius:12px;
  background:linear-gradient(135deg,var(--cyan),#0055ff);
  color:#fff;font-weight:600;font-size:16px;cursor:pointer;margin-bottom:10px;
}
.panel-box .btn-cancel{
  width:100%;padding:11px;border:1px solid #2a4a6a;border-radius:12px;
  background:transparent;color:#6a9aaa;cursor:pointer;font-size:14px;
}
.tag{
  display:inline-block;padding:3px 10px;border-radius:10px;font-size:11px;
  background:rgba(0,255,100,0.1);border:1px solid rgba(0,255,100,0.3);color:#00dd77;
  margin-top:10px;
}

/* PANEL FAMILIA */
.panel-familia .card-fam{
  background:rgba(255,255,255,0.06);border:1px solid rgba(0,150,255,0.2);
  border-radius:14px;padding:14px;margin-bottom:10px;
}
.panel-familia .btn-del{
  float:right;background:transparent;border:none;color:#ff5566;cursor:pointer;font-size:16px;
}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <div class="hdr-info">
    <div class="orb" onclick="hablar('Hola, soy Aura')"></div>
    <div>
      <div style="font-size:17px;font-weight:600">{{ nombre }}</div>
      <div id="status">● En línea</div>
    </div>
  </div>
  <div class="hdr-btns">
    <button class="btn-small" onclick="abrirPanel('familia')">👥 Familia</button>
    <button class="btn-small" onclick="abrirPanel('api')">🔑 API Key</button>
    <button class="btn-voz" id="btn-voz" onclick="toggleVoz()">🔊 Activar Voz</button>
  </div>
</div>

<!-- CHAT -->
<div class="chat" id="chat">
  <div class="msg aura">
    <div class="msg-label">Aura</div>
    Hola <strong>{{ nombre }}</strong> 👋 Estoy contigo.<br>
    Puedes hablarme, escribirme o usar los botones de abajo.<br>
    Toca <strong>Activar Voz</strong> para que te responda hablando.
    <div class="msg-time">Ahora</div>
  </div>
</div>
<div class="typing" id="typing"><span></span><span></span><span></span></div>

<!-- INPUT AREA -->
<div class="input-area">
  <div class="tools">
    <div class="tool" onclick="setText('Gasté ')">💰 Gasto</div>
    <div class="tool" onclick="setText('Recuérdame ')">⏰ Recordar</div>
    <div class="tool" onclick="setText('Clima en ')">🌤 Clima</div>
    <div class="tool" onclick="setText('Total gastado')">📊 Balance</div>
    <div class="tool" onclick="setText('Ayuda')">❓ Ayuda</div>
  </div>
  <div class="input-row">
    <button class="btn-mic" id="btn-mic" onclick="toggleMic()">🎤</button>
    <input id="msg" type="text" placeholder="Escribe o habla con Aura..."
           onkeypress="if(event.key==='Enter')enviar()">
    <button class="btn-send" onclick="enviar()">➤</button>
  </div>
</div>

<!-- PANEL API KEY -->
<div class="panel" id="panel-api" onclick="if(event.target===this)cerrarPanel('api')">
  <div class="panel-box">
    <h3>🔑 Conectar IA avanzada</h3>
    <p>Pega tu API Key de <strong>Groq</strong> (gratis en console.groq.com) para que Aura tenga conversación inteligente sobre cualquier tema.</p>
    <input id="api-input" type="text" placeholder="gsk_...">
    <button class="btn-save" onclick="guardarApi()">Guardar API Key</button>
    <button class="btn-cancel" onclick="cerrarPanel('api')">Cancelar</button>
  </div>
</div>

<!-- PANEL FAMILIA -->
<div class="panel panel-familia" id="panel-familia" onclick="if(event.target===this)cerrarPanel('familia')">
  <div class="panel-box">
    <h3>👥 Círculo de Seguridad</h3>
    <p>Hasta 6 contactos de confianza. (Máximo 6)</p>
    <div id="lista-familia"></div>
    <input id="fam-nom" type="text" placeholder="Nombre del contacto">
    <input id="fam-tel" type="tel"  placeholder="Teléfono">
    <button class="btn-save" onclick="agregarFamiliar()">Agregar contacto</button>
    <button class="btn-cancel" onclick="cerrarPanel('familia')">Cerrar</button>
  </div>
</div>

<script>
// ── Estado ──────────────────────────────────────────────────
let voz = false;
let mic = null;
let escuchando = false;

// ── Voz (síntesis) ───────────────────────────────────────────
function hablar(texto) {
  if (!voz || !texto) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(texto);
  u.lang = 'es-ES'; u.rate = 0.92; u.pitch = 1.05; u.volume = 1;
  const voces = window.speechSynthesis.getVoices();
  const v = voces.find(x => x.lang.startsWith('es') && x.name.includes('Female'))
         || voces.find(x => x.lang.startsWith('es'));
  if (v) u.voice = v;
  window.speechSynthesis.speak(u);
}

function toggleVoz() {
  voz = !voz;
  const btn = document.getElementById('btn-voz');
  if (voz) {
    btn.textContent = '🔊 Voz activa';
    btn.classList.add('active');
    hablar('Voz activada. Hola, soy Aura. ¿En qué te puedo ayudar hoy?');
    setStatus('Con voz natural');
  } else {
    btn.textContent = '🔊 Activar Voz';
    btn.classList.remove('active');
    setStatus('En línea');
  }
}

// ── Micrófono ────────────────────────────────────────────────
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  mic = new SR();
  mic.lang = 'es-ES'; mic.continuous = false; mic.interimResults = false;
  mic.onresult = e => {
    document.getElementById('msg').value = e.results[0][0].transcript;
    setTimeout(enviar, 300);
  };
  mic.onend = () => {
    escuchando = false;
    document.getElementById('btn-mic').classList.remove('listening');
    document.getElementById('btn-mic').textContent = '🎤';
    if (voz) setStatus('Con voz natural'); else setStatus('En línea');
  };
  mic.onerror = () => { escuchando = false; };
}

function toggleMic() {
  if (!mic) { alert('Usa Chrome o Safari para el micrófono.'); return; }
  if (escuchando) {
    mic.stop();
  } else {
    mic.start();
    escuchando = true;
    document.getElementById('btn-mic').classList.add('listening');
    document.getElementById('btn-mic').textContent = '⏹';
    setStatus('Escuchando...');
  }
}

// ── Helpers ──────────────────────────────────────────────────
function setStatus(t) { document.getElementById('status').textContent = '● ' + t; }
function setText(t)   { document.getElementById('msg').value = t; document.getElementById('msg').focus(); }
function hora()       { return new Date().toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'}); }

function addMsg(texto, tipo) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + tipo;
  div.innerHTML = `<div class="msg-label">${tipo==='user'?'Tú':'Aura'}</div>${texto}<div class="msg-time">${hora()}</div>`;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

// ── Enviar mensaje ───────────────────────────────────────────
async function enviar() {
  const input = document.getElementById('msg');
  const m = input.value.trim();
  if (!m) return;
  input.value = '';

  addMsg(m, 'user');
  setStatus('Pensando...');
  document.getElementById('typing').style.display = 'flex';
  document.getElementById('chat').scrollTop = 99999;

  try {
    const r = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({msg: m})
    });
    const d = await r.json();
    document.getElementById('typing').style.display = 'none';
    addMsg(d.resp, 'aura');
    hablar(d.resp);
    setStatus(voz ? 'Con voz natural' : 'En línea');
  } catch(e) {
    document.getElementById('typing').style.display = 'none';
    addMsg('Error de conexión. Comprueba que el servidor esté activo.', 'aura');
    setStatus('Error');
  }
}

// ── Paneles ──────────────────────────────────────────────────
function abrirPanel(id) {
  document.getElementById('panel-' + id).classList.add('show');
  if (id === 'familia') cargarFamilia();
}
function cerrarPanel(id) { document.getElementById('panel-' + id).classList.remove('show'); }

// ── API Key ───────────────────────────────────────────────────
async function guardarApi() {
  const key = document.getElementById('api-input').value.trim();
  if (!key) { alert('Pega tu API Key'); return; }
  if (!key.startsWith('gsk_')) { alert('La clave debe empezar con gsk_'); return; }
  const r = await fetch('/guardar-api', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});
  const d = await r.json();
  if (d.ok) { alert('✅ API Key guardada. Aura ahora tiene IA avanzada.'); cerrarPanel('api'); }
  else alert('Error al guardar');
}

// ── Familia ───────────────────────────────────────────────────
async function cargarFamilia() {
  const r = await fetch('/familia/lista');
  const d = await r.json();
  const lista = document.getElementById('lista-familia');
  lista.innerHTML = '';
  d.forEach(f => {
    lista.innerHTML += `<div class="card-fam">
      <button class="btn-del" onclick="borrarFamiliar(${f.id})">✕</button>
      <strong>${f.nombre}</strong><br><small style="color:#5588aa">${f.telefono}</small>
    </div>`;
  });
}
async function agregarFamiliar() {
  const nom = document.getElementById('fam-nom').value.trim();
  const tel = document.getElementById('fam-tel').value.trim();
  if (!nom || !tel) { alert('Rellena nombre y teléfono'); return; }
  const r = await fetch('/familia/agregar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre:nom,telefono:tel})});
  const d = await r.json();
  if (d.ok) { document.getElementById('fam-nom').value=''; document.getElementById('fam-tel').value=''; cargarFamilia(); }
  else alert(d.error);
}
async function borrarFamiliar(id) {
  await fetch('/familia/borrar/'+id, {method:'DELETE'});
  cargarFamilia();
}

// Cargar voces al arrancar
if ('speechSynthesis' in window) window.speechSynthesis.getVoices();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════
#  RUTAS — Auth
# ══════════════════════════════════════════════════════════════
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect('/aura')
    return render_template_string(HTML_LOGIN)

@app.route('/registro', methods=['POST'])
def registro():
    with app.app_context():
        db.create_all()
    d = request.json
    if not d.get('nombre') or not d.get('email') or not d.get('password'):
        return jsonify({'error': 'Rellena todos los campos'})
    if Usuario.query.filter_by(email=d['email']).first():
        return jsonify({'error': 'Ese email ya está registrado'})
    u = Usuario(nombre=d['nombre'], email=d['email'],
                password=generate_password_hash(d['password']))
    db.session.add(u); db.session.commit(); login_user(u)
    return jsonify({'ok': True})

@app.route('/login', methods=['POST'])
def login():
    d = request.json
    u = Usuario.query.filter_by(email=d.get('email','')).first()
    if not u or not check_password_hash(u.password, d.get('password','')):
        return jsonify({'error': 'Email o contraseña incorrectos'})
    login_user(u)
    return jsonify({'ok': True})

@app.route('/logout')
def logout():
    logout_user(); return redirect('/')

@app.route('/aura')
@login_required
def aura():
    return render_template_string(HTML_AURA, nombre=current_user.nombre)

# ── API Key ───────────────────────────────────────────────────
@app.route('/guardar-api', methods=['POST'])
@login_required
def guardar_api():
    d = request.json
    current_user.api_key = d.get('api_key', '')
    db.session.commit()
    return jsonify({'ok': True})

# ── Familia ───────────────────────────────────────────────────
@app.route('/familia/lista')
@login_required
def familia_lista():
    f = Familiar.query.filter_by(usuario_id=current_user.id).all()
    return jsonify([{'id': x.id, 'nombre': x.nombre, 'telefono': x.telefono} for x in f])

@app.route('/familia/agregar', methods=['POST'])
@login_required
def familia_agregar():
    d = request.json
    if Familiar.query.filter_by(usuario_id=current_user.id).count() >= 6:
        return jsonify({'error': 'Máximo 6 contactos'})
    f = Familiar(usuario_id=current_user.id, nombre=d['nombre'], telefono=d['telefono'])
    db.session.add(f); db.session.commit()
    return jsonify({'ok': True})

@app.route('/familia/borrar/<int:fid>', methods=['DELETE'])
@login_required
def familia_borrar(fid):
    f = Familiar.query.filter_by(id=fid, usuario_id=current_user.id).first()
    if f: db.session.delete(f); db.session.commit()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════════
#  CHAT — Cerebro de Aura
# ══════════════════════════════════════════════════════════════
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    msg_original = request.json.get('msg', '').strip()
    if not msg_original:
        return jsonify({'resp': '¿Me decías algo?'})
    m = msg_original.lower()

    # ── 1. GASTOS ─────────────────────────────────────────────
    if any(p in m for p in ['gasté','gaste','pagué','pague','compré','compre','costó']):
        nums = re.findall(r'\d+(?:[.,]\d{1,2})?', m)
        if nums:
            monto = float(nums[0].replace(',','.'))
            concepto = 'Gasto general'
            cats = [('café','Café'),('cafe','Café'),('comida','Comida'),
                    ('restaurante','Restaurante'),('supermercado','Supermercado'),
                    ('transporte','Transporte'),('taxi','Taxi'),('uber','Uber'),
                    ('ropa','Ropa'),('farmacia','Farmacia'),('médico','Médico'),
                    ('ocio','Ocio'),('gasolina','Gasolina')]
            for k,v in cats:
                if k in m: concepto = v; break
            g = Gasto(usuario_id=current_user.id, concepto=concepto, monto=monto)
            db.session.add(g); db.session.commit()
            total = db.session.query(db.func.sum(Gasto.monto))\
                              .filter_by(usuario_id=current_user.id).scalar() or 0
            return jsonify({'resp': f'💰 Guardado: <strong>{monto}€</strong> en {concepto}.<br>Total acumulado: <strong>{total:.2f}€</strong>'})
        return jsonify({'resp': '¿Cuánto gastaste? Dime el monto, ej: "Gasté 20 en café"'})

    # ── 2. RECORDATORIOS ─────────────────────────────────────
    if any(p in m for p in ['recuérdame','recuerdame','recuerda que','alarma','avísame','avisame']):
        texto = msg_original
        for x in ['recuérdame','recuerdame','alarma','avísame','avisame','recuerda que','recuerda']:
            texto = texto.replace(x,'').replace(x.capitalize(),'')
        texto = texto.strip() or 'Recordatorio'
        r = Recordatorio(usuario_id=current_user.id, texto=texto[:200],
                         fecha_hora=datetime.now()+timedelta(minutes=5))
        db.session.add(r); db.session.commit()
        return jsonify({'resp': f'⏰ Recordatorio creado: "<em>{texto}</em>"'})

    # ── 3. TOTAL / BALANCE ────────────────────────────────────
    if any(p in m for p in ['total','balance','cuánto he gastado','cuanto he gastado','mis gastos','gastos del mes']):
        total = db.session.query(db.func.sum(Gasto.monto))\
                          .filter_by(usuario_id=current_user.id).scalar() or 0
        n = Gasto.query.filter_by(usuario_id=current_user.id).count()
        return jsonify({'resp': f'📊 Llevas <strong>{total:.2f}€</strong> en {n} movimientos registrados.'})

    # ── 4. CLIMA (usando Open-Meteo, sin API key) ─────────────
    if any(p in m for p in ['clima','tiempo','temperatura','llueve','hace calor','hace frío']):
        try:
            import urllib.request, json as _json
            # Coordenadas por defecto: Madrid
            lat, lon, ciudad = 40.4168, -3.7038, 'Madrid'
            for city, la, lo in [('barcelona',41.38,2.17),('madrid',40.42,-3.70),
                                  ('valencia',39.47,-0.37),('sevilla',37.39,-5.99),
                                  ('bilbao',43.26,-2.93),('málaga',36.72,-4.42),
                                  ('malaga',36.72,-4.42)]:
                if city in m: lat,lon,ciudad = la,lo,city.capitalize(); break
            url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true'
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = _json.loads(resp.read())
            t = data['current_weather']['temperature']
            w = data['current_weather']['windspeed']
            return jsonify({'resp': f'🌤 En <strong>{ciudad}</strong>: <strong>{t}°C</strong>, viento {w} km/h.'})
        except:
            return jsonify({'resp': 'No pude consultar el clima ahora. Intenta en un momento.'})

    # ── 5. AYUDA ─────────────────────────────────────────────
    if 'ayuda' in m or 'qué puedes hacer' in m or 'que puedes hacer' in m:
        return jsonify({'resp': '''Hola! Puedo ayudarte con:<br>
        💰 <strong>Gastos</strong> — "Gasté 15 en café"<br>
        ⏰ <strong>Recordatorios</strong> — "Recuérdame llamar al médico"<br>
        📊 <strong>Balance</strong> — "¿Cuánto he gastado?"<br>
        🌤 <strong>Clima</strong> — "¿Qué clima hace en Barcelona?"<br>
        👥 <strong>Familia</strong> — Botón "Familia" arriba<br>
        🤖 <strong>IA avanzada</strong> — Añade tu API Key de Groq (gratis)'''})

    # ── 6. CONVERSACIÓN BÁSICA ───────────────────────────────
    basicas = {
        'hola':         f'¡Hola, {current_user.nombre}! 👋 ¿Cómo estás hoy?',
        'buenos días':  f'¡Buenos días, {current_user.nombre}! ☀️ Que tengas un gran día.',
        'buenas tardes':'¡Buenas tardes! 🌅 ¿En qué te puedo ayudar?',
        'buenas noches':'¡Buenas noches! 🌙 ¿Necesitas algo antes de dormir?',
        'cómo estás':   'Muy bien, gracias por preguntar. 😊 ¿Y tú, qué tal?',
        'como estás':   'Muy bien, gracias. 😊 ¿Y tú cómo estás?',
        'bien':         '¡Me alegra mucho! 🎉 ¿En qué te ayudo hoy?',
        'mal':          'Lo siento. 💙 ¿Quieres contarme qué pasó?',
        'gracias':      'De nada, siempre estoy aquí para ti. 🙏',
        'adiós':        f'¡Hasta luego, {current_user.nombre}! 👋 Cuídate mucho.',
        'adios':        f'¡Hasta pronto! 👋 Vuelve cuando quieras.',
    }
    for k, v in basicas.items():
        if k in m:
            return jsonify({'resp': v})

    # ── 7. IA CON GROQ ───────────────────────────────────────
    if GROQ_OK:
        try:
            client = Groq(api_key=GROQ_KEY)
            # Historial reciente
            hist = Historial.query.filter_by(usuario_id=current_user.id)\
                                  .order_by(Historial.fecha.desc()).limit(8).all()
            msgs = [{'role':'system','content':
                f'Eres Aura, la asistente personal de {current_user.nombre}. '
                f'Eres empática, inteligente, conversacional y muy útil. '
                f'Responde en español, de forma natural y breve (máximo 3 oraciones). '
                f'Si el usuario tiene gastos o recordatorios relevantes, puedes mencionarlos.'}]
            for h in reversed(hist):
                msgs.append({'role': h.rol, 'content': h.contenido})
            msgs.append({'role':'user','content': msg_original})

            resp = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=msgs,
                temperature=0.8,
                max_tokens=250
            )
            respuesta = resp.choices[0].message.content
        except Exception as e:
            respuesta = f'Hubo un error con la IA: {str(e)[:50]}'
    else:
        respuesta = ('Interesante. 🤔 Para conversaciones libres sobre cualquier tema, '
                     'activa la IA avanzada con tu API Key de Groq (gratis en console.groq.com). '
                     'O di <strong>"ayuda"</strong> para ver lo que puedo hacer.')

    # Guardar historial
    db.session.add(Historial(usuario_id=current_user.id, rol='user', contenido=msg_original))
    db.session.add(Historial(usuario_id=current_user.id, rol='assistant', contenido=respuesta))
    db.session.commit()

    return jsonify({'resp': respuesta})

# ══════════════════════════════════════════════════════════════
#  INICIO
# ══════════════════════════════════════════════════════════════

@app.route('/voz', methods=['POST'])
@login_required
def voz():
    import base64
    texto = request.json.get('texto', '')
    ELEVEN_KEY = os.environ.get('ELEVEN_KEY', '')
    ELEVEN_VOICE = '21m00Tcm4TlvDq8ikWAM'
    if ELEVEN_OK and ELEVEN_KEY and texto:
        try:
            client = ElevenLabs(api_key=ELEVEN_KEY)
            gen = client.text_to_speech.convert(
                voice_id=ELEVEN_VOICE, text=texto[:500],
                model_id='eleven_multilingual_v2')
            audio = b''.join(gen)
            return jsonify({'audio': base64.b64encode(audio).decode()})
        except Exception as e:
            return jsonify({'error': str(e)})
    return jsonify({'error': 'Voz no disponible'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
