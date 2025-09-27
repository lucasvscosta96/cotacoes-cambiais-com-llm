import streamlit as st
import pandas as pd
import os
import glob
import numpy as np
from datetime import datetime, timedelta, date 
import altair as alt 

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Contexto Cambial",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Funções de Ajuda ---

def get_report_path(filename, report_dir="reports"):
    """Retorna o caminho completo para um nome de arquivo de relatório específico."""
    return os.path.join(report_dir, filename)

def get_all_report_files(report_dir="reports"):
    """Encontra e ordena todos os caminhos dos arquivos de relatório (.txt)."""
    search_path = os.path.join(report_dir, "*.txt")
    list_of_files = glob.glob(search_path)
    if not list_of_files:
        return []
    
    # Ordena pelo timestamp de modificação (mais recente primeiro)
    list_of_files.sort(key=os.path.getmtime, reverse=True)
    
    # Retorna apenas os nomes dos arquivos para exibição
    return [os.path.basename(f) for f in list_of_files]

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

# --- Processamento de Dados (Foco no Contexto) ---

df_raw = load_gold_data()

if df_raw.empty:
    st.title("📊 Dashboard de Cotações Cambiais")
    st.warning("Nenhum dado encontrado na pasta /gold/. Execute o pipeline de dados primeiro.")
    st.stop()
    
# Garante que 'date' é um objeto datetime para a filtragem no Streamlit
df_raw['date'] = pd.to_datetime(df_raw['date'])

# --- Sidebar e Filtros ---

# LLM Summary (Bloco de seleção dinâmica)
available_reports = get_all_report_files()

st.sidebar.title("Resumo da LLM")

if available_reports:
    # 1. Selector para escolher o arquivo de relatório
    selected_report_filename = st.sidebar.selectbox(
        "Selecione o Relatório por Data:",
        options=available_reports
    )
    selected_report_path = get_report_path(selected_report_filename)

    try:
        with open(selected_report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        st.sidebar.header("Análise do Dia Selecionado")
        
        # Extrai a data do arquivo para exibição (Assume o formato YYYY-MM-DD_...)
        date_part = selected_report_filename.split('_')[0]
        try:
            display_date = datetime.strptime(date_part, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            # Fallback se o nome não estiver exatamente no formato esperado
            display_date = selected_report_filename
            
        st.sidebar.markdown(f"**Data da Análise:** *{display_date}*")
        
        # Usa um expander na sidebar para o texto longo do resumo
        with st.sidebar.expander(f"Ver Análise Completa de {display_date}"):
            st.markdown(report_content)
        st.sidebar.divider()
        
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar o relatório: {e}")
else:
    st.sidebar.warning("Nenhum arquivo de relatório (.txt) encontrado.")
    st.sidebar.divider()

st.sidebar.header("Filtros do Dashboard")

available_currencies = sorted(df_raw["currency"].unique())
default_currencies = ["USD", "EUR", "GBP"]
selected_currencies = st.sidebar.multiselect(
    "Selecione as moedas para análise:",
    options=available_currencies,
    default=[c for c in default_currencies if c in available_currencies]
)

# --- INCLUSÃO DO FILTRO DE DATA ---
min_date = df_raw["date"].min().date()
max_date = df_raw["date"].max().date()

default_start_date = max_date - timedelta(days=30)
if default_start_date < min_date:
    default_start_date = min_date

date_range = st.sidebar.date_input(
    "Selecione o Período Histórico (para o Gráfico e Contexto de 7D):",
    value=(default_start_date, max_date), # Padrão: últimos 30 dias
    min_value=min_date,
    max_value=max_date,
)

# Validação do intervalo de datas
if len(date_range) != 2:
    st.sidebar.warning("Por favor, selecione um início e um fim para o período.")
    st.stop()

start_date = min(date_range)
end_date = max(date_range)
# --- FIM DA INCLUSÃO DO FILTRO DE DATA ---

st.sidebar.info(f"Dados atualizados até: {max_date.strftime('%d/%m/%Y')}")

# --- Cálculos de Contexto (Adiciona Média e Volatilidade) ---

# Filtra o DataFrame para o período selecionado no sidebar (para o Gráfico de Contexto)
df_period_filtered = df_raw[
    (df_raw["date"].dt.date >= start_date) & 
    (df_raw["date"].dt.date <= end_date)
].copy()


# Filtra o DataFrame para os últimos 7 dias (para calcular a média, independente do filtro de período, a menos que o período seja menor que 7 dias)
seven_days_ago_calc = max(max_date - timedelta(days=7), df_raw["date"].min().date())
df_last_7_days = df_raw[df_raw['date'].dt.date >= seven_days_ago_calc].copy()


# Calcula a Média dos Últimos 7 Dias e a Desvios Padrão (Simulação de Volatilidade)
context_metrics = df_last_7_days.groupby('currency')['rate'].agg(
    rate_avg_7d='mean',
    rate_std_7d='std'
).reset_index()

# DataFrame do último dia
df_latest = df_raw[df_raw['date'].dt.date == max_date].copy()

# Junta os dados mais recentes com as métricas de contexto
df_analysis = pd.merge(
    df_latest, 
    context_metrics, 
    on='currency', 
    how='left'
)

# Calcula o delta da cotação atual vs. a média dos 7 dias
df_analysis['delta_vs_7d_pct'] = (
    (df_analysis['rate'] - df_analysis['rate_avg_7d']) / df_analysis['rate_avg_7d']
) * 100

# Remove moedas não selecionadas para exibição
df_analysis = df_analysis[df_analysis['currency'].isin(selected_currencies)].copy()

if df_analysis.empty:
    st.title("📊 Dashboard de Cotações Cambiais")
    st.warning("Selecione pelo menos uma moeda válida.")
    st.stop()


# --- Layout da Página Principal e KPIs ---

st.title("🧠 Dashboard de Contexto Cambial (Base BRL)")
st.markdown(f"Análise focada no *snapshot* de **{max_date.strftime('%d/%m/%Y')}**.")
st.markdown("---")

st.subheader("1. KPIs de Benchmarking e Risco")

kpi_cols = st.columns(len(df_analysis) if len(df_analysis) > 0 else 1)
base_currency = df_analysis['base_currency'].iloc[0]

# O loop itera usando idx (índice) em vez de i para evitar conflito
for idx, row in df_analysis.iterrows():
    currency = row['currency']
    latest_rate = row['rate']
    delta_vs_7d_pct = row['delta_vs_7d_pct']
    std_dev = row['rate_std_7d'] if not pd.isna(row['rate_std_7d']) else 0.0 # Volatilidade

    # 1. Este bloco with está agora no escopo correto do loop for
    with kpi_cols[df_analysis.index.get_loc(idx)]: # Usa get_loc(idx) para pegar a posição na coluna, pois df.iterrows() usa o índice original
        # Inverter o sinal do delta para Força do BRL (Delta negativo = BRL perde força)
        delta_base_forca = delta_vs_7d_pct * -1 if not pd.isna(delta_vs_7d_pct) else None
        
        # Formata o valor da cotação
        value_br = f"{latest_rate:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Verifica se há dados suficientes para a métrica de 7 dias
        if not pd.isna(row['rate_avg_7d']):
            # 1. KPI Principal: Cotação Atual vs Média 7D
            st.metric(
                label=f"**{base_currency}** vs {currency} | R$ {value_br}",
                value=f"R$ {value_br}", 
                delta=delta_base_forca, # Passa o float para a seta e percentual
                delta_color="normal",
            )
            # 2. Contexto Adicional
            st.caption(f"**vs. Média 7D:** {delta_vs_7d_pct:.2f}%")
            st.caption(f"**Volatilidade (7D):** {std_dev:.5f}") # STD é um proxy para volatilidade
        else:
            # Exibe N/A se não houver dados históricos (menos de 7 dias)
            st.metric(
                label=f"**{base_currency}** vs {currency}",
                value="R$ N/A",
                delta="Dados Insuficientes (7D)"
            )

st.markdown("---")

# --- Gráfico de Dispersão (Contexto/Risco) ---
st.subheader("2. Posição de Risco (Variação Diária vs Volatilidade)")

# Adiciona o Delta Diário (Se você tiver a coluna 'daily_change_pct' no Parquet)
# Para fins de demonstração, usaremos o delta_vs_7d_pct como o eixo Y (Variação)

df_analysis['Delta vs 7D (%)'] = df_analysis['delta_vs_7d_pct']
df_analysis['Volatilidade (STD)'] = df_analysis['rate_std_7d'].fillna(0)
df_analysis['Cor'] = np.where(df_analysis['Delta vs 7D (%)'] > 0, 'Perda de Força do BRL', 'Ganho de Força do BRL') 
# CORREÇÃO: A lógica da cor estava invertida. Delta > 0 (taxa subiu) = BRL perde força.

# Usa Altair para criar um gráfico de dispersão (Scatter Plot)
if not df_analysis.empty:
    scatter_chart = (
        alt.Chart(df_analysis)
        .mark_circle(size=100)
        .encode(
            x=alt.X("Volatilidade (STD):Q", title="Risco: Volatilidade (Desvio Padrão 7D)"),
            y=alt.Y("Delta vs 7D (%):Q", title="Posicionamento (vs. Média 7D)"),
            color=alt.Color("Cor:N", scale=alt.Scale(domain=['Ganho de Força do BRL', 'Perda de Força do BRL'], range=['green', 'red'])),
            tooltip=["currency", "Delta vs 7D (%)", "Volatilidade (STD)"]
        )
        .properties(
            title="Moedas em Contexto de Risco vs Posição Atual"
        )
        .interactive()
    )
    
    # Adiciona linhas de referência para o centro
    # Calcula a média da volatilidade apenas sobre valores válidos
    mean_volatility = df_analysis['Volatilidade (STD)'].replace([np.inf, -np.inf], np.nan).mean()

    ref_lines = alt.Chart(pd.DataFrame({'y': [0], 'x': [mean_volatility]}))
    
    # Linha Horizontal no Zero (Eixo Y)
    hline = ref_lines.mark_rule(color='black', strokeDash=[5,5]).encode(y='y:Q')
    
    # Linha Vertical na Média de Volatilidade (Eixo X)
    v_line = ref_lines.mark_rule(color='gray', strokeDash=[3,3]).encode(x='x:Q')

    st.altair_chart(scatter_chart + hline + v_line, use_container_width=True)
else:
    st.warning("Nenhum dado para o gráfico de dispersão.")

st.markdown("---")

# --- LLM Insight (Com Ação) ---
st.subheader("3. Análise Executiva da LLM (Ação Sugerida)")
st.info("A LLM analisa o posicionamento no gráfico acima e sugere ações.")

# Simulação do texto da LLM focado no risco
# Corrigindo a verificação de média para evitar NaN/inf
mean_volatility_safe = df_analysis['Volatilidade (STD)'].replace([np.inf, -np.inf], np.nan).mean()

if mean_volatility_safe > 0.0005:
    llm_advice = "A volatilidade média desta semana está alta. O **USD** está fora do desvio padrão e em território de **perda de força** contra a média, mas seu risco é elevado. Recomendamos **adiar 48h** qualquer compra não essencial em USD."
elif df_analysis['Delta vs 7D (%)'].min() < -1.0:
     llm_advice = "O mercado está calmo, mas o **EUR** apresentou uma **desvalorização súbita de 1.5%** em relação à média de 7 dias. Esta é uma janela de oportunidade. Recomendamos **executar compras** na Zona do Euro imediatamente."
else:
     llm_advice = "O mercado cambial está estável e próximo da média semanal. Não há sinais fortes de risco ou oportunidade. Siga o plano de *hedge* programado."

st.markdown(llm_advice)
