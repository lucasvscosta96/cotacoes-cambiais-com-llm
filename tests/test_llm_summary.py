import os
import pandas as pd
from unittest.mock import patch, MagicMock
from src.llm_summary import gerar_resumo_llm

# O teste principal corrigido
def test_llm_summary_creates_file(tmp_path, monkeypatch):
    """
    Testa se a função gerar_resumo_llm cria o arquivo de relatório
    e retorna o conteúdo simulado corretamente.
    """
    # 1. Configurar o ambiente de teste dentro de uma pasta temporária
    monkeypatch.chdir(tmp_path)
    os.makedirs("gold", exist_ok=True)
    
    # 2. Criar um arquivo Parquet de teste
    df = pd.DataFrame({
        "base_currency": ["BRL"], "currency": ["USD"], "rate": [0.2],
    })
    df.to_parquet("gold/2025-09-17.parquet", index=False)
    
    # 3. Criar o objeto de resposta simulada que a nova biblioteca OpenAI retorna
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Resumo simulado da LLM"
    
    # 4. Usar o @patch como um gerenciador de contexto (mais limpo)
    #    O alvo do patch agora é a classe 'OpenAI' que é instanciada no seu código.
    with patch('src.llm_summary.OpenAI') as mock_openai:
        # Fazer a instância do cliente simulado retornar nosso objeto de chat simulado
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Chamar a função que queremos testar
        resumo = gerar_resumo_llm(date="2025-09-17")

        # Verificar se o método simulado foi chamado
        mock_client.chat.completions.create.assert_called_once()

    # 5. Fazer as asserções
    assert "Resumo simulado da LLM" in resumo
    
    # Verificar se o arquivo foi criado
    report_path = "reports/2025-09-17_BRL_summary.txt"
    assert os.path.exists(report_path)
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Resumo simulado da LLM" in content