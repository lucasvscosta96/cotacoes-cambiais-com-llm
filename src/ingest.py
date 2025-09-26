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

    Esta função é agnóstica ao ambiente:
    - Em produção/CI (GitHub Actions), usa exclusivamente variáveis de ambiente.
    - Localmente, pode usar um arquivo .env para a chave da API e um config.yaml
      como fallback para outras configurações.
    """
    load_env()  # Carrega .env para desenvolvimento local
    setup_logging()

    # 1. Obter a chave da API (obrigatória via variável de ambiente por segurança)
    api_key = os.getenv("EXCHANGE_API_KEY")
    if not api_key:
        raise ValueError("A variável de ambiente EXCHANGE_API_KEY não foi encontrada.")

    # 2. Obter outras configurações, priorizando variáveis de ambiente
    api_url = os.getenv("API_URL")
    base_currency = os.getenv("BASE_CURRENCY")

    # 3. Se as configurações não estiverem no ambiente, tentar carregar do config.yaml como fallback
    if not api_url or not base_currency:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        if os.path.exists(config_path):
            logging.info(f"Carregando configurações do arquivo de fallback: {config_path}")
            with open(config_path, "r") as file:
                config = yaml.safe_load(file)
            # Preencher apenas o que estiver faltando, mantendo a prioridade do ambiente
            if not api_url:
                api_url = config.get("api_url")
            if not base_currency:
                base_currency = config.get("base_currency")
        else:
            logging.info("Arquivo config.yaml não encontrado. Usando apenas variáveis de ambiente.")

    # 4. Validar se as configurações essenciais foram encontradas
    if not api_url:
        raise ValueError("URL da API não definida. Configure a variável de ambiente API_URL ou a chave 'api_url' no config.yaml.")
    
    # Se a moeda base ainda não estiver definida, usar 'BRL' como padrão
    if not base_currency:
        base_currency = "BRL"
        logging.info("Moeda base não definida, usando 'BRL' como padrão.")

    # Definir data padrão se não fornecida
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    # Construir URL da API
    url = f"{api_url}/{api_key}/latest/{base_currency}"
    logging.info(f"Buscando dados de câmbio...")

    try:
        # Fazer requisição à API
        response = requests.get(url)
        response.raise_for_status()  # Lança erro para status 4xx/5xx
        data = response.json()

        # Salvar JSON bruto
        ensure_dir("raw")
        output_path = os.path.join("raw", f"{date}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info(f"Dados salvos com sucesso em {output_path}")
        return output_path

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na API: {e}")
        raise