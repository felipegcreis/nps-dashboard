import dash
from dash import Dash, html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import google.generativeai as genai
import uuid
import threading
import os

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    # Tenta ler do arquivo .env manualmente caso dotenv nao esteja presente
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip('\"\'')

genai.configure(api_key=api_key)

# ================================
# Data Loading & Utilities
# ================================
def load_data():
    df = pd.read_json("pesquisa_data.json")
    prod_order = ["Start", "Light", "Sys", "Premium", "Platinum", "Custom"]
    df['Produto'] = pd.Categorical(df['Produto'], categories=prod_order, ordered=True)
    return df

df_full = load_data()

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
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '0.5rem'}),
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

# Global Styles inside Python
SIDEBAR_STYLE = { 'position': 'fixed', 'top': 0, 'left': 0, 'bottom': 0, 'width': '16rem', 'padding': '2rem 1rem', 'backgroundColor': '#080F17', 'borderRight': '1px solid #1E2D3D', 'zIndex': 1 }
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
    
    html.Div(id='respondentes-count', style={'marginTop': '2rem', 'color': '#1565C0', 'fontWeight': 'bold', 'textAlign': 'center'})
], style=SIDEBAR_STYLE)

# Main App Layout
chat_widget = html.Div([
    dcc.Interval(id='stream-interval', interval=150, disabled=True),
    dcc.Store(id='stream-id', data=None),
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
                dbc.Input(id='chat-input', placeholder="Sua pergunta...", autocomplete="off", style={'backgroundColor': COLORS['bg'], 'color': COLORS['text'], 'borderColor': COLORS['border']}),
                dbc.Button("Enviar", id='chat-send-btn', color="primary")
            ])
        ]),
        id="chat-offcanvas", title="🤖 Isa (Sua Assistente IA)", is_open=False, placement="end",
        style={'backgroundColor': COLORS['bg'], 'color': COLORS['text'], 'borderLeft': f"1px solid {COLORS['border']}"}
    )
])

app.layout = html.Div([
    dcc.Location(id='url'),
    dcc.Store(id='nps-drill-state', data=None),
    dcc.Store(id='chat-history', data=[]),
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
    Output('page-content', 'children'),
    [Input('url', 'pathname'), Input('filter-infra', 'value'), Input('filter-prod', 'value'), Input('nps-drill-state', 'data')]
)
def render_page(pathname, infra, prod, nps_drill):
    if not infra or not prod:
        return html.Div("Selecione os filtros na barra lateral.", style={'color': COLORS['red']})
    
    df = df_full[df_full['Infra'].isin(infra) & df_full['Produto'].isin(prod)].copy()
    N_total = len(df)
    
    overall_nps = nps_score(df['NPS_Cl'])
    prom_cnt = (df['NPS_Cl'] == 'Promotor').sum()
    neut_cnt = (df['NPS_Cl'] == 'Neutro').sum()
    det_cnt = (df['NPS_Cl'] == 'Detrator').sum()

    if pathname == '/':
        kpis = dbc.Row([
            dbc.Col(kpi_card("NPS Geral", f"{overall_nps:+.0f}", nps_color(overall_nps))),
            dbc.Col(kpi_card("Promotores", f"{prom_cnt}", COLORS['green'], f"{prom_cnt/N_total*100:.1f}%" if N_total else "0%")),
            dbc.Col(kpi_card("Neutros", f"{neut_cnt}", COLORS['amber'], f"{neut_cnt/N_total*100:.1f}%" if N_total else "0%")),
            dbc.Col(kpi_card("Detratores", f"{det_cnt}", COLORS['red'], f"{det_cnt/N_total*100:.1f}%" if N_total else "0%")),
            dbc.Col(kpi_card("Respondentes", f"{N_total}", COLORS['blue']))
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
                dbc.Col([section_header("NPS por Produto"), dcc.Graph(figure=fig_nps_prod)], width=8),
                dbc.Col([section_header("NPS Classes"), dcc.Graph(figure=fig_donut)], width=4)
            ]),
            dbc.Row([
                dbc.Col([section_header("Radar CSAT"), dcc.Graph(figure=fig_radar)], width=4),
                dbc.Col([section_header("Média CSAT por Dimensão"), dcc.Graph(figure=fig_bar_csat)], width=8)
            ])
        ])
        
    elif pathname == '/nps':
        if not nps_drill:
            # Level 1
            kpis = dbc.Row([
                dbc.Col(kpi_card("NPS Geral", f"{overall_nps:+.0f}", nps_color(overall_nps))),
                dbc.Col(kpi_card("Promotores", f"{prom_cnt}", COLORS['green'])),
                dbc.Col(kpi_card("Neutros", f"{neut_cnt}", COLORS['amber'])),
                dbc.Col(kpi_card("Detratores", f"{det_cnt}", COLORS['red']))
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
                    dbc.Col([html.Strong("Histograma"), dcc.Graph(figure=fig_hist)], width=8),
                    dbc.Col([html.Strong("Gauge"), dcc.Graph(figure=fig_gauge)], width=4)
                ]),
                section_header("NPS por Produto"),
                dcc.Graph(figure=fig_stack),
                section_header("Selecione um produto para Drill-down"),
                drill_buttons
            ])
        else:
            # Level 2 Drilldown
            df_p = df[df['Produto'] == nps_drill]
            n_p = len(df_p)
            snps = nps_score(df_p['NPS_Cl'])
            kpis = dbc.Row([
                dbc.Col(kpi_card(f"NPS {nps_drill}", f"{snps:+.0f}", nps_color(snps), f"N={n_p}")),
                dbc.Col(kpi_card("Promotores", f"{(df_p['NPS_Cl']=='Promotor').sum()}", COLORS['green'])),
                dbc.Col(kpi_card("Neutros", f"{(df_p['NPS_Cl']=='Neutro').sum()}", COLORS['amber'])),
                dbc.Col(kpi_card("Detratores", f"{(df_p['NPS_Cl']=='Detrator').sum()}", COLORS['red']))
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
                    dbc.Col([html.Strong("Distribuição"), dcc.Graph(figure=fig_hp)]),
                    dbc.Col([html.Strong("CSAT Produto vs Base"), dcc.Graph(figure=fig_csat_cmp)])
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
            cols.append(dbc.Col(kpi_card(k, f"{m:.2f}", csat_color(m), f"N={len(valid)}")))
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
                dbc.Col([html.Strong("Heatmap Produto x Dimensão"), dcc.Graph(figure=fig_hm)], width=12)
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
            dbc.Row(dbc.Col([html.Strong("Concentração por Produto"), dcc.Graph(figure=fig_tm)], width=12)),
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
from dash import ctx
@callback(
    Output('nps-drill-state', 'data'),
    [Input({'type': 'drill-btn', 'index': dash.ALL}, 'n_clicks'), Input('btn-nps-back', 'n_clicks')],
    [State('nps-drill-state', 'data')]
)
def handle_drilldown(drill_clicks, back_clicks, current_state):
    if not ctx.triggered: return current_state
    trigger_id = ctx.triggered[0]['prop_id']
    if 'btn-nps-back' in trigger_id:
        return None
    
    import json
    if 'drill-btn' in trigger_id:
        try:
            dict_id = json.loads(trigger_id.split('.')[0])
            return dict_id['index']
        except:
            return current_state
    return current_state

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

STREAMS = {}

def stream_worker(sid, full_prompt):
    try:
        # Usando versão estável para evitar travamento da stream gRPC (preview lite 3.1 tem instabilidades conhecidas de conexão no meio da requisição)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(full_prompt, stream=True)
        for chunk in response:
            try:
                if chunk.text:
                    STREAMS[sid]['text'] += chunk.text
            except Exception as read_err:
                print(f"Erro lendo chunk gRPC: {read_err}")
                continue
        STREAMS[sid]['done'] = True
    except Exception as e:
        STREAMS[sid]['text'] += f"\\n\\n**(Falha na IA)**: Houve uma instabilidade de rede ou limite de cota da API ({str(e)}). Tente enviar a pergunta novamente."
        STREAMS[sid]['done'] = True

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

@callback(
    Output('chat-history', 'data', allow_duplicate=True),
    Output('stream-id', 'data'),
    Output('stream-interval', 'disabled', allow_duplicate=True),
    Output('chat-input', 'value'),
    Output('chat-display', 'children', allow_duplicate=True),
    Input('chat-send-btn', 'n_clicks'),
    Input('chat-input', 'n_submit'),
    State('chat-input', 'value'),
    State('chat-history', 'data'),
    State('filter-infra', 'value'),
    State('filter-prod', 'value'),
    prevent_initial_call=True
)
def start_chat(n_clicks, n_submit, user_message, chat_history, infra, prod):
    if not user_message: return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    if chat_history is None:
        chat_history = []
        
    chat_history.append({'role': 'user', 'parts': [user_message]})
    chat_history.append({'role': 'model', 'parts': [""]}) # Placeholder
    
    display = render_chat(chat_history)
    
    d = df_full[df_full['Infra'].isin(infra) & df_full['Produto'].isin(prod)] if infra and prod else df_full
    nps_g = nps_score(d['NPS_Cl'])
    total_resp = len(d)
    produtos = list(d['Produto'].dropna().unique())
    
    context = (f"Seu nome é Isa. Você é a inteligência artificial analisando a pesquisa NPS/CSAT da Sisloc Software. "
               f"Responda ao usuário com base no contexto filtrado atual: "
               f"Total de respondentes: {total_resp}. NPS Geral: {nps_g:.0f}. Produtos: {produtos}. "
               f"Promotores (9-10), Neutros (7-8), Detratores (0-6). Start tem NPS +100. Premium tem NPS negativo (-8). "
               f"O foco principal dos detratores é Suporte pós-venda e implantação de NFS-e pagas. ")
    
    history_text = "\\n".join([f"{m['role']}: {m['parts'][0]}" for m in chat_history[:-1]])
    full_prompt = f"{context}\\n\\nHistórico da conversa:\\n{history_text}\\n\\nResponda como a assistente Isa. Importante: Use SEMPRE formatação rica em Markdown na sua resposta:"
    
    sid = str(uuid.uuid4())
    STREAMS[sid] = {'text': '', 'done': False}
    
    threading.Thread(target=stream_worker, args=(sid, full_prompt)).start()
    
    return chat_history, sid, False, "", display

@callback(
    Output('chat-display', 'children'),
    Output('chat-history', 'data'),
    Output('stream-interval', 'disabled'),
    Input('stream-interval', 'n_intervals'),
    State('stream-id', 'data'),
    State('chat-history', 'data'),
    prevent_initial_call=True
)
def update_stream(n, sid, chat_history):
    if not sid or sid not in STREAMS or not chat_history: 
        return dash.no_update, dash.no_update, dash.no_update
        
    current_text = STREAMS[sid]['text']
    is_done = STREAMS[sid]['done']
    
    cursor = " █" if not is_done else ""
    chat_history[-1]['parts'] = [current_text + cursor]
    display = render_chat(chat_history)
    
    if is_done:
        chat_history[-1]['parts'] = [current_text]
        display = render_chat(chat_history)
        del STREAMS[sid]
        return display, chat_history, True
        
    return display, chat_history, False

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8051)
