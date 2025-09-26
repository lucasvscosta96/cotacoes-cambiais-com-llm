from src.ingest import fetch_exchange_rates
from src.transformation import transform_to_silver
from src.load import save_to_gold
from src.llm_summary import gerar_resumo_llm 
from datetime import datetime

def run_all(date=None, base_currency="BRL", top_n=5):
    """
    Executa o pipeline completo de ingestão, transformação, carga e resumo LLM.
    """
    # MUDANÇA: Corrigimos a lógica para usar a data do argumento se ela for fornecida
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")
    
    print(f"=== Iniciando pipeline para a data: {date} ===")
   
    fetch_exchange_rates(date)
    transform_to_silver(date)
    save_to_gold(date)

    print("\n=== Gerando resumo LLM ===")
    resumo = gerar_resumo_llm(date=date, base_currency=base_currency, top_n=top_n)
    
    print(f"\n--- Resumo Executivo ({base_currency} | {date}) ---")
    print(resumo)
    print("------------------------------------------")
    
    print("\n=== Pipeline concluído com sucesso! ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Executa pipeline completo de cotações + resumo LLM")
    parser.add_argument("--date", help="Data no formato YYYY-MM-DD", required=False)
    parser.add_argument("--base_currency", default="BRL", help="Moeda base para o resumo LLM")
    parser.add_argument("--top_n", type=int, default=5, help="Quantidade de moedas a incluir no resumo")
    args = parser.parse_args()

    run_all(date=args.date, base_currency=args.base_currency, top_n=args.top_n)