import pandas as pd
import os
import json
import yaml
import logging
from src.utils import ensure_dir, setup_logging

def transform_to_silver(date=None):
    """
    Carrega os dados brutos, transforma-os e filtra pelas moedas de interesse
    definidas no config.yaml antes de salvar na camada silver.
    """
    setup_logging()
    
    # Carregar as moedas de interesse a partir do config.yaml
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
    
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    
    target_currencies = config.get("target_currencies")
    if not target_currencies:
        raise ValueError("A lista 'target_currencies' não foi encontrada ou está vazia no config.yaml")

    # Carregar os dados brutos
    raw_path = os.path.join("raw", f"{date}.json")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Arquivo raw não encontrado para a data {date}")
        
    with open(raw_path, 'r') as f:
        data = json.load(f)

    # Lógica de transformação
    base_currency = data.get("base_code")
    rates = data.get("conversion_rates", {})
    timestamp = data.get("time_last_update_unix")

    transformed_data = []
    for currency, rate in rates.items():
        transformed_data.append({
            "base_currency": base_currency,
            "currency": currency,
            "rate": rate,
            "timestamp": timestamp
        })

    if not transformed_data:
        logging.warning("Nenhum dado para transformar.")
        return

    df_silver = pd.DataFrame(transformed_data)
    
    # Filtrar pelas moedas-alvo definidas no config.yaml
    logging.info(f"Filtrando o DataFrame pelas moedas de interesse: {target_currencies}")
    df_silver = df_silver[df_silver['currency'].isin(target_currencies)]

    # Verificação de qualidade dos dados
    df_silver = df_silver[df_silver["rate"] > 0]

    # Salvar na camada silver
    ensure_dir("silver")
    silver_path = os.path.join("silver", f"{date}.parquet")
    df_silver.to_parquet(silver_path, index=False)
    logging.info(f"Dados transformados e salvos com sucesso em {silver_path}")
