import argparse
from datetime import datetime
from src.ingest import fetch_exchange_rates
from src.transformation import transform_to_silver
from src.load import save_to_gold
from src.llm_summary import gerar_resumo_llm

def run_all(date=None, top_n=5):
    """
    Executa o pipeline completo de ingestão, transformação, carga e resumo LLM.
    A moeda base é lida a partir do config.yaml nas etapas relevantes.
    """
    # Corrigir a lógica para usar a data do argumento se ela for fornecida
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")
    
    print(f"=== Iniciando pipeline para a data: {date} ===")
   
    fetch_exchange_rates(date)
    transform_to_silver(date)
    save_to_gold(date)

    print("\n=== Gerando resumo LLM ===")
    # Chamada corrigida: remover base_currency, pois é lido do config.yaml
    gerar_resumo_llm(date=date, top_n=top_n)
    
    print("\n=== Pipeline concluído com sucesso! ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa pipeline completo de cotações + resumo LLM")
    parser.add_argument("--date", help="Data no formato YYYY-MM-DD", required=False)
    # Argumento base_currency removido, pois a configuração é centralizada
    parser.add_argument("--top_n", type=int, default=5, help="Quantidade de moedas a incluir no resumo")
    args = parser.parse_args()

    # Chamada corrigida: remover base_currency
    run_all(date=args.date, top_n=args.top_n)
