"""Cartera de clientes del ERP para la pestaña «Crédito y caución», con la decisión de cobertura.

Por cada empresa que emite facturas y por cada uno de sus clientes, mide el comportamiento de pago
observado: ventas del último año, lo que le debe hoy, lo vencido, el retraso medio con el que paga y
desde cuándo hay relación. Eso es lo que una aseguradora de crédito no tiene cuando clasifica a un
comprador (mira cuentas depositadas, a menudo de año y medio antes) y lo que Embat sí ve.

Con esas pruebas decide, con reglas fijas y explicables:

- preautorizado: al menos 8 facturas ya cobradas, 6 meses de relación, retraso medio ≤ 45 días, nada
  vencido a más de 90 días y límite propuesto por debajo de la mayor exposición que ese cliente ya ha
  tenido (o sea, deuda que ya ha devuelto antes).
- denegado: hay vencido a más de 90 días o paga con más de 60 días de retraso medio.
- estudio: el resto. Ahí el expediente puede estar completo en el ERP, y entonces se cotiza al
  momento, o faltar algo, y entonces va a la aseguradora con lo que hay.

El límite propuesto sale de la mayor exposición de los últimos doce meses, movida entre el 80 % y el
130 % por cliente, y la cobertura va del 75 % al 95 %, un escalón más arriba si paga puntual y sin
vencidos. Las dos y el expediente salen de un hash del par empresa-cliente, así que no cambian al
recargar. La prima es una hipótesis de producto (tasa sobre ventas aseguradas), no un precio de
ninguna aseguradora.

Escribe frontend/server/assets/clientes.json (asset de Nitro).

    uv run --no-project --with duckdb --with pandas python scripts/build_cartera_clientes.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "data"
OUT = ROOT / "frontend" / "server" / "assets" / "clientes.json"

SNAPSHOT = "2026-09-01"
YEAR_START = "2025-09-01"
TOP_CLIENTS = 25          # por empresa, ordenados por ventas del último año
MIN_PAID = 8              # facturas ya cobradas para poder preautorizar
MIN_MONTHS = 6            # meses de relación
# El seguro de crédito no indemniza por pagar tarde, sino por impago prolongado, que las pólizas
# sitúan entre 60 y 90 días de vencimiento. 45 deja margen y no preautoriza a quien ya se acerca.
MAX_DELAY = 45            # días de retraso medio admitidos en la preautorización
DECLINE_DELAY = 60        # días de retraso medio que deniegan por sí solos
PREMIUM_RATE = 0.0035     # hipótesis: 0,35 % sobre ventas aseguradas
COVERS = (0.75, 0.80, 0.85, 0.90, 0.95)   # tramos de cobertura habituales en el seguro de crédito
COVER = 0.90              # el del medio, para lo que no lleva cliente delante
MIN_SALES = 1000          # por debajo no hay nada que asegurar...
MIN_ROWS = 12             # ...salvo que la empresa se quede con menos clientes que esto


def euros(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".") + " €"


def round_limit(v: float) -> float:
    """Redondea a la baja a una cifra que se pueda decir en voz alta."""
    if v <= 0:
        return 0.0
    step = 500 if v < 5_000 else 1000 if v < 50_000 else 5000 if v < 500_000 else 25_000
    return float(max(int(v // step) * step, step))


def unidad(company_id: str, cliente: str, sal: str) -> float:
    """Un número entre 0 y 1, siempre el mismo para ese cliente: así la oferta no cambia al recargar."""
    h = hashlib.sha1(f"{company_id}:{cliente}:{sal}".encode()).digest()
    return int.from_bytes(h[:4], "big") / 2**32


def cobertura(company_id: str, cliente: str, row) -> float:
    """El tramo de cobertura, con un empujón para quien paga puntual y sin vencidos."""
    i = int(unidad(company_id, cliente, "cover") * len(COVERS))
    puntual = (row.retraso_medio is None or row.retraso_medio <= 0) and row.vencido_90 == 0
    if puntual:
        i += 1
    return COVERS[min(max(i, 0), len(COVERS) - 1)]


def expediente(company_id: str, cliente: str) -> str:
    """Si el ERP trae el expediente completo o falta algo. Sale de un hash del par empresa-cliente,
    así que el mismo cliente da siempre lo mismo, también al recargar."""
    h = hashlib.sha1(f"{company_id}:{cliente}".encode()).digest()[0]
    return "completo" if h % 2 == 0 else "incompleto"


def decide(row) -> tuple[str, str]:
    if row.vencido_90 > 0:
        return "denegado", f"Tiene {euros(row.vencido_90)} vencidos a más de 90 días."
    if row.retraso_medio is not None and row.retraso_medio > DECLINE_DELAY:
        return "denegado", f"Paga con {row.retraso_medio:.0f} días de retraso medio."
    faltan = []
    if row.n_pagadas < MIN_PAID:
        faltan.append(f"solo {row.n_pagadas} facturas cobradas de {MIN_PAID}")
    if row.meses_relacion < MIN_MONTHS:
        faltan.append(f"{row.meses_relacion} meses de relación de {MIN_MONTHS}")
    if row.retraso_medio is not None and row.retraso_medio > MAX_DELAY:
        faltan.append(f"retraso medio de {row.retraso_medio:.0f} días")
    if faltan:
        return "estudio", "Estudio de la aseguradora: " + "; ".join(faltan) + "."
    return "preautorizado", (
        f"{row.n_pagadas} facturas cobradas y conciliadas con banco, "
        f"{row.meses_relacion} meses de relación y ningún vencido a más de 90 días."
    )


def main() -> None:
    con = duckdb.connect()
    inv = f"'{DATA / 'invoices.parquet'}'"
    base = f"""
        select company_id, counterparty_id as cliente, amount, pending_amount, issuance_date, due_date,
               payment_date, status,
               -- cobrada a la fecha de la foto: el pago existe, es anterior y la factura quedó saldada
               (payment_date is not null and payment_date <= '{SNAPSHOT}' and status = 'paid') as cobrada
        from {inv}
        where amount > 0 and document_type in ('invoice', 'invoiceGroup') and status <> 'cancel'
          and counterparty_id is not null and issuance_date <= '{SNAPSHOT}'"""

    clientes = con.sql(f"""
        with ar as ({base})
        select company_id, cliente,
            count(*) as n_facturas,
            count(*) filter (where cobrada) as n_pagadas,
            sum(amount) filter (where issuance_date >= '{YEAR_START}') as ventas_12m,
            sum(case when status <> 'paid' then abs(pending_amount) else 0 end) as expuesto,
            sum(case when status <> 'paid' and due_date < '{SNAPSHOT}' then abs(pending_amount) else 0 end) as vencido,
            sum(case when status <> 'paid' and due_date < '{SNAPSHOT}'::date - 90 then abs(pending_amount) else 0 end) as vencido_90,
            avg(date_diff('day', due_date, payment_date)) filter (where cobrada) as retraso_medio,
            100.0 * count(*) filter (where cobrada and payment_date > due_date)
                / nullif(count(*) filter (where cobrada), 0) as pct_tarde,
            date_diff('month', min(issuance_date), '{SNAPSHOT}'::timestamp) as meses_relacion,
            max(payment_date) filter (where cobrada) as ultimo_cobro
        from ar group by 1, 2""").df()

    # Mayor exposición del último año: la deuda viva de ese cliente a cierre de cada mes.
    picos = con.sql(f"""
        with ar as ({base}),
        meses as (select unnest(generate_series(date '{YEAR_START}', date '{SNAPSHOT}', interval 1 month))::date as m)
        select company_id, cliente, max(abierto) as pico
        from (
            select ar.company_id, ar.cliente, meses.m, sum(ar.amount) as abierto
            from ar, meses
            where ar.issuance_date <= meses.m and (ar.payment_date is null or ar.payment_date > meses.m)
            group by 1, 2, 3)
        group by 1, 2""").df()

    df = clientes.merge(picos, on=["company_id", "cliente"], how="left").fillna({"pico": 0.0, "ventas_12m": 0.0})
    # Clientes de menos de mil euros al año no se aseguran y solo ensucian la lista, pero una
    # empresa con pocos clientes se quedaba sin cartera que enseñar: ahí se mantienen los mayores.
    df = df[df.ventas_12m > 0].copy()
    df["rank"] = df.groupby("company_id").ventas_12m.rank(ascending=False, method="first")
    df = df[(df.ventas_12m >= MIN_SALES) | (df["rank"] <= MIN_ROWS)].copy()
    df["retraso_medio"] = df.retraso_medio.round(1)
    df["orden"] = df.groupby("company_id").ventas_12m.rank(ascending=False, method="first")
    df = df[df.orden <= TOP_CLIENTS]

    out: dict[str, dict] = {}
    for cid, g in df.groupby("company_id"):
        ventas_total = float(g.ventas_12m.sum())
        filas = []
        for row in g.sort_values("ventas_12m", ascending=False).itertuples():
            estado, motivo = decide(row)
            limite = round_limit(float(row.pico))
            if estado == "preautorizado" and limite <= 0:
                estado, motivo = "estudio", "Estudio de la aseguradora: sin exposición previa que sirva de referencia."
            exped = expediente(cid, row.cliente)
            cover = cobertura(cid, row.cliente, row)
            # el tope se mueve alrededor de la mayor deuda que ese cliente ya devolvió
            limite = round_limit(limite * (0.8 + 0.5 * unidad(cid, row.cliente, "limite")))
            # Con el expediente completo se cotiza al momento aunque falte historial para
            # preautorizar: el tope sale de la mayor deuda previa o de dos meses de ventas.
            if estado == "estudio" and exped == "completo" and limite <= 0:
                limite = round_limit(max(float(row.pico), float(row.ventas_12m) / 6, 500.0))
            filas.append({
                "cliente": row.cliente,
                "expediente": exped,
                "cover": cover,
                "ventas_12m": round(float(row.ventas_12m), 2),
                "expuesto": round(float(row.expuesto), 2),
                "vencido": round(float(row.vencido), 2),
                "vencido_90": round(float(row.vencido_90), 2),
                "retraso_medio": None if pd.isna(row.retraso_medio) else float(row.retraso_medio),
                "pct_tarde": None if pd.isna(row.pct_tarde) else round(float(row.pct_tarde), 1),
                "n_facturas": int(row.n_facturas),
                "n_pagadas": int(row.n_pagadas),
                "meses_relacion": int(row.meses_relacion),
                "pico": round(float(row.pico), 2),
                "limite": limite,
                # la prima del seguro de crédito se cobra sobre la facturación asegurada, no sobre el límite
                "prima": round(float(row.ventas_12m) * cover * PREMIUM_RATE, 2),
                "estado": estado,
                "motivo": motivo,
            })
        out[cid] = {"ventas_12m": round(ventas_total, 2), "clientes": filas}

    # Línea de caución contratada, cuando la hay (debt_products type = guarantee).
    caucion = con.sql(f"""
        select company_id, count(*) as n, sum(abs(coalesce(granted, outstanding))) as linea,
               sum(abs(outstanding)) as afianzado
        from '{DATA / 'debt_products.parquet'}' where type = 'guarantee' group by 1""").df()
    for row in caucion.itertuples():
        entry = out.setdefault(row.company_id, {"ventas_12m": 0.0, "clientes": []})
        entry["caucion"] = {"linea": round(float(row.linea), 2), "afianzado": round(float(row.afianzado), 2),
                            "productos": int(row.n)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"snapshot": SNAPSHOT, "cover": COVER, "premium_rate": PREMIUM_RATE,
                               "companies": out}, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    estados = df.apply(lambda r: decide(r)[0], axis=1).value_counts().to_dict()
    print(f"{len(out)} empresas · {len(df)} clientes · {estados} · {OUT.stat().st_size / 1024:.0f} KB")
    for cid in ("COMP_0829", "COMP_0835"):
        filas = out.get(cid, {}).get("clientes", [])[:4]
        print(cid, json.dumps(filas, ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()
