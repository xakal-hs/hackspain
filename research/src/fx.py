"""Tipos de cambio reales descargados de internet (D03).

Fuentes:
1. BCE, tipos de referencia diarios (oficiales): https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip
2. fawazahmed0/currency-api vía jsdelivr para monedas que el BCE no publica (ARS, CLP, COP, AOA, MZN...):
   https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{fecha}/v1/currencies/eur.json

Salida: data/fx/fx_monthly.parquet con (month, currency, per_eur) = unidades de moneda por 1 EUR, media mensual.
"""
from __future__ import annotations
import io, json, zipfile, urllib.request
from pathlib import Path
import pandas as pd

FX_DIR = Path(__file__).resolve().parents[1] / "data" / "fx"
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{d}/v1/currencies/eur.json"
MONTHS = pd.date_range("2024-09-01", "2026-09-01", freq="MS")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "xray-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def ecb_monthly() -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(_get(ECB_URL)))
    df = pd.read_csv(z.open(z.namelist()[0]), na_values=["N/A"]).dropna(axis=1, how="all")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df[df.Date >= "2024-09-01"].set_index("Date")
    m = df.resample("MS").mean().stack().rename("per_eur").reset_index()
    m.columns = ["month", "currency", "per_eur"]
    return m.assign(source="BCE")


def api_monthly(currencies: list[str]) -> pd.DataFrame:
    rows = []
    for mo in MONTHS:
        vals = []
        for day in (1, 15):  # dos muestras por mes para aproximar la media mensual
            d = mo.replace(day=day)
            if d > pd.Timestamp("2026-09-18"):
                continue
            try:
                data = json.loads(_get(API_URL.format(d=d.date())))["eur"]
                vals.append({c: data.get(c.lower()) for c in currencies})
            except Exception as e:  # fecha no publicada: se ignora esa muestra
                print("fx api sin dato", d.date(), e)
        for c in currencies:
            v = [x[c] for x in vals if x.get(c)]
            if v:
                rows.append({"month": mo, "currency": c, "per_eur": sum(v) / len(v), "source": "currency-api"})
    return pd.DataFrame(rows)


def build(currencies: list[str]) -> pd.DataFrame:
    FX_DIR.mkdir(parents=True, exist_ok=True)
    ecb = ecb_monthly()
    missing = sorted(set(currencies) - set(ecb.currency) - {"EUR"})
    api = api_monthly(missing) if missing else pd.DataFrame(columns=ecb.columns)
    eur = pd.DataFrame({"month": MONTHS, "currency": "EUR", "per_eur": 1.0, "source": "identidad"})
    fx = pd.concat([ecb, api, eur], ignore_index=True)
    fx.to_parquet(FX_DIR / "fx_monthly.parquet")
    return fx


def load() -> pd.DataFrame:
    return pd.read_parquet(FX_DIR / "fx_monthly.parquet")


if __name__ == "__main__":
    import polars as pl
    data = Path(__file__).resolve().parents[1] / "data"
    cur = set(pl.read_parquet(data / "companies.parquet")["currency"].drop_nulls())
    cur |= set(pl.read_parquet(data / "banking_products.parquet")["currency"].drop_nulls())
    cur |= set(pl.read_parquet(data / "debt_products.parquet")["currency"].drop_nulls())
    fx = build(sorted(cur))
    print(fx.groupby("source").currency.nunique())
    print("monedas sin tipo:", sorted(cur - set(fx.currency)))
