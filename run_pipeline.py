from src.ingest import fetch_exchange_rates
from src.transform import transform_to_silver
from src.load import save_to_gold

def run_all(date=None):
    fetch_exchange_rates(date)
    transform_to_silver(date)
    save_to_gold(date)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Data no formato YYYY-MM-DD", required=False)
    args = parser.parse_args()

    run_all(args.date)