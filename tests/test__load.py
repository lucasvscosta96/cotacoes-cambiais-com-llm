import os
import pandas as pd
from src.load import save_to_gold

def test_load_saves_parquet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("silver", exist_ok=True)

    df = pd.DataFrame({
        "base_currency": ["BRL", "BRL"],
        "currency": ["USD", "EUR"],
        "rate": [0.2, 0.18],
        "timestamp": ["2025-09-17 00:00:00"] * 2
    })

    df.to_parquet("silver/2025-09-17.parquet", index=False)

    save_to_gold("2025-09-17")

    assert os.path.exists("gold/2025-09-17.parquet")
