import pandas as pd
import os
import json
import pytest
from src.transformation import transform_to_silver

def test_transform_to_silver_creates_file(tmp_path, monkeypatch):
    """
    Testa o cenário feliz da transformação, filtrando moedas-alvo.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("raw", exist_ok=True)

    raw_data = {
        "base_code": "BRL",
        "conversion_rates": {"USD": 0.2, "EUR": 0.18, "JPY": 25.5},
        "time_last_update_unix": 1631836800
    }
    with open("raw/2025-09-17.json", 'w') as f:
        json.dump(raw_data, f)

    config_content = "target_currencies: [USD, EUR]"
    with open("config.yaml", "w") as f:
        f.write(config_content)

    transform_to_silver(date="2025-09-17")

    # Verificar se o ficheiro silver foi criado
    silver_path = "silver/2025-09-17.parquet"
    assert os.path.exists(silver_path)

    # Verificar conteúdo
    df = pd.read_parquet(silver_path)
    assert len(df) == 2
    assert "JPY" not in df["currency"].tolist()
    assert "USD" in df["currency"].tolist()
    assert df.columns.tolist() == ["base_currency", "currency", "rate", "timestamp"]


def test_transform_with_no_raw_file(tmp_path, monkeypatch):
    """
    Testa se a função levanta um erro FileNotFoundError se o ficheiro raw não existir.
    """
    monkeypatch.chdir(tmp_path)
    
    config_content = "target_currencies: [USD, EUR]"
    with open("config.yaml", "w") as f:
        f.write(config_content)
        
    # Verificar se a exceção correta é levantada
    with pytest.raises(FileNotFoundError) as excinfo:
        transform_to_silver(date="2025-09-17")
    
    assert "Arquivo raw não encontrado" in str(excinfo.value)


def test_transform_with_malformed_raw_file(tmp_path, monkeypatch):
    """
    Testa se a função levanta um erro ao tentar processar um JSON malformado.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("raw", exist_ok=True)
    
    with open("raw/2025-09-17.json", 'w') as f:
        f.write("{'invalid_json':,}")
        
    config_content = "target_currencies: [USD, EUR]"
    with open("config.yaml", "w") as f:
        f.write(config_content)
        
    # Verificar se a exceção de decodificação de JSON é levantada
    with pytest.raises(json.JSONDecodeError):
        transform_to_silver(date="2025-09-17")

