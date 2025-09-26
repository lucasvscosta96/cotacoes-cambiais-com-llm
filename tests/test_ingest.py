import os
import json
from unittest.mock import patch, MagicMock
import pytest
import requests
from src.ingest import fetch_exchange_rates

def test_ingest_creates_raw_file(monkeypatch, tmp_path):
    """
    Testa se a função fetch_exchange_rates cria o ficheiro raw corretamente,
    simulando as variáveis de ambiente e a resposta da API.
    """
    monkeypatch.chdir(tmp_path)

    monkeypatch.setenv("EXCHANGE_API_KEY", "fake_api_key_for_testing")

    mock_response_data = {
        "result": "success",
        "base_code": "BRL",
        "conversion_rates": {"USD": 0.19, "EUR": 0.18}
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response) as mock_get:
        date = "2025-09-17"

        config_content = "api_url: https://fakeapi.com/v6\nbase_currency: BRL"
        with open("config.yaml", "w") as f:
            f.write(config_content)

        fetch_exchange_rates(date)

        expected_url = "https://fakeapi.com/v6/fake_api_key_for_testing/latest/BRL"
        mock_get.assert_called_once_with(expected_url)

        output_path = os.path.join("raw", f"{date}.json")
        assert os.path.exists(output_path)
        with open(output_path, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == mock_response_data


def test_fetch_exchange_rates_api_error(monkeypatch, tmp_path):
    """
    Testa se a função fetch_exchange_rates levanta uma exceção
    quando a API retorna um erro de status.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EXCHANGE_API_KEY", "fake_api_key_for_testing")
    config_content = "api_url: https://fakeapi.com/v6\nbase_currency: BRL"
    with open("config.yaml", "w") as f:
        f.write(config_content)

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")

    with patch('requests.get', return_value=mock_response):
        with pytest.raises(requests.exceptions.RequestException):
            fetch_exchange_rates("2025-09-17")

