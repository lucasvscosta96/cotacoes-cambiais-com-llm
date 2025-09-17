import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

st.set_page_config(page_title="Dashboard Câmbio", layout="wide")

st.title("📊 Variação Semanal de Moedas (base BRL)")

# Caminho para os arquivos gold/
GOLD_DIR = "gold/"

# Carregar todos os arquivos .parquet
def load_gold_data():
    all_files = sorted(glob.glob(os.path.join(GOLD_DIR, "*.parquet")))
    all_dfs = []

    for file in all_files:
        df = pd.read_parquet(file)
        date_str = os.path.basename(file).replace(".parquet", "")
        df["date"] = pd.to_datetime(date_str)
        all_dfs.append(df)

    if all_dfs:
        full_df = pd.concat(all_dfs)
        return full_df
    else:
        return pd.DataFrame()

# Carregar dados
df = load_gold_data()

if df.empty:
    st.warning("Nenhum dado encontrado na pasta /gold/")
    st.stop()

# Filtro de moedas
moedas_disponiveis = df["currency"].unique().tolist()
moedas_selecionadas = st.multiselect("Selecione as moedas:", moedas_disponiveis, default=moedas_disponiveis[:5])

# Filtrar por moedas
df_filtered = df[df["currency"].isin(moedas_selecionadas)]

# Pivotar dados para gráfico
pivot_df = df_filtered.pivot_table(
    index="date",
    columns="currency",
    values="rate"
).sort_index()

# Plotar gráfico
st.line_chart(pivot_df)

# Mostrar tabela (opcional)
with st.expander("📄 Ver dados em tabela"):
    st.dataframe(pivot_df.style.format("{:.4f}"), height=400)
