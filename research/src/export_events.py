"""Exporta los eventos v2 a un formato que la SPA pueda leer sin recalcular nada.

    cd research && uv run python src/export_events.py

Entrada : data/panel.parquet (lo genera src/panel.py)
Salidas : data/events_export.parquet  -> una fila por empresa-mes con algún evento activo
          reports/eventos_export.json -> resumen del último mes, tasas a 6 meses y catálogo divulgativo

Qué se exporta y por qué esas columnas y no otras (las definiciones viven en events_v2.py):

  E1_clean        tensión de caja en los próximos 6 meses, quitando los arranques que sólo
                  ocurren porque el grupo mueve la tesorería (cash pooling).
  E2_strict       impago de una obligación recurrente: dos meses seguidos sin nómina o sin cuota
                  con el feed vivo, o dos trimestres sin IVA. Sin el componente AP>90d, que era
                  circular respecto al riesgo que queremos anticipar.
  E3              caída estructural de cobros (mediana futura < 50 % de la base) sin rebote.
  E4              expansión sostenida y autofinanciada.
  E5_bache        bache de cobros de un mes del que la empresa ya se ha recuperado (ruido, no riesgo).
  E1_group_funded arranque de tensión descartado por cash pooling: se enseña como contexto, no como riesgo.
  E1_onset        el mes exacto en que arranca la tensión confirmada (para situarla en el tiempo).

Esto es una previsión de cómo se verán los eventos en el front. El modelo todavía no se entrena
con estas etiquetas: eso es el paso siguiente.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import events_v2 as EV  # noqa: E402

OUT_PARQUET = ROOT / "data" / "events_export.parquet"
OUT_JSON = ROOT / "reports" / "eventos_export.json"

# columnas exportadas: etiquetas a 6 meses (0/1/NaN) y marcas del mes en curso
LABELS_6M = ["E1_clean", "E2_strict", "E3", "E4"]
FLAGS_MES = ["E5_bache", "E1_group_funded", "E1_onset"]
COLS = LABELS_6M + FLAGS_MES

# catálogo divulgativo: lo que ve una persona de negocio, no la fórmula
CATALOG = [
    {
        "type": "E1_clean",
        "code": "E1",
        "label": "Tensión de caja",
        "severity": "riesgo",
        "horizon": "próximos 6 meses",
        "short": "Se queda sin colchón de caja",
        "desc": "La empresa entra en tensión de caja en los próximos 6 meses: menos de una semana de "
                "gastos cubiertos, o directamente en negativo, viniendo de tres meses sanos. Sólo cuenta "
                "si la tensión se sostiene: un mes justo no basta.",
        "why": "Es el aviso con más margen de maniobra: cuando se ve, todavía hay medio año para mover "
               "financiación, adelantar cobros o renegociar pagos.",
        "excl": "No se cuentan las empresas cuya caja la mueve el grupo (cash pooling): ahí el saldo bajo "
                "no dice nada del negocio.",
    },
    {
        "type": "E2_strict",
        "code": "E2",
        "label": "Impago de obligación fija",
        "severity": "riesgo",
        "horizon": "próximos 6 meses",
        "short": "Deja de pagar algo que siempre pagaba",
        "desc": "Deja de pagar durante dos meses seguidos una obligación que venía pagando con "
                "regularidad (nóminas o cuota de deuda), o se salta dos trimestres de IVA, con la cuenta "
                "operativa activa.",
        "why": "Cuando una empresa prioriza qué deja de pagar, la caja ya se ha roto. Es la señal más "
               "dura de las cinco.",
        "excl": "Un mes suelto sin nómina no cuenta: suele ser calendario o una categoría mal puesta.",
    },
    {
        "type": "E3",
        "code": "E3",
        "label": "Caída de cobros",
        "severity": "riesgo",
        "horizon": "próximos 6 meses",
        "short": "Pierde la mitad de lo que ingresaba",
        "desc": "Los cobros caen por debajo de la mitad de su nivel habitual durante los próximos "
                "6 meses y no rebotan en la segunda mitad del periodo.",
        "why": "Distingue perder clientes de tener un mes flojo. Si al final del periodo sigue abajo, "
               "es estructural: se ha caído demanda o se ha ido un cliente grande.",
        "excl": "Si los cobros vuelven a subir dentro de la ventana, es un bache (E5), no una caída.",
    },
    {
        "type": "E4",
        "code": "E4",
        "label": "Expansión",
        "severity": "mejora",
        "horizon": "próximos 6 meses",
        "short": "Crece y se lo paga con su propia caja",
        "desc": "Los ingresos de explotación crecen más de un 30 % de forma sostenida, la caja acaba "
                "más alta que al principio y el crecimiento no se ha financiado tirando de la póliza.",
        "why": "Es la única señal buena del catálogo y marca a quién conviene acompañar: crece sin "
               "quemar caja ajena.",
        "excl": "No cuenta si todo el crecimiento está en un solo mes (un cobro extraordinario).",
    },
    {
        "type": "E5_bache",
        "code": "E5",
        "label": "Bache pasajero",
        "severity": "ruido",
        "horizon": "este mes",
        "short": "Mes flojo del que ya se ha recuperado",
        "desc": "Un mes con cobros por debajo del 70 % de lo habitual, seguido de una recuperación en "
                "los dos meses siguientes.",
        "why": "Está en el catálogo precisamente para no confundirlo con riesgo: es el falso positivo "
               "típico de cualquier alerta de tesorería, y conviene poder nombrarlo.",
        "excl": "Si no hay recuperación, deja de ser un bache y pasa a mirarse como caída (E3).",
    },
    {
        "type": "E1_group_funded",
        "code": "E1*",
        "label": "Tensión con caja del grupo",
        "severity": "ruido",
        "horizon": "este mes",
        "short": "Saldo bajo, pero la caja la mueve el grupo",
        "desc": "Arranca una tensión de caja, pero más del 20 % del flujo de los últimos tres meses es "
                "movimiento con otras empresas del mismo grupo.",
        "why": "Se separa del riesgo real: estas empresas tienen el saldo bajo porque la matriz "
               "centraliza la tesorería, no porque el negocio vaya mal.",
        "excl": "Se excluye de E1 a propósito; se muestra sólo como contexto.",
    },
    {
        "type": "E1_onset",
        "code": "E1↘",
        "label": "Arranque de tensión",
        "severity": "riesgo",
        "horizon": "este mes",
        "short": "El mes en que empieza la tensión",
        "desc": "El mes concreto en que la empresa pasa de tener colchón a no tenerlo, confirmado "
                "porque la tensión se mantiene los meses siguientes.",
        "why": "Sitúa el evento en el calendario: E1 dice que va a pasar, esto dice cuándo empezó.",
        "excl": "Sólo arranques confirmados; los que se deshacen al mes siguiente no cuentan.",
    },
]
CAT_BY_TYPE = {c["type"]: c for c in CATALOG}

# plantillas de texto en español; {c} es el identificador de la empresa
TEXTS = {
    "E1_clean": "{c} se quedó sin colchón de caja",
    "E2_strict": "{c} dejó de pagar una obligación fija",
    "E3": "{c} perdió la mitad de sus cobros",
    "E4": "{c} creció sin quemar caja",
    "E5_bache": "{c} tuvo un mes flojo y se recuperó",
    "E1_group_funded": "{c} tiene la caja baja, pero la mueve el grupo",
    "E1_onset": "{c} empezó a quedarse sin caja",
}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def month_label(m: str) -> str:
    """'2026-08' -> 'agosto de 2026' (para que el front no tenga que traducir fechas)."""
    y, mm = m.split("-")
    return f"{MESES[int(mm) - 1]} de {y}"


def build_events(panel: pd.DataFrame) -> pd.DataFrame:
    """Una fila por empresa-mes con algún evento activo.

    Se arrastra `group_id` porque la navegación del producto es cartera -> grupo -> empresa:
    sin él, el front tendría que cruzar con otra fuente sólo para poder filtrar por grupo, y las
    empresas hermanas se miran juntas (se prestan caja entre ellas antes que a un banco).
    """
    d = EV.build(panel)
    out = d[["company_id", "group_id", "month", *COLS]].copy()
    for c in COLS:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype("int8")
    out = out[out[COLS].sum(axis=1) > 0].copy()          # sólo filas con algo que contar
    out["month"] = pd.to_datetime(out.month).dt.strftime("%Y-%m")
    return out.sort_values(["month", "company_id"]).reset_index(drop=True)


def last_observable(d: pd.DataFrame) -> dict[str, str]:
    """Último mes en que cada etiqueta se puede observar (el futuro entra en el panel).

    Las etiquetas miran 6 meses hacia delante, así que los últimos meses del panel están
    censurados: no es que no haya eventos, es que todavía no se pueden saber. E1 se corta antes
    que el resto porque además necesita 3 meses extra para confirmar que la tensión se sostiene.
    """
    m = pd.to_datetime(d.month).dt.strftime("%Y-%m")
    out = {}
    for c in LABELS_6M:
        obs = m[pd.to_numeric(d[c], errors="coerce").notna()]
        out[c] = obs.max() if len(obs) else None
    for c in FLAGS_MES:
        out[c] = m.max()
    return out


def summarize(ev: pd.DataFrame, d: pd.DataFrame) -> dict:
    """Resumen del último mes completo + tasas a 6 meses sobre las filas etiquetadas (no censuradas).

    "Mes completo" = el último en que TODAS las etiquetas son observables, no el último del panel.
    Si cogiéramos el último mes a secas, el front sólo vería baches (E5) y parecería que en 2026
    no hay riesgo, cuando lo que pasa es que aún no se puede mirar 6 meses más allá.
    """
    obs = last_observable(d)
    last = min(v for v in obs.values() if v)
    cur = ev[ev.month == last]
    summary = {c: int(cur[c].sum()) for c in COLS}
    summary["empresas"] = int(cur.company_id.nunique())
    summary["grupos"] = int(cur.group_id.nunique())
    summary["eventos"] = int(cur[COLS].to_numpy().sum())

    rates = {}
    for c in LABELS_6M:
        x = pd.to_numeric(d[c], errors="coerce")
        n = int(x.notna().sum())
        pos = int((x == 1).sum())
        rates[c] = {"n": n, "positivos": pos, "tasa": round(100 * pos / n, 2) if n else 0.0}
    for c in FLAGS_MES:
        x = d[c].fillna(False).astype(bool)
        rates[c] = {"n": int(len(d)), "positivos": int(x.sum()),
                    "tasa": round(100 * x.sum() / len(d), 2)}
    return {"month": last, "month_label": month_label(last), "summary": summary, "rates_6m": rates,
            "last_month_panel": ev.month.max(), "last_observable": obs,
            "censura": "Las etiquetas a 6 meses no se pueden calcular en los últimos meses del panel: "
                       "harían falta datos que aún no existen. El mes de referencia es el último en que "
                       "todas son observables."}


def main() -> None:
    panel = pl.read_parquet(ROOT / "data" / "panel.parquet").to_pandas()
    d = EV.build(panel)

    ev = build_events(panel)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    ev.to_parquet(OUT_PARQUET, index=False)

    meta = summarize(ev, d)
    meta["catalog"] = CATALOG
    meta["generated_from"] = "events_v2.build (E1_clean, E2_strict, E3, E4, E5_bache)"
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{OUT_PARQUET.relative_to(ROOT)}: {len(ev)} filas, {ev.company_id.nunique()} empresas, "
          f"{ev.group_id.nunique()} grupos, {ev.month.min()}..{ev.month.max()}")
    print(f"{OUT_JSON.relative_to(ROOT)}: mes de referencia {meta['month']} ({meta['month_label']}), "
          f"último mes del panel {meta['last_month_panel']}")
    print("\nÚltimo mes observable por etiqueta:")
    for c, m in meta["last_observable"].items():
        print(f"  {c:<16} {m}")
    print(f"\nMes de referencia ({meta['month']}):")
    for c in COLS:
        print(f"  {c:<16} {meta['summary'][c]:>5}")
    print("\nTasas sobre filas etiquetadas (toda la historia):")
    for c, r in meta["rates_6m"].items():
        print(f"  {c:<16} {r['positivos']:>5} / {r['n']:>6}  = {r['tasa']:>6.2f} %")


if __name__ == "__main__":
    main()
