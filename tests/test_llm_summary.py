import os
import pandas as pd
from unittest.mock import patch
from src.llm_summary import gerar_resumo_llm

@patch("openai.ChatCompletion.create")
def test_llm_summary_creates_file(mock_chat, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("gold", exist_ok=True)

    # Criar DataFrame com dados válidos
    df = pd.DataFrame({
        "base_currency": ["BRL"],
        "currency": ["USD"],
        "rate": [0.2],
        "date": ["2025-09-17 00:00:00"],
    })
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df.to_parquet("gold/2025-09-17.parquet", index=False)

    # Mock da resposta da OpenAI
    mock_chat.return_value = {
        "choices": [
            {"message": {"content": "Resumo simulado da LLM"}}
        ]
    }

    resumo = gerar_resumo_llm("2025-09-17")
    assert "Resumo simulado" in resumo
    assert os.path.exists("reports/2025-09-17_summary.txt")