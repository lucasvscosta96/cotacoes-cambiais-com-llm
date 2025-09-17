"""
llm_summary.py

Gera resumos e insights em linguagem natural (Português) para um dataset diário de cotações cambiais
usando um LLM (ex.: OpenAI ChatGPT). Projetado para o pipeline do curso "Python Programming for Data Engineers".

Principais responsabilidades:
- Ler dataset final (parquet / DataFrame) do pipeline /silver ou /gold
- Calcular estatísticas simples (variação percentual em relação ao dia anterior, ranking, volatilidade simples)
- Gerar prompt com contexto reduzido (top N moedas) e enviar ao LLM
- Salvar o resumo gerado (arquivo JSON/MD) em /gold/llm_summaries/YYYY-MM-DD.json
- Opções de linha de comando para integração com orquestrações

Uso (exemplo):
    python llm_summary.py \
      --input-parquet gold/rates_2025-09-17.parquet \
      --previous-parquet gold/rates_2025-09-16.parquet \
      --outdir gold/llm_summaries \
      --base-currency BRL \
      --top-n 5

Dependências (recomendado):
    pandas, pyarrow, requests (opcional), openai (opcional), python-dotenv (opcional para .env)

Configurações via env:
    LLM_PROVIDER=openai
    OPENAI_API_KEY=...
    OPENAI_MODEL=gpt-4o
    LOG_PROMPTS=true/false  # opcional para auditoria (use com cuidado)

Autor: Template para projeto final do MBA
"""

from __future__ import annotations
import requests
import os
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd

try:
    import openai
except Exception:
    openai = None

# ---------- Config / Logging ----------

LOG_LEVEL = os.environ.get("LLM_SUMMARY_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("llm_summary")

# ---------- Helpers ----------

REQUIRED_COLUMNS = {"base_currency", "currency", "rate", "date"}


def load_parquet(path: str) -> pd.DataFrame:
    logger.info("Carregando parquet: %s", path)
    df = pd.read_parquet(path)
    df.columns = [c.lower() for c in df.columns]

    if not REQUIRED_COLUMNS.issubset(set(df.columns)):
        missing = REQUIRED_COLUMNS - set(df.columns)
        raise ValueError(f"Arquivo faltando colunas obrigatórias: {missing}")

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    return df


def validate_rates(df: pd.DataFrame, drop_invalid: bool = True) -> pd.DataFrame:
    bad = df[~df["rate"].notna() | (df["rate"] <= 0)]
    if not bad.empty:
        logger.warning("Encontradas %s taxas nulas/negativas", len(bad))
        if drop_invalid:
            df = df.drop(bad.index)
        else:
            raise ValueError("Taxas com valores nulos ou negativos detectadas")
    return df


def compute_stats(
    df_today: pd.DataFrame,
    df_prev: Optional[pd.DataFrame] = None,
    base_currency: str = "BRL",
    top_n: int = 5,
) -> pd.DataFrame:
    logger.info("Computando estatísticas para base %s", base_currency)
    today = df_today[df_today["base_currency"] == base_currency].copy()
    if today.empty:
        raise ValueError(f"Nenhum dado encontrado para base_currency={base_currency} no dataset de hoje")
    today = today[["currency", "rate"]].set_index("currency")

    if df_prev is not None:
        prev = (
            df_prev[df_prev["base_currency"] == base_currency][["currency", "rate"]]
            .set_index("currency")
            .rename(columns={"rate": "prev_rate"})
        )
        merged = today.join(prev, how="left")
        merged["prev_rate"] = merged["prev_rate"].astype(float)
        merged["rate"] = merged["rate"].astype(float)
        merged["pct_change"] = (
            (merged["rate"] - merged["prev_rate"]) / merged["prev_rate"] * 100
        )
    else:
        merged = today.rename(columns={"rate": "rate"})
        merged["prev_rate"] = pd.NA
        merged["pct_change"] = pd.NA

    merged = merged.reset_index()
    merged = merged.sort_values(by="pct_change", ascending=False, na_position="last")
    top = merged.head(top_n).copy()
    top["rate"] = top["rate"].round(6)
    if "pct_change" in top.columns:
        top["pct_change"] = top["pct_change"].round(3)
    return top


def _render_markdown_table(df: pd.DataFrame) -> str:
    display_cols = [c for c in ["currency", "rate", "prev_rate", "pct_change"] if c in df.columns]
    lines = []
    header = " | ".join(display_cols)
    sep = " | ".join(["---"] * len(display_cols))
    lines.append(header)
    lines.append(sep)
    for _, row in df.iterrows():
        values = []
        for c in display_cols:
            v = row.get(c)
            if pd.isna(v):
                values.append("")
            else:
                values.append(str(v))
        lines.append(" | ".join(values))
    return "\n".join(lines)

# ---------- Prompt building ----------

PROMPT_TEMPLATE = (
    "Você é um analista financeiro sênior. Dado o contexto abaixo, gere um resumo executivo curto em PORTUGUÊS "
    "direcionado a um público de negócios (diretor financeiro / gerente). Inclua: 1) resumo da tendência "
    "(apreciação/depreciação das moedas frente à {base_currency}), 2) destaque 3 riscos/observações, "
    "3) 3 recomendações de atenção/monitoramento e 4) uma curta explicação técnica para analistas (máx 3 linhas).\n\n"
    "Contexto: Data do arquivo = {date}\n\nTop {top_n} moedas vs {base_currency}:\n{table}\n\n"
    "Dados adicionais: {extra_context}\n\nResponda em português. Seja direto e use linguagem clara para executivos. "
    "Faça bullets quando fizer sentido."
)


def build_prompt(
    top_df: pd.DataFrame,
    date: datetime | str,
    base_currency: str = "BRL",
    top_n: int = 5,
    extra_context: str = "",
) -> str:
    date_str = date if isinstance(date, str) else date.strftime("%Y-%m-%d")
    table = _render_markdown_table(top_df)
    prompt = PROMPT_TEMPLATE.format(base_currency=base_currency, date=date_str, top_n=top_n, table=table, extra_context=extra_context)
    return prompt

# ---------- LLM calling ----------


def call_openai_chat(
    prompt: str,
    model: str,
    api_key: str,
    api_base: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 400,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> Dict[str, Any]:
    if api_key is None:
        raise ValueError("OPENAI_API_KEY is required for provider=openai")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    if openai is not None:
        openai.api_key = api_key
        if api_base:
            openai.api_base = api_base

        for attempt in range(1, retries + 1):
            try:
                resp = openai.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "system", "content": "Você é um assistente especialista em finanças."}, {"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = resp["choices"][0]["message"]["content"].strip()
                return {"text": text, "raw_response": resp}
            except Exception as e:
                logger.exception("Erro ao chamar openai (attempt %s/%s): %s", attempt, retries, e)
                if attempt < retries:
                    time.sleep(retry_delay * attempt)
                else:
                    raise

    url = (api_base.rstrip("/") + "/v1/chat/completions") if api_base else "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": "Você é um assistente especialista em finanças."}, {"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(1, retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            resp = r.json()
            text = resp["choices"][0]["message"]["content"].strip()
            return {"text": text, "raw_response": resp}
        except Exception as e:
            logger.exception("Erro HTTP ao chamar OpenAI (attempt %s/%s): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(retry_delay * attempt)
            else:
                raise


def call_llm(
    prompt: str,
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    provider = provider.lower()
    if provider == "openai":
        model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        api_base = api_base or os.environ.get("OPENAI_API_BASE")
        return call_openai_chat(prompt, model=model, api_key=api_key, api_base=api_base, **kwargs)
    else:
        raise NotImplementedError(f"Provider {provider} não é suportado nesta versão")

# ---------- Persistence ----------


def save_summary(
    outdir: str,
    date: datetime | str,
    prompt: str,
    llm_result: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    os.makedirs(outdir, exist_ok=True)
    date_str = date if isinstance(date, str) else date.strftime("%Y-%m-%d")
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"llm_summary_{date_str}_{timestamp}.json"
    path = os.path.join(outdir, filename)

    payload = {
        "date": date_str,
        "created_at_utc": timestamp,
        "prompt": prompt if os.environ.get("LOG_PROMPTS", "false").lower() == "true" else "<hidden>",
        "response_text": llm_result.get("text"),
        "raw_response": llm_result.get("raw_response"),
        "meta": meta or {},
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("Resumo salvo em %s", path)
    return path

# ---------- Função auxiliar para testes ----------


def gerar_resumo_llm(date_str: str, base_currency: str = "BRL", top_n: int = 5) -> str:
    parquet_path = os.path.join("gold", f"{date_str}.parquet")
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {parquet_path}")

    df_today = load_parquet(parquet_path)
    df_today = validate_rates(df_today)
    top_df = compute_stats(df_today, base_currency=base_currency, top_n=top_n)
    prompt = build_prompt(top_df, date_str, base_currency=base_currency, top_n=top_n)
    llm_result = call_llm(prompt)

    os.makedirs("reports", exist_ok=True)
    out_path = os.path.join("reports", f"{date_str}_summary.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(llm_result.get("text", ""))

    return llm_result.get("text", "")

# ---------- CLI / Orquestração ----------


def main():
    parser = argparse.ArgumentParser(description="Gerar resumo LLM para cotações cambiais")
    parser.add_argument("--input-parquet", required=True, help="Parquet do dia atual com colunas base_currency,currency,rate,date")
    parser.add_argument("--previous-parquet", required=False, help="Parquet do dia anterior (opcional) para calcula pct_change")
    parser.add_argument("--outdir", default="gold/llm_summaries", help="Diretório de saída")
    parser.add_argument("--base-currency", default="BRL", help="Moeda base para o resumo (ex: BRL)")
    parser.add_argument("--top-n", default=5, type=int, help="Quantidade de moedas a enviar no prompt")
    parser.add_argument("--model", default=None, help="Modelo LLM (vai usar OPENAI_MODEL se não informado)")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "openai"), help="Provider do LLM (default=openai)")
    args = parser.parse_args()

    df_today = load_parquet(args.input_parquet)
    df_today = validate_rates(df_today)

    df_prev = None
    if args.previous_parquet:
        df_prev = load_parquet(args.previous_parquet)
        df_prev = validate_rates(df_prev)

    top_df = compute_stats(df_today, df_prev=df_prev, base_currency=args.base_currency, top_n=args.top_n)
    date_val = df_today["date"].iloc[0]
    prompt = build_prompt(top_df, date_val, base_currency=args.base_currency, top_n=args.top_n)
    logger.info("Prompt pronto. Chamando LLM provider=%s model=%s", args.provider, args.model or os.environ.get("OPENAI_MODEL"))
    llm_result = call_llm(prompt, provider=args.provider, model=args.model)

    meta = {
        "provider": args.provider,
        "model": args.model or os.environ.get("OPENAI_MODEL"),
        "input_parquet": args.input_parquet,
        "previous_parquet": args.previous_parquet,
    }
    out_path = save_summary(args.outdir, date_val, prompt, llm_result, meta=meta)

    md_path = out_path.replace(".json", ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Resumo LLM - " + str(date_val) + "\n\n")
        f.write(llm_result.get("text", ""))

    logger.info("Resumo MD salvo em %s", md_path)