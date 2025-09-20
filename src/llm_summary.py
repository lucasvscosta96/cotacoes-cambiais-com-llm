import os, base64
import logging
import pandas as pd
import requests
from datetime import datetime
from src.utils import load_env, setup_logging, ensure_dir

def load_gold_data(date):
    """
    Carrega os dados do arquivo Parquet na pasta 'gold/' para a data especificada.
    """
    gold_path = os.path.join("gold", f"{date}.parquet")
    if not os.path.exists(gold_path):
        raise FileNotFoundError(f"Arquivo {gold_path} não encontrado.")

    return pd.read_parquet(gold_path)

def gerar_prompt(df, date):
    """
    Gera um prompt para o modelo de linguagem com base nos dados do DataFrame.
    """
    moedas_top5 = df.sort_values(by="rate", ascending=False).head(5)
    linhas = [f"{row['currency']}: {row['rate']:.4f}" for _, row in moedas_top5.iterrows()]
    texto_moedas = "\n".join(linhas)

    prompt = f"""
Você é um analista econômico. Com base nas taxas de câmbio abaixo em relação ao Real (BRL) no dia {date}, gere um resumo executivo em linguagem simples para usuários de negócio.

Taxas (BRL como base):
{texto_moedas}

Escreva um resumo claro e objetivo, destacando as moedas mais valorizadas e qualquer variação relevante.
"""
    return prompt.strip()

def gerar_resumo_llm(date=None, base_currency="BRL", top_n=5):
    load_env()
    setup_logging()

    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    df = load_gold_data(date)

    # Gerar o prompt com base na moeda base e no número de moedas principais
    prompt = gerar_prompt(df, date)

    logging.info("Enviando prompt à API do Cursor...")

    # Configurar o endpoint e a chave da API do Cursor
    cursor_api_key = os.getenv("CURSOR_API_KEY")
    if not cursor_api_key:
        raise ValueError("CURSOR_API_KEY não está configurada no .env")

    # Codificar a chave da API no formato Base64
    encoded_api_key = base64.b64encode(f"{cursor_api_key}:".encode()).decode()

    endpoint = "https://api.cursor.com/v1/chat/completions"  # Substitua pelo endpoint correto, se necessário

    # Fazer a chamada à API do Cursor
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Basic {encoded_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "prompt": prompt,
            "temperature": 0.7,
            "max_tokens": 256
        }
    )

    if response.status_code != 200:
        raise ValueError(f"Erro na API do Cursor: {response.status_code} - {response.text}")

    resumo = response.json().get("text", "").strip()

    # Salvar em reports/
    ensure_dir("reports")
    report_path = os.path.join("reports", f"{date}_summary.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(resumo)

    logging.info(f"Resumo salvo em {report_path}")
    print("\n📄 Resumo Gerado:\n")
    print(resumo)

    return resumo