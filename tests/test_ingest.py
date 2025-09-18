import os
import pytest
from src.ingest import fetch_exchange_rates

def test_ingest_creates_raw_file(tmp_path, monkeypatch):
    # Mock diretório de trabalho
    monkeypatch.chdir(tmp_path)
    os.makedirs("raw", exist_ok=True)

    # Mock do caminho do arquivo config.yaml
    mock_config_path = tmp_path / "config.yaml"
    mock_config_path.write_text("""
    base_currency: BRL
    target_currencies: [USD, EUR, GBP, JPY, AUD]
    api_url: https://v6.exchangerate-api.com/v6
    """)

    # Mock variável de ambiente para apontar para o config.yaml
    monkeypatch.setenv("CONFIG_PATH", str(mock_config_path))

    # Rodar função
    fetch_exchange_rates("2025-09-17")

    # Verificar arquivo criado
    assert os.path.exists("raw/2025-09-17.json")