import os
import pandas as pd
import pytest
from src.transform import transform_to_silver

def test_transform_returns_dataframe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("raw", exist_ok=True)

    # Criar JSON simulado
    raw_data = {
        "base_code": "BRL",
        "conversion_rates": {
            "USD": 0.2,
            "EUR": -0.1,  # taxa inválida
            "JPY": 30
        },
        "time_last_update_utc": "2025-09-17 00:00:00"
    }

    with open("raw/2025-09-17.json", "w") as f:
        import json
        json.dump(raw_data, f)

    df = transform_to_silver("2025-09-17")

    # Validações
    assert isinstance(df, pd.DataFrame)
    assert "EUR" not in df["currency"].values  # taxa negativa removida
    assert "USD" in df["currency"].values
