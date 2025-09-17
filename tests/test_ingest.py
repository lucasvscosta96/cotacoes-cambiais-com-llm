import os
import pytest
from src.ingest import fetch_exchange_rates

def test_ingest_creates_raw_file(tmp_path, monkeypatch):
    # Mock diretório
    monkeypatch.chdir(tmp_path)
    os.makedirs("raw", exist_ok=True)

    # Rodar função
    fetch_exchange_rates("2025-09-17")

    # Verificar arquivo criado
    assert os.path.exists("raw/2025-09-17.json")
