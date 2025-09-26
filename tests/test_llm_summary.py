import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from src.llm_summary import gerar_resumo_llm

def test_gerar_resumo_llm_success(tmp_path, monkeypatch):
    """
    Testa o cenário feliz, verificando se o resumo é gerado e o ficheiro é criado.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("gold", exist_ok=True)
    
    df = pd.DataFrame({
        "base_currency": ["BRL"], "currency": ["USD"], "rate": [0.2],
    })
    df.to_parquet("gold/2025-09-17.parquet", index=False)
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Resumo simulado da OpenAI"
    
    with patch('src.llm_summary.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        resumo = gerar_resumo_llm(date="2025-09-17")

        mock_client.chat.completions.create.assert_called_once()

    assert "Resumo simulado da OpenAI" in resumo
    
    report_path = "reports/2025-09-17_BRL_summary.txt"
    assert os.path.exists(report_path)
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Resumo simulado da OpenAI" in content


def test_gerar_resumo_llm_is_idempotent(tmp_path, monkeypatch, caplog):
    """
    Testa se a função é idempotente e não é executada se o ficheiro de relatório já existir.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("reports", exist_ok=True)
    
    date_str = "2025-09-17"
    report_path = f"reports/{date_str}_BRL_summary.txt"
    with open(report_path, "w") as f:
        f.write("Já existe.")

    with patch('src.llm_summary.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        gerar_resumo_llm(date=date_str)

        mock_client.chat.completions.create.assert_not_called()



