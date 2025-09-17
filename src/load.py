import os
import pandas as pd
from datetime import datetime
from src.utils import setup_logging, ensure_dir

def save_to_gold(date=None):
    setup_logging()

    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    silver_path = os.path.join("silver", f"{date}.parquet")
    if not os.path.exists(silver_path):
        raise FileNotFoundError(f"Arquivo {silver_path} não encontrado.")

    df = pd.read_parquet(silver_path)

    # Aqui podemos aplicar ajustes adicionais se necessário (ex: formatação)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    ensure_dir("gold")
    gold_path = os.path.join("gold", f"{date}.parquet")
    df.to_parquet(gold_path, index=False)

    logging.info(f"Dados finais salvos em {gold_path}")
    return df


if __name__ == "__main__":
    save_to_gold()
