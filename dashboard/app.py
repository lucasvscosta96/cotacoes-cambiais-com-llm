import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime, timedelta, date 
import altair as alt 
# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Cotações Cambiais",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Função para encontrar o relatório mais recente ---
def get_latest_report_path(report_dir="reports"):
    """Encontra o caminho do arquivo de relatório (.txt) mais recente."""
    search_path = os.path.join(report_dir, "*.txt")
    list_of_files = glob.glob(search_path)
    if not list_of_files:
        return None
    
    # Encontra o arquivo modificado mais recentemente
    latest_file = max(list_of_files, key=os.path.getmtime)
    return latest_file

# --- Carregar e Exibir o Resumo ---



latest_report_path = get_latest_report_path()

st.sidebar.title("Resumo da LLM")
if latest_report_path:
    try:
        with open(latest_report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        st.sidebar.header("Relatório Mais Recente")
        report_date = datetime.fromtimestamp(os.path.getmtime(latest_report_path)).strftime('%d/%m/%Y %H:%M:%S')
        st.sidebar.markdown(f"**Data do Relatório:** *{report_date}*")
        # Usa um expander na sidebar para o texto longo do resumo
        with st.sidebar.expander("Ver Análise da LLM"):
            st.markdown(report_content)
        st.sidebar.divider()
        
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar o relatório: {e}")
else:
    st.sidebar.warning("Nenhum arquivo de relatório (.txt) encontrado.")


# --- Carregamento de Dados com Cache ---
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

    # Ordena os arquivos para garantir que o processamento seja cronológico
    all_files = sorted(glob.glob(os.path.join(gold_dir, "*.parquet")))
    if not all_files:
        return pd.DataFrame()

    df_list = []
    for file in all_files:
        try:
            df = pd.read_parquet(file)
            date_str = os.path.basename(file).split('.')[0]
            df['date'] = pd.to_datetime(date_str).date() # Armazena como objeto date puro
            df_list.append(df)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {file}: {e}")
    
    if not df_list:
        return pd.DataFrame()

    full_df = pd.concat(df_list, ignore_index=True)
    full_df['rate'] = pd.to_numeric(full_df['rate'], errors='coerce')
    full_df['date'] = pd.to_datetime(full_df['date']) # Converte de volta para datetime para manipulação no pandas
    
    return full_df.sort_values(by="date")

df = load_gold_data()

if df.empty:
    st.title("📊 Dashboard de Cotações Cambiais")
    st.warning("Nenhum dado encontrado na pasta /gold/. Execute o pipeline de dados primeiro.")
    st.stop()

st.sidebar.header("Filtros do Dashboard")

# Filtro de Moedas
available_currencies = sorted(df["currency"].unique())
default_currencies = ["USD", "EUR", "GBP"] # Ajuste as moedas padrão se necessário
selected_currencies = st.sidebar.multiselect(
    "Selecione as moedas:",
    options=available_currencies,
    default=[c for c in default_currencies if c in available_currencies]
)

# Filtro de Data
min_date = df["date"].min().date()
max_date = df["date"].max().date()

default_start_date = max_date - timedelta(days=30)
if default_start_date < min_date:
    default_start_date = min_date

date_range = st.sidebar.date_input(
    "Selecione o período:",
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


# --- Filtragem dos Dados ---

df_filtered = df[
    (df["currency"].isin(selected_currencies)) &
    (df["date"].dt.date >= start_date) &
    (df["date"].dt.date <= end_date)
].copy()
# --- Layout da Página Principal ---
st.title("📊 Dashboard de Cotações Cambiais")
st.markdown(f"Exibindo dados de **{start_date.strftime('%d/%m/%Y')}** a **{end_date.strftime('%d/%m/%Y')}**")
st.markdown(f"*Última atualização encontrada em: {max_date.strftime('%d/%m/%Y')}*")

st.markdown("---")

# O restante do seu código (Tabela de Dados) vem aqui...

# --- Tabela de Dados ---
with st.expander("📄 Ver dados detalhados em tabela"):
    if not df_filtered.empty:
        st.dataframe(
            df_filtered.sort_values(by=["date", "currency"], ascending=[False, True]),
            hide_index=True,
            use_container_width=True,
            column_order=["date", "currency", "rate"],
            column_config={
                "date": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY"),
                "currency": "Moeda",
                "rate": st.column_config.NumberColumn("Cotação (R$)", format="%.4f"),
            }
        )
    else:
        st.write("Nenhum dado para exibir.")


st.subheader("📈 Evolução das Moedas Selecionadas")
chart = (
    alt.Chart(df_filtered)
    .mark_line(point=True)
    .encode(
        x="date:T", # :T para Temporal (Data/Tempo)
        y="rate:Q", # :Q para Quantitativo (Numérico)
        color="currency:N", # :N para Nominal (Categoria/Nome)
        tooltip=["date", "currency", "rate", "daily_change_pct"]
    )
    .interactive()
)
st.altair_chart(chart, use_container_width=True)

st.markdown("---")

# --- Métricas (KPIs) ---
st.subheader("Desempenho da Base (BRL)")
st.markdown(f"*(Variação indica o ganho/perda de força do **{df['base_currency'].iloc[0]}** frente à moeda cotada)*")

# Obtém as duas datas mais recentes nos dados filtrados para calcular a variação
latest_dates = df_filtered['date'].drop_duplicates().nlargest(2).sort_values(ascending=False).tolist()

if len(latest_dates) >= 2:
    latest_date = latest_dates[0]
    previous_date = latest_dates[1]
    
    df_latest = df_filtered[df_filtered['date'] == latest_date]
    df_previous = df_filtered[df_filtered['date'] == previous_date]

    # Criar colunas para as métricas (o número de colunas é o número de moedas selecionadas)
    kpi_cols = st.columns(len(selected_currencies) if len(selected_currencies) > 0 else 1)
    base_currency = df['base_currency'].iloc[0] # Deve ser 'BRL'

    for i, currency in enumerate(selected_currencies):
        latest_rate_series = df_latest[df_latest['currency'] == currency]['rate']
        previous_rate_series = df_previous[df_previous['currency'] == currency]['rate']

        if not latest_rate_series.empty and not previous_rate_series.empty:
            latest_rate = latest_rate_series.iloc[0]
            previous_rate = previous_rate_series.iloc[0]
            
            # Cálculo Padrão: Variação da moeda cotada (USD/BRL)
            delta_moeda_cotada = ((latest_rate - previous_rate) / previous_rate) * 100
            
            # NOVO CÁLCULO: Variação da Moeda Base (BRL/USD)
            # Se a taxa sobe (positivo), a moeda base (BRL) perde força (negativo).
            # Se a taxa desce (negativo), a moeda base (BRL) ganha força (positivo).
            delta_base_forca = delta_moeda_cotada * -1
            
            with kpi_cols[i]:
                # Formato brasileiro para o valor principal
                value_br = f"{latest_rate:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                # Exibe a FORÇA DA BASE (BRL)
                st.metric(
                    label=f"**{base_currency}** vs {currency}",
                    value=f"R$ {value_br}", # Valor da cotação
                    delta=f"{delta_base_forca:.2f}% (Força do {base_currency})",
                    # delta_color="normal" # Streamlit já inverte a cor para delta negativo
                )
        else:
             with kpi_cols[i]:
                st.metric(
                    label=f"**{base_currency}** vs {currency}",
                    value="N/A",
                    delta="Dados Insuficientes"
                )
else:
    st.info("Selecione um período com pelo menos dois dias de dados para ver a variação.")

st.markdown("---")

