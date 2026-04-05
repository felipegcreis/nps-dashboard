import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from google import genai
from google.genai import types as genai_types
from flask import session, redirect, request
import uuid
import threading
import os
import rag

# ================================
# Leitura do .env
# ================================
def read_env():
    env = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"\'')
    return env

_env = read_env()

api_key = os.environ.get("GEMINI_API_KEY") or _env.get("GEMINI_API_KEY", "")
secret_key = os.environ.get("SECRET_KEY") or _env.get("SECRET_KEY", "sisloc-secret")
ADMIN_USER = os.environ.get("ADMIN_USER") or _env.get("ADMIN_USER", "")
USERS_FILE = "users.json"

import hashlib, json

def hash_pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def check_credentials(username, password):
    users = load_users()
    return users.get(username) == hash_pwd(password)

gemini_client = genai.Client(api_key=api_key)

ISA_SYSTEM_PROMPT = """Você é Isa, especialista em análise de pesquisas de NPS e CSAT da Sisloc Software.

Regras que você NUNCA deve quebrar:
1. Respostas diretas, objetivas e claras — sem rodeios, sem introduções longas.
2. Use sempre dados concretos: números, percentuais, nomes de produtos/clientes quando relevante.
3. SEMPRE termine sua resposta propondo uma próxima ação ao usuário (ex: "Quer ver as principais reclamações dos detratores do Premium?").
4. Quando citar dados de fora do filtro ativo do dashboard, deixe isso explícito (ex: "⚠️ Este dado é do conjunto completo, fora do seu filtro atual.").
5. Responda em Markdown.
6. Nunca invente dados — se não souber, diga que não há informação suficiente."""

# ================================
# Data Loading & Utilities
# ================================
def load_data():
    df = pd.read_excel("nps.xlsx")

    # Renomear colunas longas para nomes curtos usados no app
    df = df.rename(columns={
        'Qual a probabilidade de recomendar  a Sisloc a um amigo ou colega?': 'NPS',
        'Considerando sua experiência geral, você está satisfeito com o sistema da Sisloc?': 'CS_Sis',
        'Considerando sua experiência geral, quanto você está satisfeito com o Suporte da Sisloc?': 'CS_Sup',
        'Considerando sua experiência geral, quanto você está satisfeito com a Sisloc Academy (Universidade Corporativa)?': 'CS_Aca',
        'Considerando sua experiência geral, quanto você está satisfeito com o atendimento da área Comercial da Sisloc?': 'CS_Com',
        'Considerando sua experiência geral, quanto você está satisfeito com o Sisloc In Cloud?': 'CS_Cld',
        'O que você mais gosta na Sisloc? Por quê? (Produto, atendimento, suporte, pessoas, processos ou outros pontos positivos).': 'Positivos',
        'O que você acredita que a Sisloc pode melhorar para oferecer uma experiência ainda melhor?': 'Melhorias',
        'Se pudéssemos melhorar apenas UMA coisa hoje, o que faria mais diferença para você?': 'Uma_Melhoria',
    })

    # NPS numérico e classificação
    df['NPS'] = pd.to_numeric(df['NPS'], errors='coerce')
    df['NPS_Cl'] = df['NPS'].apply(
        lambda x: 'Promotor' if x >= 9 else ('Neutro' if x >= 7 else 'Detrator')
        if pd.notna(x) else None
    )

    # Infra derivado de Cloud(S/N)
    df['Infra'] = df['Cloud(S/N)'].map({'S': 'Cloud', 'N': 'On-Premises'})

    # CSAT numérico
    csat_map = {'Insatisfeito': 1, 'Pouco Satisfeito': 2, 'Satisfeito': 3, 'Muito Satisfeito': 4}
    for col in ['CS_Sis', 'CS_Sup', 'CS_Aca', 'CS_Com', 'CS_Cld']:
        df[f'{col}_n'] = df[col].map(csat_map)

    prod_order = ["Start", "Light", "Sys", "Premium", "Platinum", "Custom"]
    df['Produto'] = pd.Categorical(df['Produto'], categories=prod_order, ordered=True)
    return df

df_full = load_data()
rag_index = rag.load_or_build_index(df_full.to_dict('records'), gemini_client)

COLORS = {
    'bg': '#080F17', 'card': '#101B27', 'border': '#1E2D3D', 'navy': '#0D1B2A',
    'blue': '#1565C0', 'teal': '#00838F', 'green': '#2E7D32', 'amber': '#E65100',
    'red': '#B71C1C', 'text': '#E8EDF2', 'sub': '#4A6080'
}

def nps_score(series):
    if len(series) == 0: return 0
    prom = (series == 'Promotor').sum()
    det = (series == 'Detrator').sum()
    raw = ((prom - det) / len(series)) * 100
    # Arredondamento padrão (round half up/away from zero)
    return int(raw + 0.5) if raw >= 0 else int(raw - 0.5)

def nps_color(score):
    if score >= 50: return COLORS['green']
    if score >= 0: return COLORS['amber']
    return COLORS['red']

def csat_color(val):
    if pd.isna(val) or val == 0: return COLORS['border']
    if val >= 4.0: return COLORS['green']
    if val >= 3.5: return COLORS['amber']
    if val >= 3.0: return '#F57C00'
    return COLORS['red']

def base_layout(title='', h=400):
    return dict(
        title=dict(text=title, font=dict(color=COLORS['text'])),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=h,
        font=dict(color=COLORS['text'], family="DM Sans"),
        xaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border']),
        yaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border']),
        margin=dict(l=20, r=20, t=40, b=20)
    )

# ================================
# Components Generators
# ================================
def kpi_card(label, value, color, sub=''):
    return html.Div([
        html.Div(label, style={'color': '#4A6080', 'fontSize': '0.85rem', 'textTransform': 'uppercase', 'fontWeight': 'bold', 'marginBottom': '0.2rem'}),
        html.Div(value, style={'color': '#E8EDF2', 'fontSize': '2.2rem', 'margin': '0.2rem 0', 'fontWeight': '700', 'lineHeight': '1.1', 'fontFamily': 'Syne'}),
        html.Div(sub, style={'color': '#4A6080', 'fontSize': '0.8rem'})
    ], style={
        'backgroundColor': '#101B27', 'border': '1px solid #1E2D3D', 'borderRadius': '8px', 
        'padding': '1rem', 'textAlign': 'center', 'marginBottom': '1rem', 
        'position': 'relative', 'overflow': 'hidden', 'borderTop': f'4px solid {color}'
    })

def quote_card(texto, classe, score, produto, infra):
    b_col = COLORS['green'] if classe == 'Promotor' else COLORS['amber'] if classe == 'Neutro' else COLORS['red']
    return html.Div([
        html.Div([
            html.Span(f"{classe.upper()} • {score}", style={'padding': '2px 6px', 'borderRadius': '4px', 'fontWeight': 'bold', 'color': 'white', 'fontSize': '0.75rem', 'backgroundColor': b_col}),
            html.Span(f"{produto} • {infra}", style={'color': '#4A6080', 'fontSize': '0.85rem'})
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '4px', 'marginBottom': '0.5rem'}),
        html.Div(f'"{texto}"', style={'color': '#E8EDF2', 'fontStyle': 'italic', 'lineHeight': '1.4'})
    ], style={'backgroundColor': '#101B27', 'border': '1px solid #1E2D3D', 'borderRadius': '6px', 'padding': '1rem', 'marginBottom': '0.8rem'})

def section_header(text):
    return html.Div(text, style={
        'textTransform': 'uppercase', 'letterSpacing': '1px', 'borderBottom': '1px solid #1E2D3D',
        'paddingBottom': '0.5rem', 'marginTop': '2rem', 'marginBottom': '1rem', 'color': '#E8EDF2',
        'fontSize': '1.2rem', 'fontFamily': 'Syne'
    })

# ================================
# App Setup
# ================================
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, "https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=Syne:wght@600;700;800&display=swap"], suppress_callback_exceptions=True)
app.title = "Sisloc - Dash"
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <!-- Google Tag Manager -->
        <script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
        new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
        j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
        'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
        })(window,document,'script','dataLayer','GTM-KS4T8RFM');</script>
        <!-- End Google Tag Manager -->
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        <!-- Google Tag Manager (noscript) -->
        <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-KS4T8RFM"
        height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
        <!-- End Google Tag Manager (noscript) -->
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''
app.server.secret_key = secret_key

# ================================
# Autenticação Flask
# ================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sisloc — Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #080F17; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: 'DM Sans', sans-serif; }}
        .card {{ background: #101B27; border: 1px solid #1E2D3D; border-radius: 12px; padding: 2.5rem 2rem; width: 100%; max-width: 380px; }}
        h1 {{ font-family: 'Syne', sans-serif; color: #E8EDF2; font-size: 1.6rem; margin-bottom: 0.3rem; }}
        p {{ color: #4A6080; font-size: 0.9rem; margin-bottom: 2rem; }}
        label {{ color: #4A6080; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 0.4rem; }}
        input {{ width: 100%; background: #080F17; border: 1px solid #1E2D3D; border-radius: 6px; padding: 10px 14px; color: #E8EDF2; font-size: 1rem; margin-bottom: 1.2rem; outline: none; }}
        input:focus {{ border-color: #1565C0; }}
        button {{ width: 100%; background: #1565C0; color: white; border: none; border-radius: 6px; padding: 12px; font-size: 1rem; font-weight: 500; cursor: pointer; font-family: 'DM Sans', sans-serif; }}
        button:hover {{ background: #1976D2; }}
        .error {{ color: #B71C1C; font-size: 0.85rem; margin-bottom: 1rem; background: rgba(183,28,28,0.1); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(183,28,28,0.3); }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Sisloc Analytics</h1>
        <p>Pesquisa de Satisfação — Fev/2026</p>
        {error}
        <form method="POST" action="/login">
            <label>Usuário</label>
            <input type="text" name="username" autocomplete="username" required autofocus>
            <label>Senha</label>
            <input type="password" name="password" autocomplete="current-password" required>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

MANAGE_USERS_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sisloc — Gerenciar Usuários</title>
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #080F17; font-family: 'DM Sans', sans-serif; color: #E8EDF2; padding: 2rem; }}
        h1 {{ font-family: 'Syne', sans-serif; font-size: 1.6rem; margin-bottom: 0.3rem; }}
        .sub {{ color: #4A6080; font-size: 0.9rem; margin-bottom: 2rem; }}
        .card {{ background: #101B27; border: 1px solid #1E2D3D; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; max-width: 600px; }}
        h2 {{ font-family: 'Syne', sans-serif; font-size: 1.1rem; margin-bottom: 1rem; color: #E8EDF2; }}
        label {{ color: #4A6080; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 0.4rem; margin-top: 0.8rem; }}
        input {{ width: 100%; background: #080F17; border: 1px solid #1E2D3D; border-radius: 6px; padding: 9px 12px; color: #E8EDF2; font-size: 0.95rem; outline: none; }}
        input:focus {{ border-color: #1565C0; }}
        .btn {{ display: inline-block; padding: 9px 20px; border-radius: 6px; border: none; cursor: pointer; font-size: 0.9rem; font-family: 'DM Sans', sans-serif; font-weight: 500; margin-top: 1rem; }}
        .btn-primary {{ background: #1565C0; color: white; }}
        .btn-primary:hover {{ background: #1976D2; }}
        .btn-danger {{ background: transparent; border: 1px solid #B71C1C; color: #B71C1C; padding: 4px 12px; margin-top: 0; font-size: 0.8rem; }}
        .btn-danger:hover {{ background: rgba(183,28,28,0.1); }}
        .msg-ok {{ color: #2E7D32; background: rgba(46,125,50,0.1); border: 1px solid rgba(46,125,50,0.3); padding: 8px 12px; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; }}
        .msg-err {{ color: #B71C1C; background: rgba(183,28,28,0.1); border: 1px solid rgba(183,28,28,0.3); padding: 8px 12px; border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td, th {{ padding: 10px 12px; border-bottom: 1px solid #1E2D3D; text-align: left; font-size: 0.9rem; }}
        th {{ color: #4A6080; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }}
        .badge-admin {{ background: #1565C0; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
        a.back {{ color: #4A6080; text-decoration: none; font-size: 0.85rem; display: inline-block; margin-bottom: 1.5rem; }}
        a.back:hover {{ color: #E8EDF2; }}
    </style>
</head>
<body>
    <a class="back" href="/">← Voltar ao Dashboard</a>
    <h1>Gerenciar Usuários</h1>
    <p class="sub">Apenas você pode acessar esta página.</p>
    {msg}
    <div class="card">
        <h2>Usuários Cadastrados</h2>
        <table>
            <tr><th>E-mail</th><th>Perfil</th><th></th></tr>
            {user_rows}
        </table>
    </div>
    <div class="card">
        <h2>Adicionar / Atualizar Usuário</h2>
        <form method="POST" action="/admin/users">
            <input type="hidden" name="action" value="add">
            <label>E-mail</label>
            <input type="email" name="new_username" placeholder="nome@empresa.com.br" required>
            <label>Senha</label>
            <div style="position:relative;">
                <input type="password" name="new_password" id="new_password" placeholder="Mínimo 6 caracteres" required style="padding-right:42px;">
                <button type="button" onclick="var i=document.getElementById('new_password');i.type=i.type==='password'?'text':'password';this.textContent=i.type==='password'?'👁':'🙈';" style="position:absolute;right:0;top:0;height:100%;background:transparent;border:none;cursor:pointer;padding:0 12px;font-size:1rem;color:#4A6080;">👁</button>
            </div>
            <br>
            <button type="submit" class="btn btn-primary">Salvar Usuário</button>
        </form>
    </div>
</body>
</html>
"""

@app.server.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if check_credentials(username, password):
            session["authenticated"] = True
            session["username"] = username
            return redirect("/")
        error = '<div class="error">Usuário ou senha incorretos.</div>'
    return LOGIN_HTML.format(error=error)

@app.server.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.server.route("/admin/users", methods=["GET", "POST"])
def manage_users():
    if not session.get("authenticated") or session.get("username") != ADMIN_USER:
        return redirect("/")
    msg = ""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            u = request.form.get("new_username", "").strip()
            p = request.form.get("new_password", "").strip()
            if u and len(p) >= 6:
                users = load_users()
                users[u] = hash_pwd(p)
                save_users(users)
                msg = f'<div class="msg-ok">Usuário <strong>{u}</strong> salvo com sucesso.</div>'
            else:
                msg = '<div class="msg-err">Preencha e-mail e senha (mín. 6 caracteres).</div>'
        elif action == "delete":
            u = request.form.get("del_username", "").strip()
            if u and u != ADMIN_USER:
                users = load_users()
                users.pop(u, None)
                save_users(users)
                msg = f'<div class="msg-ok">Usuário <strong>{u}</strong> removido.</div>'
            else:
                msg = '<div class="msg-err">Não é possível remover o administrador.</div>'

    users = load_users()
    rows = ""
    for u in users:
        is_admin = u == ADMIN_USER
        badge = '<span class="badge-admin">Admin</span>' if is_admin else ""
        delete_btn = "" if is_admin else f"""
            <form method="POST" action="/admin/users" style="display:inline">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="del_username" value="{u}">
                <button type="submit" class="btn btn-danger" onclick="return confirm('Remover {u}?')">Remover</button>
            </form>"""
        rows += f"<tr><td>{u}</td><td>{badge}</td><td>{delete_btn}</td></tr>"

    return MANAGE_USERS_HTML.format(msg=msg, user_rows=rows)

@app.server.before_request
def require_login():
    allowed = ["/login", "/admin/users", "/_dash-component-suites", "/_dash-layout",
               "/_dash-dependencies", "/assets", "/_reload-hash", "/_dash-update-component"]
    if any(request.path.startswith(p) for p in allowed):
        return None
    if not session.get("authenticated"):
        return redirect("/login")

# Global Styles inside Python
SIDEBAR_STYLE = { 'position': 'fixed', 'top': 0, 'left': 0, 'bottom': 0, 'width': '16rem', 'padding': '2rem 1rem', 'backgroundColor': '#080F17', 'borderRight': '1px solid #1E2D3D', 'zIndex': 1050 }
CONTENT_STYLE = { 'marginLeft': '16rem', 'padding': '2rem 2rem', 'backgroundColor': '#080F17', 'minHeight': '100vh', 'fontFamily': 'DM Sans' }

sidebar = html.Div([
    html.H3("Sisloc Analytics", style={'fontFamily': 'Syne', 'color': '#E8EDF2'}),
    html.P("Pesquisa Fev/2026", style={'color': '#4A6080', 'marginBottom': '2rem'}),
    
    dbc.Nav([
        dbc.NavLink("📊 Visão Geral", href="/", active="exact"),
        dbc.NavLink("📈 Análise NPS", href="/nps", active="exact"),
        dbc.NavLink("⭐ Análise CSAT", href="/csat", active="exact"),
        dbc.NavLink("🚨 Detratores", href="/detratores", active="exact"),
        dbc.NavLink("💬 Respostas Abertas", href="/respostas", active="exact")
    ], vertical=True, pills=True, style={'marginBottom': '2rem'}),
    
    html.Hr(style={'borderColor': '#1E2D3D'}),
    html.Strong("Filtros Globais", style={'color': '#E8EDF2'}),
    
    html.Div("Infraestrutura", style={'color': '#4A6080', 'fontSize': '0.85rem', 'marginTop': '1rem', 'marginBottom': '0.5rem'}),
    dcc.Dropdown(
        id='filter-infra',
        options=[{'label': i, 'value': i} for i in df_full['Infra'].dropna().unique()],
        value=df_full['Infra'].dropna().unique().tolist(),
        multi=True,
        style={'color': '#000'} # Dropdown text color needs to be dark for standard dcc.Dropdown to be visible against white box
    ),
    
    html.Div("Produto", style={'color': '#4A6080', 'fontSize': '0.85rem', 'marginTop': '1rem', 'marginBottom': '0.5rem'}),
    dcc.Dropdown(
        id='filter-prod',
        options=[{'label': p, 'value': p} for p in ["Start", "Light", "Sys", "Premium", "Platinum", "Custom"] if p in df_full['Produto'].dropna().unique()],
        value=df_full['Produto'].dropna().unique().tolist(),
        multi=True,
        style={'color': '#000'}
    ),
    
    html.Div(id='cross-filter-badge', style={'marginTop': '1rem'}),
    dbc.Button("✕ Limpar seleção", id='clear-cross-filter', size="sm", color="warning", style={'display': 'none', 'width': '100%', 'marginTop': '0.5rem'}),
    html.Div(id='respondentes-count', style={'marginTop': '2rem', 'color': '#1565C0', 'fontWeight': 'bold', 'textAlign': 'center'}),
    html.Div(id='sidebar-admin-link'),
    html.A("Sair", href="/logout", style={'display': 'block', 'marginTop': '1rem', 'color': '#4A6080', 'fontSize': '0.85rem', 'textDecoration': 'none', 'textAlign': 'center'})
], id='sidebar', style=SIDEBAR_STYLE)

# Main App Layout
chat_widget = html.Div([
    dbc.Button("💬 Chat IA", id="open-chat-btn", color="primary", style={'position': 'fixed', 'bottom': '20px', 'right': '20px', 'borderRadius': '50px', 'padding': '10px 20px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.3)', 'zIndex': 9999}),
    dbc.Offcanvas(
        html.Div([
            html.Div(id='drag-handle', style={
                'position': 'absolute', 'top': 0, 'bottom': 0, 'left': '-5px', 'width': '15px', 
                'cursor': 'ew-resize', 'zIndex': 9999, 'backgroundColor': 'transparent'
            }),
            html.P("Pergunte para a Isa qualquer coisa sobre os dados da pesquisa.", style={'color': COLORS['sub']}),
            html.Div(id='chat-display', style={'height': '70vh', 'overflowY': 'auto', 'backgroundColor': COLORS['card'], 'padding': '1rem', 'borderRadius': '8px', 'border': f"1px solid {COLORS['border']}", 'marginBottom': '1rem'}),
            dbc.InputGroup([
                dcc.Input(id='chat-input', placeholder="Sua pergunta...", autoComplete="off", debounce=False, n_submit=0, type='text', style={'flex': '1', 'backgroundColor': COLORS['bg'], 'color': COLORS['text'], 'borderColor': COLORS['border'], 'borderRadius': '4px 0 0 4px', 'padding': '8px 12px', 'border': f"1px solid {COLORS['border']}", 'outline': 'none', 'width': '100%'}),
                dbc.Button("Enviar", id='chat-send-btn', color="primary")
            ])
        ]),
        id="chat-offcanvas", title="Isa - Inteligência Artificial Sisloc", is_open=False, placement="end",
        style={'backgroundColor': COLORS['bg'], 'color': COLORS['text'], 'borderLeft': f"1px solid {COLORS['border']}"}
    )
])

app.layout = html.Div([
    dcc.Location(id='url'),
    dcc.Store(id='nps-drill-state', data=None),
    dcc.Store(id='chat-history', data=[]),
    dcc.Store(id='stream-id', data=None),
    dcc.Store(id='sidebar-open', data=False),
    dcc.Store(id='cross-filter', data={}),
    dcc.Interval(id='stream-interval', interval=300, n_intervals=0, disabled=False),
    html.Button("☰", id='hamburger-btn'),
    html.Div(id='sidebar-overlay'),
    sidebar,
    html.Div(id='page-content', style=CONTENT_STYLE),
    chat_widget
])

# ================================
# Callbacks
# ================================
@callback(
    Output('respondentes-count', 'children'),
    [Input('filter-infra', 'value'), Input('filter-prod', 'value')]
)
def update_count(infra, prod):
    if not infra or not prod: return "0 respondentes"
    d = df_full[df_full['Infra'].isin(infra) & df_full['Produto'].isin(prod)]
    return f"{len(d)} respondentes filtrados"

@callback(
    Output('sidebar-admin-link', 'children'),
    Input('url', 'pathname')
)
def show_admin_link(pathname):
    if session.get("username") == ADMIN_USER:
        return html.A("⚙ Gerenciar Usuários", href="/admin/users", style={
            'display': 'block', 'marginTop': '2rem', 'color': '#1565C0',
            'fontSize': '0.85rem', 'textDecoration': 'none', 'textAlign': 'center'
        })
    return None

@callback(
    Output('sidebar', 'className'),
    Output('sidebar-overlay', 'className'),
    Output('sidebar-open', 'data'),
    [Input('hamburger-btn', 'n_clicks'),
     Input('sidebar-overlay', 'n_clicks'),
     Input('url', 'pathname')],
    State('sidebar-open', 'data'),
    prevent_initial_call=True
)
def toggle_sidebar(ham_clicks, overlay_clicks, pathname, is_open):
    trigger = ctx.triggered_id
    if trigger in ('hamburger-btn', 'sidebar-overlay'):
        new_open = not is_open
    else:
        new_open = False
    return ('sidebar-open' if new_open else '', 'overlay-open' if new_open else '', new_open)

@callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'), Input('filter-infra', 'value'), Input('filter-prod', 'value'),
     Input('cross-filter', 'data'), Input('nps-drill-state', 'data')]
)
def render_page(pathname, infra, prod, cross_filter, nps_drill):
    if not infra or not prod:
        return html.Div("Selecione os filtros na barra lateral.", style={'color': COLORS['red']})
    
    df = df_full[df_full['Infra'].isin(infra) & df_full['Produto'].isin(prod)].copy()

    # Aplicar cross-filter (cliques nos gráficos)
    cf = cross_filter or {}
    if cf.get('Produto'):
        df = df[df['Produto'] == cf['Produto']]
    if cf.get('NPS_Cl'):
        df = df[df['NPS_Cl'] == cf['NPS_Cl']]
    _CSAT_DIM_COL = {'Sistema': 'CS_Sis', 'Suporte': 'CS_Sup', 'Academy': 'CS_Aca', 'Comercial': 'CS_Com', 'Cloud': 'CS_Cld'}
    if cf.get('CSAT_dim'):
        _col = _CSAT_DIM_COL.get(cf['CSAT_dim'])
        if _col:
            df = df[df[f'{_col}_n'].notna()]

    N_total = len(df)
    
    overall_nps = nps_score(df['NPS_Cl'])
    prom_cnt = (df['NPS_Cl'] == 'Promotor').sum()
    neut_cnt = (df['NPS_Cl'] == 'Neutro').sum()
    det_cnt = (df['NPS_Cl'] == 'Detrator').sum()

    if pathname == '/':
        kpis = dbc.Row([
            dbc.Col(kpi_card("NPS Geral", f"{overall_nps:+.0f}", nps_color(overall_nps)), xs=6, md=True),
            dbc.Col(kpi_card("Promotores", f"{prom_cnt}", COLORS['green'], f"{prom_cnt/N_total*100:.1f}%" if N_total else "0%"), xs=6, md=True),
            dbc.Col(kpi_card("Neutros", f"{neut_cnt}", COLORS['amber'], f"{neut_cnt/N_total*100:.1f}%" if N_total else "0%"), xs=6, md=True),
            dbc.Col(kpi_card("Detratores", f"{det_cnt}", COLORS['red'], f"{det_cnt/N_total*100:.1f}%" if N_total else "0%"), xs=6, md=True),
            dbc.Col(kpi_card("Respondentes", f"{N_total}", COLORS['blue']), xs=6, md=True)
        ])
        
        # NPS Bar
        prod_nps = df.groupby('Produto', observed=True)['NPS_Cl'].apply(nps_score).reset_index().sort_values(by='Produto', ascending=False)
        fig_nps_prod = go.Figure(go.Bar(
            y=prod_nps['Produto'], x=prod_nps['NPS_Cl'], orientation='h',
            marker_color=[nps_color(x) for x in prod_nps['NPS_Cl']], text=[f"{x:+.0f}" for x in prod_nps['NPS_Cl']], textposition='auto'
        ))
        lay1 = base_layout(h=300)
        lay1['xaxis'].update(dtick=20)
        fig_nps_prod.update_layout(**lay1)
        
        # NPS Donut
        fig_donut = go.Figure(go.Pie(
            labels=['Promotores', 'Neutros', 'Detratores'], values=[prom_cnt, neut_cnt, det_cnt],
            hole=0.6, marker_colors=[COLORS['green'], COLORS['amber'], COLORS['red']], textinfo='percent'
        ))
        fig_donut.update_layout(**base_layout(h=300), showlegend=True, annotations=[dict(text=f"{overall_nps:+.0f}", font_size=28, showarrow=False, font_color=COLORS['text'])])
        
        # CSAT Radar
        csat_cols = ['CS_Sis_n', 'CS_Sup_n', 'CS_Aca_n', 'CS_Com_n', 'CS_Cld_n']
        labels = ['Sistema', 'Suporte', 'Academy', 'Comercial', 'Cloud']
        means = [df[c].dropna().mean() if len(df[c].dropna())>0 else 0 for c in csat_cols]
        fig_radar = go.Figure(go.Scatterpolar(r=means + [means[0]] if means else [], theta=labels + [labels[0]] if labels else [], fill='toself', fillcolor='rgba(21, 101, 192, 0.4)', line_color=COLORS['blue']))
        rlay = base_layout(h=300)
        rlay.update(polar=dict(radialaxis=dict(visible=True, range=[1, 5], gridcolor=COLORS['border'], linecolor=COLORS['border']), angularaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border'])))
        fig_radar.update_layout(**rlay)
        
        # CSAT Bar
        df_csat = pd.DataFrame({'Dimensão': labels, 'Média': means})
        fig_bar_csat = go.Figure(go.Bar(
            x=df_csat['Dimensão'], y=df_csat['Média'], marker_color=[csat_color(x) for x in df_csat['Média']], text=[f"{x:.2f}" for x in df_csat['Média']], textposition='auto'
        ))
        fig_bar_csat.add_hline(y=4.0, line_dash="dash", line_color=COLORS['green'], annotation_text="Meta (4.0)")
        fig_bar_csat.add_hline(y=3.5, line_dash="dash", line_color=COLORS['amber'], annotation_text="Alerta (3.5)")
        lay2 = base_layout(h=300)
        lay2['yaxis'].update(range=[1, 5])
        fig_bar_csat.update_layout(**lay2)
        
        return html.Div([
            html.H2("📊 Visão Geral Executiva", style={'fontFamily':'Syne'}),
            kpis,
            dbc.Row([
                dbc.Col([section_header("NPS por Produto"), dcc.Graph(id={'type': 'cf-graph', 'index': 'nps-prod'}, figure=fig_nps_prod)], xs=12, md=8),
                dbc.Col([section_header("NPS Classes"), dcc.Graph(id={'type': 'cf-graph', 'index': 'donut'}, figure=fig_donut)], xs=12, md=4)
            ]),
            dbc.Row([
                dbc.Col([section_header("Radar CSAT"), dcc.Graph(id={'type': 'cf-graph', 'index': 'radar'}, figure=fig_radar)], xs=12, md=4),
                dbc.Col([section_header("Média CSAT por Dimensão"), dcc.Graph(id={'type': 'cf-graph', 'index': 'csat-bar'}, figure=fig_bar_csat)], xs=12, md=8)
            ])
        ])
        
    elif pathname == '/nps':
        if not nps_drill:
            # Level 1
            kpis = dbc.Row([
                dbc.Col(kpi_card("NPS Geral", f"{overall_nps:+.0f}", nps_color(overall_nps)), xs=6, md=True),
                dbc.Col(kpi_card("Promotores", f"{prom_cnt}", COLORS['green']), xs=6, md=True),
                dbc.Col(kpi_card("Neutros", f"{neut_cnt}", COLORS['amber']), xs=6, md=True),
                dbc.Col(kpi_card("Detratores", f"{det_cnt}", COLORS['red']), xs=6, md=True)
            ])
            fig_hist = px.histogram(df, x='NPS', color='NPS_Cl', nbins=11, range_x=[-0.5, 10.5], color_discrete_map={'Promotor': COLORS['green'], 'Neutro': COLORS['amber'], 'Detrator': COLORS['red']}, category_orders={"NPS_Cl": ["Detrator", "Neutro", "Promotor"]})
            l_hist = base_layout(h=250)
            l_hist['xaxis'].update(dtick=1)
            fig_hist.update_layout(**l_hist)
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=overall_nps, domain={'x': [0, 1], 'y': [0, 1]},
                gauge=dict(axis=dict(range=[-100, 100]), bar=dict(color=nps_color(overall_nps)),
                steps=[dict(range=[-100, 0], color="rgba(183,28,28,0.2)"), dict(range=[0, 50], color="rgba(230,81,0,0.2)"), dict(range=[50, 100], color="rgba(46,125,50,0.2)")],
                threshold=dict(line=dict(color=COLORS['text'], width=2), thickness=0.75, value=35))
            ))
            fig_gauge.update_layout(**base_layout(h=250))
            
            prod_comp = df.groupby(['Produto', 'NPS_Cl'], observed=True).size().unstack(fill_value=0)
            prods_sorted = df.groupby('Produto', observed=True)['NPS_Cl'].apply(nps_score).sort_values(ascending=False).index
            prod_comp = prod_comp.reindex(prods_sorted)
            fig_stack = go.Figure()
            for c, color in zip(["Detrator", "Neutro", "Promotor"], [COLORS['red'], COLORS['amber'], COLORS['green']]):
                if c in prod_comp.columns:
                    fig_stack.add_trace(go.Bar(name=c, y=prod_comp.index, x=prod_comp[c], orientation='h', marker_color=color))
            fig_stack.update_layout(**base_layout(h=300), barmode='stack')
            
            drill_buttons = html.Div([
                dbc.Button(f"Explorar {p} →", id={'type': 'drill-btn', 'index': p}, color="primary", className="m-1")
                for p in prods_sorted
            ], style={'display':'flex', 'flexWrap': 'wrap', 'gap': '10px'})
            
            return html.Div([
                html.H2("📈 Análise NPS", style={'fontFamily':'Syne'}),
                kpis,
                dbc.Row([
                    dbc.Col([html.Strong("Histograma"), dcc.Graph(figure=fig_hist)], xs=12, md=8),
                    dbc.Col([html.Strong("Gauge"), dcc.Graph(figure=fig_gauge)], xs=12, md=4)
                ]),
                section_header("NPS por Produto"),
                dcc.Graph(id={'type': 'cf-graph', 'index': 'nps-stack'}, figure=fig_stack),
                section_header("Selecione um produto para Drill-down"),
                drill_buttons
            ])
        else:
            # Level 2 Drilldown
            df_p = df[df['Produto'] == nps_drill]
            n_p = len(df_p)
            snps = nps_score(df_p['NPS_Cl'])
            kpis = dbc.Row([
                dbc.Col(kpi_card(f"NPS {nps_drill}", f"{snps:+.0f}", nps_color(snps), f"N={n_p}"), xs=6, md=True),
                dbc.Col(kpi_card("Promotores", f"{(df_p['NPS_Cl']=='Promotor').sum()}", COLORS['green']), xs=6, md=True),
                dbc.Col(kpi_card("Neutros", f"{(df_p['NPS_Cl']=='Neutro').sum()}", COLORS['amber']), xs=6, md=True),
                dbc.Col(kpi_card("Detratores", f"{(df_p['NPS_Cl']=='Detrator').sum()}", COLORS['red']), xs=6, md=True)
            ])
            
            fig_hp = px.histogram(df_p, x='NPS', color='NPS_Cl', nbins=11, range_x=[-0.5, 10.5], color_discrete_map={'Promotor': COLORS['green'], 'Neutro': COLORS['amber'], 'Detrator': COLORS['red']})
            l_hp = base_layout(h=300)
            l_hp['xaxis'].update(dtick=1)
            fig_hp.update_layout(**l_hp)
            
            csat_cols = ['CS_Sis_n', 'CS_Sup_n', 'CS_Aca_n', 'CS_Com_n', 'CS_Cld_n']
            labels = ['Sistema', 'Suporte', 'Academy', 'Comercial', 'Cloud']
            means_p = [df_p[c].dropna().mean() if len(df_p[c].dropna())>0 else 0 for c in csat_cols]
            means_base = [df[c].dropna().mean() if len(df[c].dropna())>0 else 0 for c in csat_cols]
            
            fig_csat_cmp = go.Figure(data=[
                go.Bar(name=nps_drill, x=labels, y=means_p, marker_color=COLORS['blue']),
                go.Scatter(name='Média Base', x=labels, y=means_base, mode='lines+markers', line=dict(color=COLORS['text'], dash='dash'))
            ])
            lay_cm = base_layout(h=300)
            lay_cm['yaxis'].update(range=[1, 5.5])
            fig_csat_cmp.update_layout(**lay_cm, barmode='group')
            
            # Quotes
            dets = df_p[df_p['NPS_Cl'] == 'Detrator']
            quote_divs = []
            for _, row in dets.iterrows():
                msg = row['Uma_Melhoria'] if pd.notna(row['Uma_Melhoria']) else row['Melhorias']
                if pd.notna(msg): quote_divs.append(quote_card(msg, row['NPS_Cl'], row['NPS'], row['Produto'], row['Infra']))
            
            return html.Div([
                dbc.Button("← Voltar", id='btn-nps-back', outline=True, color="light", className="mb-3"),
                html.H2(f"🔍 Drill-down: {nps_drill}", style={'fontFamily':'Syne'}),
                kpis,
                dbc.Row([
                    dbc.Col([html.Strong("Distribuição"), dcc.Graph(figure=fig_hp)], xs=12, md=6),
                    dbc.Col([html.Strong("CSAT Produto vs Base"), dcc.Graph(figure=fig_csat_cmp)], xs=12, md=6)
                ]),
                section_header("Voz dos Detratores do Produto"),
                html.Div(quote_divs if quote_divs else "Nenhum feedback de detrator disponível.", style={'maxHeight':'400px', 'overflowY':'auto'})
            ])
            
    elif pathname == '/csat':
        csat_map = {'Sistema': 'CS_Sis_n', 'Suporte': 'CS_Sup_n', 'Academy': 'CS_Aca_n', 'Comercial': 'CS_Com_n', 'Cloud': 'CS_Cld_n'}
        cols = []
        for k, colname in csat_map.items():
            valid = df[colname].dropna()
            m = valid.mean() if len(valid) > 0 else 0
            cols.append(dbc.Col(kpi_card(k, f"{m:.2f}", csat_color(m), f"N={len(valid)}"), xs=6, md=True))
        kpis = dbc.Row(cols)
        
        hm_data = []
        for p in df['Produto'].unique():
            row = {'Produto': p}
            for k, col in csat_map.items():
                d = df[df['Produto']==p][col].dropna()
                row[k] = d.mean() if len(d) > 0 else np.nan
            hm_data.append(row)
        df_hm = pd.DataFrame(hm_data).set_index('Produto')
        fig_hm = px.imshow(df_hm.fillna(0), text_auto='.2f', aspect="auto", color_continuous_scale="RdYlGn", range_color=[1, 5])
        fig_hm.update_layout(**base_layout(h=350))
        
        return html.Div([
            html.H2("⭐ Análise CSAT (Geral)", style={'fontFamily':'Syne'}),
            kpis,
            dbc.Row([
                dbc.Col([html.Strong("Heatmap Produto x Dimensão"), dcc.Graph(id={'type': 'cf-graph', 'index': 'csat-hm'}, figure=fig_hm)], width=12)
            ])
        ])
        
    elif pathname == '/detratores':
        dets = df[df['NPS_Cl'] == 'Detrator']
        n_det = len(dets)
        if n_det == 0: return html.Div("Nenhum detrator encontrado!")
        
        counts = dets['Produto'].value_counts().reset_index()
        counts.columns = ['Produto', 'N']
        fig_tm = px.treemap(counts, path=['Produto'], values='N', color='N', color_continuous_scale="Reds")
        fig_tm.update_layout(**base_layout(h=350))
        
        quote_divs = []
        for _, row in dets.sort_values(by='NPS').iterrows():
            msg = row['Uma_Melhoria'] if pd.notna(row['Uma_Melhoria']) else row['Melhorias']
            if pd.notna(msg): quote_divs.append(quote_card(msg, row['NPS_Cl'], row['NPS'], row['Produto'], row['Infra']))
            
        return html.Div([
            html.H2("🚨 Análise de Risco (Detratores)", style={'fontFamily':'Syne'}),
            dbc.Row(dbc.Col(kpi_card("Total Detratores", f"{n_det}", COLORS['red']))),
            dbc.Row(dbc.Col([html.Strong("Concentração por Produto"), dcc.Graph(id={'type': 'cf-graph', 'index': 'treemap'}, figure=fig_tm)], width=12)),
            section_header("Voz dos Detratores"),
            html.Div(quote_divs)
        ])
        
    elif pathname == '/respostas':
        quote_divs = []
        d_filt = df.dropna(subset=['Uma_Melhoria'])
        for _, row in d_filt.iterrows():
            quote_divs.append(quote_card(row['Uma_Melhoria'], row['NPS_Cl'], row['NPS'], row['Produto'], row['Infra']))
            
        return html.Div([
            html.H2("💬 Respostas Abertas (Visão Geral - Uma Melhoria)", style={'fontFamily':'Syne'}),
            dbc.Row(dbc.Col(kpi_card("Total Respostas (Uma Melhoria)", f"{len(d_filt)}", COLORS['blue']))),
            html.Div(quote_divs)
        ])
        
    return html.Div([
        html.H2("Página não encontrada", style={'fontFamily':'Syne'})
    ])

# Callback for Drilldown clicks
import json

@callback(
    Output('nps-drill-state', 'data'),
    Input({'type': 'drill-btn', 'index': dash.ALL}, 'n_clicks'),
    State('nps-drill-state', 'data'),
    prevent_initial_call=True
)
def handle_drill(drill_clicks, current_state):
    if not ctx.triggered: return current_state
    trigger_id = ctx.triggered[0]['prop_id']
    if 'drill-btn' in trigger_id:
        try:
            dict_id = json.loads(trigger_id.split('.')[0])
            return dict_id['index']
        except:
            return current_state
    return current_state

@callback(
    Output('nps-drill-state', 'data', allow_duplicate=True),
    Input('btn-nps-back', 'n_clicks'),
    prevent_initial_call=True
)
def handle_back(n_clicks):
    return None

@callback(
    Output('cross-filter', 'data'),
    Input({'type': 'cf-graph', 'index': dash.ALL}, 'clickData'),
    State({'type': 'cf-graph', 'index': dash.ALL}, 'id'),
    State('cross-filter', 'data'),
    prevent_initial_call=True
)
def update_cross_filter(all_clicks, all_ids, current_cf):
    if not ctx.triggered:
        return {}
    triggered_prop = ctx.triggered[0]['prop_id']
    if not triggered_prop or 'cf-graph' not in triggered_prop:
        return current_cf or {}

    # Encontrar qual gráfico foi clicado
    click_data = ctx.triggered[0]['value']
    if not click_data or not click_data.get('points'):
        return {}

    try:
        import json as _json
        graph_id = _json.loads(triggered_prop.split('.')[0])['index']
    except Exception:
        return {}

    point = click_data['points'][0]
    cf = current_cf or {}

    if graph_id == 'nps-prod':
        val = point.get('y')
        # toggle: clicar no mesmo deseleciona
        new_cf = {} if cf.get('Produto') == val else {'Produto': val}
    elif graph_id == 'donut':
        label_map = {'Promotores': 'Promotor', 'Neutros': 'Neutro', 'Detratores': 'Detrator'}
        val = label_map.get(point.get('label', ''))
        new_cf = {} if cf.get('NPS_Cl') == val else {'NPS_Cl': val}
    elif graph_id in ('nps-stack',):
        val = point.get('y')
        new_cf = {} if cf.get('Produto') == val else {'Produto': val}
    elif graph_id == 'csat-hm':
        val = point.get('y')
        new_cf = {} if cf.get('Produto') == val else {'Produto': val}
    elif graph_id == 'treemap':
        val = point.get('label') or point.get('id', '').split('/')[-1]
        new_cf = {} if cf.get('Produto') == val else {'Produto': val}
    elif graph_id == 'csat-bar':
        val = point.get('x')  # nome da dimensão: 'Sistema', 'Suporte', etc.
        new_cf = {} if cf.get('CSAT_dim') == val else {'CSAT_dim': val}
    elif graph_id == 'radar':
        val = point.get('theta')  # nome da dimensão no eixo angular
        new_cf = {} if cf.get('CSAT_dim') == val else {'CSAT_dim': val}
    else:
        return current_cf or {}

    return new_cf


@callback(
    Output('cross-filter', 'data', allow_duplicate=True),
    Input('clear-cross-filter', 'n_clicks'),
    prevent_initial_call=True
)
def clear_cross_filter(_):
    return {}


@callback(
    Output('clear-cross-filter', 'style'),
    Output('cross-filter-badge', 'children'),
    Input('cross-filter', 'data')
)
def update_cross_filter_ui(cf):
    cf = cf or {}
    if not cf:
        return {'display': 'none', 'width': '100%', 'marginTop': '0.5rem'}, None

    parts = []
    if cf.get('Produto'):
        parts.append(f"Produto: {cf['Produto']}")
    if cf.get('NPS_Cl'):
        parts.append(f"Classe: {cf['NPS_Cl']}")
    if cf.get('CSAT_dim'):
        parts.append(f"Dimensão CSAT: {cf['CSAT_dim']}")

    badge = html.Div([
        html.Div("Seleção ativa:", style={'color': '#E65100', 'fontSize': '0.75rem', 'textTransform': 'uppercase', 'fontWeight': 'bold', 'marginBottom': '0.25rem'}),
        html.Div(" • ".join(parts), style={'color': '#E8EDF2', 'fontSize': '0.85rem'})
    ], style={'backgroundColor': '#1a2a1a', 'border': '1px solid #E65100', 'borderRadius': '6px', 'padding': '0.5rem'})

    return {'display': 'block', 'width': '100%', 'marginTop': '0.5rem'}, badge


@callback(
    Output("chat-offcanvas", "is_open"),
    Input("open-chat-btn", "n_clicks"),
    [State("chat-offcanvas", "is_open")],
    prevent_initial_call=True
)
def toggle_chat(n_clicks, is_open):
    if n_clicks is not None:
        return not is_open
    return is_open

@callback(
    Output("open-chat-btn", "style"),
    Input("chat-offcanvas", "is_open")
)
def toggle_button_visibility(is_open):
    base_style = {'position': 'fixed', 'bottom': '20px', 'right': '20px', 'borderRadius': '50px', 'padding': '10px 20px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.3)', 'zIndex': 9999}
    if is_open:
        base_style['display'] = 'none'
    return base_style

stream_buffers = {}  # {stream_id: {'text': str, 'done': bool}}

def stream_gemini_bg(stream_id, user_message, filter_stats, active_prod, active_infra, history_text):
    print(f"[DEBUG] stream_gemini_bg started: {stream_id[:8]}", flush=True)
    try:
        # Estágio 1: buscando contexto via RAG
        stream_buffers[stream_id]['stage'] = 'rag'
        hits = rag.retrieve(user_message, gemini_client, rag_index, top_k=6)
        rag_lines = []
        for score, doc in hits:
            meta = doc['meta']
            outside = meta.get('Produto') not in active_prod or meta.get('Infra') not in active_infra
            flag = " ⚠️ [fora do filtro ativo]" if outside else ""
            rag_lines.append(f"[relevância {score:.2f}{flag}] {doc['text']}")
        rag_context = "\n".join(rag_lines)

        full_prompt = (
            f"## Estatísticas do filtro ativo\n{filter_stats}\n\n"
            f"## Respostas mais relevantes da pesquisa (RAG)\n{rag_context}\n\n"
            f"## Histórico da conversa\n{history_text}\n\n"
            f"## Pergunta do usuário\n{user_message}"
        )

        # Estágio 2: gerando resposta com o modelo
        stream_buffers[stream_id]['stage'] = 'generating'
        for chunk in gemini_client.models.generate_content_stream(
            model='gemini-3.1-flash-lite-preview',
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(system_instruction=ISA_SYSTEM_PROMPT),
        ):
            if chunk.text:
                stream_buffers[stream_id]['text'] += chunk.text
        print(f"[DEBUG] stream done: {stream_id[:8]}, text_len={len(stream_buffers[stream_id]['text'])}", flush=True)
    except Exception as e:
        print(f"[DEBUG] stream error: {e}", flush=True)
        stream_buffers[stream_id]['text'] = f"**(Falha na IA)**: {str(e)}"
    finally:
        stream_buffers[stream_id]['done'] = True

def render_chat(chat_history):
    display_children = []
    for msg in chat_history:
        if not msg['parts'][0]: continue
        is_user = msg['role'] == 'user'
        align = 'right' if is_user else 'left'
        bg = COLORS['blue'] if is_user else COLORS['navy']
        border = f"1px solid {COLORS['border']}" if not is_user else "none"
        display_children.append(
            html.Div(
                html.Div(
                    dcc.Markdown(msg['parts'][0], style={'margin': '0'}, dangerously_allow_html=True), 
                    style={'backgroundColor': bg, 'padding': '10px 15px', 'borderRadius': '15px', 'border': border, 'display': 'inline-block', 'maxWidth': '85%', 'textAlign': 'left', 'color': 'white', 'overflowX': 'auto'}
                ),
                style={'textAlign': align, 'marginBottom': '10px'}
            )
        )
    return display_children

STAGE_LABELS = {
    'rag':        '🔍 Buscando contexto na pesquisa...',
    'generating': '✍️ Gerando resposta...',
}

def _status_bubble(label: str):
    return html.Div(
        html.Div([
            html.Span(className='isa-spinner', children=[
                html.Span(), html.Span(), html.Span()
            ]),
            html.Span(label, style={'fontSize': '0.9rem'}),
        ], className='isa-status', style={
            'backgroundColor': COLORS['navy'], 'padding': '10px 15px', 'borderRadius': '15px',
            'border': f"1px solid {COLORS['border']}", 'display': 'inline-block', 'maxWidth': '85%',
        }),
        style={'textAlign': 'left', 'marginBottom': '10px'}
    )

def _thinking_bubble():
    return _status_bubble("Preparando...")

def _streaming_bubble(text):
    return html.Div(
        html.Div([
            dcc.Markdown(text, style={'margin': '0'}, dangerously_allow_html=True),
            html.Span("▌", style={'color': COLORS['sub']})
        ], style={
            'backgroundColor': COLORS['navy'], 'padding': '10px 15px', 'borderRadius': '15px',
            'border': f"1px solid {COLORS['border']}", 'display': 'inline-block', 'maxWidth': '85%',
            'textAlign': 'left', 'color': 'white', 'overflowX': 'auto'
        }),
        style={'textAlign': 'left', 'marginBottom': '10px'}
    )

@callback(
    Output('chat-history', 'data'),
    Output('chat-display', 'children'),
    Output('chat-input', 'value'),
    Output('stream-id', 'data'),
    Input('chat-send-btn', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    State('chat-input', 'value'),
    State('chat-history', 'data'),
    State('filter-infra', 'value'),
    State('filter-prod', 'value'),
    prevent_initial_call=True
)
def send_chat(n_clicks, n_submit, user_message, chat_history, infra, prod):
    if not user_message:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if chat_history is None:
        chat_history = []

    chat_history = chat_history + [{'role': 'user', 'parts': [user_message]}]

    # Filtro ativo
    active_infra = set(infra) if infra else set(df_full['Infra'].dropna().unique())
    active_prod  = set(prod)  if prod  else set(df_full['Produto'].dropna().unique())
    d = df_full[df_full['Infra'].isin(active_infra) & df_full['Produto'].isin(active_prod)]

    # Estatísticas do filtro ativo
    nps_g = nps_score(d['NPS_Cl'])
    total_resp = len(d)
    stats_lines = [f"**Filtro ativo** — {total_resp} respondentes | NPS Geral: {nps_g}"]
    for prod_name, grp in d.groupby('Produto', observed=True):
        n = len(grp)
        prom = (grp['NPS_Cl'] == 'Promotor').sum()
        neu  = (grp['NPS_Cl'] == 'Neutro').sum()
        det  = (grp['NPS_Cl'] == 'Detrator').sum()
        nps_p = nps_score(grp['NPS_Cl'])
        stats_lines.append(f"- {prod_name}: n={n}, NPS={nps_p}, Promotores={prom}, Neutros={neu}, Detratores={det}")
    filter_stats = "\n".join(stats_lines)

    history_text = "\n".join([f"{m['role']}: {m['parts'][0]}" for m in chat_history[:-1]])

    sid = str(uuid.uuid4())
    stream_buffers[sid] = {'text': '', 'done': False, 'stage': 'rag'}
    threading.Thread(
        target=stream_gemini_bg,
        args=(sid, user_message, filter_stats, active_prod, active_infra, history_text),
        daemon=True,
    ).start()

    # Feedback imediato: mostra mensagem do usuário + thinking bubble sem esperar o interval
    return chat_history, render_chat(chat_history) + [_thinking_bubble()], "", sid


@callback(
    Output('chat-display', 'children', allow_duplicate=True),
    Output('chat-history', 'data', allow_duplicate=True),
    Input('stream-interval', 'n_intervals'),
    State('stream-id', 'data'),
    State('chat-history', 'data'),
    prevent_initial_call=True
)
def poll_stream(n_intervals, stream_id, chat_history):
    history = chat_history or []

    # Sem stream ativo: não toca em nada (evita sobrescrever com State desatualizado)
    if not stream_id or stream_id not in stream_buffers:
        return dash.no_update, dash.no_update

    buf = stream_buffers[stream_id]
    text = buf['text']
    done = buf['done']
    print(f"[DEBUG] poll_stream: sid={stream_id[:8]}, done={done}, text_len={len(text)}", flush=True)

    if done:
        del stream_buffers[stream_id]
        final_history = history + [{'role': 'model', 'parts': [text]}]
        return render_chat(final_history), final_history

    display = render_chat(history)
    if text:
        display.append(_streaming_bubble(text))
    else:
        stage = buf.get('stage', 'rag')
        display.append(_status_bubble(STAGE_LABELS.get(stage, 'Preparando...')))
    return display, history

app.clientside_callback(
    """
    function(children) {
        var el = document.getElementById('chat-display');
        if (el) {
            setTimeout(function() { el.scrollTop = el.scrollHeight; }, 30);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('chat-display', 'data-autoscroll'),
    Input('chat-display', 'children'),
)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8051))
    app.run(debug=False, host='0.0.0.0', port=port)
