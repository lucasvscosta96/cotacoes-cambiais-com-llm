from src.ingest import fetch_exchange_rates
from src.transformation import transform_to_silver
from src.load import save_to_gold
from src.llm_summary import gerar_resumo_llm 

def run_all(date=None, base_currency="BRL", top_n=5):
    """
    Executa o pipeline completo de ingestão, transformação, carga e resumo LLM.

    Args:
        date: Data no formato YYYY-MM-DD (default = hoje)
        base_currency: Moeda base para o resumo LLM
        top_n: Quantidade de moedas principais a incluir no resumo
    """
    print(f"=== Iniciando pipeline para a data: {date or 'hoje'} ===")
    fetch_exchange_rates(date)
    transform_to_silver(date)
    save_to_gold(date)

    print("=== Gerando resumo LLM ===")
    resumo = gerar_resumo_llm(date, base_currency=base_currency, top_n=top_n)
    print(f"=== Resumo LLM ({base_currency}) ===\n{resumo}\n")
    print("=== Pipeline concluído ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Executa pipeline completo de cotações + resumo LLM")
    parser.add_argument("--date", help="Data no formato YYYY-MM-DD", required=False)
    parser.add_argument("--base_currency", default="BRL", help="Moeda base para o resumo LLM")
    parser.add_argument("--top_n", type=int, default=5, help="Quantidade de moedas a incluir no resumo")
    args = parser.parse_args()

    run_all(args.date, base_currency=args.base_currency, top_n=args.top_n)
