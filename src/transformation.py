import os
import json
import pandas as pd
import logging
from datetime import datetime
from src.utils import setup_logging, ensure_dir

def transform_to_silver(date=None):
    setup_logging()

    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    raw_path = os.path.join("raw", f"{date}.json")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Arquivo {raw_path} não encontrado.")

    with open(raw_path, 'r') as f:
        data = json.load(f)

    base_currency = data["base_code"]
    timestamp = data["time_last_update_utc"]
    rates = data["conversion_rates"]

    logging.info(f"Transformando dados de {base_currency} - {timestamp}")

    # Criar DataFrame
    df = pd.DataFrame([
        {"base_currency": base_currency,
         "currency": k,
         "rate": v,
         "timestamp": timestamp}
        for k, v in rates.items()
    ])

    # Validação: remover taxas nulas ou negativas
    df = df[df["rate"] > 0]

    # Salvar como Parquet
    ensure_dir("silver")
    silver_path = os.path.join("silver", f"{date}.parquet")
    df.to_parquet(silver_path, index=False)

    logging.info(f"Arquivo salvo em {silver_path}")
