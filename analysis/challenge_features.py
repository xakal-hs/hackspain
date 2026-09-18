#!/usr/bin/env python3
"""Calcula las features del catalogo y las alinea con los objetivos de ``context/challenge.html``.

Usa el panel canonico de ``research/src`` (mismo que el score) para calcular las features
adimensionales y las evalua contra los eventos ancla (apagado, tension de caja, declive y
crecimiento). Cada feature se etiqueta con la pregunta del reto y la capacidad que sirve,
y con su criticidad segun ``context/scoring.md``.

Genera un artefacto autocontenido: ``analysis/features_challenge.html``.

Requisitos: haber construido el panel (``cd research && uv run python src/ingest.py``,
``src/fx.py``, ``src/panel.py``). Si falta ``research/data/panel.parquet`` se intenta
construir al vuelo.
"""

from __future__ import annotations

import html
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
PANEL = RESEARCH / "data" / "panel.parquet"
OUTPUT = ROOT / "analysis" / "features_challenge.html"
for _p in (RESEARCH / "src",):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import polars as pl  # noqa: E402
from features import CONTEXT_FEATURES, SCORE_FEATURES, add_features  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from targets import add_events  # noqa: E402

HORIZON = 6
EVENTS = {
    "adverse": "Evento adverso (apagado, caída o tensión de caja)",
    "churn": "Apagado: deja de operar",
    "cash_stress": "Tensión de caja: saldo negativo",
    "decline": "Declive: cobros futuros < 50 % de la base anual",
    "positive": "Crecimiento: cobros > 130 % y caja al alza",
}

# Preguntas del reto (context/challenge.html).
QUESTIONS = {
    "Q1": "¿Quién está sano?",
    "Q2": "¿Quién está mejorando?",
    "Q3": "¿Quién empieza a torcerse?",
    "Q4": "¿Es un bache o una caída?",
    "Q5": "¿Por qué ha cambiado?",
    "Q6": "¿Cuándo se vio venir?",
}

CAPABILITIES = {
    "rastro": "Leer el rastro",
    "score": "Construir el score",
    "explica": "Explicarse",
    "producto": "Construir algo encima",
}

CRITICALITY = {
    "critica": ("Crítica", "#e5484d"),
    "alta": ("Alta", "#f59e0b"),
    "media": ("Media", "#1463ff"),
    "bache": ("Bache", "#27b3c2"),
    "cobertura": ("No es salud", "#64748b"),
}

# feature -> (lenguaje llano, pregunta principal, capacidades, criticidad, ¿más = más sano?)
ALIGNMENT: dict[str, tuple[str, str, tuple[str, ...], str, bool]] = {
    "runway": ("El dinero que le queda expresado en meses de gasto", "Q1", ("score", "explica", "producto"), "critica", True),
    "lc_util": ("Cuánto tiene dispuesto de su póliza", "Q3", ("score", "explica"), "alta", False),
    "net_margin_6m": ("Si cobra más de lo que gasta", "Q1", ("score",), "media", True),
    "growth_vs_12m": ("Si factura más que su media anual", "Q2", ("score",), "media", True),
    "debt_burden": ("Cuánto de lo que ingresa va a pagar deuda", "Q3", ("score", "explica"), "alta", False),
    "payroll_burden": ("Cuánto de lo que ingresa se va en nóminas", "Q3", ("score", "explica"), "alta", False),
    "ap_late_share": ("Cuánto tarda en pagar a proveedores (DPO)", "Q5", ("score", "explica"), "media", False),
    "ar_late_share": ("Cuánto tarda en cobrar de clientes (DSO)", "Q3", ("score", "explica"), "media", False),
    "ap_overdue_ratio": ("Lo que debe a proveedores y ya venció", "Q3", ("score",), "media", False),
    "ar_overdue_90_ratio": ("Lo que le deben y llevan más de 90 días", "Q3", ("score", "explica"), "alta", False),
    "refund_rate": ("Devoluciones de cobros sobre cobros", "Q4", ("score",), "bache", False),
    "activity_trend": ("Si se mueve menos dinero que antes", "Q3", ("score", "explica", "producto"), "alta", True),
    "transfer_dep": ("Si vive de que le transfieran dinero", "Q5", ("score",), "bache", False),
    "hhi_ar_6m": ("Si depende de pocos clientes", "Q3", ("score",), "alta", False),
    "net_vol_6m": ("Cuánto se le hunde la caja en meses malos", "Q4", ("score",), "media", False),
    "cust_trend": ("Si factura a más o menos clientes", "Q2", ("score", "explica"), "alta", True),
    "lost_share": ("La facturación de clientes que ya no le compran", "Q3", ("score", "explica", "producto"), "alta", False),
    "oper_share": ("Cuánto de lo que entra son cobros de su negocio", "Q5", ("score",), "media", True),
}

CONTEXT_ALIGNMENT: dict[str, tuple[str, str, str]] = {
    "log_scale": ("Tamaño de la empresa en EUR", "Q5", "cobertura"),
    "fx_share": ("Peso de los movimientos en divisa", "Q5", "cobertura"),
    "uncat_share": ("Movimientos que no se dejan etiquetar", "Q5", "cobertura"),
    "activity_log": ("Número de movimientos al mes", "Q5", "cobertura"),
    "dormant": ("Si está inactiva", "Q3", "alta"),
    "months_since_last_tx": ("Meses seguidos sin movimientos (causal)", "Q3", "alta"),
}


def load_panel() -> pl.DataFrame:
    if PANEL.exists():
        return pl.read_parquet(PANEL)
    fx = RESEARCH / "data" / "fx" / "fx_monthly.parquet"
    if not fx.exists():
        raise SystemExit(
            "Falta research/data/panel.parquet y los tipos de cambio. Ejecuta:\n"
            "  cd research && uv run python src/ingest.py && uv run python src/fx.py && uv run python src/panel.py"
        )
    from panel import build_panel  # import tardío: solo si hace falta

    panel = build_panel()
    panel.write_parquet(PANEL)
    return panel


def finite(value) -> bool:
    return value is not None and value == value


def auc(frame: pl.DataFrame, feature: str, event: str) -> float | None:
    pair = frame.select([feature, event]).drop_nulls()
    if pair.height < 30:
        return None
    y = pair[event].to_numpy()
    if len(set(y.tolist())) < 2:
        return None
    try:
        return float(roc_auc_score(y, pair[feature].to_numpy()))
    except Exception:
        return None


def feature_stats(frame: pl.DataFrame, feature: str) -> dict:
    col = frame[feature].drop_nulls()
    if col.len() == 0:
        return {"coverage": 0.0, "p10": None, "p50": None, "p90": None}
    q = col.quantile(0.1), col.median(), col.quantile(0.9)
    return {
        "coverage": 100.0 * col.len() / frame.height,
        "p10": q[0],
        "p50": q[1],
        "p90": q[2],
    }


def fmt_num(value) -> str:
    if value is None:
        return "—"
    if abs(value) >= 100:
        return f"{value:,.0f}".replace(",", ".")
    if abs(value) >= 1:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{value:.3f}".replace(".", ",")


def fmt_pct(value) -> str:
    return "—" if value is None else f"{value:.0f} %"


def auc_cell(value: float | None, healthier_up: bool) -> str:
    if value is None:
        return '<td class="na">—</td>'
    # AUC orientado a riesgo: >0,5 = la feature apunta al evento en la dirección sana esperada
    risk = value if not healthier_up else 1 - value
    if risk >= 0.58:
        tone = "sig"  # señal fuerte en la dirección esperada
    elif risk >= 0.52:
        tone = "mild"
    elif risk <= 0.42:
        tone = "rev"  # apunta al revés de lo esperado
    else:
        tone = "flat"
    return f'<td class="auc {tone}">{value:.2f}</td>'


def crit_badge(key: str) -> str:
    label, color = CRITICALITY[key]
    return f'<span class="crit" style="--c:{color}">{label}</span>'


def build_html(frame: pl.DataFrame) -> str:
    rows = []
    for feature in SCORE_FEATURES:
        stats = feature_stats(frame, feature)
        a = {event: auc(frame, feature, f"{event}_{HORIZON}m") for event in EVENTS}
        plain, question, capabilities, crit, healthier_up = ALIGNMENT[feature]
        rows.append(
            {
                "feature": feature,
                "plain": plain,
                "question": question,
                "capabilities": capabilities,
                "crit": crit,
                "healthier_up": healthier_up,
                "stats": stats,
                "auc": a,
            }
        )

    # Resumen por pregunta del reto.
    q_cards = []
    for qid, qtitle in QUESTIONS.items():
        members = [r for r in rows if r["question"] == qid]
        crits = [r["crit"] for r in members]
        top = min(crits, key=lambda c: list(CRITICALITY).index(c)) if crits else None
        coverage = sum(r["stats"]["coverage"] for r in members) / len(members) if members else 0
        chips = "".join(f'<span class="chip">{html.escape(ALIGNMENT[r["feature"]][0])}</span>' for r in members) or (
            '<span class="muted">Se responde con la previsión y el monitor, no con una feature de nivel.</span>'
        )
        q_cards.append(
            f"""<article class="qcard">
              <header><span class="qid">{qid}</span><h3>{html.escape(qtitle)}</h3>{crit_badge(top) if top else ''}</header>
              <div class="chips">{chips}</div>
              <footer>{len(members)} features · cobertura media {coverage:.0f} %</footer>
            </article>"""
        )

    # Tabla completa agrupada por pregunta.
    sections = []
    for qid, qtitle in QUESTIONS.items():
        members = [r for r in rows if r["question"] == qid]
        if not members:
            continue
        body = ""
        for r in members:
            s = r["stats"]
            body += (
                "<tr>"
                f'<td><b>{html.escape(r["feature"])}</b><small>{html.escape(r["plain"])}</small></td>'
                f'<td>{crit_badge(r["crit"])}</td>'
                f'<td class="num">{fmt_pct(s["coverage"])}</td>'
                f'<td class="num">{fmt_num(s["p50"])}<small>[{fmt_num(s["p10"])} – {fmt_num(s["p90"])}]</small></td>'
                f'{auc_cell(r["auc"]["adverse"], r["healthier_up"])}'
                f'{auc_cell(r["auc"]["cash_stress"], r["healthier_up"])}'
                f'{auc_cell(r["auc"]["decline"], r["healthier_up"])}'
                f'{auc_cell(r["auc"]["positive"], r["healthier_up"])}'
                f'<td class="dir">{"↑ sano" if r["healthier_up"] else "↓ sano"}</td>'
                "</tr>"
            )
        sections.append(
            f"""<section class="block">
              <h2>{qid} · {html.escape(qtitle)}</h2>
              <div class="table-wrap"><table>
                <thead><tr><th>Feature</th><th>Criticidad</th><th>Cobertura</th><th>p50 [p10–p90]</th>
                <th>AUC adverso</th><th>AUC caja</th><th>AUC declive</th><th>AUC positivo</th><th>Dirección</th></tr></thead>
                <tbody>{body}</tbody>
              </table></div>
            </section>"""
        )

    # Contexto / observabilidad.
    ctx_rows = ""
    for feature in CONTEXT_FEATURES:
        if feature not in CONTEXT_ALIGNMENT:
            continue
        plain, question, crit = CONTEXT_ALIGNMENT[feature]
        stats = feature_stats(frame, feature)
        ctx_rows += (
            "<tr>"
            f'<td><b>{html.escape(feature)}</b><small>{html.escape(plain)}</small></td>'
            f'<td>{html.escape(question)}</td><td>{crit_badge(crit)}</td>'
            f'<td class="num">{fmt_pct(stats["coverage"])}</td>'
            f'<td class="num">{fmt_num(stats["p50"])}</td>'
            "</tr>"
        )

    computed = len(rows)
    mean_cov = sum(r["stats"]["coverage"] for r in rows) / len(rows)
    kpis = [
        ("Features calculadas", str(computed)),
        ("Cobertura media", f"{mean_cov:.0f} %"),
        ("Preguntas cubiertas", "6 / 6"),
        ("Empresas × mes", f"{frame.height:,}".replace(",", ".")),
    ]
    kpi_html = "".join(f'<div class="kpi"><small>{a}</small><strong>{b}</strong></div>' for a, b in kpis)

    cap_html = "".join(
        f'<span class="cap"><b>{html.escape(name)}</b><small>{sum(1 for r in rows if key in r["capabilities"])} features</small></span>'
        for key, name in CAPABILITIES.items()
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>X-Ray · Features calculadas y alineadas con el reto</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero">
  <div class="eyebrow">EMBAT X-RAY · FEATURES VS OBJETIVOS DEL RETO</div>
  <h1>Las features, calculadas<br>y atadas a las seis preguntas.</h1>
  <p>Cada señal sale del panel canónico de tesorería y se evalúa contra los eventos ancla (apagado, tensión de caja, declive y crecimiento). La columna <b>AUC</b> dice si la señal anticipa de verdad: valores ≥ 0,58 son señal útil; cerca de 0,50 no separan.</p>
  <div class="hero-meta"><span>Generado el {datetime.now():%Y-%m-%d %H:%M}</span><span>Horizonte {HORIZON} meses</span><span>Objetivos: context/challenge.html</span></div>
  <div class="kpis">{kpi_html}</div>
  <div class="caps">{cap_html}</div>
</header>

<main>
  <section class="block">
    <h2>Cómo leer esta tabla</h2>
    <div class="readgrid">
      <div><h3>Cobertura</h3><p>Porcentaje de filas empresa-mes con dato. Una cobertura baja es un hueco de observabilidad: no imputa salud, baja la confianza (D16, D17).</p></div>
      <div><h3>AUC</h3><p>Capacidad de ordenar el evento a 6 meses, en la dirección sana esperada. <b class="c-sig">Verde</b> ≥ 0,58 (señal), <b class="c-mild">ámbar</b> ≥ 0,52 (débil), <b class="c-rev">rojo</b> ≤ 0,42 (apunta al revés), <b class="c-flat">gris</b> el resto (no separa).</p></div>
      <div><h3>Criticidad</h3><p>Del marco de scoring: la caja que se evapora pesa más que un DSO que se mueve unos días, y la observabilidad no es salud.</p></div>
    </div>
  </section>

  <section class="block">
    <h2>Las seis preguntas del reto</h2>
    <p class="lead">Qué señales calculadas responden a cada pregunta y con qué criticidad dominante.</p>
    <div class="qgrid">{''.join(q_cards)}</div>
  </section>

  {''.join(sections)}

  <section class="block">
    <h2>Contexto y observabilidad (no puntúan)</h2>
    <p class="lead">Alimentan la confianza, la detección fuera de distribución y la explicación. Nunca se usan como nivel de salud.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Variable</th><th>Pregunta</th><th>Papel</th><th>Cobertura</th><th>p50</th></tr></thead>
      <tbody>{ctx_rows}</tbody>
    </table></div>
  </section>

  <section class="block caveat">
    <h2>Lo que aún no resuelven</h2>
    <ul>
      <li><b>Q4 · bache o caída:</b> ninguna feature de nivel separa bien un mal mes que rebota de un deterioro estructural (AUC ≈ 0,50 en el sistema). Hacen falta señales de recuperación (cobros post-bache, caja mínima intramensual).</li>
      <li><b>Q6 · cuándo se vio venir:</b> la antelación no vive en una feature, sino en el forecaster de trayectoria. El sistema mide una antelación mediana de 3 meses en las caídas estructurales (ver <code>research/reports/anticipation_v5.json</code>).</li>
      <li><b>Q2 · mejora:</b> las señales positivas existen (crecimiento, tendencia de clientes) pero su AUC es más débil que la cara de deterioro; la mejora se detecta simétrica vía previsión.</li>
      <li><b>Datos finales:</b> deuda y saldos vienen como foto a 1-sep-2026. Proyectar esa foto hacia atrás filtraría información; las features de deuda mensual salen de los flujos de <code>transactions</code>.</li>
    </ul>
  </section>

  <footer>
    <p>Reproducible con <code>cd research &amp;&amp; uv run python ../analysis/challenge_features.py</code>. Panel y features: <code>research/src/panel.py</code>, <code>research/src/features.py</code>. Eventos: <code>research/src/targets.py</code>. Objetivos: <a href="../context/challenge.html">context/challenge.html</a>. Criticidad: <a href="../context/scoring.md">context/scoring.md</a>.</p>
  </footer>
</main>
</body>
</html>"""


CSS = """
:root{--navy:#102a43;--blue:#1463ff;--cyan:#27b3c2;--green:#22a06b;--amber:#f59e0b;--red:#e5484d;--slate:#64748b;--line:#e2e8f0;--bg:#f6f8fc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--navy);font:15px/1.55 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em;background:#eef3fb;padding:1px 5px;border-radius:4px}
a{color:var(--blue)}
.hero{background:linear-gradient(135deg,#0b1f36,#102a43 55%,#12406b);color:#fff;padding:48px clamp(20px,5vw,72px) 40px}
.eyebrow{letter-spacing:.18em;font-size:12px;font-weight:700;color:#7fb0ff}
.hero h1{font-size:clamp(28px,4.2vw,46px);line-height:1.1;margin:14px 0;font-weight:800}
.hero p{max-width:860px;color:#c7d6ea;font-size:16px}
.hero-meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.hero-meta span{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);padding:5px 12px;border-radius:999px;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:26px}
.kpi{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:14px 16px}
.kpi small{display:block;color:#9db4d0;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.kpi strong{font-size:25px;font-weight:800}
.caps{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.cap{background:rgba(52,195,207,.14);border:1px solid rgba(52,195,207,.35);border-radius:10px;padding:8px 12px;display:flex;flex-direction:column}
.cap small{color:#a9d7dc;font-size:11px}
main{max-width:1180px;margin:0 auto;padding:8px clamp(16px,4vw,40px) 60px}
.block{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px clamp(16px,3vw,32px);margin-top:26px;box-shadow:0 10px 30px -24px rgba(16,42,67,.5)}
.block h2{margin:0 0 6px;font-size:22px}
.lead{color:#486581;max-width:940px;margin:0 0 18px}
.readgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}
.readgrid h3{margin:0 0 6px;font-size:15px;color:#164f86}
.readgrid p{margin:0;color:#486581;font-size:13.5px}
.c-sig{color:var(--green)}.c-mild{color:var(--amber)}.c-rev{color:var(--red)}.c-flat{color:var(--slate)}
.qgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.qcard{border:1px solid var(--line);border-radius:12px;padding:16px;background:#fbfdff}
.qcard header{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.qcard h3{margin:0;font-size:15px;flex:1;min-width:120px}
.qid{font-weight:800;color:var(--blue);font-size:12px;letter-spacing:.08em}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}
.chip{background:#eef3fb;color:#234e70;border-radius:999px;font-size:11.5px;padding:3px 9px}
.muted{color:#8a97a8;font-size:13px}
.qcard footer{margin-top:6px;color:#6b7c93;font-size:12px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin-top:10px}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:940px}
thead th{background:#f1f5fb;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#486581;border-bottom:1px solid var(--line)}
td{padding:11px 12px;border-bottom:1px solid #eef2f7;vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafcff}
td small{display:block;color:#6b7c93;font-size:11.5px;margin-top:2px}
td.num{white-space:nowrap;font-variant-numeric:tabular-nums}
td.dir{white-space:nowrap;color:#486581}
td.na{color:#9aa7b6;text-align:center}
td.auc{text-align:center;font-weight:700;font-variant-numeric:tabular-nums}
td.auc.sig{color:var(--green)}
td.auc.mild{color:var(--amber)}
td.auc.rev{color:var(--red)}
td.auc.flat{color:var(--slate)}
td.auc.sig,td.auc.mild,td.auc.rev,td.auc.flat{background:#fbfdff}
.crit{display:inline-block;background:color-mix(in srgb,var(--c) 14%,#fff);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 40%,#fff);font-weight:700;font-size:12px;padding:3px 10px;border-radius:999px;white-space:nowrap}
.caveat{background:linear-gradient(180deg,#fff,#fff8ef);border-color:#f6dfbe}
.caveat ul{margin:0;padding-left:20px;color:#486581}
.caveat li{margin:8px 0}
footer{padding:24px 6px 0;color:#6b7c93;font-size:13px;text-align:center}
"""


def main() -> None:
    panel = load_panel()
    frame = add_events(add_features(panel), HORIZON)
    OUTPUT.write_text(build_html(frame), encoding="utf-8")
    n = sum(1 for c in SCORE_FEATURES if c in frame.columns)
    print(f"Escrito {OUTPUT.relative_to(ROOT)} ({n} features sobre {frame.height} filas empresa-mes)")


if __name__ == "__main__":
    main()
