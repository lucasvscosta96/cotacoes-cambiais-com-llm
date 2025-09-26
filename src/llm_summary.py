import os
import logging
import pandas as pd
from datetime import datetime
from src.utils import setup_logging, ensure_dir, load_env
from openai import OpenAI

def load_gold_data(date):
    gold_path = os.path.join("gold", f"{date}.parquet")
    if not os.path.exists(gold_path):
        logging.error(f"Arquivo {gold_path} não encontrado.")
        raise FileNotFoundError(f"Arquivo {gold_path} não encontrado.")
    logging.info(f"Carregando dados de {gold_path}")
    return pd.read_parquet(gold_path)

def gerar_prompt(df, date, base_currency="BRL", top_n=5):
    df_base = df[df['base_currency'] == base_currency].copy()
    if df_base.empty:
        raise ValueError(f"Não foram encontrados dados para a moeda base {base_currency} na data {date}.")
    df_base['rate'] = pd.to_numeric(df_base['rate'], errors='coerce')
    df_base.dropna(subset=['rate'], inplace=True)
    moedas_top_n = df_base.sort_values(by="rate", ascending=False).head(top_n)
    linhas = [f"- {row['currency']}: {row['rate']:.4f}" for _, row in moedas_top_n.iterrows()]
    texto_moedas = "\n".join(linhas)
    prompt = f"""
Você é um analista financeiro especializado em câmbio e seu público são gestores de negócio sem conhecimento aprofutado em economia.
Sua tarefa é criar um resumo executivo claro e conciso sobre a cotação de moedas estrangeiras em relação ao Real Brasileiro (BRL).

**Data do Relatório:** {date}

**Principais Cotações (em relação ao BRL):**
{texto_moedas}

**Instruções:**
1.  Comece com uma frase de impacto que resuma o cenário cambial do dia.
2.  Explique de forma simples o que significa a valorização ou desvalorização dessas moedas em relação ao Real.
3.  Destaque a moeda de maior cotação e o que isso representa na prática.
4.  Mantenha o tom profissional, direto e focado em insights para negócios.
5.  O resumo deve ter no máximo 3 parágrafos.
"""
    return prompt.strip()

def gerar_resumo_llm(date=None, base_currency="BRL", top_n=5):
    load_env()
    setup_logging()
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    try:
        client = OpenAI()
        logging.info("Cliente OpenAI inicializado com sucesso.")

        df = load_gold_data(date)
        prompt_usuario = gerar_prompt(df, date, base_currency=base_currency, top_n=top_n)

        logging.info("Enviando prompt para a API da OpenAI (modelo gpt-3.5-turbo)...")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Você é um analista financeiro especializado em câmbio.",
                },
                {
                    "role": "user",
                    "content": prompt_usuario,
                }
            ],
            model="gpt-3.5-turbo"
        )
        
        resumo = chat_completion.choices[0].message.content.strip()
        
        ensure_dir("reports")
        report_path = os.path.join("reports", f"{date}_{base_currency}_summary.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(resumo)

        logging.info(f"Resumo salvo com sucesso em {report_path}")
        print("\n--- Resumo Executivo ({} | {}) ---\n".format(base_currency, date))
        print(resumo)
        return resumo

    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado ao gerar o resumo do LLM: {e}", exc_info=True)
        print(f"\n❌ Ocorreu um erro inesperado: {e}")
    
    return None