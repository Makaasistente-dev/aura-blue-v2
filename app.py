import os, base64
from flask import Flask, render_template_string, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

GROQ_KEY     = os.environ.get('GROQ_KEY', '')
ELEVEN_KEY   = os.environ.get('ELEVEN_KEY', '')
ELEVEN_VOICE = '21m00Tcm4TlvDq8ikWAM'

try:
    from groq import Groq
    GROQ_OK = True
except ImportError:
    GROQ_OK = False

try:
    from elevenlabs.client import ElevenLabs
    ELEVEN_OK = True
except ImportError:
    ELEVEN_OK = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'aura-blue-2026-v3'
_db = os.environ.get('DATABASE_URL', 'sqlite:////tmp/aura.db')
if _db.startswith('postgres://'):
    _db = _db.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = '/'

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id       = db.Column(db.Integer, primary_key=True)
    nombre   = db.Column(db.String(80))
    email    = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))

class Gasto(db.Model):
    __tablename__ = 'gastos'
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    concepto   = db.Column(db.String(100), default='Gasto')
    monto      = db.Column(db.Float)
    fecha      = db.Column(db.DateTime, default=datetime.utcnow)

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

def ensure_tables():
    with app.app_context():
        db.create_all()

HTML_LOGIN = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aura Blue</title>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;600;700&family=Exo+2:wght@200;300;400&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Exo 2',sans-serif;background:#010b1f;min-height:100vh;
  display:flex;align-items:center;justify-content:center;overflow:hidden;color:#fff}
canvas{position:fixed;inset:0;z-index:0;pointer-events:none}
.wrap{position:relative;z-index:1;display:flex;flex-direction:column;
  align-items:center;width:100%;max-width:380px;padding:24px}
.logo-area{text-align:center;margin-bottom:40px}
.orb-wrap{position:relative;width:120px;height:120px;margin:0 auto 20px}
.orb{width:120px;height:120px;border-radius:50%;
  background:radial-gradient(circle at 35% 25%,#fff9e6,#fbbf24 30%,#d97706 60%,#1e40af 85%,#0f172a);
  box-shadow:0 0 40px #fbbf2466,0 0 80px #d9770622,0 0 0 1px rgba(251,191,36,0.3);
  animation:orbP 4s ease-in-out infinite}
.orb-ring{position:absolute;inset:-12px;border-radius:50%;
  border:1px solid rgba(251,191,36,0.2);animation:ringP 4s ease-in-out infinite}
.orb-ring2{position:absolute;inset:-24px;border-radius:50%;
  border:1px solid rgba(251,191,36,0.08);animation:ringP 4s ease-in-out infinite .5s}
@keyframes orbP{0%,100%{box-shadow:0 0 40px #fbbf2466,0 0 80px #d9770622}
  50%{box-shadow:0 0 60px #fbbf24aa,0 0 120px #d9770644}}
@keyframes ringP{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.05);opacity:1}}
h1{font-family:'Rajdhani',sans-serif;font-size:32px;font-weight:700;
  letter-spacing:12px;color:#fbbf24;text-shadow:0 0 30px #fbbf2466}
.sub{font-size:11px;letter-spacing:6px;color:#1e4a8a;margin-top:4px;text-transform:uppercase}
.card{width:100%;background:rgba(1,11,31,0.85);
  border:1px solid rgba(251,191,36,0.15);border-radius:24px;padding:32px;
  backdrop-filter:blur(20px)}
input{display:block;width:100%;padding:14px 18px;margin:8px 0;
  border-radius:12px;border:1px solid rgba(251,191,36,0.15);
  background:rgba(0,0,0,.4);color:#fff;font-size:15px;
  font-family:'Exo 2',sans-serif;outline:none;transition:all .25s}
input:focus{border-color:rgba(251,191,36,.5)}
input::placeholder{color:#1e3a5a}
.btn{width:100%;padding:15px;margin-top:16px;border:none;border-radius:14px;
  background:linear-gradient(135deg,#fbbf24,#d97706);
  color:#000;font-size:15px;font-weight:700;font-family:'Rajdhani',sans-serif;
  letter-spacing:2px;cursor:pointer;text-transform:uppercase}
.btn:hover{opacity:.9}
.link{text-align:center;margin-top:18px;color:#1e4a8a;font-size:13px;cursor:pointer}
.link span{color:#3a7aaa}
.err{color:#ff6677;font-size:13px;text-align:center;margin-top:10px;min-height:18px}
.div{display:flex;align-items:center;gap:12px;margin:18px 0}
.div::before,.div::after{content:'';flex:1;height:1px;background:rgba(251,191,36,.1)}
.div span{font-size:11px;color:#1e3a5a;letter-spacing:2px}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="wrap">
  <div class="logo-area">
    <div class="orb-wrap">
      <div class="orb"></div><div class="orb-ring"></div><div class="orb-ring2"></div>
    </div>
    <h1>AURA</h1>
    <div class="sub">Barcelona · Asistente Personal</div>
  </div>
  <div class="card" id="box-login">
    <input id="l-email" type="email" placeholder="Email">
    <input id="l-pass" type="password" placeholder="Contraseña">
    <button class="btn" onclick="doLogin()">Entrar</button>
    <div class="div"><span>o</span></div>
    <p class="link" onclick="show('reg')">¿Primera vez? <span>Crear cuenta →</span></p>
    <div class="err" id="err-login"></div>
  </div>
  <div class="card" id="box-reg" style="display:none">
    <input id="r-nom" type="text" placeholder="Tu nombre">
    <input id="r-email" type="email" placeholder="Email">
    <input id="r-pass" type="password" placeholder="Contraseña (mín. 6 caracteres)">
    <button class="btn" onclick="doRegistro()">Crear cuenta</button>
    <div class="div"><span>o</span></div>
    <p class="link" onclick="show('login')"><span>← Ya tengo cuenta</span></p>
    <div class="err" id="err-reg"></div>
  </div>
</div>
<script>
const canvas=document.getElementById('c'),ctx=canvas.getContext('2d');
let W,H,pts=[];
function resize(){W=canvas.width=innerWidth;H=canvas.height=innerHeight;
  pts=[];for(let i=0;i<80;i++)pts.push({x:Math.random()*W,y:Math.random()*H,
  vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,r:Math.random()*1.5+.5,o:Math.random()*.4+.1})}
function draw(){ctx.clearRect(0,0,W,H);
  pts.forEach(p=>{p.x+=p.vx;p.y+=p.vy;
    if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
    ctx.fillStyle=`rgba(251,191,36,${p.o})`;ctx.fill()});
  pts.forEach((a,i)=>pts.slice(i+1).forEach(b=>{const d=Math.hypot(a.x-b.x,a.y-b.y);
    if(d<120){ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
      ctx.strokeStyle=`rgba(251,191,36,${.05*(1-d/120)})`;ctx.lineWidth=.5;ctx.stroke()}}));
  requestAnimationFrame(draw)}
window.addEventListener('resize',resize);resize();draw();
function show(t){document.getElementById('box-login').style.display=t==='login'?'block':'none';
  document.getElementById('box-reg').style.display=t==='reg'?'block':'none'}
async function doLogin(){
  const email=document.getElementById('l-email').value.trim();
  const pass=document.getElementById('l-pass').value;
  const err=document.getElementById('err-login');err.textContent='';
  if(!email||!pass){err.textContent='Rellena todos los campos';return}
  const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email,password:pass})});
  const d=await r.json();if(d.ok)location='/aura';else err.textContent=d.error||'Datos incorrectos'}
async function doRegistro(){
  const nombre=document.getElementById('r-nom').value.trim();
  const email=document.getElementById('r-email').value.trim();
  const pass=document.getElementById('r-pass').value;
  const err=document.getElementById('err-reg');err.textContent='';
  if(!nombre||!email||!pass){err.textContent='Rellena todos los campos';return}
  if(pass.length<6){err.textContent='Mínimo 6 caracteres';return}
  const r=await fetch('/registro',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({nombre,email,password:pass})});
  const d=await r.json();if(d.ok)location='/aura';else err.textContent=d.error||'Error al crear cuenta'}
</script>
</body>
</html>"""

HTML_AURA = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Aura · {{ nombre }}</title>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;600;700&family=Exo+2:wght@200;300;400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--gold:#fbbf24;--gold2:#d97706;--bg:#010b1f}
body{font-family:'Exo 2',sans-serif;background:var(--bg);color:#fff;
  height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
.hdr{padding:12px 16px;background:rgba(1,8,24,.97);
  border-bottom:1px solid rgba(251,191,36,.12);
  display:flex;justify-content:space-between;align-items:center;flex-shrink:0}
.hdr-logo{font-family:'Rajdhani',sans-serif;font-size:20px;font-weight:700;letter-spacing:6px;color:var(--gold)}
.hdr-name{font-size:12px;color:#2a5a8a;letter-spacing:1px;margin-top:1px}
.hdr-btns{display:flex;gap:8px}
.hb{padding:8px 13px;border-radius:14px;border:1px solid rgba(251,191,36,.2);
  background:transparent;color:var(--gold);font-size:12px;cursor:pointer;font-family:'Exo 2',sans-serif}
.hb.on{background:rgba(16,185,129,.15);border-color:#10b981;color:#10b981}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.dashboard{flex:1;display:flex;align-items:center;justify-content:center;position:relative;padding:10px}
.circle-bg{position:absolute;width:320px;height:320px;border-radius:50%;border:1px solid rgba(251,191,36,.08)}
.circle-bg2{position:absolute;width:260px;height:260px;border-radius:50%;border:1px solid rgba(251,191,36,.05)}
.panels{position:relative;width:310px;height:310px}
.panel{position:absolute;width:138px;height:138px;background:rgba(1,12,35,.9);
  border:1px solid rgba(251,191,36,.15);cursor:pointer;transition:all .25s;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px}
.panel:hover{background:rgba(251,191,36,.08);border-color:rgba(251,191,36,.4)}
.panel-tl{top:0;left:0;border-radius:50% 16px 16px 16px}
.panel-tr{top:0;right:0;border-radius:16px 50% 16px 16px}
.panel-bl{bottom:0;left:0;border-radius:16px 16px 16px 50%}
.panel-br{bottom:0;right:0;border-radius:16px 16px 50% 16px}
.panel-icon{font-size:26px}
.panel-title{font-family:'Rajdhani',sans-serif;font-size:11px;font-weight:600;letter-spacing:2px;color:var(--gold);text-align:center}
.panel-value{font-size:12px;color:#4a8aaa;text-align:center;max-width:110px;padding:0 6px}
.orb-center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:90px;height:90px;border-radius:50%;
  background:radial-gradient(circle at 35% 25%,#fff9e6,#fbbf24 30%,#d97706 60%,#1e40af 85%,#010b1f);
  box-shadow:0 0 30px #fbbf2455,0 0 60px #d9770622;
  animation:orbG 4s ease-in-out infinite;cursor:pointer;z-index:10}
.orb-center::before{content:'';position:absolute;inset:-8px;border-radius:50%;
  border:1px solid rgba(251,191,36,.25);animation:ringG 4s ease-in-out infinite}
.orb-center::after{content:'';position:absolute;inset:-16px;border-radius:50%;
  border:1px solid rgba(251,191,36,.1);animation:ringG 4s ease-in-out infinite .3s}
@keyframes orbG{0%,100%{box-shadow:0 0 30px #fbbf2455}50%{box-shadow:0 0 50px #fbbf2488}}
@keyframes ringG{0%,100%{transform:scale(1);opacity:.7}50%{transform:scale(1.06);opacity:1}}
.chat-area{display:none;flex-direction:column;flex:1;overflow:hidden}
.chat-area.show{display:flex}
.msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:82%;padding:11px 15px;border-radius:16px;font-size:14px;line-height:1.55;animation:fadeUp .2s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.msg.aura{align-self:flex-start;background:rgba(1,15,40,.9);border:1px solid rgba(251,191,36,.12);border-bottom-left-radius:4px}
.msg.user{align-self:flex-end;background:linear-gradient(135deg,rgba(0,30,80,.9),rgba(0,15,50,.95));border:1px solid rgba(14,165,233,.2);border-bottom-right-radius:4px}
.msg-lbl{font-size:10px;font-weight:600;opacity:.5;margin-bottom:3px;letter-spacing:1px}
.msg-time{font-size:10px;color:#1a4a7a;margin-top:4px}
.typing{align-self:flex-start;background:rgba(1,15,40,.9);border:1px solid rgba(251,191,36,.12);
  border-radius:16px;border-bottom-left-radius:4px;padding:12px 16px;display:none}
.typing span{display:inline-block;width:6px;height:6px;border-radius:50%;
  background:var(--gold);animation:bounce 1.2s infinite;margin:0 2px}
.typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.input-area{padding:10px 14px 14px;background:rgba(1,5,18,.95);border-top:1px solid rgba(251,191,36,.08);flex-shrink:0}
.tools{display:flex;gap:6px;margin-bottom:9px;overflow-x:auto}
.tools::-webkit-scrollbar{display:none}
.tool{padding:6px 12px;background:rgba(251,191,36,.05);border:1px solid rgba(251,191,36,.15);
  border-radius:14px;color:#8a7a3a;font-size:11px;cursor:pointer;white-space:nowrap;flex-shrink:0}
.tool:hover{background:rgba(251,191,36,.12);color:var(--gold)}
.irow{display:flex;gap:7px;align-items:center;background:rgba(0,8,25,.9);padding:6px;
  border-radius:22px;border:1px solid rgba(251,191,36,.15)}
.irow:focus-within{border-color:rgba(251,191,36,.4)}
.irow input{flex:1;background:transparent;border:none;color:#fff;padding:9px 12px;font-size:15px;outline:none}
.irow input::placeholder{color:#1a3a5a}
.btn-mic{width:40px;height:40px;border-radius:50%;border:none;flex-shrink:0;
  background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000;font-size:16px;cursor:pointer}
.btn-mic.on{background:linear-gradient(135deg,#ef4444,#b91c1c);animation:micP 1s infinite}
@keyframes micP{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.5)}50%{box-shadow:0 0 0 8px rgba(239,68,68,0)}}
.btn-send{width:40px;height:40px;border-radius:50%;border:none;flex-shrink:0;
  background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000;font-size:16px;cursor:pointer}
.btn-back{padding:8px 14px;border-radius:14px;border:1px solid rgba(251,191,36,.2);
  background:transparent;color:var(--gold);font-size:12px;cursor:pointer;margin-bottom:10px}
.hormiga-page{display:none;flex-direction:column;flex:1;overflow:hidden}
.hormiga-page.show{display:flex}
.h-content{flex:1;overflow-y:auto;padding:16px}
.h-total{background:linear-gradient(135deg,rgba(1,15,40,.9),rgba(1,8,25,.95));
  border:1px solid rgba(251,191,36,.25);border-radius:18px;padding:20px;margin-bottom:14px}
.h-total-lbl{font-size:12px;color:#3a6a8a;letter-spacing:2px;margin-bottom:4px}
.h-total-amt{font-size:36px;font-weight:700;color:var(--gold);font-family:'Rajdhani',sans-serif}
.h-total-sub{font-size:12px;color:#2a5a7a;margin-top:3px}
.h-card{background:rgba(1,10,30,.8);border:1px solid rgba(251,191,36,.1);border-radius:16px;padding:16px;margin-bottom:12px}
.h-card-title{font-size:12px;color:#3a6a8a;letter-spacing:2px;margin-bottom:14px;font-family:'Rajdhani',sans-serif}
.filtros{display:flex;gap:6px;margin-bottom:14px;overflow-x:auto}
.filtros::-webkit-scrollbar{display:none}
.filtro{padding:7px 14px;border-radius:14px;border:1px solid rgba(251,191,36,.15);
  background:transparent;color:#3a6a8a;font-size:12px;cursor:pointer;white-space:nowrap}
.filtro.active{background:rgba(251,191,36,.1);border-color:var(--gold);color:var(--gold)}
.barra{margin-bottom:11px}
.barra-info{display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px}
.barra-bg{background:rgba(255,255,255,.05);border-radius:5px;height:7px;overflow:hidden}
.barra-fill{height:100%;border-radius:5px;background:linear-gradient(90deg,var(--gold),#f97316);transition:width 1s ease}
.mov-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(251,191,36,.06)}
.mov-item:last-child{border-bottom:none}
.mov-l{display:flex;align-items:center;gap:9px}
.mov-emoji{font-size:20px}
.mov-name{font-size:13px;font-weight:500}
.mov-date{font-size:11px;color:#1a4a6a;margin-top:1px}
.mov-amt{font-size:15px;font-weight:700;color:var(--gold);font-family:'Rajdhani',sans-serif}
.alerta{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:14px;padding:14px;margin-bottom:14px;display:none}
.alerta.show{display:flex;gap:10px}
.add-row{display:flex;gap:7px;margin-top:8px}
.add-inp{flex:1;background:rgba(0,0,0,.35);border:1px solid rgba(251,191,36,.15);border-radius:10px;color:#fff;padding:10px 12px;font-size:14px;outline:none}
.add-inp:focus{border-color:rgba(251,191,36,.4)}
.add-btn{padding:10px 16px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000;font-weight:700;cursor:pointer;white-space:nowrap}
.overlay{position:fixed;inset:0;z-index:100;background:rgba(1,5,18,.92);backdrop-filter:blur(14px);display:none;align-items:center;justify-content:center;padding:20px}
.overlay.show{display:flex}
.opanel{background:rgba(1,10,30,.98);border:1px solid rgba(251,191,36,.2);border-radius:22px;padding:24px;width:100%;max-width:420px;max-height:85vh;overflow-y:auto}
.opanel h3{font-family:'Rajdhani',sans-serif;color:var(--gold);font-size:18px;letter-spacing:3px;margin-bottom:6px}
.opanel p{color:#2a5a8a;font-size:13px;margin-bottom:16px;line-height:1.5}
.opanel input{width:100%;padding:12px 14px;border-radius:11px;border:1px solid rgba(251,191,36,.18);background:rgba(0,0,0,.4);color:#fff;font-size:14px;outline:none;margin-bottom:9px}
.opanel input:focus{border-color:rgba(251,191,36,.5)}
.btn-ok{width:100%;padding:13px;border:none;border-radius:11px;background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000;font-weight:700;font-size:14px;cursor:pointer;margin-bottom:8px;text-transform:uppercase;font-family:'Rajdhani',sans-serif;letter-spacing:2px}
.btn-no{width:100%;padding:11px;border:1px solid rgba(251,191,36,.15);border-radius:11px;background:transparent;color:#4a6a8a;cursor:pointer;font-size:13px}
.fam-card{background:rgba(255,255,255,.04);border:1px solid rgba(251,191,36,.12);border-radius:12px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.fam-del{background:transparent;border:none;color:#ff4455;cursor:pointer;font-size:15px}
.hr{border:none;border-top:1px solid rgba(251,191,36,.1);margin:16px 0}
</style>
</head>
<body>
<div class="hdr">
  <div><div class="hdr-logo">AURA</div><div class="hdr-name">{{ nombre }}</div></div>
  <div class="hdr-btns">
    <button class="hb" onclick="showHormiga()">🐜</button>
    <button class="hb" onclick="abrirOverlay('familia')">👥</button>
    <button class="hb" id="btn-voz" onclick="toggleVoz()">🔊 Voz</button>
    <button class="hb" onclick="location='/logout'" style="color:#3a5a7a;font-size:11px">Salir</button>
  </div>
</div>
<div class="main">
  <div class="dashboard" id="dashboard">
    <div class="circle-bg"></div><div class="circle-bg2"></div>
    <div class="panels">
      <div class="panel panel-tl" onclick="abrirOverlay('familia')">
        <div class="panel-icon">👥</div>
        <div class="panel-title">CÍRCULO</div>
        <div class="panel-value" id="p-familia">Cargando...</div>
      </div>
      <div class="panel panel-tr" onclick="showHormiga()">
        <div class="panel-icon">🐜</div>
        <div class="panel-title">HORMIGA</div>
        <div class="panel-value" id="p-hormiga">0.00€ hoy</div>
      </div>
      <div class="panel panel-bl" onclick="setText('¿Cuál es mi próximo recordatorio?')">
        <div class="panel-icon">📅</div>
        <div class="panel-title">PRÓXIMO</div>
        <div class="panel-value">Habla con Aura</div>
      </div>
      <div class="panel panel-br" onclick="showChat()">
        <div class="panel-icon">💬</div>
        <div class="panel-title">HABLAR</div>
        <div class="panel-value">Con Aura IA</div>
      </div>
      <div class="orb-center" onclick="showChat()"></div>
    </div>
  </div>
  <div class="chat-area" id="chat-area">
    <div style="padding:10px 14px 0;flex-shrink:0">
      <button class="btn-back" onclick="showDashboard()">← Volver</button>
    </div>
    <div class="msgs" id="msgs">
      <div class="msg aura">
        <div class="msg-lbl">AURA</div>
        ¡Hola <strong>{{ nombre }}</strong>! 👋 Soy tu asistente personal con IA.<br>
        Toca el orbe o escríbeme para empezar.
        <div class="msg-time">Ahora</div>
      </div>
    </div>
    <div class="typing" id="typing"><span></span><span></span><span></span></div>
    <div class="input-area">
      <div class="tools">
        <div class="tool" onclick="setText('Gasté ')">💰 Gasto</div>
        <div class="tool" onclick="setText('Clima en Barcelona')">🌤 Clima</div>
        <div class="tool" onclick="setText('Cuánto he gastado')">📊 Balance</div>
        <div class="tool" onclick="setText('Recuérdame ')">⏰ Recordar</div>
        <div class="tool" onclick="setText('Cuéntame algo interesante')">✨ Sorpresa</div>
      </div>
      <div class="irow">
        <button class="btn-mic" id="btn-mic" onclick="toggleMic()">🎤</button>
        <input id="msg-input" type="text" placeholder="Escribe o habla con Aura..."
               onkeypress="if(event.key==='Enter')enviar()">
        <button class="btn-send" onclick="enviar()">➤</button>
      </div>
    </div>
  </div>
  <div class="hormiga-page" id="hormiga-page">
    <div style="padding:10px 14px 0;flex-shrink:0;background:rgba(1,5,18,.95);border-bottom:1px solid rgba(251,191,36,.08)">
      <button class="btn-back" onclick="showDashboard()">← Volver</button>
    </div>
    <div class="h-content">
      <div class="h-total">
        <div class="h-total-lbl">GASTOS HORMIGA</div>
        <div class="h-total-amt" id="h-total">0.00€</div>
        <div class="h-total-sub" id="h-sub">0 movimientos</div>
      </div>
      <div class="alerta" id="h-alerta">
        <span style="font-size:24px">😬</span>
        <div>
          <div style="color:#ff6677;font-weight:700;font-size:13px;margin-bottom:3px">¡Alerta hormiga!</div>
          <div style="font-size:12px;color:#ffaaaa;line-height:1.4" id="h-alerta-txt"></div>
        </div>
      </div>
      <div class="filtros">
        <button class="filtro active" onclick="setFiltro('todo',this)">Todo</button>
        <button class="filtro" onclick="setFiltro('hoy',this)">Hoy</button>
        <button class="filtro" onclick="setFiltro('semana',this)">Semana</button>
        <button class="filtro" onclick="setFiltro('mes',this)">Mes</button>
      </div>
      <div class="h-card">
        <div class="h-card-title">DISTRIBUCIÓN 🐜</div>
        <div id="h-grafica"></div>
      </div>
      <div class="h-card">
        <div class="h-card-title">ÚLTIMOS MOVIMIENTOS</div>
        <div id="h-movs"></div>
      </div>
      <div class="h-card">
        <div class="h-card-title">REGISTRAR GASTO</div>
        <div class="add-row">
          <input class="add-inp" id="h-concepto" placeholder="¿En qué? (café, taxi...)">
          <input class="add-inp" id="h-monto" type="number" placeholder="€" style="max-width:80px">
          <button class="add-btn" onclick="addGasto()">+ 🐜</button>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="overlay" id="overlay-familia" onclick="if(event.target===this)cerrarOverlay('familia')">
  <div class="opanel">
    <h3>CÍRCULO</h3>
    <p>Tus contactos de seguridad. Máximo 6 personas.</p>
    <div id="lista-fam"></div>
    <div class="hr"></div>
    <input id="fam-nom" type="text" placeholder="Nombre del contacto">
    <input id="fam-tel" type="tel" placeholder="Teléfono (+34...)">
    <button class="btn-ok" onclick="addFam()">Agregar</button>
    <button class="btn-no" onclick="cerrarOverlay('familia')">Cerrar</button>
  </div>
</div>
<script>
let voz=false,mic=null,escuchando=false,hablando=false,gastos=[],filtro='todo';
if('webkitSpeechRecognition' in window||'SpeechRecognition' in window){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  mic=new SR();mic.lang='es-ES';mic.continuous=false;mic.interimResults=false;
  mic.onresult=e=>{document.getElementById('msg-input').value=e.results[0][0].transcript;setTimeout(enviar,300)};
  mic.onend=()=>{escuchando=false;const b=document.getElementById('btn-mic');b.classList.remove('on');b.textContent='🎤'}}
function toggleMic(){
  if(!mic){alert('Usa Chrome o Safari');return}
  if(escuchando)mic.stop();
  else{if(hablando)window.speechSynthesis.cancel();showChat();mic.start();escuchando=true;
    const b=document.getElementById('btn-mic');b.classList.add('on');b.textContent='⏹'}}
function toggleVoz(){
  voz=!voz;const btn=document.getElementById('btn-voz');
  if(voz){btn.textContent='🔊 ON';btn.classList.add('on');hablar('Voz activada. Soy Aura, ¿en qué puedo ayudarte?')}
  else{btn.textContent='🔊 Voz';btn.classList.remove('on');window.speechSynthesis.cancel()}}
async function hablar(texto){
  if(!voz||!texto)return;
  const t=texto.replace(/<[^>]*>/g,'').replace(/[*_#]/g,'').substring(0,500);
  hablando=true;
  try{const r=await fetch('/voz',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:t})});
    const d=await r.json();
    if(d.audio){const a=new Audio('data:audio/mp3;base64,'+d.audio);a.onended=()=>{hablando=false};a.play();return}}catch(e){}
  window.speechSynthesis.cancel();
  const u=new SpeechSynthesisUtterance(t);u.lang='es-ES';u.rate=0.92;u.pitch=1.05;
  const vs=window.speechSynthesis.getVoices();
  const v=vs.find(x=>x.lang.startsWith('es')&&x.name.includes('Monica'))||vs.find(x=>x.lang.startsWith('es'));
  if(v)u.voice=v;u.onend=()=>{hablando=false};window.speechSynthesis.speak(u)}
function hora(){return new Date().toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'})}
function setText(t){showChat();document.getElementById('msg-input').value=t;document.getElementById('msg-input').focus()}
function showDashboard(){document.getElementById('dashboard').style.display='flex';document.getElementById('chat-area').classList.remove('show');document.getElementById('hormiga-page').classList.remove('show')}
function showChat(){document.getElementById('dashboard').style.display='none';document.getElementById('chat-area').classList.add('show');document.getElementById('hormiga-page').classList.remove('show')}
function showHormiga(){document.getElementById('dashboard').style.display='none';document.getElementById('chat-area').classList.remove('show');document.getElementById('hormiga-page').classList.add('show');cargarGastos()}
function addMsg(html,tipo){const c=document.getElementById('msgs'),d=document.createElement('div');
  d.className='msg '+tipo;d.innerHTML=`<div class="msg-lbl">${tipo==='user'?'TÚ':'AURA'}</div>${html}<div class="msg-time">${hora()}</div>`;
  c.appendChild(d);c.scrollTop=c.scrollHeight}
async function enviar(){const inp=document.getElementById('msg-input'),m=inp.value.trim();if(!m)return;
  inp.value='';showChat();addMsg(m,'user');
  const typing=document.getElementById('typing');typing.style.display='flex';document.getElementById('msgs').scrollTop=99999;
  try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg:m})});
    const d=await r.json();typing.style.display='none';addMsg(d.resp,'aura');hablar(d.resp);actualizarPaneles()}
  catch(e){typing.style.display='none';addMsg('Error de conexión.','aura')}}
function abrirOverlay(id){document.getElementById('overlay-'+id).classList.add('show');if(id==='familia')cargarFam()}
function cerrarOverlay(id){document.getElementById('overlay-'+id).classList.remove('show')}
async function cargarFam(){const r=await fetch('/familia/lista'),d=await r.json();
  const el=document.getElementById('lista-fam');el.innerHTML='';
  if(d.length===0){el.innerHTML='<p style="color:#1a4a6a;font-size:13px">Sin contactos aún.</p>';return}
  d.forEach(f=>{el.innerHTML+=`<div class="fam-card"><div><strong>${f.nombre}</strong><br><small style="color:#2a5a7a">${f.telefono}</small></div><button class="fam-del" onclick="delFam(${f.id})">✕</button></div>`});
  document.getElementById('p-familia').textContent=d.length+' seguros'}
async function addFam(){const nom=document.getElementById('fam-nom').value.trim(),tel=document.getElementById('fam-tel').value.trim();
  if(!nom||!tel){alert('Rellena nombre y teléfono');return}
  const r=await fetch('/familia/agregar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre:nom,telefono:tel})});
  const d=await r.json();if(d.ok){document.getElementById('fam-nom').value='';document.getElementById('fam-tel').value='';cargarFam()}else alert(d.error)}
async function delFam(id){await fetch('/familia/borrar/'+id,{method:'DELETE'});cargarFam()}
const emojis={'café':'☕','cafe':'☕','comida':'🍔','restaurante':'🍽️','taxi':'🚕','uber':'🚗','transporte':'🚌','ropa':'👗','farmacia':'💊','gasolina':'⛽','supermercado':'🛒','ocio':'🎮'};
function getEmoji(c){const cl=c.toLowerCase();for(const[k,v] of Object.entries(emojis)){if(cl.includes(k))return v}return '💸'}
function setFiltro(f,btn){filtro=f;document.querySelectorAll('.filtro').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderGastos()}
function filtrarGastos(){const ahora=new Date();return gastos.filter(g=>{const fecha=new Date(g.fecha);
  if(filtro==='hoy')return fecha.toDateString()===ahora.toDateString();
  if(filtro==='semana')return(ahora-fecha)/(1000*60*60*24)<=7;
  if(filtro==='mes')return fecha.getMonth()===ahora.getMonth()&&fecha.getFullYear()===ahora.getFullYear();
  return true})}
function renderGastos(){const data=filtrarGastos(),total=data.reduce((s,g)=>s+g.monto,0);
  document.getElementById('h-total').textContent=total.toFixed(2)+'€';
  document.getElementById('h-sub').textContent=data.length+' movimientos registrados';
  document.getElementById('p-hormiga').textContent=total.toFixed(2)+'€ total';
  const cats={};data.forEach(g=>{cats[g.concepto]=(cats[g.concepto]||0)+g.monto});
  const sorted=Object.entries(cats).sort((a,b)=>b[1]-a[1]),max=sorted[0]?sorted[0][1]:1;
  const graf=document.getElementById('h-grafica');
  if(sorted.length===0)graf.innerHTML='<p style="color:#1a4a6a;font-size:12px;text-align:center;padding:16px">Sin gastos en este período</p>';
  else graf.innerHTML=sorted.map(([cat,amt])=>`<div class="barra"><div class="barra-info"><span style="color:#8a8a7a">${getEmoji(cat)} ${cat}</span><span style="color:var(--gold);font-family:Rajdhani,sans-serif">${amt.toFixed(2)}€</span></div><div class="barra-bg"><div class="barra-fill" style="width:${(amt/max*100).toFixed(0)}%"></div></div></div>`).join('');
  const movs=document.getElementById('h-movs');
  if(data.length===0)movs.innerHTML='<p style="color:#1a4a6a;font-size:12px;text-align:center;padding:16px">Sin movimientos</p>';
  else movs.innerHTML=[...data].reverse().slice(0,15).map(g=>{const f=new Date(g.fecha).toLocaleDateString('es-ES',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
    return `<div class="mov-item"><div class="mov-l"><span class="mov-emoji">${getEmoji(g.concepto)}</span><div><div class="mov-name">${g.concepto}</div><div class="mov-date">${f}</div></div></div><div class="mov-amt">${g.monto.toFixed(2)}€</div></div>`}).join('');
  const alerta=document.getElementById('h-alerta'),alertaTxt=document.getElementById('h-alerta-txt');
  if(total>100){alerta.classList.add('show');alertaTxt.textContent=`Los gastos pequeños ya suman ${total.toFixed(2)}€`}
  else alerta.classList.remove('show')}
async function cargarGastos(){const r=await fetch('/gastos/lista');gastos=await r.json();renderGastos()}
async function addGasto(){const concepto=document.getElementById('h-concepto').value.trim();
  const monto=parseFloat(document.getElementById('h-monto').value);
  if(!concepto||isNaN(monto)||monto<=0){alert('Rellena concepto y monto');return}
  await fetch('/gastos/agregar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({concepto,monto})});
  document.getElementById('h-concepto').value='';document.getElementById('h-monto').value='';cargarGastos()}
async function actualizarPaneles(){const r=await fetch('/familia/lista'),d=await r.json();
  if(d.length>0)document.getElementById('p-familia').textContent=d.length+' seguros';
  else document.getElementById('p-familia').textContent='Sin contactos';
  const r2=await fetch('/gastos/lista'),g2=await r2.json();
  const hoy=new Date(),gastoHoy=g2.filter(g=>new Date(g.fecha).toDateString()===hoy.toDateString());
  document.getElementById('p-hormiga').textContent=gastoHoy.reduce((s,g)=>s+g.monto,0).toFixed(2)+'€ hoy'}
if('speechSynthesis' in window)window.speechSynthesis.getVoices();
actualizarPaneles();
</script>
</body>
</html>"""

@app.route('/')
def index():
    ensure_tables()
    if current_user.is_authenticated:
        return redirect('/aura')
    return render_template_string(HTML_LOGIN)

@app.route('/login', methods=['POST'])
def login():
    ensure_tables()
    d = request.json
    u = Usuario.query.filter_by(email=d.get('email','')).first()
    if u and check_password_hash(u.password, d.get('password','')):
        login_user(u); return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Email o contraseña incorrectos'})

@app.route('/registro', methods=['POST'])
def registro():
    ensure_tables()
    d = request.json
    if Usuario.query.filter_by(email=d.get('email','')).first():
        return jsonify({'ok': False, 'error': 'Este email ya está registrado'})
    u = Usuario(nombre=d.get('nombre',''), email=d.get('email',''),
                password=generate_password_hash(d.get('password','')))
    db.session.add(u); db.session.commit(); login_user(u)
    return jsonify({'ok': True})

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect('/')

@app.route('/aura')
@login_required
def aura():
    return render_template_string(HTML_AURA, nombre=current_user.nombre)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    msg = request.json.get('msg','')
    hist = Historial.query.filter_by(usuario_id=current_user.id)\
        .order_by(Historial.fecha.desc()).limit(10).all()[::-1]
    msgs = [{'role':h.rol,'content':h.contenido} for h in hist]
    msgs.append({'role':'user','content':msg})
    resp = ''
    if GROQ_OK and GROQ_KEY:
        try:
            client = Groq(api_key=GROQ_KEY)
            r = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role':'system','content':f'Eres Aura, asistente personal de {current_user.nombre} en Barcelona. Respondes en español, de forma natural y concisa. MUY IMPORTANTE: NUNCA inventes datos, gastos ni información que el usuario no haya dicho. Si no tienes datos reales di honestamente que no los tienes.'}]+msgs,
                max_tokens=400)
            resp = r.choices[0].message.content
        except Exception as e:
            resp = f'Error: {str(e)}'
    else:
        resp = 'IA no disponible en este momento.'
    db.session.add(Historial(usuario_id=current_user.id, rol='user', contenido=msg))
    db.session.add(Historial(usuario_id=current_user.id, rol='assistant', contenido=resp))
    db.session.commit()
    return jsonify({'resp': resp})

@app.route('/voz', methods=['POST'])
@login_required
def voz():
    texto = request.json.get('texto','')
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

@app.route('/gastos/agregar', methods=['POST'])
@login_required
def gastos_agregar():
    d = request.json
    g = Gasto(usuario_id=current_user.id, concepto=d.get('concepto','Gasto'), monto=float(d.get('monto',0)))
    db.session.add(g); db.session.commit()
    return jsonify({'ok': True})

@app.route('/gastos/lista')
@login_required
def gastos_lista():
    gs = Gasto.query.filter_by(usuario_id=current_user.id).order_by(Gasto.fecha).all()
    return jsonify([{'id':g.id,'concepto':g.concepto,'monto':g.monto,'fecha':g.fecha.isoformat()} for g in gs])

@app.route('/familia/lista')
@login_required
def familia_lista():
    fs = Familiar.query.filter_by(usuario_id=current_user.id).all()
    return jsonify([{'id':f.id,'nombre':f.nombre,'telefono':f.telefono} for f in fs])

@app.route('/familia/agregar', methods=['POST'])
@login_required
def familia_agregar():
    d = request.json
    if Familiar.query.filter_by(usuario_id=current_user.id).count() >= 6:
        return jsonify({'ok':False,'error':'Máximo 6 contactos'})
    f = Familiar(usuario_id=current_user.id, nombre=d.get('nombre',''), telefono=d.get('telefono',''))
    db.session.add(f); db.session.commit()
    return jsonify({'ok': True})

@app.route('/familia/borrar/<int:fid>', methods=['DELETE'])
@login_required
def familia_borrar(fid):
    f = Familiar.query.filter_by(id=fid, usuario_id=current_user.id).first()
    if f: db.session.delete(f); db.session.commit()
    return jsonify({'ok': True})

if __name__ == '__main__':
    ensure_tables()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
