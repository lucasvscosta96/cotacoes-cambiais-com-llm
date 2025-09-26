# 📊 Cotações Cambiais com LLM: Insights Diários e Automatizados

Este projeto implementa um **pipeline de dados robusto** e **100% automatizado** que transforma dados brutos de cotações cambiais (Dólar, Euro, etc.) em **insights estratégicos diários** usando um Large Language Model (LLM).

O objetivo é fornecer à diretoria e aos gestores um **Dashboard Executivo (Streamlit)** com KPIs em tempo real, gráficos interativos e, o mais importante, um resumo narrativo gerado por IA que traduz os números em decisões de negócio.

---

## ✨ Principais Funcionalidades

- **Pipeline 100% Automatizado:** Coleta, processamento (Parquet) e análise de dados sem intervenção manual.
- **Dashboard Interativo (Streamlit):** Visualização fácil de **KPIs** (cotação e variação percentual) e filtros de período/moeda.
- **Insights com IA:** Geração de um **resumo executivo** em linguagem natural (via LLM) que explica as tendências e o impacto dos movimentos cambiais.
- **Estrutura de Dados Robusta:** Uso de arquivos **Parquet** (`gold/Y-M-D.parquet`) para eficiência e rastreabilidade histórica.

---

## ⚙️ Tecnologias Utilizadas

| Categoria | Tecnologia | Uso Principal |
| :--- | :--- | :--- |
| **Linguagem** | Python | Backend, pipeline de dados e LLM. |
| **Processamento** | Pandas | Manipulação de dados e cálculo de variação. |
| **Armazenamento** | Parquet (via `pyarrow`) | Formato de dados eficiente e versionado na camada Gold (`gold/`). |
| **Visualização** | Streamlit | Criação do Dashboard interativo. |
| **Inteligência** | LLM da OpenAI | Geração do resumo analítico (`reports/`). |

---

## 🚀 Como Executar o Projeto Localmente

Siga estes passos para configurar e executar o dashboard em sua máquina:

### 1. Pré-requisitos e Instalação

Clone o repositório e instale as bibliotecas necessárias.

```bash
# Clone o repositório
git clone [https://github.com/lucasvscosta96/cotacoes-cambiais-com-llm.git](https://github.com/lucasvscosta96/cotacoes-cambiais-com-llm.git)
cd cotacoes-cambiais-com-llm

# Instale as bibliotecas necessárias
pip install -r requirements.txt

# Há duas formas de executar o programa:
1 - python3 run_pipeline.py #Ele fará a ingestão dos dados da data da execução
2 - python3 run_pipeline.py --date <data no formato y-m-d>