import os
import yaml
from dotenv import load_dotenv
import logging
from datetime import datetime

# Carregar variáveis de ambiente
def load_env():
    load_dotenv()

# Carregar arquivo de configuração
def load_config(path="config.yaml"):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

# Configurar logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

# Criar diretório se não existir
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
