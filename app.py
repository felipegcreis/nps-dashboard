import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np

st.set_page_config(page_title="Sisloc - Pesquisa de Satisfação", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&family=Syne:wght@600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3, .section-header, .kpi-value { font-family: 'Syne', sans-serif; }
    header {visibility: hidden;} footer {visibility: hidden;}
    
    .kpi-card { background-color: #101B27; border: 1px solid #1E2D3D; border-radius: 8px; padding: 1rem; text-align: center; margin-bottom: 1rem; position: relative; overflow: hidden; }
    .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background-color: var(--card-color, #1E2D3D); }
    .kpi-label { color: #4A6080; font-size: 0.85rem; text-transform: uppercase; font-weight: bold; margin-bottom: 0.2rem; }
    .kpi-value { color: #E8EDF2; font-size: 2.2rem; margin: 0.2rem 0; font-weight: 700; line-height: 1.1; }
    .kpi-sub { color: #4A6080; font-size: 0.8rem; }
    
    .section-header { text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #1E2D3D; padding-bottom: 0.5rem; margin-top: 2rem; margin-bottom: 1rem; color: #E8EDF2; font-size: 1.2rem; }
    
    .quote-card { background-color: #101B27; border: 1px solid #1E2D3D; border-radius: 6px; padding: 1rem; margin-bottom: 0.8rem; }
    .quote-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.85rem; }
    .quote-badge { padding: 2px 6px; border-radius: 4px; font-weight: bold; color: white; font-size: 0.75rem; }
    .badge-det { background-color: #B71C1C; } .badge-neut { background-color: #E65100; } .badge-prom { background-color: #2E7D32; }
    .quote-meta { color: #4A6080; } .quote-text { color: #E8EDF2; font-style: italic; line-height: 1.4; }
    
    .insight-card { background-color: #101B27; border-left: 4px solid #1E2D3D; padding: 1rem; margin-bottom: 1rem; border-radius: 0 4px 4px 0; }
    .insight-card.risk { border-left-color: #B71C1C; } .insight-card.warn { border-left-color: #E65100; } .insight-card.ok { border-left-color: #2E7D32; } .insight-card.info { border-left-color: #1565C0; }
    .insight-title { font-weight: bold; margin-bottom: 0.3rem; color: #E8EDF2; } .insight-text { font-size: 0.9rem; color: #4A6080; line-height: 1.4; }
    
    div[data-testid="stSidebar"] { border-right: 1px solid #1E2D3D !important; }
    button[kind="secondary"] { border: 1px solid #1E2D3D !important; color: #E8EDF2 !important; }
    button[kind="secondary"]:hover { border-color: #1565C0 !important; color: #1565C0 !important; }
</style>
""", unsafe_allow_html=True)

COLORS = { 'bg': '#080F17', 'card': '#101B27', 'border': '#1E2D3D', 'navy': '#0D1B2A', 'blue': '#1565C0', 'teal': '#00838F', 'green': '#2E7D32', 'amber': '#E65100', 'red': '#B71C1C', 'text': '#E8EDF2', 'sub': '#4A6080' }

@st.cache_data
def load_data():
    df = pd.read_json("pesquisa_data.json")
    prod_order = ["Start", "Light", "Sys", "Premium", "Platinum", "Custom"]
    df['Produto'] = pd.Categorical(df['Produto'], categories=prod_order, ordered=True)
    return df

try:
    df_full = load_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

def nps_score(series):
    if len(series) == 0: return 0.0
    prom = (series == 'Promotor').sum()
    det = (series == 'Detrator').sum()
    return ((prom - det) / len(series)) * 100

def nps_color(score):
    if score >= 50: return COLORS['green']
    if score >= 0: return COLORS['amber']
    return COLORS['red']

def nps_class_color(cls):
    if cls == 'Promotor': return COLORS['green']
    if cls == 'Neutro': return COLORS['amber']
    return COLORS['red']

def csat_color(val):
    if pd.isna(val): return COLORS['border']
    if val >= 4.0: return COLORS['green']
    if val >= 3.5: return COLORS['amber']
    if val >= 3.0: return '#F57C00' # Laranja
    return COLORS['red']

def base_layout(title='', h=400):
    return dict(
        title=dict(text=title, font=dict(color=COLORS['text'])),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=h,
        font=dict(color=COLORS['text']),
        xaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border']),
        yaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border']),
        margin=dict(l=20, r=20, t=40, b=20)
    )

def kpi_card(label, value, color, sub=''):
    st.markdown(f"""
    <div class="kpi-card" style="--card-color: {color};">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def quote_card(texto, classe, score, produto, infra):
    badge_cls = 'badge-prom' if classe == 'Promotor' else 'badge-neut' if classe == 'Neutro' else 'badge-det'
    st.markdown(f"""
    <div class="quote-card">
        <div class="quote-header">
            <span class="quote-badge {badge_cls}">{classe.upper()} &middot; {score}</span>
            <span class="quote-meta">{produto} &middot; {infra}</span>
        </div>
        <div class="quote-text">"{texto}"</div>
    </div>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = "Visão Geral"
if 'nps_drill_prod' not in st.session_state: st.session_state.nps_drill_prod = None

# Sidebar
with st.sidebar:
    st.title("Sisloc Analytics")
    st.markdown("### Pesquisa de Satisfação (Fev/2026)")
    
    pg_options = ["Visão Geral", "Análise NPS", "Análise CSAT", "Detratores", "Respostas Abertas"]
    current_index = pg_options.index(st.session_state.page) if st.session_state.page in pg_options else 0
    # Provide a selectbox or radio without firing direct session_state sync bugs
    selected_page = st.radio("Navegação", pg_options, index=current_index, key="nav_radio")
    
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.session_state.nps_drill_prod = None
        st.rerun()
        
    st.markdown("---")
    st.markdown("**Filtros Globais**")
    
    all_infra = sorted([x for x in df_full['Infra'].unique() if pd.notna(x)])
    sel_infra = st.multiselect("Infraestrutura", all_infra, default=all_infra)
    
    all_prods = list(df_full['Produto'].dropna().unique())
    all_prods = [p for p in ["Start", "Light", "Sys", "Premium", "Platinum", "Custom"] if p in all_prods]
    sel_prods = st.multiselect("Produto", all_prods, default=all_prods)

if not sel_infra or not sel_prods:
    st.warning("Selecione ao menos uma infraestrutura e um produto nos filtros da barra lateral.")
    st.stop()

df = df_full[df_full['Infra'].isin(sel_infra) & df_full['Produto'].isin(sel_prods)].copy()
N_total = len(df)
st.sidebar.markdown(f"*(**{N_total}** respondentes filtrados)*")

# Page Content
if st.session_state.page == "Visão Geral":
    st.title("📊 Visão Geral Executiva")
    st.markdown(f"**Pesquisa de Satisfação de Clientes Sisloc — Fevereiro 2026**")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    overall_nps = nps_score(df['NPS_Cl'])
    prom_cnt = (df['NPS_Cl'] == 'Promotor').sum()
    neut_cnt = (df['NPS_Cl'] == 'Neutro').sum()
    det_cnt = (df['NPS_Cl'] == 'Detrator').sum()
    
    with c1: kpi_card("NPS Geral", f"{overall_nps:+.1f}", nps_color(overall_nps), "Score da Base")
    with c2: kpi_card("Promotores", f"{prom_cnt}", COLORS['green'], f"{prom_cnt/N_total*100:.1f}%" if N_total else "0%")
    with c3: kpi_card("Neutros", f"{neut_cnt}", COLORS['amber'], f"{neut_cnt/N_total*100:.1f}%" if N_total else "0%")
    with c4: kpi_card("Detratores", f"{det_cnt}", COLORS['red'], f"{det_cnt/N_total*100:.1f}%" if N_total else "0%")
    with c5: kpi_card("Respondentes", f"{N_total}", COLORS['blue'], "Total Válidos")
    
    r1c1, r1c2 = st.columns([2, 1])
    with r1c1:
        st.markdown("<div class='section-header'>NPS por Produto</div>", unsafe_allow_html=True)
        prod_nps = df.groupby('Produto', observed=True)['NPS_Cl'].apply(nps_score).reset_index()
        prod_nps = prod_nps.sort_values(by='Produto', ascending=False)
        fig_nps_prod = go.Figure(go.Bar(
            y=prod_nps['Produto'], x=prod_nps['NPS_Cl'], orientation='h',
            marker_color=[nps_color(x) for x in prod_nps['NPS_Cl']],
            text=[f"{x:+.1f}" for x in prod_nps['NPS_Cl']], textposition='auto'
        ))
        fig_nps_prod.update_layout(**base_layout(h=300))
        st.plotly_chart(fig_nps_prod, use_container_width=True)
        
    with r1c2:
        st.markdown("<div class='section-header'>NPS Classes</div>", unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=['Promotores', 'Neutros', 'Detratores'], values=[prom_cnt, neut_cnt, det_cnt],
            hole=0.6, marker_colors=[COLORS['green'], COLORS['amber'], COLORS['red']], textinfo='percent'
        ))
        fig_donut.update_layout(**base_layout(h=300), showlegend=True, 
            legend=dict(yanchor="bottom", y=-0.2, xanchor="center", x=0.5, orientation="h"),
            annotations=[dict(text=f"{overall_nps:+.1f}", font_size=28, showarrow=False, font_color=COLORS['text'])]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    r2c1, r2c2 = st.columns([1, 2])
    csat_cols = ['CS_Sis_n', 'CS_Sup_n', 'CS_Aca_n', 'CS_Com_n', 'CS_Cld_n']
    labels = ['Sistema', 'Suporte', 'Academy', 'Comercial', 'Cloud']
    means = [df[c].dropna().mean() if len(df[c].dropna())>0 else 0 for c in csat_cols]
    
    with r2c1:
        st.markdown("<div class='section-header'>Radar CSAT</div>", unsafe_allow_html=True)
        fig_radar = go.Figure(go.Scatterpolar(
            r=means + [means[0]] if means else [], theta=labels + [labels[0]] if labels else [],
            fill='toself', fillcolor='rgba(21, 101, 192, 0.4)', line_color=COLORS['blue']
        ))
        rlay = base_layout(h=300)
        rlay.update(polar=dict(radialaxis=dict(visible=True, range=[1, 5], gridcolor=COLORS['border'], linecolor=COLORS['border']), angularaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border'])))
        fig_radar.update_layout(**rlay)
        st.plotly_chart(fig_radar, use_container_width=True)
        
    with r2c2:
        st.markdown("<div class='section-header'>Média CSAT por Dimensão</div>", unsafe_allow_html=True)
        df_csat = pd.DataFrame({'Dimensão': labels, 'Média': means})
        fig_bar_csat = go.Figure(go.Bar(
            x=df_csat['Dimensão'], y=df_csat['Média'],
            marker_color=[csat_color(x) for x in df_csat['Média']],
            text=[f"{x:.2f}" for x in df_csat['Média']], textposition='auto'
        ))
        fig_bar_csat.add_hline(y=4.0, line_dash="dash", line_color=COLORS['green'], annotation_text="Meta (4.0)")
        fig_bar_csat.add_hline(y=3.5, line_dash="dash", line_color=COLORS['amber'], annotation_text="Alerta (3.5)")
        lay2 = base_layout(h=300)
        lay2['yaxis']['range'] = [1, 5]
        fig_bar_csat.update_layout(**lay2)
        st.plotly_chart(fig_bar_csat, use_container_width=True)

    st.markdown("<div class='section-header'>Insights Estratégicos</div>", unsafe_allow_html=True)
    i1, i2 = st.columns(2)
    with i1:
        st.markdown("""<div class="insight-card risk"><div class="insight-title">🔴 Premium é o epicentro do problema</div><div class="insight-text">NPS de -8.3 no maior grupo. CSAT inferior em todas dimensões. Concentra a maioria dos detratores.</div></div>""", unsafe_allow_html=True)
        st.markdown("""<div class="insight-card ok"><div class="insight-title">🟢 Sys e Start confirmam tese</div><div class="insight-text">NPS alto (+30.8 / +100.0). Aderência alta valida focar nos segmentos de pequenas e médias empresas.</div></div>""", unsafe_allow_html=True)
    with i2:
        st.markdown("""<div class="insight-card warn"><div class="insight-title">🟠 Suporte é driver de detração</div><div class="insight-text">Aparece nas respostas de detratores com sensação de abandono, lentidão e resolução ineficaz de bugs.</div></div>""", unsafe_allow_html=True)
        st.markdown("""<div class="insight-card info"><div class="insight-title">🔵 Fiscal/NFS-e como ruptura</div><div class="insight-text">Clientes Premium/Platinum sinalizam churn por terem que pagar adaptações fiscais tendo mensalidade alta.</div></div>""", unsafe_allow_html=True)

elif st.session_state.page == "Análise NPS":
    prod_focus = st.session_state.nps_drill_prod
    if not prod_focus:
        # Nivel 1
        st.title("📈 Análise NPS")
        
        overall_nps = nps_score(df['NPS_Cl'])
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("NPS Geral", f"{overall_nps:+.1f}", nps_color(overall_nps))
        with c2: kpi_card("Promotores", f"{(df['NPS_Cl']=='Promotor').sum()}", COLORS['green'])
        with c3: kpi_card("Neutros", f"{(df['NPS_Cl']=='Neutro').sum()}", COLORS['amber'])
        with c4: kpi_card("Detratores", f"{(df['NPS_Cl']=='Detrator').sum()}", COLORS['red'])
        
        r1c1, r1c2 = st.columns([2, 1])
        with r1c1:
            st.markdown("**(0-10) Histograma**")
            fig_hist = px.histogram(df, x='NPS', color='NPS_Cl', nbins=11, range_x=[-0.5, 10.5], 
                color_discrete_map={'Promotor': COLORS['green'], 'Neutro': COLORS['amber'], 'Detrator': COLORS['red']},
                category_orders={"NPS_Cl": ["Detrator", "Neutro", "Promotor"]})
            lay_hist = base_layout(h=250)
            lay_hist['xaxis'].update(dtick=1)
            fig_hist.update_layout(**lay_hist)
            st.plotly_chart(fig_hist, use_container_width=True)
        with r1c2:
            st.markdown("**Gauge NPS**")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=overall_nps, domain={'x': [0, 1], 'y': [0, 1]},
                gauge=dict(axis=dict(range=[-100, 100]), bar=dict(color=nps_color(overall_nps)),
                steps=[dict(range=[-100, 0], color="rgba(183,28,28,0.2)"), dict(range=[0, 50], color="rgba(230,81,0,0.2)"), dict(range=[50, 100], color="rgba(46,125,50,0.2)")],
                threshold=dict(line=dict(color=COLORS['text'], width=2), thickness=0.75, value=35))
            ))
            fig_gauge.update_layout(**base_layout(h=250))
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        st.markdown("<div class='section-header'>NPS por Produto (Clique para detalhes)</div>", unsafe_allow_html=True)
        prod_comp = df.groupby(['Produto', 'NPS_Cl'], observed=True).size().unstack(fill_value=0)
        prods_sorted = df.groupby('Produto', observed=True)['NPS_Cl'].apply(nps_score).sort_values(ascending=False).index
        prod_comp = prod_comp.reindex(prods_sorted)
        
        fig_stack = go.Figure()
        for c, color in zip(["Detrator", "Neutro", "Promotor"], [COLORS['red'], COLORS['amber'], COLORS['green']]):
            if c in prod_comp.columns:
                fig_stack.add_trace(go.Bar(name=c, y=prod_comp.index, x=prod_comp[c], orientation='h', marker_color=color))
        fig_stack.update_layout(**base_layout(h=300), barmode='stack')
        st.plotly_chart(fig_stack, use_container_width=True)
        
        st.markdown("**Selecione um produto para Drill-down**")
        cols = st.columns(len(prods_sorted))
        for i, p in enumerate(prods_sorted):
            score = nps_score(df[df['Produto']==p]['NPS_Cl'])
            n_p = len(df[df['Produto']==p])
            with cols[i]:
                st.markdown(f"**{p}**<br/><span style='color:{nps_color(score)}; font-weight:bold; font-size:1.5rem;'>{score:+.1f}</span><br>N={n_p}", unsafe_allow_html=True)
                if st.button("Explorar →", key=f"btn_{p}"):
                    st.session_state.nps_drill_prod = p
                    st.rerun()
                    
    else:
        # Nivel 2
        col_back, col_title = st.columns([1, 10])
        with col_back:
            if st.button("← Voltar"):
                st.session_state.nps_drill_prod = None
                st.rerun()
        with col_title:
            st.title(f"🔍 Drill-down: {prod_focus}")
            
        df_p = df[df['Produto'] == prod_focus]
        n_p = len(df_p)
        if n_p == 0:
            st.warning("Sem dados para este produto nos filtros atuais.")
            st.stop()
            
        snps = nps_score(df_p['NPS_Cl'])
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card(f"NPS {prod_focus}", f"{snps:+.1f}", nps_color(snps), f"N={n_p}")
        with c2: kpi_card("Promotores", f"{(df_p['NPS_Cl']=='Promotor').sum()}", COLORS['green'])
        with c3: kpi_card("Neutros", f"{(df_p['NPS_Cl']=='Neutro').sum()}", COLORS['amber'])
        with c4: kpi_card("Detratores", f"{(df_p['NPS_Cl']=='Detrator').sum()}", COLORS['red'])
        
        r1c1, r1c2 = st.columns([1, 1])
        with r1c1:
            st.markdown("**Distribuição (0-10)**")
            fig_hp = px.histogram(df_p, x='NPS', color='NPS_Cl', nbins=11, range_x=[-0.5, 10.5], 
                color_discrete_map={'Promotor': COLORS['green'], 'Neutro': COLORS['amber'], 'Detrator': COLORS['red']})
            lay_hp = base_layout(h=300)
            lay_hp['xaxis'].update(dtick=1)
            fig_hp.update_layout(**lay_hp)
            st.plotly_chart(fig_hp, use_container_width=True)
            
        with r1c2:
            st.markdown("**CSAT do Produto vs Base Geral**")
            csat_cols = ['CS_Sis_n', 'CS_Sup_n', 'CS_Aca_n', 'CS_Com_n', 'CS_Cld_n']
            labels = ['Sistema', 'Suporte', 'Academy', 'Comercial', 'Cloud']
            means_p = [df_p[c].dropna().mean() if len(df_p[c].dropna())>0 else 0 for c in csat_cols]
            means_base = [df[c].dropna().mean() if len(df[c].dropna())>0 else 0 for c in csat_cols]
            
            fig_csat_cmp = go.Figure(data=[
                go.Bar(name=prod_focus, x=labels, y=means_p, marker_color=COLORS['blue']),
                go.Scatter(name='Média Base', x=labels, y=means_base, mode='lines+markers', line=dict(color=COLORS['text'], dash='dash'))
            ])
            lay = base_layout(h=300)
            lay['yaxis']['range'] = [1, 5.5]
            fig_csat_cmp.update_layout(**lay, barmode='group')
            st.plotly_chart(fig_csat_cmp, use_container_width=True)
            
        st.markdown("<div class='section-header'>🗣️ O que dizem os detratores</div>", unsafe_allow_html=True)
        dets = df_p[df_p['NPS_Cl'] == 'Detrator']
        if dets.empty:
            st.info("Não há detratores neste grupo.")
        else:
            for _, row in dets.iterrows():
                msg = row['Uma_Melhoria'] if pd.notna(row['Uma_Melhoria']) else row['Melhorias']
                if pd.notna(msg):
                    quote_card(msg, row['NPS_Cl'], row['NPS'], row['Produto'], row['Infra'])

# Continuing to Page 3, 4, 5... (in smaller layout chunks)
elif st.session_state.page == "Análise CSAT":
    st.title("⭐ Análise CSAT")
    
    csat_map = {
        'Sistema': 'CS_Sis_n', 'Suporte': 'CS_Sup_n', 'Academy': 'CS_Aca_n', 'Comercial': 'CS_Com_n', 'Cloud': 'CS_Cld_n'
    }
    
    dim_sel = st.selectbox("Selecione a Dimensão CSAT para Drill-down:", ["Todas as Dimensões"] + list(csat_map.keys()))
    
    if dim_sel == "Todas as Dimensões":
        cols = st.columns(5)
        for i, (k, colname) in enumerate(csat_map.items()):
            valid = df[colname].dropna()
            m = valid.mean() if len(valid) > 0 else 0
            with cols[i]: kpi_card(k, f"{m:.2f}", csat_color(m), f"N={len(valid)}")
            
        r1c1, r1c2 = st.columns([1.5, 1])
        with r1c1:
            st.markdown("<div class='section-header'>Heatmap Produto x Dimensão</div>", unsafe_allow_html=True)
            hm_data = []
            for p in df['Produto'].unique():
                row = {'Produto': p}
                for k, col in csat_map.items():
                    d = df[df['Produto']==p][col].dropna()
                    row[k] = d.mean() if len(d) > 0 else np.nan
                hm_data.append(row)
            df_hm = pd.DataFrame(hm_data).set_index('Produto')
            # For Plotly heatmap, we need to handle NaN
            fig_hm = px.imshow(df_hm.fillna(0), text_auto='.2f', aspect="auto", color_continuous_scale="RdYlGn", range_color=[1, 5])
            fig_hm.update_layout(**base_layout(h=350))
            st.plotly_chart(fig_hm, use_container_width=True)
            
        with r1c2:
            st.markdown("<div class='section-header'>Composição CSAT</div>", unsafe_allow_html=True)
            comp_data = []
            for k, col in csat_map.items():
                d = df[col].dropna()
                satisfeito = (d >= 4).sum()
                regular = (d == 3).sum()
                insatisfeito = (d <= 2).sum()
                total = len(d)
                if total > 0:
                    comp_data.append({'Dimensão': k, 'Satisfeito': satisfeito/total, 'Regular': regular/total, 'Insatisfeito': insatisfeito/total})
            if comp_data:
                df_comp = pd.DataFrame(comp_data)
                fig_c = go.Figure()
                fig_c.add_trace(go.Bar(name="Satisfeito+", y=df_comp['Dimensão'], x=df_comp['Satisfeito'], orientation='h', marker_color=COLORS['green']))
                fig_c.add_trace(go.Bar(name="Regular", y=df_comp['Dimensão'], x=df_comp['Regular'], orientation='h', marker_color=COLORS['amber']))
                fig_c.add_trace(go.Bar(name="Insatisfeito-", y=df_comp['Dimensão'], x=df_comp['Insatisfeito'], orientation='h', marker_color=COLORS['red']))
                lay_c = base_layout(h=350)
                lay_c['barmode'] = 'stack'
                lay_c['xaxis'].update(tickformat=".0%")
                fig_c.update_layout(**lay_c)
                st.plotly_chart(fig_c, use_container_width=True)
            
    else:
        # Nivel 2: Single dimension
        st.markdown(f"### Detalhamento: {dim_sel}")
        col_used = csat_map[dim_sel]
        data_dim = df[col_used].dropna()
        n_dim = len(data_dim)
        if n_dim == 0:
            st.warning("Sem dados para esta dimensão.")
            st.stop()
            
        m = data_dim.mean()
        sat = (data_dim >= 4).sum() / n_dim * 100
        reg = (data_dim == 3).sum() / n_dim * 100
        ins = (data_dim <= 2).sum() / n_dim * 100
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("CSAT Médio", f"{m:.2f}", csat_color(m), f"N={n_dim}")
        with c2: kpi_card("Satisfeito+ (4-5)", f"{sat:.1f}%", COLORS['green'])
        with c3: kpi_card("Regular (3)", f"{reg:.1f}%", COLORS['amber'])
        with c4: kpi_card("Insatisfeito (1-2)", f"{ins:.1f}%", COLORS['red'])
        
        c_p1, c_p2 = st.columns([1, 1.5])
        with c_p1:
            dist = data_dim.value_counts().sort_index().reset_index()
            dist.columns = ['Nota', 'Contagem']
            fig_p = px.pie(dist, values='Contagem', names='Nota', hole=0.5, color='Nota',
                          color_discrete_map={1: COLORS['red'], 2: COLORS['amber'], 3: '#F57C00', 4: COLORS['teal'], 5: COLORS['green']})
            fig_p.update_layout(**base_layout(h=350))
            st.plotly_chart(fig_p, use_container_width=True)
            
        with c_p2:
            prod_m = df.groupby('Produto', observed=True)[col_used].mean().reset_index()
            fig_pm = px.bar(prod_m, y='Produto', x=col_used, orientation='h', text_auto='.2f', color=col_used, color_continuous_scale="RdYlGn", range_color=[1,5])
            lay = base_layout(h=350)
            lay['xaxis']['range'] = [0, 5]
            fig_pm.update_layout(**lay)
            st.plotly_chart(fig_pm, use_container_width=True)

elif st.session_state.page == "Detratores":
    st.title("🚨 Análise de Risco (Detratores)")
    dets = df[df['NPS_Cl'] == 'Detrator']
    n_det = len(dets)
    
    if n_det == 0:
        st.success("Nenhum detrator encontrado!")
        st.stop()
        
    p_risco = dets['Produto'].value_counts().idxmax()
    csat_cols = ['CS_Sis_n', 'CS_Sup_n', 'CS_Aca_n', 'CS_Com_n', 'CS_Cld_n']
    csat_m_det = dets[csat_cols].mean().mean() # average across all dims
    coments = dets['Uma_Melhoria'].dropna().shape[0]
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Detratores", f"{n_det}", COLORS['red'])
    with c2: kpi_card("Produto de Risco", f"{p_risco}", COLORS['red'])
    with c3: kpi_card("CSAT Médio (Geral)", f"{csat_m_det:.2f}", csat_color(csat_m_det))
    with c4: kpi_card("Ocorrências Abertas", f"{coments}", COLORS['sub'])
    
    r1, r2 = st.columns([1, 1])
    with r1:
        st.markdown("<div class='section-header'>Composição por Produto</div>", unsafe_allow_html=True)
        counts = dets['Produto'].value_counts().reset_index()
        counts.columns = ['Produto', 'N']
        fig_tm = px.treemap(counts, path=['Produto'], values='N', color='N', color_continuous_scale="Reds")
        fig_tm.update_layout(**base_layout(h=350))
        st.plotly_chart(fig_tm, use_container_width=True)
    with r2:
        st.markdown("<div class='section-header'>Comparativo CSAT (Detratores vs Base)</div>", unsafe_allow_html=True)
        labels = ['Sistema', 'Suporte', 'Academy', 'Comercial', 'Cloud']
        m_det = [dets[c].dropna().mean() for c in csat_cols]
        m_base = [df[c].dropna().mean() for c in csat_cols]
        
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatterpolar(r=m_det + [m_det[0]], theta=labels + [labels[0]], fill='toself', name='Detratores', line_color=COLORS['red']))
        fig_cmp.add_trace(go.Scatterpolar(r=m_base + [m_base[0]], theta=labels + [labels[0]], fill='toself', name='Base Toda', line_color=COLORS['blue']))
        rlay = base_layout(h=350)
        rlay.update(polar=dict(radialaxis=dict(visible=True, range=[1, 5], gridcolor=COLORS['border'], linecolor=COLORS['border']), angularaxis=dict(gridcolor=COLORS['border'], linecolor=COLORS['border'])))
        fig_cmp.update_layout(**rlay)
        st.plotly_chart(fig_cmp, use_container_width=True)
        
    st.markdown("<div class='section-header'>Voz dos Detratores</div>", unsafe_allow_html=True)
    p_filtro = st.selectbox("Filtrar por Produto", ["Todos"] + list(dets['Produto'].unique()))
    
    df_show = dets if p_filtro == "Todos" else dets[dets['Produto'] == p_filtro]
    df_show = df_show.sort_values(by='NPS')
    
    for _, row in df_show.iterrows():
        msg = row['Uma_Melhoria'] if pd.notna(row['Uma_Melhoria']) else row['Melhorias']
        if pd.notna(msg):
            quote_card(msg, row['NPS_Cl'], row['NPS'], row['Produto'], row['Infra'])

elif st.session_state.page == "Respostas Abertas":
    st.title("💬 Respostas Abertas")
    
    c1, c2, c3 = st.columns(3)
    with c1: kpi_card("Uma Melhoria", f"{df['Uma_Melhoria'].dropna().shape[0]}", COLORS['blue'])
    with c2: kpi_card("Pontos Positivos", f"{df['Positivos'].dropna().shape[0]}", COLORS['green'])
    with c3: kpi_card("O que Melhorar", f"{df['Melhorias'].dropna().shape[0]}", COLORS['amber'])
    
    st.markdown("---")
    
    f1, f2, f3 = st.columns(3)
    c_nps = f1.multiselect("Classe NPS", ["Promotor", "Neutro", "Detrator"], default=["Promotor", "Neutro", "Detrator"])
    c_prod = f2.multiselect("Produto (Abertas)", list(df['Produto'].dropna().unique()), default=list(df['Produto'].dropna().unique()))
    c_campo = f3.selectbox("Campo", ["Uma_Melhoria", "Positivos", "Melhorias"])
    
    d_filt = df[df['NPS_Cl'].isin(c_nps) & df['Produto'].isin(c_prod)]
    d_filt = d_filt.dropna(subset=[c_campo])
    
    st.markdown(f"**Resultados encontrados:** {len(d_filt)}")
    
    for _, row in d_filt.iterrows():
        quote_card(row[c_campo], row['NPS_Cl'], row['NPS'], row['Produto'], row['Infra'])

