import os
import json
from unittest.mock import patch, MagicMock
from src.ingest import fetch_exchange_rates

def test_ingest_creates_raw_file(monkeypatch, tmp_path):
    """
    Testa se a função fetch_exchange_rates cria o ficheiro raw corretamente,
    simulando as variáveis de ambiente e a resposta da API.
    """
    # 1. Mudar para um diretório temporário para não criar ficheiros no projeto
    monkeypatch.chdir(tmp_path)

    # 2. Simular a variável de ambiente da API Key
    #    Esta é a correção principal: o monkeypatch cria a variável
    #    necessária para o teste passar.
    monkeypatch.setenv("EXCHANGE_RATE_API_KEY", "fake_api_key_for_testing")

    # 3. Preparar uma resposta simulada (mock) da API
    mock_response_data = {
        "result": "success",
        "base_code": "BRL",
        "conversion_rates": {"USD": 0.19, "EUR": 0.18}
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    
    # 4. Usar o patch para intercetar a chamada `requests.get`
    with patch('requests.get', return_value=mock_response) as mock_get:
        date = "2025-09-17"
        
        # Como o código de ingestão lê um config.yaml, vamos criá-lo para o teste
        config_content = "api_url: https://v6.exchangerate-api.com/v6\nbase_currency: BRL"
        with open("config.yaml", "w") as f:
            f.write(config_content)
            
        fetch_exchange_rates(date)

        # 5. Verificar se a função foi chamada com o URL correto
        expected_url = "https://v6.exchangerate-api.com/v6/fake_api_key_for_testing/latest/BRL"
        mock_get.assert_called_once_with(expected_url)

        # 6. Verificar se o ficheiro raw foi criado
        expected_file = tmp_path / "raw" / f"{date}.json"
        assert expected_file.exists()

        # 7. Verificar se o conteúdo do ficheiro está correto
        with open(expected_file, 'r') as f:
            content = json.load(f)
            assert content["base_code"] == "BRL"
            assert content["conversion_rates"]["USD"] == 0.19

