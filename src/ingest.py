import os
import requests
import json
import yaml
import logging
from datetime import datetime
from src.utils import load_env, load_config, setup_logging, ensure_dir

def fetch_exchange_rates(date=None):
    # Carregar variáveis de ambiente
    load_env()
    setup_logging()

    # Obter caminho do arquivo config.yaml
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")

    # Carregar configurações do arquivo config.yaml
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    # Obter chave da API
    api_key = os.getenv("EXCHANGE_API_KEY")
    if not api_key:
        raise ValueError("Chave da API não encontrada no .env")

    # Configurações da API
    base_currency = config["base_currency"]
    target_currencies = config["target_currencies"]
    api_url = config["api_url"]

    # Definir data padrão se não fornecida
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    # Construir URL da API
    url = f"{api_url}/{api_key}/latest/{base_currency}"
    logging.info(f"Buscando dados de câmbio da URL: {url}")

    # Fazer requisição à API
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        # Salvar JSON bruto
        ensure_dir("raw")
        output_path = os.path.join("raw", f"{date}.json")
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logging.info(f"Dados salvos com sucesso em {output_path}")
    else:
        logging.error(f"Erro na API: {response.status_code} - {response.text}")
        raise Exception("Falha na chamada da API de câmbio")


if __name__ == "__main__":
    fetch_exchange_rates()