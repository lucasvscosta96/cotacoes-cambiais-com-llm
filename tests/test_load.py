import pandas as pd
import os
import pytest
from src.load import save_to_gold
from datetime import datetime, timedelta

def test_save_to_gold_calculates_daily_change(tmp_path, monkeypatch):
    """
    Testa se a função save_to_gold cria o ficheiro gold, enriquecido
    com a coluna de variação percentual diária calculada corretamente.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("silver", exist_ok=True)


    date_yesterday_str = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    df_yesterday = pd.DataFrame({
        "currency": ["USD", "EUR"],
        "rate": [5.0, 6.0] 
    })
    df_yesterday.to_parquet(f"silver/{date_yesterday_str}.parquet")

    date_today_str = datetime.today().strftime("%Y-%m-%d")
    df_today = pd.DataFrame({
        "currency": ["USD", "EUR"],
        "rate": [5.5, 5.7] # Cotação de hoje (USD subiu 10%, EUR desceu 5%)
    })
    df_today.to_parquet(f"silver/{date_today_str}.parquet")

    # --- Execução ---
    save_to_gold(date=date_today_str)

    # --- Verificação ---
    gold_path = f"gold/{date_today_str}.parquet"
    assert os.path.exists(gold_path)

    df_result = pd.read_parquet(gold_path)
    
    # Verificar se a nova coluna existe
    assert "daily_change_pct" in df_result.columns

    # Verificar os cálculos da variação percentual (ajustado para esperar valor percentual, ex: 10.0 para 10%)
    # Para o USD: (5.5 - 5.0) / 5.0 * 100 = 10.0
    # Para o EUR: (5.7 - 6.0) / 6.0 * 100 = -5.0
    usd_change = df_result[df_result["currency"] == "USD"]["daily_change_pct"].iloc[0]
    eur_change = df_result[df_result["currency"] == "EUR"]["daily_change_pct"].iloc[0]
    
    assert pytest.approx(usd_change) == 10.0
    assert pytest.approx(eur_change) == -5.0


def test_save_to_gold_first_day(tmp_path, monkeypatch):
    """
    Testa o comportamento da função no primeiro dia de execução,
    quando não há dados do dia anterior para comparar.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("silver", exist_ok=True)

    # Criar dados apenas para o dia atual
    date_today_str = datetime.today().strftime("%Y-%m-%d")
    df_today = pd.DataFrame({"currency": ["USD"], "rate": [5.5]})
    df_today.to_parquet(f"silver/{date_today_str}.parquet")

    save_to_gold(date=date_today_str)

    # Verificar que o ficheiro foi criado
    gold_path = f"gold/{date_today_str}.parquet"
    assert os.path.exists(gold_path)

    # Verificar que a coluna de variação existe e contém 0.0 (em vez de NaN)
    df_result = pd.read_parquet(gold_path)
    assert "daily_change_pct" in df_result.columns
    assert df_result["daily_change_pct"].iloc[0] == 0.0


def test_save_to_gold_no_silver_file(tmp_path, monkeypatch):
    """
    Testa se a função levanta um erro FileNotFoundError se o ficheiro silver não existir.
    """
    monkeypatch.chdir(tmp_path)
    date_str = "2025-09-17"
    
    with pytest.raises(FileNotFoundError) as excinfo:
        save_to_gold(date=date_str)

    assert "Arquivo silver não encontrado" in str(excinfo.value)

