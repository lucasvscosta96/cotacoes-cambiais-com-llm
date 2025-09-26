import pandas as pd
import os
import logging
from datetime import datetime, timedelta
from src.utils import ensure_dir, setup_logging

def save_to_gold(date=None):
    """
    Carrega os dados da camada silver e os enriquece com a variação
    percentual diária antes de salvar na camada gold.
    """
    setup_logging()
    
    # Carregar dados da camada silver para a data atual
    silver_path = os.path.join("silver", f"{date}.parquet")
    if not os.path.exists(silver_path):
        raise FileNotFoundError(f"Arquivo silver não encontrado para a data {date}")

    df_today = pd.read_parquet(silver_path)

    # Calcular a data do dia anterior
    current_date_obj = datetime.strptime(date, "%Y-%m-%d")
    previous_date_obj = current_date_obj - timedelta(days=1)
    previous_date_str = previous_date_obj.strftime("%Y-%m-%d")
    
    previous_silver_path = os.path.join("silver", f"{previous_date_str}.parquet")

    if os.path.exists(previous_silver_path):
        logging.info(f"Dados do dia anterior ({previous_date_str}) encontrados. Calculando a variação percentual.")
        df_yesterday = pd.read_parquet(previous_silver_path)
        
        df_yesterday = df_yesterday[['currency', 'rate']].rename(columns={'rate': 'rate_yesterday'})
        
        df_gold = pd.merge(df_today, df_yesterday, on='currency', how='left')
        
        df_gold['daily_change_pct'] = ((df_gold['rate'] - df_gold['rate_yesterday']) / df_gold['rate_yesterday']) * 100
        
        df_gold['daily_change_pct'] = df_gold['daily_change_pct'].fillna(0.0)
        
        df_gold = df_gold.drop(columns=['rate_yesterday'])
        
    else:
        logging.warning(f"Dados do dia anterior ({previous_date_str}) não encontrados. A variação diária será definida como 0.")
        df_gold = df_today.copy()
        df_gold['daily_change_pct'] = 0.0

    # Salvar na camada gold
    ensure_dir("gold")
    gold_path = os.path.join("gold", f"{date}.parquet")
    df_gold.to_parquet(gold_path, index=False)
    logging.info(f"Dados enriquecidos da camada gold salvos com sucesso em {gold_path}")



if __name__ == "__main__":
    save_to_gold()
