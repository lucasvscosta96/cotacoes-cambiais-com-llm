import streamlit as st
import pandas as pd
import os
import glob
import numpy as np
from datetime import datetime, timedelta, date
import altair as alt
import openai

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Contexto Cambial",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Funções de Ajuda e Carregamento de Dados ---

@st.cache_data
def load_gold_data() -> pd.DataFrame:
    """Carrega e consolida todos os arquivos Parquet da pasta 'gold/'."""
    gold_dir = "gold/"
    if not os.path.exists(gold_dir): return pd.DataFrame()

    all_files = sorted(glob.glob(os.path.join(gold_dir, "*.parquet")))
    if not all_files: return pd.DataFrame()

    df_list = []
    for file in all_files:
        try:
            df = pd.read_parquet(file)
            date_str = os.path.basename(file).split('.')[0]
            df['date'] = pd.to_datetime(date_str).date()
            df_list.append(df)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {file}: {e}")
            
    if not df_list: return pd.DataFrame()

    full_df = pd.concat(df_list, ignore_index=True)
    full_df['rate'] = pd.to_numeric(full_df['rate'], errors='coerce')
    return full_df.sort_values(by="date")

def get_all_report_files(report_dir="reports"):
    """Encontra e ordena todos os caminhos dos arquivos de relatório (.txt)."""
    search_path = os.path.join(report_dir, "*.txt")
    list_of_files = glob.glob(search_path)
    if not list_of_files: return []
    list_of_files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(f) for f in list_of_files]

@st.cache_data
def get_llm_actionable_insight(currency, delta, volatility, avg_volatility):
    """
    Chama a API da OpenAI para gerar uma recomendação de ação baseada nos dados.
    """
    try:
        # Tenta obter a chave da API dos secrets do Streamlit
        openai.api_key = st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return "AVISO: A chave da API da OpenAI não foi configurada nos secrets do Streamlit. Mostrando análise simulada."

    volatility_context = "acima da média do período (maior risco)" if volatility > avg_volatility else "abaixo da média do período (menor risco)"
    
    prompt = f"""
    Aja como um consultor financeiro sênior, extremamente conciso e direto.
    Contexto: A moeda {currency} está com uma variação de {delta:.2f}% em relação à sua média no período selecionado.
    Sua volatilidade (risco) é de {volatility:.5f}, que está {volatility_context}.
    Tarefa: Forneça uma única recomendação acionável em uma frase curta. Comece com "Ação Recomendada:".
    Exemplo: "Ação Recomendada: Adiar compras não essenciais em {currency} devido à alta volatilidade e perda de força do BRL."
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um consultor financeiro sênior, focado em recomendações acionáveis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro ao chamar a API da LLM: {e}"

# --- Carregamento Inicial ---
df_raw = load_gold_data()

if df_raw.empty:
    st.title("📊 Dashboard de Cotações Cambiais")
    st.warning("Nenhum dado encontrado na pasta /gold/. Execute o pipeline de dados primeiro.")
    st.stop()
    
df_raw['date'] = pd.to_datetime(df_raw['date'])
max_date_geral = df_raw["date"].max().date()

# --- Sidebar e Filtros ---
st.sidebar.title("Análise da LLM")
available_reports = get_all_report_files()
if available_reports:
    selected_report_filename = st.sidebar.selectbox("Selecione o Relatório por Data:", options=available_reports)
    try:
        with open(os.path.join("reports", selected_report_filename), 'r', encoding='utf-8') as f:
            report_content = f.read()
        date_part = selected_report_filename.split('_')[0]
        display_date = datetime.strptime(date_part, '%Y-%m-%d').strftime('%d/%m/%Y')
        with st.sidebar.expander(f"Ver Resumo Completo de {display_date}"):
            st.markdown(report_content)
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar o relatório: {e}")
else:
    st.sidebar.warning("Nenhum relatório (.txt) encontrado.")
st.sidebar.divider()

st.sidebar.header("Filtros do Dashboard")
min_date = df_raw["date"].min().date()
default_start_date = max(min_date, max_date_geral - timedelta(days=30))

date_range = st.sidebar.date_input(
    "Selecione o Período de Análise:",
    value=(default_start_date, max_date_geral),
    min_value=min_date, max_value=max_date_geral,
)

if len(date_range) != 2: st.stop()
start_date, end_date = date_range

available_currencies = sorted(df_raw["currency"].unique())
default_currencies = ["USD", "EUR", "GBP"]
selected_currencies = st.sidebar.multiselect(
    "Selecione as moedas:",
    options=available_currencies,
    default=[c for c in default_currencies if c in available_currencies]
)

st.sidebar.info(f"Dados atualizados até: {max_date_geral.strftime('%d/%m/%Y')}")

# --- LÓGICA DE CÁLCULO CORRIGIDA ---

# Filtra o DataFrame principal para o período E moedas selecionados no sidebar
df_period_filtered = df_raw[
    (df_raw["date"].dt.date >= start_date) & 
    (df_raw["date"].dt.date <= end_date) &
    (df_raw["currency"].isin(selected_currencies))
].copy()

# Validação se há dados após a filtragem completa
if df_period_filtered.empty:
    st.title("📊 Dashboard de Cotações Cambiais")
    st.warning("Nenhuma moeda selecionada ou dados insuficientes para o período e moedas escolhidas.")
    st.stop()

# 1. Determinar o último dia DENTRO do período filtrado
end_date_in_period = df_period_filtered["date"].max().date()

# 2. Calcular a Média e Volatilidade DENTRO do período selecionado
context_metrics = df_period_filtered.groupby('currency')['rate'].agg(
    rate_avg_period='mean',
    rate_std_period='std'
).reset_index()

# 3. Obter os dados do último dia DENTRO do período filtrado
df_latest_in_period = df_period_filtered[df_period_filtered['date'].dt.date == end_date_in_period].copy()

# 4. Juntar os dados mais recentes com as métricas do período para análise
df_analysis = pd.merge(df_latest_in_period, context_metrics, on='currency', how='left')

# 5. Calcular o delta da cotação atual vs. a média do período
df_analysis['delta_vs_period_pct'] = ((df_analysis['rate'] - df_analysis['rate_avg_period']) / df_analysis['rate_avg_period']) * 100


# --- Layout da Página Principal e KPIs ---
st.title("🧠 Dashboard de Contexto Cambial (Base BRL)")
st.markdown(f"Análise do dia **{end_date_in_period.strftime('%d/%m/%Y')}** em contexto com o período de **{start_date.strftime('%d/%m/%Y')}** a **{end_date.strftime('%d/%m/%Y')}**.")
st.markdown("---")

st.subheader("1. KPIs de Benchmarking e Risco")
kpi_cols = st.columns(len(df_analysis) if len(df_analysis) > 0 else 1)
base_currency = df_analysis['base_currency'].iloc[0]

for idx, row in df_analysis.iterrows():
    with kpi_cols[df_analysis.index.get_loc(idx)]:
        delta_brl_strength = -row['delta_vs_period_pct'] if pd.notna(row['delta_vs_period_pct']) else 0.0
        st.metric(
            label=f"**{base_currency}** vs **{row['currency']}**",
            value=f"R$ {row['rate']:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta=f"{delta_brl_strength:.2f}% vs. Média do Período",
            help=f"A cotação atual está {abs(row['delta_vs_period_pct']):.2f}% {'acima' if row['delta_vs_period_pct'] > 0 else 'abaixo'} da média do período selecionado. Um delta positivo indica perda de força do BRL."
        )
        st.caption(f"**Volatilidade (Período):** {row['rate_std_period']:.5f}")

st.markdown("---")

# --- Gráfico de Dispersão (Contexto/Risco) ---
st.subheader("2. Posição de Risco (Variação vs. Volatilidade)")

df_analysis['Posicionamento vs. Média (%)'] = df_analysis['delta_vs_period_pct']
df_analysis['Risco (Volatilidade)'] = df_analysis['rate_std_period'].fillna(0)
df_analysis['Status'] = np.where(df_analysis['Posicionamento vs. Média (%)'] > 0, 'Perda de Força do BRL', 'Ganho de Força do BRL') 

if not df_analysis.empty:
    scatter_chart = alt.Chart(df_analysis).mark_circle(size=100).encode(
        x=alt.X("Risco (Volatilidade):Q", title="Risco: Volatilidade no Período"),
        y=alt.Y("Posicionamento vs. Média (%):Q", title="Posicionamento (vs. Média do Período)"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Ganho de Força do BRL', 'Perda de Força do BRL'], range=['#2ca02c', '#d62728'])),
        tooltip=["currency", "Posicionamento vs. Média (%)", "Risco (Volatilidade)"]
    ).properties(title="Moedas em Contexto de Risco vs. Posição Atual").interactive()

    avg_volatility = df_analysis['Risco (Volatilidade)'].mean()
    ref_lines_data = pd.DataFrame({'y': [0], 'x': [avg_volatility]})
    hline = alt.Chart(ref_lines_data).mark_rule(color='black', strokeDash=[5,5]).encode(y='y:Q')
    vline = alt.Chart(ref_lines_data).mark_rule(color='gray', strokeDash=[3,3]).encode(x='x:Q')
    
    st.altair_chart(scatter_chart + hline + vline, use_container_width=True)
else:
    st.warning("Nenhum dado para o gráfico de dispersão.")

st.markdown("---")

# --- LLM Insight (Com Ação Real) ---
st.subheader("3. Análise Executiva da LLM (Ação Sugerida)")
st.info("A LLM analisa a moeda mais relevante no gráfico acima e sugere uma ação.")

# Encontra a moeda mais "interessante" (mais distante da origem do gráfico)
df_analysis['distancia'] = np.sqrt(df_analysis['Risco (Volatilidade)']**2 + df_analysis['Posicionamento vs. Média (%)']**2)
outlier_currency_row = df_analysis.loc[df_analysis['distancia'].idxmax()]

# Gera a recomendação da LLM para a moeda em destaque
llm_advice = get_llm_actionable_insight(
    currency=outlier_currency_row['currency'],
    delta=outlier_currency_row['Posicionamento vs. Média (%)'],
    volatility=outlier_currency_row['Risco (Volatilidade)'],
    avg_volatility=avg_volatility
)

st.success(llm_advice)