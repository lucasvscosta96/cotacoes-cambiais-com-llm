import os
import json
import pandas as pd
import logging
from datetime import datetime
from src.utils import setup_logging, ensure_dir


def transform_to_silver(date=None):
    # Usar a data atual como padrão se nenhuma data for fornecida
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    raw_path = os.path.join("raw", f"{date}.json")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Arquivo {raw_path} não encontrado.")

    # Carregar dados do JSON
    with open(raw_path, "r") as f:
        raw_data = json.load(f)

    # Validar e transformar os dados
    conversion_rates = raw_data.get("conversion_rates", {})
    valid_rates = {
        currency: rate
        for currency, rate in conversion_rates.items()
        if isinstance(rate, (int, float)) and rate > 0  # Filtrar taxas inválidas
    }

    if not valid_rates:
        raise ValueError("Nenhuma taxa de câmbio válida encontrada.")

    df = pd.DataFrame([
        {"base_currency": raw_data["base_code"], "currency": currency, "rate": rate, "date": date}
        for currency, rate in valid_rates.items()
    ])

    # Salvar em formato parquet
    silver_path = os.path.join("silver", f"{date}.parquet")
    os.makedirs("silver", exist_ok=True)
    df.to_parquet(silver_path, index=False)

    return df