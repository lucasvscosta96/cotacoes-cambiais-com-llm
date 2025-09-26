import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime, timedelta

# --- Configuração da Página ---
# Usar st.set_page_config() como o primeiro comando do Streamlit
st.set_page_config(
    page_title="Dashboard de Cotações Cambiais",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Carregamento de Dados com Cache ---
# O decorador @st.cache_data garante que os dados sejam carregados apenas uma vez,
# tornando a aplicação muito mais rápida em interações subsequentes.
@st.cache_data
def load_gold_data() -> pd.DataFrame:
    """
    Carrega e consolida todos os arquivos Parquet da pasta 'gold/'.
    Adiciona uma coluna 'date' baseada no nome do arquivo.
    Retorna um DataFrame vazio se nenhum arquivo for encontrado.
    """
    gold_dir = "gold/"
    if not os.path.exists(gold_dir):
        return pd.DataFrame()

    all_files = sorted(glob.glob(os.path.join(gold_dir, "*.parquet")))
    if not all_files:
        return pd.DataFrame()

    df_list = []
    for file in all_files:
        try:
            df = pd.read_parquet(file)
            # Extrai a data do nome do arquivo de forma mais robusta
            date_str = os.path.basename(file).split('.')[0]
            df['date'] = pd.to_datetime(date_str)
            df_list.append(df)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {file}: {e}")
    
    if not df_list:
        return pd.DataFrame()

    full_df = pd.concat(df_list, ignore_index=True)
    # Garante que a coluna de taxa seja numérica
    full_df['rate'] = pd.to_numeric(full_df['rate'], errors='coerce')
    return full_df.sort_values(by="date")

# --- Lógica Principal da Aplicação ---
df = load_gold_data()

if df.empty:
    st.warning("Nenhum dado encontrado na pasta /gold/. Execute o pipeline de dados primeiro.")
    st.stop()

# --- Barra Lateral (Sidebar) para Filtros ---
st.sidebar.header("Filtros do Dashboard")

# Filtro de Moedas
available_currencies = sorted(df["currency"].unique())
default_currencies = ["USD", "EUR", "GBP", "JPY", "AUD"]
# Garante que as moedas padrão existam nos dados
selected_currencies = st.sidebar.multiselect(
    "Selecione as moedas:",
    options=available_currencies,
    default=[c for c in default_currencies if c in available_currencies]
)

# Filtro de Data
min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.sidebar.date_input(
    "Selecione o período:",
    value=(max_date - timedelta(days=30), max_date), # Padrão: últimos 30 dias
    min_value=min_date,
    max_value=max_date,
)

# Validação do intervalo de datas
if len(date_range) != 2:
    st.sidebar.warning("Por favor, selecione um início e um fim para o período.")
    st.stop()

start_date, end_date = date_range

# --- Filtragem dos Dados ---
# Aplica os filtros da barra lateral ao DataFrame
df_filtered = df[
    (df["currency"].isin(selected_currencies)) &
    (df["date"].dt.date >= start_date) &
    (df["date"].dt.date <= end_date)
]

# --- Layout da Página Principal ---
st.title("📊 Dashboard de Cotações Cambiais")
st.markdown(f"Exibindo dados de **{start_date.strftime('%d/%m/%Y')}** a **{end_date.strftime('%d/%m/%Y')}**")
st.markdown(f"*Última atualização encontrada em: {max_date.strftime('%d/%m/%Y')}*")

st.markdown("---")

# --- Métricas (KPIs) ---
st.subheader("Desempenho Recente")

# Obter as duas datas mais recentes nos dados filtrados para calcular a variação
latest_dates = df_filtered['date'].nlargest(2).unique()

if len(latest_dates) >= 2:
    latest_date = latest_dates[0]
    previous_date = latest_dates[1]
    
    df_latest = df_filtered[df_filtered['date'] == latest_date]
    df_previous = df_filtered[df_filtered['date'] == previous_date]

    # Criar colunas para as métricas
    kpi_cols = st.columns(len(selected_currencies))

    for i, currency in enumerate(selected_currencies):
        latest_rate_series = df_latest[df_latest['currency'] == currency]['rate']
        previous_rate_series = df_previous[df_previous['currency'] == currency]['rate']

        if not latest_rate_series.empty and not previous_rate_series.empty:
            latest_rate = latest_rate_series.iloc[0]
            previous_rate = previous_rate_series.iloc[0]
            delta = ((latest_rate - previous_rate) / previous_rate) * 100
            
            with kpi_cols[i]:
                st.metric(
                    label=f"**{currency}** vs BRL",
                    value=f"{latest_rate:.4f}",
                    delta=f"{delta:.2f}% (vs {previous_date.strftime('%d/%m')})",
                )
else:
    st.info("Selecione um período com pelo menos dois dias de dados para ver a variação.")

st.markdown("---")

# --- Gráfico de Linha ---
st.subheader("Evolução Histórica (base BRL)")

if not df_filtered.empty:
    pivot_df = df_filtered.pivot_table(
        index="date",
        columns="currency",
        values="rate"
    ).sort_index()

    st.line_chart(pivot_df)
else:
    st.warning("Nenhum dado disponível para os filtros selecionados.")


# --- Tabela de Dados ---
with st.expander("📄 Ver dados detalhados em tabela"):
    if not df_filtered.empty:
        # Exibe o DataFrame filtrado, que é mais fácil de ler que o pivotado
        st.dataframe(
            df_filtered.sort_values(by=["date", "currency"], ascending=[False, True]),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.write("Nenhum dado para exibir.")
