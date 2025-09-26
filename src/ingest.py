import os
import requests
import json
import yaml
import logging
from datetime import datetime
from src.utils import load_env, setup_logging, ensure_dir

def fetch_exchange_rates(date=None):
    """
    Busca as taxas de câmbio da API e salva os dados brutos.
    Verifica se o ficheiro de saída já existe para garantir a idempotência.
    """
    load_env()
    setup_logging()

    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    # --- VERIFICAÇÃO DE IDEMPOTÊNCIA ---
    output_path = os.path.join("raw", f"{date}.json")
    if os.path.exists(output_path):
        logging.info(f"O ficheiro de destino {output_path} já existe. A pular a etapa de ingestão.")
        return output_path
    # ------------------------------------

    api_key = os.getenv("EXCHANGE_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente EXCHANGE_API_KEY não foi encontrada.")

    api_url = os.getenv("API_URL")
    base_currency = os.getenv("BASE_CURRENCY")

    if not api_url or not base_currency:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        if os.path.exists(config_path):
            logging.info(f"A carregar configurações do ficheiro de fallback: {config_path}")
            with open(config_path, "r") as file:
                config = yaml.safe_load(file)
            if not api_url:
                api_url = config.get("api_url")
            if not base_currency:
                base_currency = config.get("base_currency")
        else:
            logging.info("Ficheiro config.yaml não encontrado. A usar apenas variáveis de ambiente.")

    if not api_url:
        raise ValueError("URL da API não definida. Configure a variável de ambiente API_URL ou a chave 'api_url' no config.yaml.")
    
    if not base_currency:
        base_currency = "BRL"
        logging.info("Moeda base não definida, a usar 'BRL' como padrão.")

    url = f"{api_url}/{api_key}/latest/{base_currency}"
    logging.info("A buscar dados de câmbio...")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        ensure_dir("raw")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info(f"Dados guardados com sucesso em {output_path}")
        return output_path

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na API: {e}. Resposta: {e.response.text if e.response else 'N/A'}")
        raise
