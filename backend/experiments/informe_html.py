"""salida/*.json -> experiments/pesos_2x2.html (autocontenido, se abre sin servidor).

    uv run python informe_html.py
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "pesos_2x2.html"
S = HERE / "salida"

ARMS = ["A", "B", "C", "D", "E", "F", "G"]
DESC = {"A": ("17 features · pesos calibrados", "el backend de hoy"),
        "B": ("17 features · pesos del doc", "solo cambian los pesos"),
        "C": ("42 features del doc · pesos del doc", "el doc entero, tal cual"),
        "D": ("42 features del doc · pesos calibrados", "solo cambian las features"),
        "E": ("17 features · mezcla 50/50", "¿y a medio camino?"),
        "F": ("17 + 7 features nuevas · calibradas", "las nuevas que aguantan la calibración"),
        "G": ("17 + 2 features nuevas · calibradas", "la extracción neta: lo único que se adopta")}
ANCLAS = ["tension_np_raw_6m", "incumplimiento_6m", "caida_6m", "expansion_6m"]
CLAVE = ANCLAS + ["entrada_estres_2m", "rompe_caja_2m", "tension_entrada_6m", "impago_iva_6m",
                  "impago_ap_6m", "caida_3m_corto", "recaida_6m", "tension_grupo_6m"]
NOMBRE = {
    "tension_np_raw_6m": "tensión de caja (ancla)", "incumplimiento_6m": "deja de pagar nómina o IVA",
    "caida_6m": "caída estructural de cobros", "expansion_6m": "expansión sostenida",
    "entrada_estres_2m": "entra en estrés en 2 meses", "rompe_caja_2m": "caja negativa en 2 meses",
    "tension_entrada_6m": "entra en tensión (6m)", "impago_iva_6m": "impago de IVA",
    "impago_ap_6m": "mora crónica con proveedores", "caida_3m_corto": "caída corta (3m)",
    "recaida_6m": "recaída tras curarse", "tension_grupo_6m": "tensión del grupo",
}
CSS = """
:root{--navy:#102a43;--blue:#1463ff;--green:#22a06b;--amber:#f59e0b;--red:#e5484d;--slate:#64748b;--line:#e2e8f0;--bg:#f6f8fc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--navy);font:16px/1.65 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em;background:#eef3fb;padding:1px 5px;border-radius:4px;color:#0b3a6b}
.hero{background:linear-gradient(135deg,#0b1f36,#102a43 55%,#12406b);color:#fff;padding:44px clamp(20px,5vw,72px) 30px}
.eyebrow{letter-spacing:.18em;font-size:12px;font-weight:700;color:#7fb0ff}
.hero h1{font-size:clamp(26px,4vw,40px);line-height:1.14;margin:14px 0 14px;font-weight:800;max-width:940px}
.hero p{max-width:900px;color:#c7d6ea;margin:0 0 10px}
.hero-meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.hero-meta span{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);padding:5px 12px;border-radius:999px;font-size:12px}
main{max-width:1060px;margin:0 auto;padding:8px clamp(16px,4vw,40px) 56px}
.block{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px clamp(18px,3.2vw,34px);margin-top:24px;box-shadow:0 10px 30px -24px rgba(16,42,67,.5)}
.block h2{margin:0 0 12px;font-size:22px;letter-spacing:-.01em}
.block h3{margin:24px 0 8px;font-size:16px;color:#164f86}
.block p{margin:0 0 13px}
.block ul{margin:0 0 14px;padding-left:20px}.block li{margin:6px 0}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:6px 0 16px}
table{width:100%;border-collapse:collapse;font-size:14px;min-width:560px}
thead th{background:#f1f5fb;text-align:left;padding:9px 11px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#486581;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 11px;border-bottom:1px solid #eef2f7;vertical-align:top;white-space:nowrap}
tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#fafcff}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.win{color:var(--green);font-weight:700}.lose{color:var(--red);font-weight:700}.flat{color:var(--slate)}
.best{background:#eefaf3}
blockquote{margin:0 0 16px;padding:13px 17px;background:#f5f8ff;border-left:4px solid var(--blue);border-radius:0 10px 10px 0}
blockquote p{margin:0;color:#334e68;font-size:14.5px}
.verdict{border-left-color:var(--red);background:#fdf2f2}
.bar{display:inline-block;height:9px;border-radius:3px;background:var(--blue);vertical-align:middle}
.foot{max-width:1060px;margin:22px auto 0;padding:0 8px;color:#6b7c93;font-size:13px;text-align:center}
@media(max-width:640px){.block{padding:18px 15px}.hero{padding:30px 18px}}
"""


def esc(x) -> str:
    return html.escape(str(x))


def es(v, nd=3, sign=False) -> str:
    if v is None:
        return "—"
    return (f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}").replace(".", ",")


def tabla(head: list[str], rows: list[list[str]], nums: set[int] = frozenset()) -> str:
    th = "".join(f'<th class="{"num" if i in nums else ""}">{esc(h)}</th>' for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td class="{"num" if i in nums else ""}">{c}</td>'
                                  for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def sigma_cell(d: dict) -> str:
    s = d["sigmas"]
    cls = "win" if s >= 2 else "lose" if s <= -2 else "flat"
    return f'<span class="{cls}">{es(d["delta"], 3, True)} · {es(s, 1, True)}σ</span>'


def main() -> None:
    met = {a: json.loads((S / f"metrics_{a}.json").read_text()) for a in ARMS}
    par = {a: {r["evento"]: r for r in json.loads((S / f"pareado_{a}.json").read_text())}
           for a in ARMS if a != "A"}
    auc = {a: {r["evento"]: r for r in met[a]["auc"]} for a in ARMS}

    # --- resumen
    res_rows = []
    for a in ARMS:
        m, ant = met[a], met[a]["anticipacion"]
        res_rows.append([f"<b>{a}</b> · {esc(DESC[a][0])}<br><span class=flat>{esc(DESC[a][1])}</span>",
                         str(m["n_features"]), es(auc[a]["tension_np_raw_6m"]["auc"]),
                         es(m["pm"], 4), f'{es(100 * ant["cobertura"], 1)} %',
                         es(ant["meses_mediana"], 1), es(m["cobertura_media"], 3)])
    resumen = tabla(["brazo", "features", "AUC tensión (ancla)", "PM", "avisos cubiertos",
                     "meses de antelación", "cobertura de dato"], res_rows, {1, 2, 3, 4, 5, 6})

    # --- la cara positiva, con sus propios pesos
    exp = {r["evento"]: r for r in json.loads((S / "pareado_Gexp.json").read_text())}
    exp_tbl = tabla(["evento", "A · nota de expansión", "G · nota de expansión", "Δ", "σ pareadas"],
                    [[f"<code>{esc(e)}</code>", es(r["auc_a"]), es(r["auc_b"]),
                      es(r["delta"], 3, True), es(r["sigmas"], 1, True) + " σ"]
                     for e, r in exp.items()], {1, 2, 3, 4})

    # --- AUC por evento
    ev_rows = []
    for e in CLAVE:
        if e not in auc["A"]:
            continue
        best = max(ARMS, key=lambda a: auc[a].get(e, {}).get("auc", 0))
        cells = []
        for a in ARMS:
            v = auc[a].get(e, {}).get("auc")
            cells.append(f'<span class="{"win" if a == best else ""}">{es(v)}</span>')
        ev_rows.append([f"{esc(NOMBRE.get(e, e))}<br><span class=flat><code>{esc(e)}</code></span>",
                        str(auc["A"][e]["positivos"]), *cells])
    eventos = tabla(["evento", "positivos", *ARMS], ev_rows, set(range(1, 8)))

    # --- pareado contra A
    pa_rows = []
    for e in CLAVE:
        if e not in par["B"]:
            continue
        pa_rows.append([esc(NOMBRE.get(e, e)), *[sigma_cell(par[a][e]) for a in ARMS if a != "A"]])
    pareado = tabla(["evento", *[a for a in ARMS if a != "A"]], pa_rows, set(range(1, 6)))

    # --- pesos: dónde va la masa
    pesos = {a: met[a]["pesos"] for a in ARMS}
    liq_doc = ["runway", "cash_end_eur", "burn_rate", "cash_trend_3m", "cash_negative", "liquidity_available"]
    pw_rows = []
    for f in ["runway", "payroll_cv", "activity_trend", "oper_persistence_6m", "lost_share",
              "ap_overdue_ratio", "cust_trend", "ar_overdue_90_ratio", "net_vol_6m"]:
        pw_rows.append([f"<code>{esc(f)}</code>", *[es(100 * pesos[a].get(f, 0), 1) + " %" for a in ARMS]])
    pw_rows.append(["<b>bloque de liquidez entero</b>",
                    *[f"<b>{es(100 * sum(pesos[a].get(x, 0) for x in liq_doc), 1)} %</b>" for a in ARMS]])
    pesos_tbl = tabla(["feature", *ARMS], pw_rows, set(range(1, 7)))

    # --- lo nuevo que sí pesa al calibrarlo
    nuevos = [(f, w) for f, w in sorted(met["D"]["pesos"].items(), key=lambda kv: -kv[1])
              if f not in met["A"]["pesos"]][:12]
    nuevos_tbl = tabla(["variable nueva del catálogo", "peso que le da la logística (brazo D)", "barra"],
                       [[f"<code>{esc(f)}</code>", es(100 * w, 1) + " %",
                         f'<span class="bar" style="width:{int(w * 900)}px"></span>'] for f, w in nuevos],
                       {1})

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>¿Los pesos del catálogo a priori son mejores que los del backend?</title>
<style>{CSS}</style></head><body>
<header class="hero">
  <div class="eyebrow">EMBAT X-RAY · EXPERIMENTO DE PESOS · 2x2</div>
  <h1>Los pesos a priori del catálogo, medidos contra los pesos calibrados del backend</h1>
  <p><code>docs/explicacion_pesos.md</code> describe 42 variables en 7 pilares con pesos de juicio
  experto. El backend puntúa 17 features con pesos calibrados. Cambiar lo uno por lo otro mezcla
  dos cosas —features nuevas y pesos fijos—, así que se miden por separado en un 2x2, más una
  mezcla (E) y la extracción neta (F).</p>
  <p>La medición es la del repo, sin tocar: fuera de grupo, fuera del futuro (un scorer por fold y
  mes), error típico remuestreando grupos enteros y <b>bootstrap pareado</b> contra el brazo A.</p>
  <div class="hero-meta"><span>Generado el {ts}</span><span>21.538 empresa-mes · 250 grupos</span>
  <span>backend/experiments/medir.py</span></div>
</header>
<main>

<section class="block">
  <h2>El veredicto, en una frase</h2>
  <blockquote class="verdict"><p><b>No.</b> Poner los pesos del documento hunde justo aquello para lo
  que se vende el score: la tensión de caja cae de <b>0,848 a 0,719</b> AUC (−9,7 σ pareadas) y la
  capacidad de anticipar la entrada en estrés cae de 0,637 a 0,552 (−4,8 σ). Las 25 features nuevas
  no lo arreglan: con ellas y los pesos del doc sigue en 0,740. Lo que sí sobrevive a la medición es
  un puñado de variables sueltas del catálogo, calibradas — el brazo F.</p></blockquote>
  <p>La trampa está en la métrica-resumen. <b>PM sube con los pesos del doc</b> (0,6285 → 0,6303) y
  eso, leído solo, diría que el cambio es bueno. PM es la media de cuatro AUC: esconde que el ancla
  se desploma mientras tres eventos secundarios mejoran un poco. Es exactamente el motivo por el que
  el repo la reporta pero no la deja decidir.</p>
  {resumen}
  <p class="flat">«Avisos cubiertos» es la fracción de empresas que entran en estrés con aviso previo
  (nota &lt; 35); «meses de antelación» es la mediana de ese aviso. El brazo A reproduce el README al
  decimal (PM 0,6285 · tensión 0,848 · 18,6 % de cobertura), que es lo que valida el banco de pruebas.</p>
</section>

<section class="block">
  <h2>AUC por evento · los seis brazos</h2>
  {eventos}
  <p>Se lee así: los pesos del doc (<b>B</b>) ordenan <b>mejor</b> la caída de cobros, la expansión,
  la mora con proveedores y la recuperación, y <b>mucho peor</b> todo lo que es liquidez. No es azar:
  es lo que pasa cuando se reparte el peso en plano. El score deja de ser un detector de caja y pasa
  a ser un índice general de salud — que suena bien, salvo que el producto vende avisar de la caja.</p>
</section>

<section class="block">
  <h2>Contra el brazo A, en pareado</h2>
  <p>El <code>se</code> que decide es el de la <b>diferencia</b> con los mismos grupos remuestreados
  en los dos brazos. Verde ≥ +2 σ, rojo ≤ −2 σ.</p>
  {pareado}
</section>

<section class="block">
  <h2>Por qué se rompe: la masa de peso</h2>
  <p>El catálogo reparte 24,2 % a liquidez, pero <b>entre seis variables</b>, así que ninguna pasa de
  4,8 %. La logística, en cambio, le da a <code>runway</code> ella sola el 27 %. El documento predica
  que «la criticidad no es uniforme» y su propio reparto la aplana.</p>
  {pesos_tbl}
  <p>La prueba de que el problema es el <b>reparto</b> y no las variables está en el brazo D: con las
  42 features del doc pero pesos calibrados, la logística vuelve a juntar ~27 % de masa en liquidez
  (<code>runway</code> 15,2 % + <code>cash_end</code> 6,3 % + <code>burn_rate</code> 6,0 %) y el ancla
  vuelve a 0,835. Mismas variables, otro reparto, 10 puntos de AUC.</p>
  <h3>Tres defectos más del catálogo, medidos</h3>
  <ul>
    <li><b>Las estrellas no tienen datos.</b> <code>lost_accel</code> lleva 4,6 % de peso —el tercero
    del catálogo— y solo existe en el <b>24,1 %</b> de las filas; <code>lost_share</code>, en el 31,6 %.
    El resto del tiempo el score rellena con un 50 neutro: peso nominal alto, señal nula.</li>
    <li><b>Dos variables son tamaño disfrazado.</b> <code>cash_end</code> (4,7 %) y <code>burn_rate</code>
    (4,3 %) son niveles en euros: juntos, el 9 % del score ordena por «empresa grande / pequeña».
    Calibrados se aprovechan (son el par que reconstruye el runway); a mano, compiten con él.</li>
    <li><b>El veto dentro de la nota.</b> El catálogo puntúa <code>impago nómina/SS/IVA/cuota</code> con
    3,2 %, y el propio documento explica tres párrafos después por qué un veto no debe sumar puntos.</li>
  </ul>
  <p class="flat">Cobertura honesta del experimento: <code>debt_utilization</code>,
  <code>factoring_confirming</code> e <code>interest_rate</code> salen de ficheros sin fecha, así que
  son constantes por empresa; <code>schedule_pressure</code> existe en el 0,6 % de las filas;
  <code>payee_concentration</code> se calcula con las contrapartes de las facturas recibidas porque el
  89,6 % de las transacciones de salida no trae contraparte. Está todo en <code>catalogo.DESVIACIONES</code>.</p>
</section>

<section class="block">
  <h2>Lo que sí vale la pena llevarse</h2>
  <p>El brazo D deja ver qué variables nuevas resisten la calibración, que es la pregunta útil:</p>
  {nuevos_tbl}
  <p>El brazo <b>F</b> añade siete de ellas a las 17 actuales (fuera el impago, que es veto) y las
  calibra: el ancla no se mueve (0,849), el IVA sube +3,9 σ… pero la antelación mediana cae de 4 a
  3 meses. Siete variables para una ganancia que venía de dos. El brazo <b>G</b> deja solo esas dos
  —<code>tax_miss</code> (deja de pagar impuestos en el trimestre que toca) y
  <code>payroll_continuity_6m</code> (paga la nómina todos los meses)— y es el resultado del experimento:</p>
  <ul>
    <li><b>El ancla intacta</b>: 0,848 → 0,848 (−0,1 σ). No se paga nada donde más duele.</li>
    <li><b>Impago de IVA +0,049 (+5,9 σ)</b> e incumplimiento <b>+0,021 (+2,3 σ)</b>: ataca el punto
    flojo que el propio backend declara (0,588 en incumplimiento).</li>
    <li><b>Anticipación</b>: entrada en estrés a 2 meses +0,022 (+3,1 σ), entrada en tensión a 6 meses
    +0,043 (+2,8 σ), y los avisos cubren <b>22,6 % de las entradas frente al 18,6 %</b> manteniendo la
    mediana en 4 meses. Eso es la dimensión «timing» del jurado, con dos features.</li>
    <li><b>El coste, declarado</b>: la expansión baja. Medida con los pesos adversos parecía −4,1 σ,
    pero esa nota no vende expansión; con la <b>nota de expansión</b> y sus propios pesos el daño real
    es cuatro veces menor:</li>
  </ul>
  {exp_tbl}
  <blockquote><p><b>Recomendación.</b> No adoptar los pesos del documento (B), ni el catálogo completo
  (C), ni la mezcla (E): las tres compran eventos secundarios pagando con liquidez y anticipación.
  Adoptar <b>G</b>: dos features nuevas, ancla intacta, +5,9 σ en impago de IVA y cuatro puntos más de
  cobertura de aviso, a cambio de −0,015 de AUC en expansión. Y corregir el documento: los pesos que
  publica no son los del score y, medidos, no deberían serlo.</p></blockquote>
</section>

<section class="block">
  <h2>Cómo reproducirlo</h2>
  <p>Nueve brazos (siete adversos y dos de expansión), ~1-2 minutos cada uno. Los pesos del documento no se copian a mano: se regeneran
  ejecutando el propio generador del artefacto.</p>
  <div class="table-wrap"><table><thead><tr><th>paso</th><th>comando</th></tr></thead><tbody>
  <tr><td>pesos del doc</td><td><code>uv run --with duckdb python experiments/dump_pesos_doc.py &gt; experiments/pesos_doc.json</code></td></tr>
  <tr><td>las 42 features</td><td><code>uv run python experiments/catalogo.py</code></td></tr>
  <tr><td>un brazo</td><td><code>uv run python experiments/medir.py A|B|C|D|E|F</code></td></tr>
  <tr><td>comparación</td><td><code>uv run python experiments/medir.py informe</code></td></tr>
  <tr><td>esta página</td><td><code>uv run python experiments/informe_html.py</code></td></tr>
  </tbody></table></div>
</section>
</main>
<footer class="foot"><p>Generado por <code>backend/experiments/informe_html.py</code> desde
<code>backend/experiments/salida/*.json</code>. Los <code>oof_*.parquet</code> no se versionan.</p></footer>
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"Escrito {OUT.relative_to(HERE.parent.parent)} ({len(doc):,} bytes)")


if __name__ == "__main__":
    main()
