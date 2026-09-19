"""Tipos de cambio reales (D03), en cuatro capas de menos a más aproximada.

1. BCE, tipos de referencia diarios (oficiales): eurofxref-hist.zip.
   Se descarga de la web y, si la red lo bloquea, se lee el MISMO fichero empaquetado dentro
   del paquete `currencyconverter` de PyPI. No es una aproximación: es el mismo CSV del BCE.
   Cubre 26 de las 39 monedas del dataset y el 91 % de las transacciones en divisa.
2. fawazahmed0/currency-api vía jsdelivr, para las monedas que el BCE no publica
   (ARS, CLP, COP, AOA, MZN...). Requiere red; si no hay, se salta.
3. Paridades fijas oficiales (PEGS), para monedas que no flotan. Son exactas por construcción,
   no estimaciones: franco CFA y marco convertible están fijados por ley al euro, el dírham
   al dólar desde 1997 y el dólar namibio va 1:1 con el rand.
4. Mediana de los `exchange_rate` del propio dataset, encadenada desde EUR, para lo que quede.
   Último recurso y claramente marcado: sirve sobre todo para detectar los tipos basura del
   dataset (fx=1 o 0), que es para lo que panel.py usa esta tabla.

La columna `source` dice de qué capa sale cada tipo, para poder auditarlo.

Salida: data/fx/fx_monthly.parquet con (month, currency, per_eur) = unidades de moneda por 1 EUR,
media mensual.
"""
from __future__ import annotations
import io, json, zipfile, urllib.request
from pathlib import Path
import pandas as pd

FX_DIR = Path(__file__).resolve().parents[1] / "data" / "fx"
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{d}/v1/currencies/eur.json"
MONTHS = pd.date_range("2024-09-01", "2026-09-01", freq="MS")

# Paridades fijas oficiales, para monedas que el BCE no publica y que no flotan.
# No son estimaciones: están fijadas por ley o por régimen cambiario declarado.
PEG_EUR = {
    "XOF": 655.957,    # franco CFA de África Occidental, fijado al euro
    "BAM": 1.95583,    # marco convertible de Bosnia, currency board contra el euro
}
PEG_TO = {
    "AED": ("USD", 3.6725),   # dírham, anclado al dólar desde 1997
    "NAD": ("ZAR", 1.0),      # dólar namibio, a la par con el rand (sí publicado por el BCE)
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "xray-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _ecb_zip() -> bytes:
    """El histórico del BCE, de la web o del que empaqueta currencyconverter (el mismo fichero).

    El paquete `currencyconverter` de PyPI incluye `eurofxref-hist.zip` tal cual lo publica el
    BCE, así que en una máquina sin salida a la web del BCE seguimos usando tipos oficiales en
    lugar de inventarlos. Si tampoco está el paquete, se propaga el error de red original.
    """
    try:
        return _get(ECB_URL)
    except Exception as err:
        try:
            import currency_converter
        except ImportError:
            raise err
        p = Path(currency_converter.__file__).parent / "eurofxref-hist.zip"
        if not p.exists():
            raise err
        print(f"BCE inaccesible ({err}); uso el histórico empaquetado en currencyconverter: {p}")
        return p.read_bytes()


def ecb_monthly() -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(_ecb_zip()))
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


def peg_monthly(currencies: list[str], have: pd.DataFrame) -> pd.DataFrame:
    """Capa 3: monedas con paridad fija. Exactas, no aproximadas."""
    rows = []
    base = {(r.month, r.currency): r.per_eur for r in have.itertuples()}
    for c in currencies:
        if c in PEG_EUR:
            rows += [{"month": m, "currency": c, "per_eur": PEG_EUR[c], "source": "paridad fija"} for m in MONTHS]
        elif c in PEG_TO:
            anchor, rate = PEG_TO[c]
            for m in MONTHS:
                a = base.get((m, anchor))
                if a:  # per_eur[c] = per_eur[ancla] * (unidades de c por unidad de ancla)
                    rows.append({"month": m, "currency": c, "per_eur": a * rate, "source": f"paridad fija ({anchor})"})
    return pd.DataFrame(rows)


def dataset_monthly(currencies: list[str]) -> pd.DataFrame:
    """Capa 4, último recurso: mediana de los `exchange_rate` del dataset, encadenada desde EUR.

    Sólo para monedas que no cubren ni el BCE, ni currency-api, ni una paridad fija. El tipo sale
    de las propias operaciones, así que no vale para auditar el dataset contra la realidad; sirve
    para lo que panel.py necesita, que es detectar los tipos imposibles (fx=1 o 0) comparando cada
    operación con la mediana de su moneda y mes.
    """
    import polars as pl
    data = Path(__file__).resolve().parents[1] / "data"
    if not (data / "transactions.parquet").exists():
        return pd.DataFrame(columns=["month", "currency", "per_eur", "source"])
    pr = pl.concat([pl.read_parquet(data / f"{n}.parquet").select("product_id", "currency")
                    for n in ("banking_products", "debt_products")]).rename({"currency": "pcur"})
    comp = pl.read_parquet(data / "companies.parquet").select("company_id", pl.col("currency").alias("ccur"))
    x = (pl.read_parquet(data / "transactions.parquet").join(pr, on="product_id", how="left")
           .join(comp, on="company_id", how="left")
           .with_columns(month=pl.col("date").dt.truncate("1mo"))
           .filter(pl.col("pcur").is_not_null() & pl.col("ccur").is_not_null()
                   & (pl.col("pcur") != pl.col("ccur")) & (pl.col("exchange_rate") > 0)))
    med = (x.group_by("month", "pcur", "ccur").agg(r=pl.col("exchange_rate").median(), n=pl.len())
            .filter(pl.col("n") >= 3).to_pandas())
    rows = []
    for m in MONTHS:
        mm, per = med[med.month == m], {"EUR": 1.0}
        for _ in range(6):  # encadena EUR -> pares directos -> indirectos
            for e in mm.itertuples():
                if e.ccur in per and e.pcur not in per:
                    per[e.pcur] = per[e.ccur] * float(e.r)
                elif e.pcur in per and e.ccur not in per and e.r > 0:
                    per[e.ccur] = per[e.pcur] / float(e.r)
        # per_eur == 1 exacto en una moneda que no es el euro no es un tipo: es el valor centinela
        # del propio bug (MZN lo trae en el 99,9 % de sus operaciones). Publicarlo sería peor que
        # no tener nada, porque panel.py compara cada operación contra esta tabla y daría por
        # bueno el tipo basura en vez de marcarlo como no verificado.
        rows += [{"month": m, "currency": c, "per_eur": v, "source": "mediana del dataset"}
                 for c, v in per.items() if c in currencies and v > 0 and abs(v - 1) > 1e-3]
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # rellena meses sueltos: en 2 años estos tipos no se mueven tanto como para dejar huecos
    full = []
    for c, g in out.groupby("currency"):
        v = g.set_index("month").per_eur.reindex(MONTHS).ffill().bfill()
        full.append(pd.DataFrame({"month": MONTHS, "currency": c, "per_eur": v.to_numpy(),
                                  "source": "mediana del dataset"}))
    return pd.concat(full, ignore_index=True).dropna(subset=["per_eur"])


def build(currencies: list[str]) -> pd.DataFrame:
    FX_DIR.mkdir(parents=True, exist_ok=True)
    eur = pd.DataFrame({"month": MONTHS, "currency": "EUR", "per_eur": 1.0, "source": "identidad"})
    fx = pd.concat([ecb_monthly(), eur], ignore_index=True)

    def pending():
        return sorted(set(currencies) - set(fx.currency))

    if pending():  # capa 2: currency-api (necesita red)
        try:
            api = api_monthly(pending())
            if len(api):
                fx = pd.concat([fx, api], ignore_index=True)
        except Exception as err:
            print(f"currency-api inaccesible ({err}); sigo con paridades fijas y dataset")
    if pending():  # capa 3: paridades fijas
        peg = peg_monthly(pending(), fx)
        if len(peg):
            fx = pd.concat([fx, peg], ignore_index=True)
    if pending():  # capa 4: mediana del dataset
        ds = dataset_monthly(pending())
        if len(ds):
            fx = pd.concat([fx, ds], ignore_index=True)

    fx = fx[fx.currency.isin(currencies) | (fx.currency == "EUR")].reset_index(drop=True)
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
