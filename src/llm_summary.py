import os
import logging
import pandas as pd
import yaml
from datetime import datetime
from src.utils import setup_logging, ensure_dir, load_env
from openai import OpenAI
logger = logging.getLogger(__name__)


def load_gold_data(date):
    """Carrega os dados do ficheiro Parquet na pasta 'gold/' para a data especificada."""
    gold_path = os.path.join("gold", f"{date}.parquet")
    if not os.path.exists(gold_path):
        logging.error(f"Ficheiro {gold_path} não encontrado.")
        raise FileNotFoundError(f"Ficheiro {gold_path} não encontrado.")
    logging.info(f"A carregar dados de {gold_path}")
    return pd.read_parquet(gold_path)


def gerar_prompt(df, date, top_n=5):
    """Gera um prompt avançado para a LLM com destaques e contexto."""
    df_copy = df.copy()

    if "daily_change_pct" not in df_copy.columns:
        df_copy["daily_change_pct"] = 0.0

    df_copy["daily_change_pct"] = df_copy["daily_change_pct"].fillna(0)

    df_copy = df_copy.sort_values(
        by="daily_change_pct",
        key=abs,
        ascending=False
    ).head(top_n)

    texto_principais_moedas = "\n".join([
        f"- {row['currency']}: {row['rate']:.4f} "
        f"(Variação diária: {row['daily_change_pct']:.2%})"
        for _, row in df_copy.iterrows()
    ])

    max_change = df_copy["daily_change_pct"].max()
    min_change = df_copy["daily_change_pct"].min()

    if max_change > 0.0001 or min_change < -0.0001:
        moeda_maior_alta = df_copy.loc[df_copy["daily_change_pct"].idxmax()]
        moeda_maior_baixa = df_copy.loc[df_copy["daily_change_pct"].idxmin()]
        texto_destaques = f"""
**Destaques do Dia:**
- Maior alta: {moeda_maior_alta['currency']} ({moeda_maior_alta['daily_change_pct']:.2%})
- Maior baixa: {moeda_maior_baixa['currency']} ({moeda_maior_baixa['daily_change_pct']:.2%})
"""
    else:
        texto_destaques = (
            "**Destaques do Dia:**\n- O mercado apresentou estabilidade, "
            "sem variações significativas entre as moedas analisadas."
        )

    prompt = f"""
**Contexto:** Análise das cotações em relação ao Real Brasileiro (BRL) na data {date}.

**Dados Principais:**
{texto_principais_moedas}
{texto_destaques}

**Tarefa:**
Escreva um resumo executivo (máx. 3 parágrafos) que aborde:
1. Panorama geral do dia.
2. Destaques do dia e implicações.
3. Impacto prático do USD e EUR em importação, exportação e turismo no Brasil.
"""
    return prompt.strip()


def gerar_resumo_llm(date=None, top_n=5, save=True):
    """Gera resumo executivo usando LLM e salva em /reports/ (opcional)."""
    load_env()
    setup_logging()

    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    config_path = "config.yaml"
    base_currency = "BRL"
    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        base_currency = config.get("base_currency", "BRL")

    report_path = os.path.join("reports", f"{date}_{base_currency}_summary.txt")

    if save and os.path.exists(report_path):
        logging.info(f"Relatório para {date} já existe em {report_path}.")
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()

    try:
        logger.info("Enviando dados para análise pela LLM...")
        client = OpenAI()
        df = load_gold_data(date)
        prompt_usuario = gerar_prompt(df, date, top_n=top_n)

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um consultor financeiro sênior. "
                        "Escreva de forma clara e acessível para executivos não-técnicos."
                    ),
                },
                {"role": "user", "content": prompt_usuario},
            ],
            model="gpt-4o-mini",
        )

        resumo = chat_completion.choices[0].message.content.strip()

        if save:
            ensure_dir("reports")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(resumo)
            logging.info(resumo)    
            logging.info(f"Resumo salvo em {report_path}")

        return resumo

    except Exception as e:
        logging.error(f"Erro ao gerar resumo: {e}", exc_info=True)
        return f"Erro ao gerar resumo: {e}"


if __name__ == "__main__":
    gerar_resumo_llm()
