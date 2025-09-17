import os
import requests
import json
from datetime import datetime
from src.utils import load_env, load_config, setup_logging, ensure_dir

def fetch_exchange_rates(date=None):
    load_env()
    setup_logging()
    config = load_config()

    api_key = os.getenv("EXCHANGE_API_KEY")
    if not api_key:
        raise ValueError("Chave da API não encontrada no .env")

    base_currency = config["base_currency"]
    target_currencies = config["target_currencies"]
    api_url = config["api_url"]

    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    url = f"{api_url}/{api_key}/latest/{base_currency}"
    logging.info(f"Buscando dados de câmbio da URL: {url}")

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
