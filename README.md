#  Dashboard Contextual de Câmbio com LLM

## Visão Geral: De Dados Brutos a Decisões Acionáveis

Este projeto resolve o desafio de interpretar rapidamente os movimentos do mercado cambial. Em vez de apenas exibir números brutos, ele implementa um pipeline de dados automatizado que utiliza um **Large Language Model (LLM)** para transformar o *snapshot* diário das cotações em **análises executivas de alto valor**.

O Dashboard Streamlit final serve como uma ferramenta de inteligência crucial para a diretoria, fornecendo contexto de risco (Volatilidade) e sugestões de ação.

##  Principais Diferenciais e Valor de Negócio

| Recurso | Valor Entregue | Foco Estratégico | 
| ----- | ----- | ----- | 
| **Análise da LLM por Data** | Resumos em linguagem natural que traduzem números em narrativa estratégica. O usuário pode **navegar pelos relatórios diários** no menu lateral. | **Interpretação** | 
| **KPIs de Contexto** | Compara a cotação de hoje (Base BRL) com a **média dos últimos 7 dias** e exibe o percentual de Força do Real. | **Benchmarking** | 
| **Gráfico de Dispersão (Risco)** | Visualiza a posição da moeda em um quadrante de Risco (**Volatilidade**) vs. Posicionamento (**Delta vs. 7D**), facilitando a identificação de anomalias. | **Mitigação de Risco** | 
| **Pipeline 100% Automatizado** | Coleta de dados e geração de relatórios e Parquet são agendadas via GitHub Actions. | **Eficiência** | 

##  Principais Funcionalidades

- **Pipeline 100% Automatizado:** Coleta, processamento (Parquet) e análise de dados sem intervenção manual.
- **Dashboard Interativo (Streamlit):** Visualização fácil de **KPIs** (cotação e variação percentual) e filtros de período/moeda.
- **Insights com IA:** Geração de um **resumo executivo** em linguagem natural (via LLM) que explica as tendências e o impacto dos movimentos cambiais.
- **Estrutura de Dados Robusta:** Uso de arquivos **Parquet** (`gold/Y-M-D.parquet`) para eficiência e rastreabilidade histórica.

---

##  Arquitetura e Tecnologias

O pipeline de dados segue uma arquitetura robusta de três camadas (`Raw`, `Silver`, `Gold`).

## Estrutura de diretório

```bash
cotacoes-cambiais-com-llm/
├── .github/
│   └── workflows/
│       └── data_pipeline.yml  # Definição do GitHub Action
├── dashboard/
│   └── app.py                 # Aplicação Streamlit (Frontend)
├── src/
│   ├── ingest.py              # Busca dados da API
│   ├── transform.py           # Limpeza/Transformação (Silver)
│   ├── llm_summary.py         # Módulo que chama o LLM
|   ├── load.py                # Carrega os dados da Silver e enriquece para a Gold
|   └──  utils.py              # Configurações gerais do projeto
├── tests/                     # Testes unitários
|   ├── test_ingest.py         # Testa o ingest.py
|   ├── test_llm_summary.py    # Testa o llm_summary
|   ├── test_load.py           # Testa o load
|   └── test_transform.py      # Testa o transform
├── gold/                      # Camada Gold (Dados prontos para consumo: Parquet)
├── raw/                       # Camada Raw (Dados brutos: JSON)
├── reports/                   # Relatórios e análises da LLM (TXT)
├── run_pipeline.py            # Ponto de entrada do pipeline
├── config.yaml                # Arquivo de configuração para API Exchange
└── requirements.txt
```

### Camadas de Dados

| Camada | Conteúdo | Tecnologia | 
| ----- | ----- | ----- | 
| **raw/** | Respostas JSON originais da API (`YYYY-MM-DD.json`). | JSON | 
| **gold/** | Dados consolidados, limpos e otimizados para consumo. Arquivos **Parquet** (`YYYY-MM-DD.parquet`) para performance e rastreabilidade. | Parquet / Pandas | 
| **reports/** | Análises executivas geradas pela LLM (`YYYY-MM-DD_summary.txt`). | Markdown / TXT | 

### Stack de Desenvolvimento

| Categoria | Tecnologia | Uso Principal | 
| :--- | :--- | :--- | 
| **Backend/Pipeline** | Python | Orquestração e processamento | 
| **Processamento/Análise** | Pandas, NumPy | Manipulação de dados e cálculo de variação. | 
| **Visualização/Front-end** | Streamlit, Altair | Criação do Dashboard interativo. | 
| **Inteligência** | LLM (via API - para análise de resumo) | Geração do resumo analítico (`reports/`). | 


## Execução automática

- Esse projeto é executado diáriamente as 23:00 GMT-3 via GithubActions e o executar um Pull Request para a branch main, e publica no dashboard [cotações cambiais com llm no Streamlit](https://cotacoes-cambiais-com-llm-7xnwovurdlh4nrd6vcyg2f.streamlit.app/)


##  Como Executar o Dashboard Localmente

Siga estes passos para configurar e rodar o aplicativo Streamlit.

### 1. Pré-requisitos

- Certifique-se de que você tem o Python instalado
- Necessário uma chave de API da OpenAI
- Necessário uma chave de API do Exchange
- Necessário configura-los como variáveis de ambiente


### 2. Clone do repositório

```bash
git clone https://github.com/lucasvscosta96/cotacoes-cambiais-com-llm.git

cd cotacoes-cambiais-com-llm
```

### 3. Crie o Venv

```bash
python -m venv venv

source venv/bin/activate
```
### 4. Instale as dependencias

```bash
pip install -r requirements.txt
```

### 5. Execute o programa
```bash
python run_pipeline.py
```

### 6. Abra o Streamlit
```bash
streamlit run dashboard/app.py
```