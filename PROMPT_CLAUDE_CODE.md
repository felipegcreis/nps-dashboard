# PROMPT PARA CLAUDE CODE
## Projeto: Dashboard Interativo — Pesquisa de Satisfação Sisloc Fev/2026

---

## CONTEXTO GERAL DO PROJETO

Você vai construir um **web app profissional de análise de NPS e CSAT** para a Sisloc Software, empresa brasileira de ERP para o mercado de locação de equipamentos.

O app deve ser construído com **Python + Streamlit** para a estrutura e roteamento, **Plotly** para todos os gráficos interativos, com suporte a **drilldown e drillup** por produto, infraestrutura e classe NPS.

---

## CONTEXTO DE NEGÓCIO

**Empresa:** Sisloc Software  
**Mercado:** ERP para locação de equipamentos (mercado brasileiro)  
**Modelo de receita:** Setup inicial (implantação) + mensalidade recorrente  
**Produtos (do menor ao maior):** Start → Light → Sys → Premium → Platinum → Custom  
**Infraestrutura:** Clientes Cloud (hospedado pela Sisloc) e On-Premises (instalado no cliente)

**Pesquisa:**
- Tipo: NPS Relacional (enviada para toda a base, não pós-evento)
- Coleta: E-mail — Fevereiro 2026
- Respondentes: 183
- Última pesquisa anterior: 2020 (sem benchmark interno disponível)

**Hipótese estratégica central (validada pelos dados):**
> O volume de churn vem aumentando. O produto está caro para clientes pequenos, e os clientes maiores (Premium/Platinum) têm nível de maturidade de processo que o sistema não atende plenamente. A hipótese é que o foco deveria ser nos clientes pequenos e médios, onde há maior aderência e satisfação.

---

## DADOS DA PESQUISA

**Arquivo de dados:** `pesquisa_data.json` (183 registros, já processado)

**Campos disponíveis por respondente:**
```
first_name       → Nome do respondente
Cliente          → Nome da empresa
Produto          → Plano do cliente: Start, Light, Sys, Premium, Platinum, Custom
Cloud(S/N)       → S = Cloud, N = On-Premises
Infra            → 'Cloud' ou 'On-Premises' (campo derivado)
NPS              → Score numérico 0–10
NPS_Cl           → Classificação: 'Promotor' (9-10), 'Neutro' (7-8), 'Detrator' (0-6)
CS_Sis           → CSAT Sistema (texto)
CS_Sup           → CSAT Suporte (texto)
CS_Aca           → CSAT Academy/Universidade Corporativa (texto)
CS_Com           → CSAT Comercial (texto)
CS_Cld           → CSAT Cloud (texto)
CS_Sis_n         → CSAT Sistema numérico 1–5 (null = "Não sei informar")
CS_Sup_n         → CSAT Suporte numérico 1–5
CS_Aca_n         → CSAT Academy numérico 1–5
CS_Com_n         → CSAT Comercial numérico 1–5
CS_Cld_n         → CSAT Cloud numérico 1–5
Positivos        → Resposta aberta: "O que mais gosta na Sisloc"
Melhorias        → Resposta aberta: "O que pode melhorar"
Uma_Melhoria     → Resposta aberta: "Uma melhoria que faria diferença"
```

**Escala CSAT (texto → numérico):**
```
Insatisfeito       → 1
Pouco Satisfeito   → 2
Regular            → 3
Satisfeito         → 4  (corrigir typo "Satifeito" → também 4)
Muito Satisfeito   → 5
Não sei Informar   → null (excluir do denominador)
```

---

## RESULTADOS DA ANÁLISE (já calculados — use como referência)

### NPS Geral
| Métrica | Valor |
|---|---|
| NPS Score | **+14.2** |
| Promotores | 78 (42.6%) |
| Neutros | 53 (29.0%) |
| Detratores | 52 (28.4%) |
| Zona | Aperfeiçoamento (benchmark SaaS B2B: 30–45) |

### NPS por Produto
| Produto | N | NPS Score | Zona |
|---|---|---|---|
| Start | 9 | **+100.0** | Excelente |
| Sys | 26 | **+30.8** | Aperfeiçoamento |
| Light | 9 | **+11.1** | Aperfeiçoamento |
| Custom | 32 | **+25.0** | Aperfeiçoamento |
| Platinum | 46 | **+13.0** | Aperfeiçoamento |
| **Premium** | **60** | **-8.3** | **CRÍTICO** |

### NPS por Infraestrutura
| Infra | N | NPS Score |
|---|---|---|
| On-Premises | 79 | +16.5 |
| Cloud | 104 | +12.5 |

### CSAT Médio por Dimensão (escala 1–5)
| Dimensão | Média | N Válido |
|---|---|---|
| Cloud | 3.94 | 72 |
| Comercial | 3.89 | 148 |
| Suporte | 3.79 | 177 |
| Sistema | 3.69 | 181 |
| Academy | 3.67 | 100 |

### CSAT por Produto (5 dimensões)
| Produto | Sistema | Suporte | Academy | Comercial | Cloud |
|---|---|---|---|---|---|
| Start | 4.44 | 4.62 | 4.00 | 4.00 | 4.67 |
| Sys | 4.04 | 4.00 | 3.79 | 3.91 | 4.14 |
| Custom | 3.84 | 4.09 | 3.87 | 4.04 | 4.29 |
| Platinum | 3.74 | 3.70 | 3.89 | 4.17 | 4.00 |
| Light | 3.44 | 3.44 | 3.50 | 3.75 | 3.25 |
| **Premium** | **3.34** | **3.55** | **3.35** | **3.53** | **3.56** |

---

## INSIGHTS ESTRATÉGICOS (devem aparecer no app)

### 🔴 Insight 1 — Premium é o epicentro do problema
- NPS -8.3 com 60 respondentes (maior grupo da pesquisa, único NPS negativo)
- CSAT inferior em todas as 5 dimensões comparado aos demais produtos
- Concentra a maior parte dos detratores em valor absoluto

### 🟠 Insight 2 — Suporte é o principal driver de detração
- Aparece em múltiplas respostas abertas de detratores Premium e Platinum
- Padrão: sensação de abandono pós-venda, não apenas lentidão
- Respostas diretas: "o suporte é ineficiente e compromete tudo", "suporte com relação a telas de erros", "agilidade no atendimento técnico"

### 🟢 Insight 3 — Sys e Start confirmam a tese estratégica
- NPS 30.8 e 100.0 respectivamente — validam o foco em clientes menores/médios
- CSAT acima de 4.0 em todas as dimensões para Start
- Aderência alta e satisfação consistente nesse segmento

### 🔵 Insight 4 — Fiscal/NFS-e como ponto de ruptura
- Clientes que pagam mensalidade elevada e precisaram pagar à parte para adaptar compliance fiscal (NFS-e)
- Argumento explícito de churn em respostas Platinum: "pagamos caro por um sistema que ainda gera retrabalho"
- Sinaliza desconfiança estrutural no modelo de evolução do produto

### 🟡 Insight 5 — Cloud com NPS ligeiramente inferior ao On-Premises
- Counter-intuitivo: Cloud (12.5) < On-Premises (16.5)
- Pode indicar problemas de estabilidade/performance no ambiente cloud
- Pede investigação: perfil dos clientes Cloud vs On-Premises

---

## ESPECIFICAÇÃO TÉCNICA DO APP

### Stack Obrigatória
```
Python 3.10+
streamlit >= 1.30
plotly >= 5.18
pandas >= 2.0
numpy >= 1.24
```

### Estrutura de Arquivos
```
sisloc_dashboard/
├── app.py                  ← Arquivo principal Streamlit
├── pesquisa_data.json      ← Dados processados (183 registros)
├── requirements.txt
└── .streamlit/
    └── config.toml         ← Configurações de tema
```

### Comando para rodar
```bash
streamlit run app.py --server.port 8501
```

---

## DESIGN E VISUAL

**Tema:** Dark mode profissional — executivo, não genérico  
**Paleta de cores:**
```python
COLORS = {
    'bg':     '#080F17',   # fundo geral
    'card':   '#101B27',   # fundo de cards
    'border': '#1E2D3D',   # bordas
    'navy':   '#0D1B2A',   # sidebar e headers
    'blue':   '#1565C0',
    'teal':   '#00838F',
    'green':  '#2E7D32',   # NPS bom / CSAT bom
    'amber':  '#E65100',   # NPS regular / atenção
    'red':    '#B71C1C',   # NPS ruim / detratores
    'text':   '#E8EDF2',
    'sub':    '#4A6080',   # texto secundário
}
```

**Lógica de cores NPS:**
- Score ≥ 50 → Verde
- Score 0–49 → Âmbar
- Score < 0 → Vermelho

**Lógica de cores CSAT:**
- Média ≥ 4.0 → Verde
- Média 3.5–3.9 → Âmbar
- Média 3.0–3.4 → Laranja
- Média < 3.0 → Vermelho

**Tipografia:** Google Fonts — `Syne` (títulos, KPIs, labels uppercase) + `DM Sans` (corpo)

---

## PÁGINAS DO APP (5 páginas via sidebar)

---

### PÁGINA 1 — 📊 Visão Geral

**Propósito:** Overview executivo, primeira tela que a diretoria vê

**Conteúdo:**
1. **Header** com título e subtítulo (empresa, data, N respondentes)
2. **5 KPI Cards** em linha: NPS Geral, Promotores, Neutros, Detratores, Respondentes
   - Cada card com: label, valor grande, subtexto (% ou contexto)
   - Cor de destaque no topo do card de acordo com a métrica
3. **NPS por Produto** — gráfico de barras horizontais com color-coded por zona
4. **Donut NPS Classes** — com NPS score no centro (grande)
5. **Radar CSAT** — todas as 5 dimensões
6. **Bar CSAT** — média por dimensão com linhas de referência em 3.5 e 4.0
7. **4 Insight Cards** fixos (texto) com os principais achados estratégicos

---

### PÁGINA 2 — 📈 Análise NPS (com Drilldown)

**Propósito:** Análise profunda do NPS com capacidade de drill

**Nível 1 — Visão Geral NPS:**
1. 4 KPI Cards: NPS Geral, Promotores, Neutros, Detratores
2. **Histograma 0–10** — barras coloridas por classe (Detrator=vermelho, Neutro=âmbar, Promotor=verde)
3. **Gauge/Velocímetro NPS** — com referência de benchmark (35 = linha de referência)
4. **Stacked bar** — composição P/N/D por produto
5. **Cards de produto clicáveis** — cada produto mostra NPS score com botão "Ver detalhes →"
6. **Barras Cloud vs On-Premises**

**Nível 2 — Drill-down por produto (ao clicar):**
- Breadcrumb de navegação + botão "← Voltar"
- 4 KPI Cards do produto selecionado
- Histograma de scores 0–10 do produto
- Bar CSAT do produto vs média geral (linha tracejada)
- Respostas abertas dos detratores daquele produto (cards de citação)

**Lógica de drilldown:** usar `st.session_state` para controlar o nível

---

### PÁGINA 3 — ⭐ Análise CSAT (com Drilldown)

**Propósito:** Análise detalhada das 5 dimensões CSAT

**Nível 1 — Overview todas as dimensões:**
1. 5 KPI Cards (um por dimensão) com média e N válido
2. `selectbox` para selecionar dimensão específica (default: "Todas")
3. **Heatmap** Produto × Dimensão (colorido por CSAT médio)
4. **Stacked bar** — proporção Satisfeito+/Regular/Insatisfeito- por dimensão
5. **Boxplot** — distribuição CSAT por produto para dimensão selecionada

**Nível 2 — Drill-down por dimensão:**
- 4 KPI Cards: CSAT médio, % Satisfeito+, % Regular, % Insatisfeito-
- **Pie chart** breakdown das 5 opções da escala
- **Barras horizontais** CSAT por produto para essa dimensão
- **Grouped bar** CSAT por dimensão separado por classe NPS (Detrator/Neutro/Promotor)

---

### PÁGINA 4 — 🚨 Detratores (com Drilldown)

**Propósito:** Análise de risco de churn, foco em ação

**Conteúdo:**
1. 4 KPI Cards: Total Detratores, Produto de Maior Risco, CSAT Médio Detratores, Qtd com Resposta Aberta
2. **Barras duplas** — N de detratores + linha % de detratores por produto
3. **Treemap** — detratores por produto (visual de concentração)
4. **Radar comparativo** — CSAT Detratores vs Neutros vs Promotores (3 polígonos sobrepostos)
5. **Selectbox produto** para filtrar respostas abertas
6. **Cards de citação** — todas as respostas "Uma melhoria" dos detratores
   - Ordenadas por score NPS (pior primeiro)
   - Badge colorido: DETRATOR · Score X
   - Produto + Infraestrutura
   - Texto da resposta em itálico

---

### PÁGINA 5 — 💬 Respostas Abertas

**Propósito:** Análise qualitativa completa, com filtros

**Conteúdo:**
1. 3 KPI Cards: Qtd Uma Melhoria, Qtd Pontos Positivos, Qtd O que Melhorar
2. **Filtros:**
   - Multiselect: Classe NPS (Detrator/Neutro/Promotor)
   - Multiselect: Produto
   - Selectbox: Campo (Uma melhoria / Pontos positivos / O que melhorar)
3. Contador de resultados filtrados
4. **Cards de citação** para cada resposta filtrada:
   - Badge com classe NPS + score
   - Produto + Infra
   - Texto da resposta

---

## FILTROS GLOBAIS (Sidebar)

Aplicados em todas as páginas:
- **Infraestrutura:** Multiselect [Cloud, On-Premises] — default: ambos
- **Produto:** Multiselect [Start, Light, Sys, Premium, Platinum, Custom] — default: todos

Sidebar também exibe:
- Logo/nome Sisloc
- Nome e subtítulo da pesquisa
- N respondentes da base filtrada

---

## COMPONENTES REUTILIZÁVEIS

### KPI Card (HTML via `st.markdown`)
```python
def kpi_card(label, value, color, sub=''):
    """
    color: 'green' | 'amber' | 'red' | 'blue' | 'teal'
    Renderiza card com barra colorida no topo, valor grande centralizado
    """
```

### Citação de Respondente
```python
def quote_card(texto, classe, score, produto, infra):
    """
    Badge colorido por classe, produto + infra em cinza, texto em itálico
    """
```

### Layout base de gráficos Plotly
```python
def base_layout(title='', h=400):
    """
    Retorna dict com: paper_bgcolor escuro, plot_bgcolor transparente,
    fonte DM Sans, cores de grid e texto do tema dark
    """
```

---

## CONFIGURAÇÃO STREAMLIT

### `.streamlit/config.toml`
```toml
[theme]
base = "dark"
backgroundColor = "#080F17"
secondaryBackgroundColor = "#101B27"
textColor = "#E8EDF2"
font = "sans serif"

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

---

## CSS GLOBAL (injetar via `st.markdown`)

Incluir no início do `app.py`:
- Import Google Fonts: Syne (800, 700, 600) + DM Sans (300, 400, 500)
- Esconder header padrão e footer do Streamlit
- Estilizar sidebar com fundo escuro
- Classes para: `.kpi-card`, `.kpi-value`, `.kpi-label`, `.kpi-sub`
- Classes para: `.quote-card`, `.quote-badge`, `.badge-det`, `.badge-prom`, `.badge-neut`
- Classes para: `.insight-card` com variantes `.risk`, `.warn`, `.ok`, `.info`
- Classes para: `.section-header` (uppercase, espaçado, com linha inferior)
- Estilizar botões do Streamlit com borda fina e hover colorido

---

## REQUIREMENTS.TXT

```
streamlit>=1.30.0
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
```

---

## PASSOS DE CONSTRUÇÃO (ordem sugerida)

1. **Setup inicial**
   - Criar estrutura de diretórios
   - Criar `requirements.txt`
   - Criar `.streamlit/config.toml`
   - Instalar dependências: `pip install -r requirements.txt`

2. **Carregamento de dados**
   - Função `load_data()` com `@st.cache_data`
   - Ler `pesquisa_data.json`
   - Converter tipos (NPS numérico, CSAT numérico)
   - Validar: 183 registros, 6 produtos presentes

3. **Funções utilitárias**
   - `nps_score(series)` — calcula NPS de uma série de classes
   - `nps_color(score)` — retorna cor hex por score
   - `csat_color(valor)` — retorna cor hex por média CSAT
   - `base_layout(title, h)` — layout padrão Plotly dark
   - `kpi_card(label, value, color, sub)` — HTML do card
   - `quote_card(...)` — HTML do card de citação

4. **CSS Global**
   - Injetar no início do app com `st.markdown(..., unsafe_allow_html=True)`

5. **Sidebar**
   - Logo + título
   - Radio para navegação entre páginas
   - Filtros globais (Infra, Produto)
   - Mostrar N filtrado

6. **Lógica de filtro**
   - Aplicar filtros à base após sidebar
   - Recalcular métricas derivadas (prom, neut, det, nps)

7. **Página 1 — Visão Geral**

8. **Página 2 — NPS com drilldown** (session_state)

9. **Página 3 — CSAT com drilldown** (selectbox)

10. **Página 4 — Detratores** (selectbox + cards)

11. **Página 5 — Respostas Abertas** (filtros + cards)

12. **Testes**
    - Rodar `streamlit run app.py`
    - Testar todos os filtros
    - Testar drilldown NPS (clicar em produto, voltar)
    - Verificar que gráficos não quebram com filtros que resultam em N pequeno (ex: Start com N=9)

---

## CUIDADOS IMPORTANTES

1. **Divisão por zero:** Sempre checar `len(serie) > 0` antes de calcular NPS ou CSAT médio
2. **NaN no CSAT:** `dropna()` antes de qualquer cálculo numérico de CSAT (Não sei Informar = null)
3. **Filtro com N pequeno:** Quando produto filtrado tem poucos respondentes, gráficos devem degradar graciosamente (não quebrar)
4. **Session state:** Inicializar todas as keys no início do app para evitar KeyError
5. **Cache:** `@st.cache_data` na função de carregamento de dados
6. **Ordenação dos produtos:** sempre usar a ordem Start → Light → Sys → Premium → Platinum → Custom (do menor ao maior)
7. **Typo no dado:** "Satifeito" deve ser tratado como "Satisfeito" (valor 4) — isso já está corrigido no JSON
8. **Cores do radar:** Converter hex para rgba com alpha ao usar `fill='toself'` no Plotly Scatterpolar

---

## VALIDAÇÕES ESPERADAS

Ao finalizar, verificar que os seguintes números estão corretos no app (sem filtros):
- NPS Geral: +14.2 (ou +14)
- Promotores: 78
- Neutros: 53
- Detratores: 52
- NPS Premium: -8.3
- NPS Start: +100.0
- CSAT Sistema médio: 3.69
- CSAT Suporte médio: 3.79

---

## OBSERVAÇÃO FINAL

O arquivo `pesquisa_data.json` já está com os dados processados e normalizados. Não é necessário ler o Excel original. Todos os campos CSAT numéricos já estão calculados, todos os typos corrigidos, e o campo `Infra` ('Cloud' / 'On-Premises') já está derivado do campo original `Cloud(S/N)`.

O app deve rodar com um único `streamlit run app.py` sem dependências externas além das listadas no `requirements.txt`.
