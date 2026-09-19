#!/usr/bin/env python3
"""Back-engineering de variables a nivel de ítem para el X-Ray Score (v8).

Parte de los hallazgos nuevos del repo (``research/reports/eventos_v2.md``,
``docs/eventos.md``, ``research/reports/eda.md``, ``scripts/crosscheck.txt``,
``src/mapping/ISSUES.md``) y hace el camino inverso:

    evento adverso  ->  variable que lo discrimina  ->  ítem crudo del que sale
                    ->  pilar (liquidez, cash flow, endeudamiento, ...)  ->  prioridad

No reescribe los CSV. La cobertura por empresa se calcula al vuelo con DuckDB sobre
``data/``; la evidencia de AUC y persistencia se cita del repo (no se reinventa).

Genera un artefacto autocontenido que se abre sin servidor:
    ``analysis/back_engineering_variables.html``

Reproducir (este box no tiene Python global; uv sí):
    uv run --python 3.12 --with duckdb --no-project python analysis/back_engineering_variables.py
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "analysis" / "back_engineering_variables.html"

# ---------------------------------------------------------------------------
# 1. Eventos: la diana. Tasas y veredicto de viabilidad (fuente: eventos_v2.md §1-§2, §8).
# ---------------------------------------------------------------------------
EVENTS = [
    {
        "id": "E1",
        "name": "Entrada en tensión de caja persistente",
        "def": "Pasa de sano (runway ≥ 0,5 y caja ≥ 0) a tensión (caja < 0 o runway < 0,25) y se confirma ≥2 de 3 meses siguientes.",
        "rate": "2,7 % empresa-mes · 7,2 % empresas",
        "n": "196 arranques brutos · 75 confirmados · 51 tras excluir financiados por el grupo",
        "verdict": "usable",
        "note": "Sesgo de selección si se mide sobre todas las filas: en el conjunto en riesgo, la caja de hoy casi no predice (|AUC−0,5| < 0,03). Medir siempre dentro del conjunto en riesgo.",
    },
    {
        "id": "E1_liq",
        "name": "E1 contando la póliza disponible como liquidez",
        "def": "Igual que E1 pero runway = (caja + póliza disponible) / burn.",
        "rate": "2,4 % empresa-mes · 6,4 % empresas",
        "n": "—",
        "verdict": "diagnóstico",
        "note": "Útil como contraste: el 12 % de los E1 no se daría si la póliza cubriera el hueco. Separa ahogo real de iliquidez técnica.",
    },
    {
        "id": "E2",
        "name": "Incumplimiento estricto de obligación recurrente",
        "def": "Nómina, cuota, IVA (2 trimestres) o deuda >90d con proveedores. Versión agregada.",
        "rate": "29,6 % empresa-mes · 43,4 % empresas",
        "n": "1.988 meses · nómina 291 · cuota 394 · IVA 37 · AP>90 1.342",
        "verdict": "roto",
        "note": "No discrimina: lo domina el componente AP>90 (17 %) y el 38,6 % de nóminas/cuotas 'desaparecidas' reaparecen al mes siguiente. Separar por tipo, exigir regularidad y usar la versión estricta (7,6 %).",
    },
    {
        "id": "E3",
        "name": "Caída estructural de cobros",
        "def": "Mediana de cobros de los 6 meses siguientes < 50 % de la base de 12, sin apagado y sin rebote.",
        "rate": "10,2 % empresa-mes · 26,6 % empresas",
        "n": "581 filas · 15 % rebotan después del horizonte",
        "verdict": "usable",
        "note": "Es el evento central de Q3/Q4. Exigir 'sin rebote' quita el 36,2 % de las caídas brutas: el filtro es lo que separa caída de bache.",
    },
    {
        "id": "E4",
        "name": "Expansión sostenida autofinanciada",
        "def": "Cobros operativos >130 % de la base, caja al alza, sin más póliza dispuesta.",
        "rate": "5,9 % empresa-mes · 21,9 % empresas",
        "n": "486 filas · 16,9 % revierten",
        "verdict": "usable",
        "note": "Los filtros quitan el 66,8 % de las expansiones brutas: sin ellos, 'crecer' marca cualquier pico puntual.",
    },
    {
        "id": "churn",
        "name": "Apagado (deja de operar)",
        "def": "Sin movimientos de forma persistente.",
        "rate": "3,0 % empresa-mes · 9,1 % empresas",
        "n": "—",
        "verdict": "usable",
        "note": "La cara más extrema del deterioro. Muchas features 'de desconexión' (concentración, nómina irregular) brillan aquí; no confundir ese poder con anticipación de tensión de caja.",
    },
    {
        "id": "E5",
        "name": "Bache",
        "def": "Cobros < 70 % de la mediana y recuperan ≥ 80 % en ≤ 2 meses.",
        "rate": "71,6 % de empresas con ≥12 meses",
        "n": "por cada caída que no recupera hay 1,66 baches",
        "verdict": "central",
        "note": "Los baches son la norma, no la excepción. Un score que trata cada mal mes como deterioro estructural grita en falso constantemente.",
    },
    {
        "id": "E6",
        "name": "Sano sostenido",
        "def": "≥9 meses sin E1/E2/E3, mediana de runway ≥1 y ≥3 movimientos/mes.",
        "rate": "7,9 % de las empresas",
        "n": "102 empresas",
        "verdict": "clase positiva",
        "note": "Da la cara de 'quién está sano' (Q1) con criterio, no solo por el nivel de score del mes.",
    },
]

# ---------------------------------------------------------------------------
# 2. Matriz evento x variable. AUC medida (fuente: research/reports/eventos_v2.md §4).
# Orden de columnas: E1, E1_liq, E2, E3, E4, churn_6m. Negrita = |AUC-0,5| >= 0,10.
# ---------------------------------------------------------------------------
AUC = {
    # variable:            [E1,   E1liq, E2,   E3,   E4,   churn]
    "runway":               [0.68, 0.66, 0.49, 0.49, 0.44, 0.51],
    "lc_util":              [0.30, 0.40, 0.48, 0.44, 0.46, 0.30],
    "net_margin_6m":        [0.51, 0.49, 0.52, 0.52, 0.47, 0.48],
    "growth_vs_12m":        [0.46, 0.43, 0.52, 0.41, 0.59, 0.48],
    "debt_burden":          [0.48, 0.49, 0.56, 0.47, 0.47, 0.45],
    "payroll_burden":       [0.48, 0.55, 0.47, 0.47, 0.52, 0.44],
    "ap_late_share":        [0.49, 0.45, 0.61, 0.52, 0.50, 0.70],
    "ar_late_share":        [0.54, 0.50, 0.57, 0.55, 0.48, 0.62],
    "ap_overdue_ratio":     [0.51, 0.50, 0.72, 0.53, 0.52, 0.53],
    "ar_overdue_90_ratio":  [0.49, 0.48, 0.58, 0.48, 0.48, 0.50],
    "refund_rate":          [0.49, 0.47, 0.51, 0.48, 0.51, 0.50],
    "activity_trend":       [0.49, 0.48, 0.51, 0.36, 0.60, 0.41],
    "transfer_dep":         [0.48, 0.48, 0.50, 0.47, 0.51, 0.43],
    "hhi_ar_6m":            [0.52, 0.51, 0.46, 0.54, 0.50, 0.54],
    "net_vol_6m":           [0.56, 0.58, 0.50, 0.53, 0.46, 0.48],
    "cust_trend":           [0.48, 0.49, 0.51, 0.46, 0.53, 0.39],
    "lost_share":           [0.48, 0.46, 0.45, 0.60, 0.44, 0.72],
    "payee_concentration":  [0.59, 0.54, 0.51, 0.62, 0.39, 0.76],
    "lost_accel":           [0.66, 0.65, 0.53, 0.56, 0.51, 0.74],
    "payroll_cv":           [0.58, 0.52, 0.53, 0.62, 0.57, 0.69],
    "payroll_continuity_6m":[0.37, 0.39, 0.53, 0.41, 0.49, 0.34],
    "tax_miss":             [0.51, 0.49, 0.50, 0.52, 0.55, 0.62],
    "billing_to_cash":      [0.49, 0.44, 0.54, 0.43, 0.57, 0.33],
    "oper_persistence_6m":  [0.50, 0.49, 0.48, 0.39, 0.56, 0.53],
    "yoy_inflow":           [0.54, 0.52, 0.53, 0.39, 0.56, 0.42],
    "multi_signal_stress":  [0.54, 0.55, 0.55, 0.60, 0.45, 0.54],
    "hhi_ap_6m":            [0.59, 0.58, 0.49, 0.61, 0.46, 0.60],
}

# Corrección clave: E1 medido en el conjunto en riesgo (eventos_v2.md §8.1).
IN_RISK_E1 = {
    "lost_accel": 0.65,
    "payroll_cv": 0.59,
    "payroll_continuity_6m": 0.40,
    "lc_util": 0.35,
}

# Persistencia lag-1 (fuente: research/reports/eda.md). Alta = estructural; baja = cambia mes a mes.
PERSISTENCE = {
    "runway": 0.87, "cash_negative": 0.77, "net_margin_6m": 0.51, "growth_3m": 0.57,
    "debt_burden": 0.93, "payroll_burden": 0.95, "refund_rate": 0.82, "oper_share": 0.85,
    "ap_late_share": 0.65, "ar_late_share": 0.67, "ap_overdue_ratio": 0.83,
    "ar_overdue_ratio": 0.82, "top_client_share": 0.69, "net_vol_6m": 0.93, "activity_log": 0.97,
}

# ---------------------------------------------------------------------------
# 3. Pilares (grupos) y banda de peso sugerida para v8.
# ---------------------------------------------------------------------------
PILLARS = [
    {
        "id": "LIQ",
        "name": "Liquidez y autonomía de caja",
        "weight": "22 – 26 %",
        "why": "Es la criticidad que manda: la caja que se evapora. Pero el hallazgo nuevo obliga a separar nivel de tendencia: el nivel de caja de hoy predice mal el arranque de tensión dentro del conjunto en riesgo; el cambio y la aceleración de la caja sí. Además, la voz de Embat avisa de que el umbral no es universal: el mismo runway no vale igual en un negocio de cobro recurrente que en un mayorista a 90 días, así que el corte se modula por régimen de negocio.",
        "items": "caja disponible, caja negativa, burn, runway, Δcaja 3m, póliza disponible",
    },
    {
        "id": "AR",
        "name": "Cobros y ciclo de cliente (AR)",
        "weight": "18 – 22 %",
        "why": "La caída limpia de cobros (E3) y el apagado son los eventos que esta señal anticipa. La pérdida de clientes y su aceleración son la mejor señal temprana; el DSO puro apenas mueve el ranking.",
        "items": "cobros operativos, facturación AR, DSO, vencido AR, vencido >90d, HHI cliente, clientes perdidos, aceleración de pérdida",
    },
    {
        "id": "DEBT",
        "name": "Endeudamiento y obligaciones recurrentes",
        "weight": "16 – 20 %",
        "why": "Aquí vive el incumplimiento (E2), que el hallazgo nuevo obliga a trocear: nómina, Seguridad Social, IVA y cuota se comportan distinto, y la falta de pago es más veto que feature continua. La póliza disponible, en cambio, protege (AUC 0,35 frente a E1).",
        "items": "cuota de deuda, intereses, utilización de póliza, calendario contractual, nómina regular, SS, impuestos, deuda nueva",
    },
    {
        "id": "CF",
        "name": "Generación de caja / actividad operativa",
        "weight": "12 – 16 %",
        "why": "La tendencia de actividad es la señal más 'en tiempo real' (persistencia lag-1 0,97 es nivel, pero su caída precede al apagado). El margen neto, en cambio, revierte a la media: mucho peso ahí es ruido.",
        "items": "oper_in, flujo neto, nº de movimientos, tendencia de actividad, persistencia operativa, crecimiento vs 12m",
    },
    {
        "id": "AP",
        "name": "Pagos y disciplina con proveedores",
        "weight": "8 – 11 %",
        "why": "El vencido a proveedores es el mejor discriminador crudo de E2 (0,72), pero E2 está contaminado: parte de su señal es mecánica. La concentración de pagos anticipa muy bien el apagado (0,76).",
        "items": "DPO, vencido AP, AP >90d, concentración de pagos (HHI AP), carga de nómina",
    },
    {
        "id": "STAB",
        "name": "Estabilidad: bache vs caída",
        "weight": "8 – 12 %",
        "why": "El 72 % de las empresas tiene baches. La volatilidad a la baja y el stress multi-señal separan el mal mes del deterioro. Es la pregunta 4 y hoy es la más floja: aquí está la mayor ganancia marginal.",
        "items": "volatilidad a la baja, shock vs habitual, stress multi-señal, asimetría de volatilidad, persistencia operativa, reembolsos, notas de crédito",
    },
    {
        "id": "SOLV",
        "name": "Solvencia y capacidad de cobertura",
        "weight": "2 – 5 %",
        "why": "El margen y la cobertura de intereses apenas separan eventos en este dataset (AUC ≈ 0,50). Se mantienen como contexto explicativo y para el corte de decisión de crédito, no como motor del score.",
        "items": "margen neto, cobertura de intereses, cobertura de cuota, autofinanciación",
    },
    {
        "id": "GRP",
        "name": "Grupo y contagio",
        "weight": "overlay",
        "why": "El 32 % de los arranques de E1 son filiales financiadas por su grupo: entran en 'tensión' sin estar en riesgo individual. El runway relativo al grupo y la dependencia intragrupo son modificadores, no features de nivel. Aquí entra también el régimen de negocio: fija qué runway es aceptable para cada tipo de empresa.",
        "items": "runway vs grupo, flujo intragrupo, tensión agregada del grupo, tamaño del grupo, régimen de negocio (huella operativa)",
    },
    {
        "id": "OBS",
        "name": "Observabilidad (no es salud)",
        "weight": "0 % (confianza)",
        "why": "ERP, conciliación, categoría y país son huecos de cobertura. Bajan la confianza del score, nunca el nivel. Con 501 empresas sin facturas y 25 % de movimientos sin categoría, confundirlos con riesgo es el error más caro.",
        "items": "erp conectado, % sin categoría, conciliación, antigüedad, divisa, transferencias internas",
    },
]

# ---------------------------------------------------------------------------
# 4. Catalogo item -> variable. 'cov' referencia una métrica calculada con DuckDB.
# tier: P0 nucleo, P1 alto, P2 medio, P3 bache/contexto, COV cobertura.
# ---------------------------------------------------------------------------
ITEMS = [
    # --- LIQ -----------------------------------------------------------------
    dict(var="cash_end", pillar="LIQ", item="balances.balance / available (cuenta corriente, ahorro, wallet)",
         plain="El dinero que le queda en la cuenta", dir="↑ sano", tier="P0", cov="bal_companies",
         ev="Nivel: AUC débil dentro del conjunto en riesgo. Sigue siendo P0 como estado y como disparador de veto.",
         note="Reconstruir hacia atrás desde la foto final (D09); redondear a céntimos para que el signo no oscile."),
    dict(var="cash_negative", pillar="LIQ", item="signo de cash_end reconstruido",
         plain="La cuenta está en negativo", dir="↓ sano", tier="P0", cov="bal_negative",
         ev="Dispara veto de decisión, no un punto más de score.",
         note="No es veto automático (D26): depende de persistencia y de si el grupo cubre el desfase."),
    dict(var="burn_rate", pillar="LIQ", item="transactions.amount < 0 (excluir internas e intragrupo)",
         plain="Lo que gasta al mes", dir="↓ sano", tier="P0", cov="tx_companies",
         ev="Denominador del runway. Base robusta máx(3m, 12m) para que encogerse no infle la autonomía.",
         note="19 % del volumen es transferencia y los pares internos reales llegan al 26,8 %: hay que excluirlos."),
    dict(var="runway", pillar="LIQ", item="cash_end / burn",
         plain="Meses que aguanta con el dinero que tiene", dir="↑ sano", tier="P0", cov="bal_companies",
         ev="AUC 0,68 / 0,66 frente a E1 en la población total; cae a ~0,50 dentro del conjunto en riesgo.",
         note="Excelente para nivel y explicación; flojo para anticipar el arranque. No confiarle la Q3 solo."),
    dict(var="cash_trend_3m", pillar="LIQ", item="Δcash_end a 3 meses",
         plain="Si la cuenta se está vaciando", dir="↑ sano", tier="P0", cov="bal_companies",
         ev="Es la señal que el marco exige que pese más que un DSO que empeora 3 días.",
         note="Criticidad crítica: va por delante del nivel de caja para detectar el giro."),
    dict(var="liquidity_available", pillar="LIQ", item="debt_products.liquidity (lineofcredit)",
         plain="Crédito que aún puede disponer", dir="↑ sano", tier="P1", cov="debt_lc",
         ev="lc_util 0,30 frente a E1 (usar la póliza protege) y 0,35 en el conjunto en riesgo.",
         note="Casi nunca reportado: tratarlo como cobertura, no como cero."),
    # --- CF ------------------------------------------------------------------
    dict(var="oper_share", pillar="CF", item="category in (collection, bulk_collection, pos_settlement, cash_settlement)",
         plain="Cuánto de lo que entra es cobro de su negocio", dir="↑ sano", tier="P0", cov="tx_collection",
         ev="Base de la generación operativa; distingue negocio real de transferencias.",
         note="1.264 de 1.286 empresas tienen algún cobro."),
    dict(var="activity_trend", pillar="CF", item="nº de movimientos 3m vs 12m",
         plain="Si se mueve menos dinero que antes", dir="↑ sano", tier="P1", cov="tx_companies",
         ev="AUC 0,60 vs E4 y 0,41 vs apagado: se apaga antes de caer. Persistencia lag-1 0,97 (muy estructural).",
         note="Lead indicator de apagado. Su caída es de las primeras cosas que se ve."),
    dict(var="oper_persistence_6m", pillar="CF", item="oper_in >= 50 % mediana 12m en últimos 6m",
         plain="Si su operación sigue activa la mayoría de los meses", dir="↑ sano", tier="P2", cov="tx_collection",
         ev="AUC 0,39 vs E3 (protege) y 0,56 vs E4. Persistencia alta.",
         note="Pieza de bache vs estructural: poca persistencia = la operación se está apagando."),
    dict(var="net_margin_6m", pillar="CF", item="(inflow - outflow) / (inflow + outflow)",
         plain="Si cobra más de lo que gasta", dir="↑ sano", tier="P2", cov="tx_companies",
         ev="AUC ≈ 0,50-0,52 en todos los eventos. Persistencia lag-1 0,51: revierte a la media.",
         note="Candidata a bajar peso: explica, no discrimina."),
    dict(var="growth_vs_12m", pillar="CF", item="inflow 3m vs inflow 12m",
         plain="Si factura más que su media anual", dir="↑ sano", tier="P2", cov="tx_companies",
         ev="AUC 0,59 vs E4 (expansión), 0,41 vs E3. Sirve para Q2, no para riesgo.",
         note="La cara positiva es más débil que la de deterioro: usar previsión simétrica."),
    # --- AR ------------------------------------------------------------------
    dict(var="billing_to_cash", pillar="AR", item="ar_issued 3m / oper_in 3m",
         plain="Cuánto de su cobro está respaldado por facturas emitidas", dir="↑ sano", tier="P2", cov="inv_companies",
         ev="AUC 0,57 vs E4 y 0,33 vs apagado: su fuerza era sobre todo desconexión.",
         note="Se debilita al separar apagado de tensión. Mantener con peso bajo."),
    dict(var="ar_late_share", pillar="AR", item="invoices.due_date vs payment_date (lado AR)",
         plain="Cuánto tarda en cobrar (DSO)", dir="↓ sano", tier="P2", cov="inv_ar",
         ev="AUC 0,62 vs apagado, 0,55 vs E3. Crítica media por el marco: unos días no deben dominar.",
         note="34 % de pago tardío bruto. payment_date no es fiable en vencidas (alias de due_date)."),
    dict(var="overdue_ar", pillar="AR", item="invoices AR con pending_amount≠0 y status≠paid",
         plain="Facturas de clientes vencidas y sin cobrar", dir="↓ sano", tier="P1", cov="inv_overdue_ar",
         ev="Mide stock de impago, no flujo; complementa al DSO.",
         note="12,5 % del AR emitido está vencido y abierto (18,8 B)."),
    dict(var="ar_overdue_90_ratio", pillar="AR", item="invoices AR con due_date > 2m",
         plain="Lo que le deben y lleva más de 90 días", dir="↓ sano", tier="P1", cov="inv_overdue_ar",
         ev="Separa mora reciente de un stock que ya no se cobra. AUC 0,58 vs E2.",
         note="Mezclar mora y stock eterno infla el deterioro."),
    dict(var="hhi_ar_6m", pillar="AR", item="HHI de invoices AR por counterparty_id (6m)",
         plain="Si depende de pocos clientes", dir="↓ sano", tier="P1", cov="inv_ar",
         ev="Señal de cartera para la aseguradora; AUC 0,52-0,54 (moderada sola, potente en combinación).",
         note="Concentración de contraparte = prima de impago, no necesariamente tensión de caja."),
    dict(var="cust_trend", pillar="AR", item="nº clientes AR 3m vs 12m",
         plain="Si factura a más o menos clientes", dir="↑ sano", tier="P1", cov="inv_ar",
         ev="AUC 0,39 vs apagado: perder amplitud de cartera avisa antes que la caja.",
         note="63.814 clientes distintos en facturas emitidas."),
    dict(var="lost_share", pillar="AR", item="facturación de clientes que ya no compran (3m vs 3-12m)",
         plain="La facturación de clientes que ya no le compran", dir="↓ sano", tier="P1", cov="inv_ar",
         ev="AUC 0,72 vs apagado, 0,60 vs E3, pero 0,45-0,48 vs E1/E2: es señal de declive, no de caja.",
         note="La señal más temprana de apagado (D11, D24)."),
    dict(var="lost_accel", pillar="AR", item="lost_share_m − lost_share_{m-3m}",
         plain="Si la pérdida de clientes se acelera", dir="↓ sano", tier="P0", cov="inv_ar",
         ev="AUC 0,74 vs apagado y 0,65 frente a E1 en el conjunto en riesgo: la mejor señal de arranque.",
         note="Sube de P2 (brainstorming) a P0: es exactamente lo que E1 necesita."),
    # --- AP ------------------------------------------------------------------
    dict(var="ap_late_share", pillar="AP", item="invoices.due_date vs payment_date (lado AP)",
         plain="Cuánto tarda en pagar (DPO)", dir="↓ sano", tier="P2", cov="inv_ap",
         ev="AUC 0,70 vs apagado, 0,61 vs E2. Persistencia 0,65: cambia mes a mes, útil para timing.",
         note="Pagar tarde puede ser tensión o abuso de posición: se lee junto a la caja."),
    dict(var="ap_overdue_ratio", pillar="AP", item="overdue AP / salidas medias 3m",
         plain="Lo que debe a proveedores y ya venció", dir="↓ sano", tier="P1", cov="inv_overdue_ap",
         ev="AUC 0,72 frente a E2: el mejor discriminador crudo de incumplimiento.",
         note="Pero E2 está contaminado por su propio componente AP>90. Valorar con la versión estricta."),
    dict(var="payee_concentration", pillar="AP", item="HHI de transactions.amount<0 por counterparty_id (3m)",
         plain="Si concentra sus pagos en pocos proveedores", dir="↓ sano", tier="P1", cov="tx_companies",
         ev="AUC 0,76 vs apagado y 0,62 vs E3. Sobrevive al control de desconexión.",
         note="Riesgo de cadena de suministro: si cae el proveedor clave, cae la operación."),
    dict(var="payroll_burden", pillar="AP", item="salary + social_security / inflow",
         plain="Cuánto de lo que entra se va en nóminas", dir="↓ sano", tier="P1", cov="tx_salary",
         ev="Coste rígido. Persistencia lag-1 0,95: muy estructural.",
         note="878 empresas con nóminas registradas. Si no se cubre con cobros, se vive de deuda o caja."),
    # --- DEBT / obligaciones recurrentes ------------------------------------
    dict(var="payroll_continuity_6m", pillar="DEBT", item="presencia mensual de category=salary",
         plain="Si paga la nómina todos los meses", dir="↑ sano", tier="P1", cov="tx_salary",
         ev="AUC 0,40 vs E1 en el conjunto en riesgo (la continuidad protege); 0,66 vs apagado.",
         note="Su ausencia es veto de decisión (no prestar hasta ver la siguiente), no un punto más."),
    dict(var="payroll_cv", pillar="DEBT", item="coeficiente de variación de salary mensual",
         plain="Si la nómina es irregular", dir="↓ sano", tier="P0", cov="tx_salary",
         ev="AUC 0,69 vs apagado y 0,59 frente a E1 en el conjunto en riesgo.",
         note="Nómina irregular = tensión real. Sube a P0 junto a lost_accel."),
    dict(var="debt_service_burden", pillar="DEBT", item="debt_repayment + interest_charge / inflow",
         plain="Lo que paga de cuotas sobre lo que ingresa", dir="↓ sano", tier="P1", cov="tx_debt",
         ev="AUC 0,56 vs E2. Pagar deuda con deuda nueva es la tarjeta que tapa el agujero.",
         note="718 empresas pagando deuda por categoría."),
    dict(var="lc_util", pillar="DEBT", item="debt_products.outstanding / granted (lineofcredit)",
         plain="Cuánto tiene dispuesto de su póliza", dir="↓ sano", tier="P1", cov="debt_lc",
         ev="AUC 0,30 vs E1: usarla protege. Para nivel, dispuesto cerca del concedido = ahogo.",
         note="45 % de utilización mediana de póliza. 206 empresas con línea."),
    dict(var="debt_utilization", pillar="DEBT", item="debt_products outstanding/granted (todos los tipos)",
         plain="Cuánto de su deuda total está viva", dir="↓ sano", tier="P1", cov="debt_companies",
         ev="41,7 % de utilización mediana. Signo sucio: pasar a pasivo canónico.",
         note="La foto es final; proyectarla hacia atrás filtra información (D11)."),
    dict(var="factoring_confirming", pillar="DEBT", item="debt_products.type in (factoring, confirming)",
         plain="Cuánto anticipa o confirma con bancos", dir="↓ sano", tier="P2", cov="debt_factor",
         ev="Uso intensivo = financiar circulante que no cobra. Sin AUC fuerte medida aún.",
         note="378 empresas con producto de deuda; factoring/confirming son la cola."),
    dict(var="schedule_pressure", pillar="DEBT", item="debt_schedule_config.next_payment_date, total_periods, outstanding_balance",
         plain="Cuánto le vence próximamente", dir="↓ sano", tier="P1", cov="debt_schedule",
         ev="Cuotas contractuales: la caja tiene que llegar a cada vencimiento. Disparador condicional.",
         note="Solo 87 préstamos con calendario y 40 empresas: señal rara pero decisiva cuando existe."),
    dict(var="interest_rate", pillar="DEBT", item="debt_schedule_config.annual_interest_rate_or_spread",
         plain="El interés que le cobran", dir="↓ sano", tier="P2", cov="debt_schedule",
         ev="Coste financiero que anticipa tensión si el margen es estrecho.",
         note="Alimenta cobertura de intereses."),
    dict(var="tax_miss", pillar="DEBT", item="category=tax en meses fiscales (ene/abr/jul/oct)",
         plain="Si deja de pagar impuestos", dir="↓ sano", tier="P2", cov="tx_tax",
         ev="AUC 0,62 vs apagado pero solo 0,5 frente a E1-E4: señal débil de tensión.",
         note="IVA ausente 2 trimestres seguidos es componente de E2 (1,1 %, 3,1 % empresas)."),
    dict(var="impago_nomina / ss / iva / cuota", pillar="DEBT", item="regularidad de salary, social_security, tax, debt_repayment",
         plain="Deja de pagar una obligación que pagaba siempre", dir="↓ sano", tier="P0", cov="tx_salary",
         ev="Evento, no feature: se separa por tipo y exige regularidad e historial de pago.",
         note="38,6 % de las ausencias se retoman al mes siguiente: sin exigir regularidad, es ruido."),
    dict(var="new_debt_vs_cash", pillar="DEBT", item="debt_products.granted por fecha vs Δcash",
         plain="Pide crédito nuevo mientras la caja cae", dir="↓ sano", tier="P1", cov="debt_companies",
         ev="La tarjeta que tapa el agujero. Sin AUC propia: la foto de deuda es final (D11).",
         note="Usar los flujos de debt_repayment como proxy mensual; la foto solo para nivel."),
    # --- SOLV ----------------------------------------------------------------
    dict(var="interest_coverage", pillar="SOLV", item="oper_in / (interest_charge + debt_service)",
         plain="Cuántas veces cubre sus cuotas con lo que cobra", dir="↑ sano", tier="P2", cov="tx_debt",
         ev="Contexto de solvencia. En este dataset separa poco (AUC ≈ 0,50).",
         note="Sirve para el corte de crédito y la explicación, no como motor del score."),
    dict(var="self_funding", pillar="SOLV", item="Δcaja vs Δlc_drawn",
         plain="Si crece sin pedir más crédito", dir="↑ sano", tier="P2", cov="tx_companies",
         ev="Filtro de la expansión limpia (E4): los filtros quitan 66,8 % de las expansiones brutas.",
         note="Distingue crecer de verdad de apalancarse para crecer."),
    # --- STAB ----------------------------------------------------------------
    dict(var="net_vol_6m", pillar="STAB", item="semidesviación a la baja del flujo neto / gasto",
         plain="Cuánto se le hunde la caja en meses malos", dir="↓ sano", tier="P1", cov="tx_companies",
         ev="AUC 0,56/0,58 frente a E1. Persistencia 0,93: rasgo estructural de la empresa.",
         note="Se ancla al gasto, no a la caja (D25)."),
    dict(var="shock_vs_usual", pillar="STAB", item="|flujo neto negativo| / mediana de meses negativos",
         plain="Si el golpe fue grande o pequeño", dir="↓ sano", tier="P2", cov="tx_companies",
         ev="Separa bache de deterioro. Evidencia preliminar 0,57.",
         note="Necesita historia de meses negativos; cobertura irregular."),
    dict(var="multi_signal_stress", pillar="STAB", item="cuenta de 4 señales: cobros, actividad, clientes, caja",
         plain="Cuántas señales se activan a la vez", dir="↓ sano", tier="P1", cov="tx_companies",
         ev="AUC 0,60 vs E3. Varias señales a la vez = deterioro, no ruido.",
         note="Clave para la pregunta 4."),
    dict(var="vol_asymmetry", pillar="STAB", item="volatilidad al alza / volatilidad a la baja (6m)",
         plain="Si su volatilidad es de ciclo o solo de caída", dir="↑ sano", tier="P2", cov="tx_companies",
         ev="Propuesta de brainstorming (≈0,61 vs crecimiento). Sin medir contra E1-E4 todavía.",
         note="Pendiente de validar; no meter con peso alto sin evidencia."),
    dict(var="refund_rate", pillar="STAB", item="category in (collection_refund, payment_refund)",
         plain="Reembolsos y devoluciones", dir="↓ sano", tier="P3", cov="tx_refund",
         ev="AUC ≈ 0,50 y 88 % de filas a cero en el análisis previo.",
         note="Pico puntual, no deterioro estructural. Candidata a quitar o peso mínimo."),
    dict(var="credit_notes", pillar="STAB", item="invoices.document_type in (note, refund)",
         plain="Notas de crédito emitidas", dir="↓ sano", tier="P3", cov="inv_companies",
         ev="Puede revertir facturación ya emitida: se lee aparte del declive.",
         note="7,8 % de documentos no-factura sobre el total ERP."),
    # --- GRP -----------------------------------------------------------------
    dict(var="runway_vs_group", pillar="GRP", item="runway − mediana(runway del group_id)",
         plain="Si va peor que sus empresas hermanas", dir="↑ sano", tier="P1", cov="companies_total",
         ev="AUC 0,57 vs estructural. Modificador, no feature de nivel.",
         note="Cobertura casi total (grupos de 1 a 24 empresas, mediana 2)."),
    dict(var="operating_regime", pillar="GRP", item="huella operativa: DSO, recurrencia de collection, estacionalidad de inflow, nº de clientes",
         plain="Qué régimen de negocio tiene (cobro recurrente vs ciclo largo)", dir="neutro", tier="P2", cov="tx_companies",
         ev="La PM de Embat: la criticidad de la liquidez depende del sector. No es señal de salud, es el contexto que fija el umbral.",
         note="Inferir régimen (huella operativa) y modular el umbral de runway y el peso de la caja; no usarlo como nivel."),
    dict(var="intragroup_dependency", pillar="GRP", item="pares de transactions mismo grupo/día/importe opuesto",
         plain="Si vive de que le transfiera el grupo", dir="↓ sano", tier="P1", cov="tx_companies",
         ev="El 32 % de los arranques de E1 tiene >20 % de flujo intragrupo; excluirlos deja 51 de 75.",
         note="Filtro obligatorio: sin él, las filiales financiadas por el grupo parecen en tensión sin estarlo."),
    dict(var="group_stress", pillar="GRP", item="agregado de tension_np_raw por group_id",
         plain="Si el grupo entero está tenso", dir="↓ sano", tier="P2", cov="companies_total",
         ev="Diagnóstico para la decisión de crédito, aparte del score individual.",
         note="No marcar automáticamente como sana a la empresa financiada por su grupo, ni al contrario."),
    # --- OBS -----------------------------------------------------------------
    dict(var="erp_connected", pillar="OBS", item="companies.erp / groups.erp / presencia de invoices",
         plain="Si deja ver sus facturas", dir="neutro", tier="COV", cov="inv_companies",
         ev="57,9 % con ERP; 501 empresas sin facturas.",
         note="Cobertura, no salud: baja la confianza, no el nivel."),
    dict(var="uncat_share", pillar="OBS", item="transactions.category in ('-', null)",
         plain="Cuánto movimiento no está etiquetado", dir="neutro", tier="COV", cov="tx_companies",
         ev="24,9 % de movimientos sin categoría.",
         note="No imputar salud a ese hueco (afecta sobre todo a cobros y pagos)."),
    dict(var="reconciliation", pillar="OBS", item="transactions.accounting_status",
         plain="Si lleva la contabilidad al día", dir="neutro", tier="COV", cov="tx_companies",
         ev="20,7 % conciliado; 308.568 movimientos DISCARDED.",
         note="Es proceso, no solvencia."),
    dict(var="history_length", pillar="OBS", item="companies.created_at / products.created_at",
         plain="Cuánto tiempo lleva en la plataforma",
         dir="neutro", tier="COV", cov="companies_total",
         ev="Historia de 1 a 25 meses; 397 empresas con <12 meses.",
         note="Percentiles congelados en train + confianza publicada (D16, D17)."),
    dict(var="currency_exposure", pillar="OBS", item="product.currency vs company.currency + exchange_rate",
         plain="Cuánto mueve en otra divisa", dir="neutro", tier="COV", cov="companies_total",
         ev="28 divisas; 77 filas con fx=0.",
         note="No agregar sin conversión; corrige con tipo real (D03)."),
    dict(var="internal_flow", pillar="OBS", item="pares mismo día/importe opuesto; intragrupo",
         plain="Traspasos entre sus propias cuentas", dir="neutro", tier="COV", cov="tx_companies",
         ev="19 % del volumen por categoría; pares internos reales hasta 26,8 %.",
         note="Excluir antes de medir cobros, pagos y quema."),
]

# ---------------------------------------------------------------------------
# 5. Vetos y asimetria (fuente: docs/eventos.md).
# ---------------------------------------------------------------------------
VETOES = [
    ("veto_caja_negativa", "Caja negativa", "No es veto automático: depende de persistencia, cobros pendientes y capacidad del grupo."),
    ("veto_nomina_ausente", "Nómina ausente", "No prestar hasta ver la siguiente nómina regular."),
    ("veto_ss_ausente", "Seguridad Social ausente", "Deja de pagar una obligación que pagaba siempre."),
    ("veto_iva_ausente", "IVA ausente", "2 trimestres fiscales seguidos sin pago."),
    ("veto_cuota_ausente", "Cuota de deuda ausente", "Deja de pagar una cuota habitual."),
    ("veto_poliza_agotada", "Póliza agotada con caja corta", "No ampliar: ya vive al límite del disponible."),
    ("veto_grupo_en_estres", "Grupo en estrés", "Diagnóstico agregado del grupo; modula la decisión, no el score individual."),
]

FINDINGS = [
    {
        "tag": "E1 · sesgo de selección",
        "title": "El nivel de caja de hoy no anticipa el arranque de tensión",
        "body": "Medido sobre todas las filas, tener más caja parece predecir más tensión (AUC 0,68): es selección inversa, porque solo puede entrar en tensión quien hoy está sano. Dentro del conjunto en riesgo (5.722 empresa-mes, 4,5 % de evento), el nivel de caja casi no predice (|AUC−0,5| < 0,03). Las señales que sí mandan son la aceleración de pérdida de clientes (0,65), la nómina irregular (0,59), la continuidad de nómina (0,40, protege) y el uso de póliza (0,35, protege).",
        "impact": "Reordenar prioridades: runway baja de 'única verdad' a nivel/explicación; lost_accel y payroll_cv suben a P0.",
    },
    {
        "tag": "E2 · etiqueta rota",
        "title": "El incumplimiento agregado mezcla cosas y parte es mecánico",
        "body": "E2 marca el 29,6 % de las empresa-mes y lo domina el componente deuda >90d con proveedores (17 %). El 38,6 % de las nóminas o cuotas 'desaparecidas' reaparecen al mes siguiente, y el 31 % de las expansiones limpias también tienen 'incumplimiento'. La versión estricta (nómina o cuota ausente 2 meses seguidos, sin proveedores) baja a 7,6 % de filas y 13,7 % de empresas.",
        "impact": "Trocear el evento por tipo y separar impago actual de futuro. La falta de pago es veto de decisión, no feature continua.",
    },
    {
        "tag": "Grupo · artefacto",
        "title": "Un tercio de las 'tensiones' son financiación intragrupo",
        "body": "El 32 % de los arranques de E1 tiene más del 20 % de su flujo intragrupo (24 % en el panel). Una filial que opera con la caja justa porque la financia el grupo 'entra en tensión' sin estar en riesgo individual. Al excluirlos quedan 51 de 75 arranques. La hipótesis alternativa (productos sin saldo) queda descartada: el 99 % del volumen pasa por cuentas corrientes.",
        "impact": "Filtro intragrupo obligatorio antes de etiquetar y antes de puntuar; el grupo entra como overlay, no como nivel.",
    },
    {
        "tag": "Features · desconexión",
        "title": "Varias features del brainstorming brillaban por apagado, no por tensión",
        "body": "Concentración de pagos (0,76), aceleración de pérdida de clientes (0,74), nómina irregular (0,69), continuidad de nómina (0,66) y concentración de proveedores (0,60) conservan señal. En cambio tax_miss (0,62 → 0,5) y billing_to_cash (0,54 → 0,5) se debilitan: eran sobre todo proxies de desconexión.",
        "impact": "Subir lost_accel, payroll_cv, payee_concentration y hhi_ap; bajar tax_miss y billing_to_cash a peso residual.",
    },
    {
        "tag": "Bache · frecuencia",
        "title": "El 72 % de las empresas tiene baches, no caídas",
        "body": "Por cada caída de cobros que no se recupera hay 1,66 baches. El 15 % de las caídas limpias rebotan después del horizonte y el 16,9 % de las expansiones revierten. Tratar cada mal mes como deterioro estructural llena el monitor de falsas alarmas.",
        "impact": "La detección de bache sube a pilar propio con peso 8-12 %: es la mayor ganancia marginal (Q4).",
    },
    {
        "tag": "Datos · cobertura",
        "title": "501 empresas sin facturas y 25 % de movimientos sin categoría",
        "body": "Solo 785 de 1.286 empresas tienen facturas ERP. 308.568 movimientos están DISCARDED, 243.028 tienen fecha de apunte posterior a la de valor, 77 con tipo de cambio 0, y en vencidas payment_date es un alias de due_date (~186.638). Historia por empresa: de 1 a 25 meses.",
        "impact": "Las features de disciplina (AR/AP) tienen cobertura estructural baja y no pueden ser el motor del score para todos. Percentiles congelados + confianza publicada.",
    },
    {
        "tag": "Voz Embat · régimen",
        "title": "El mismo runway no significa lo mismo en todo negocio",
        "body": "La PM de Embat (context/voz_embat.md) señala que la criticidad de la liquidez depende del sector: hay empresas que viven de la liquidez y otras para las que no es la prioridad. Un mayorista que cobra a 90 días y un negocio de cobro recurrente no deberían compartir el mismo umbral de meses de caja. La conciliación perfecta no hace falta para leer solvencia: bastan colchón y previsión.",
        "impact": "Modular el umbral de runway por régimen inferido (huella operativa: DSO, recurrencia de cobros, estacionalidad), no por un corte global. Refuerza runway_vs_group y añade un modificador de régimen.",
    },
]

PRIORITY_BASE = {"P0": 1.00, "P1": 0.72, "P2": 0.45, "P3": 0.25, "COV": 0.05}

# Peso objetivo por pilar (punto medio de la banda sugerida). Los pilares puntuables se
# normalizan a 100; GRP (overlay) y OBS (cobertura) no puntúan. El reparto dentro de cada
# pilar es proporcional a la prioridad de cada variable: peso_var = peso_pilar × prioridad/Σ.
PILLAR_TARGET = {"LIQ": 24.0, "AR": 20.0, "DEBT": 18.0, "CF": 14.0, "AP": 9.5, "STAB": 10.0, "SOLV": 3.5}
PILLAR_NON_SCORING = {"GRP": "overlay", "OBS": "cobertura"}

# Variables críticas sin AUC propia: se les asigna una fuerza de marco (0-1) para que la
# ordenación no las hunda por falta de medida. El HTML las marca como 'marco', no 'medida'.
STRENGTH_OVERRIDE = {
    "cash_end": 0.65, "cash_negative": 0.70, "burn_rate": 0.50, "cash_trend_3m": 0.60,
    "liquidity_available": 0.42, "oper_share": 0.45, "overdue_ar": 0.30,
    "debt_service_burden": 0.30, "debt_utilization": 0.25, "factoring_confirming": 0.20,
    "schedule_pressure": 0.45, "interest_rate": 0.20,
    "impago_nomina / ss / iva / cuota": 0.75, "new_debt_vs_cash": 0.40,
    "interest_coverage": 0.15, "self_funding": 0.25, "shock_vs_usual": 0.30,
    "vol_asymmetry": 0.35, "credit_notes": 0.20, "runway_vs_group": 0.30,
    "intragroup_dependency": 0.55, "group_stress": 0.35, "operating_regime": 0.30,
}
TIER_LABEL = {
    "P0": ("P0 · núcleo", "#e5484d"),
    "P1": ("P1 · alto", "#f59e0b"),
    "P2": ("P2 · medio", "#1463ff"),
    "P3": ("P3 · bache/contexto", "#27b3c2"),
    "COV": ("Cobertura", "#64748b"),
}
PILLAR_COLOR = {
    "LIQ": "#e5484d", "AR": "#1463ff", "DEBT": "#b4530a", "CF": "#22a06b",
    "AP": "#f59e0b", "STAB": "#27b3c2", "SOLV": "#7c3aed", "GRP": "#0e7490", "OBS": "#64748b",
}

# Un solo escaneo por fichero: agregados condicionales en vez de una consulta por métrica.
COVERAGE_QUERIES = [
    ("companies.csv", "SELECT count(*) FROM read_csv_auto('{d}/companies.csv', header=true)", ["companies_total"]),
    ("transactions.csv", """SELECT
        count(DISTINCT company_id) AS tx_companies,
        count(DISTINCT company_id) FILTER (WHERE category IN ('collection','bulk_collection','pos_settlement','cash_settlement','cash_settlements')) AS tx_collection,
        count(DISTINCT company_id) FILTER (WHERE category IN ('salary','social_security')) AS tx_salary,
        count(DISTINCT company_id) FILTER (WHERE category = 'tax') AS tx_tax,
        count(DISTINCT company_id) FILTER (WHERE category IN ('debt_repayment','interest_charge')) AS tx_debt,
        count(DISTINCT company_id) FILTER (WHERE category IN ('collection_refund','payment_refund')) AS tx_refund
        FROM read_csv_auto('{d}/transactions.csv', header=true)""",
     ["tx_companies", "tx_collection", "tx_salary", "tx_tax", "tx_debt", "tx_refund"]),
    ("invoices.csv", """SELECT
        count(DISTINCT company_id) AS inv_companies,
        count(DISTINCT company_id) FILTER (WHERE amount > 0) AS inv_ar,
        count(DISTINCT company_id) FILTER (WHERE amount < 0) AS inv_ap,
        count(DISTINCT company_id) FILTER (WHERE amount > 0 AND pending_amount <> 0 AND status <> 'paid') AS inv_overdue_ar,
        count(DISTINCT company_id) FILTER (WHERE amount < 0 AND pending_amount <> 0 AND status <> 'paid') AS inv_overdue_ap
        FROM read_csv_auto('{d}/invoices.csv', header=true)""",
     ["inv_companies", "inv_ar", "inv_ap", "inv_overdue_ar", "inv_overdue_ap"]),
    ("debt_products.csv", """SELECT
        count(DISTINCT company_id) AS debt_companies,
        count(DISTINCT company_id) FILTER (WHERE type = 'lineofcredit') AS debt_lc,
        count(DISTINCT company_id) FILTER (WHERE type IN ('factoring','confirming')) AS debt_factor
        FROM read_csv_auto('{d}/debt_products.csv', header=true)""",
     ["debt_companies", "debt_lc", "debt_factor"]),
    ("debt_schedule_config.csv", "SELECT count(DISTINCT company_id) FROM read_csv_auto('{d}/debt_schedule_config.csv', header=true)", ["debt_schedule"]),
    ("balances.csv", """SELECT
        count(DISTINCT company_id) AS bal_companies,
        count(DISTINCT company_id) FILTER (WHERE balance < 0) AS bal_negative
        FROM read_csv_auto('{d}/balances.csv', header=true)""",
     ["bal_companies", "bal_negative"]),
]


def compute_coverage() -> dict[str, int]:
    """Cobertura por empresa de cada señal de ítem. Si no hay DuckDB, devuelve vacío."""
    try:
        import duckdb  # type: ignore
    except Exception:
        print("aviso: duckdb no disponible; el HTML sale sin coberturas calculadas")
        return {}
    d = str(DATA).replace("\\", "/")
    con = duckdb.connect()
    cov: dict[str, int] = {}
    for fname, sql, keys in COVERAGE_QUERIES:
        try:
            row = con.execute(sql.format(d=d)).fetchone()
        except Exception as exc:  # pragma: no cover - defensivo
            print(f"aviso: no se pudo perfilar {fname}: {exc}")
            for key in keys:
                cov[key] = 0
            continue
        for key, value in zip(keys, row):
            cov[key] = int(value) if value is not None else 0
    con.close()
    return cov


def priority(item: dict, cov: dict[str, int]) -> tuple[int, dict]:
    """Prioridad transparente: criticidad base x evidencia x cobertura.

    La evidencia es la mayor |AUC-0,5| medida entre eventos (con la corrección en riesgo
    para E1). Si la variable no tiene AUC propia, se usa una fuerza de marco declarada.
    """
    base = PRIORITY_BASE[item["tier"]]
    n = cov.get("companies_total") or 1286
    cov_n = cov.get(item["cov"], 0)
    cov_frac = min(1.0, (cov_n / n) if n else 0.0)
    cov_factor = 0.5 + 0.5 * (cov_frac ** 0.5)
    strengths = [abs(a - 0.5) for a in AUC.get(item["var"], [])]
    if item["var"] in IN_RISK_E1:
        strengths.append(abs(IN_RISK_E1[item["var"]] - 0.5))
    if priorities_override := STRENGTH_OVERRIDE.get(item["var"]):
        strength = priorities_override
        src = "marco"
    elif strengths:
        strength = min(1.0, max(strengths) / 0.26)
        src = "medida"
    else:
        strength = 0.0
        src = "marco"
    value = round(100 * base * (0.55 + 0.45 * strength) * cov_factor)
    return value, {
        "base": base,
        "strength": strength,
        "cov_frac": cov_frac,
        "cov_factor": cov_factor,
        "src": src,
    }


def fmt_int(v) -> str:
    return f"{v:,}".replace(",", ".")


def fmt_weight(v: float) -> str:
    return f"{v:.1f} %".replace(".", ",")


def ordered_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda x: (["P0", "P1", "P2", "P3", "COV"].index(x["tier"]), x["var"]))


def pillar_weights(items_by_pillar: dict[str, list], cov: dict[str, int]) -> tuple[dict[str, float], dict[str, float]]:
    """Reparte el peso de cada pilar entre sus variables, proporcional a la prioridad.

    Devuelve (peso por variable, peso realizado por pilar). Los pilares overlay/cobertura
    no puntúan: sus variables salen sin peso.
    """
    scored_total = sum(PILLAR_TARGET.values())
    var_w: dict[str, float] = {}
    pillar_w: dict[str, float] = {}
    for p in PILLARS:
        pid = p["id"]
        items = ordered_items(items_by_pillar[pid])
        if pid in PILLAR_NON_SCORING:
            pillar_w[pid] = 0.0
            for it in items:
                var_w[it["var"]] = 0.0
            continue
        target = PILLAR_TARGET.get(pid, 0.0) * 100.0 / scored_total
        pris = [max(priority(it, cov)[0], 1) for it in items]
        s = sum(pris) or 1
        raw = [target * pr / s for pr in pris]
        rounded = [round(r, 1) for r in raw]
        residual = round(target - sum(rounded), 1)
        if rounded and abs(residual) >= 0.05:
            top = max(range(len(rounded)), key=lambda i: rounded[i])
            rounded[top] = round(rounded[top] + residual, 1)
        for it, w in zip(items, rounded):
            var_w[it["var"]] = w
        pillar_w[pid] = round(sum(rounded), 1)
    return var_w, pillar_w


def crit_badge(tier: str) -> str:
    label, color = TIER_LABEL[tier]
    return f'<span class="crit" style="--c:{color}">{label}</span>'


def auc_cell(value: float) -> str:
    strength = abs(value - 0.5)
    if strength >= 0.10:
        tone = "sig"
    elif strength >= 0.05:
        tone = "mild"
    else:
        tone = "flat"
    return f'<td class="auc {tone}">{value:.2f}</td>'


def build_html(cov: dict[str, int]) -> str:
    n_companies = cov.get("companies_total") or 1286

    # --- KPIs ---------------------------------------------------------------
    kpis = [
        ("Empresas", fmt_int(n_companies)),
        ("Con facturas ERP", fmt_int(cov.get("inv_companies", 0))),
        ("Con nóminas", fmt_int(cov.get("tx_salary", 0))),
        ("Con deuda conectada", fmt_int(cov.get("debt_companies", 0))),
        ("Con calendario", fmt_int(cov.get("debt_schedule", 0))),
        ("Saldo negativo", fmt_int(cov.get("bal_negative", 0))),
    ]
    kpi_html = "".join(f'<div class="kpi"><small>{html.escape(a)}</small><strong>{b}</strong></div>' for a, b in kpis)

    # --- Findings -----------------------------------------------------------
    findings_html = "".join(
        f"""<article class="finding">
          <span class="ftag">{html.escape(f['tag'])}</span>
          <h3>{html.escape(f['title'])}</h3>
          <p>{html.escape(f['body'])}</p>
          <div class="impact"><b>Qué prioriza</b>{html.escape(f['impact'])}</div>
        </article>"""
        for f in FINDINGS
    )

    # --- Events -------------------------------------------------------------
    vcolor = {"usable": "#22a06b", "diagnóstico": "#1463ff", "roto": "#e5484d", "central": "#27b3c2", "clase positiva": "#7c3aed"}
    events_rows = "".join(
        f"""<tr>
          <td><b>{html.escape(e['id'])}</b><small>{html.escape(e['name'])}</small></td>
          <td class="def">{html.escape(e['def'])}</td>
          <td class="num">{html.escape(e['rate'])}</td>
          <td class="num">{html.escape(e['n'])}</td>
          <td><span class="vtag" style="--c:{vcolor.get(e['verdict'], '#64748b')}">{html.escape(e['verdict'])}</span></td>
          <td class="note">{html.escape(e['note'])}</td>
        </tr>"""
        for e in EVENTS
    )

    # --- Item -> variable map (grouped by pillar) ---------------------------
    pillar_order = [p["id"] for p in PILLARS]
    items_by_pillar: dict[str, list] = {pid: [] for pid in pillar_order}
    for it in ITEMS:
        items_by_pillar[it["pillar"]].append(it)
    var_w, pillar_w = pillar_weights(items_by_pillar, cov)

    pillar_blocks = []
    for p in PILLARS:
        rows = []
        items = ordered_items(items_by_pillar[p["id"]])
        non_scoring = p["id"] in PILLAR_NON_SCORING
        for it in items:
            prio, comp = priority(it, cov)
            src_tag = '<span class="srcmark">medida</span>' if comp["src"] == "medida" else '<span class="srcmark marco">marco</span>'
            cov_n = cov.get(it["cov"], 0)
            cov_frac = (cov_n / n_companies) if n_companies else 0
            w = var_w.get(it["var"], 0.0)
            if non_scoring:
                w_cell = f'<td class="num wt noW">—<small>{PILLAR_NON_SCORING[p["id"]]}</small></td>'
            else:
                w_cell = f'<td class="num wt"><b>{fmt_weight(w)}</b><small>del score total</small></td>'
            rows.append(
                f"""<tr>
                  <td><b>{html.escape(it['var'])}</b><small>{html.escape(it['plain'])}</small></td>
                  <td class="item"><code>{html.escape(it['item'])}</code></td>
                  <td>{crit_badge(it['tier'])}</td>
                  {w_cell}
                  <td class="dir">{html.escape(it['dir'])}</td>
                  <td class="num">{fmt_int(cov_n)}<small>{cov_frac*100:.0f} % empresas</small></td>
                  <td class="num prio"><b>{prio}</b><small>{src_tag}</small></td>
                  <td class="ev">{html.escape(it['ev'])}<small class="note">{html.escape(it['note'])}</small></td>
                </tr>"""
            )
        color = PILLAR_COLOR[p["id"]]
        realized = pillar_w.get(p["id"], 0.0)
        total_txt = (
            f'<b>{fmt_weight(realized)}</b><small>{len(items)} variables · no puntúa (modificador)</small>'
            if non_scoring else
            f'<b>{fmt_weight(realized)}</b><small>{len(items)} variables · banda {html.escape(p["weight"])}</small>'
        )
        pillar_blocks.append(
            f"""<section class="pblock" style="--pc:{color}">
              <div class="phead">
                <div><span class="ptag">{html.escape(p['id'])}</span><h3>{html.escape(p['name'])}</h3></div>
                <div class="pweight">peso del pilar {total_txt}</div>
              </div>
              <p class="pwhy">{html.escape(p['why'])}</p>
              <div class="table-wrap"><table>
                <thead><tr><th>Variable</th><th>Ítem crudo en data/</th><th>Prioridad</th><th>Peso</th><th>Dirección</th><th>Cobertura</th><th>Score</th><th>Evidencia y cautela</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table></div>
            </section>"""
        )

    # --- Pillar summary -----------------------------------------------------
    def pillar_vars(p) -> str:
        items = ordered_items(items_by_pillar[p["id"]])
        if p["id"] in PILLAR_NON_SCORING:
            return ", ".join(f"<code>{html.escape(it['var'])}</code>" for it in items)
        return ", ".join(
            f"<code>{html.escape(it['var'])}</code> <span class='wchip'>{fmt_weight(var_w.get(it['var'], 0))}</span>"
            for it in items
        )

    pillar_rows = "".join(
        f"""<tr>
          <td><b>{html.escape(p['id'])}</b><small>{html.escape(p['name'])}</small></td>
          <td class="num w">{html.escape(p['weight'])}<small>realizado {fmt_weight(pillar_w.get(p['id'], 0.0))}</small></td>
          <td class="num">{len(items_by_pillar[p['id']])}<small>variables</small></td>
          <td>{pillar_vars(p)}</td>
        </tr>"""
        for p in PILLARS
    )

    # --- AUC matrix ---------------------------------------------------------
    event_cols = ["E1", "E1_liq", "E2", "E3", "E4", "churn"]
    auc_rows = ""
    for var, vals in AUC.items():
        brainstorm = var in {"payee_concentration", "lost_accel", "payroll_cv", "payroll_continuity_6m",
                             "tax_miss", "billing_to_cash", "oper_persistence_6m", "yoy_inflow",
                             "multi_signal_stress", "hhi_ap_6m"}
        star = ' <span class="bs">brainstorm</span>' if brainstorm else ""
        cells = "".join(auc_cell(v) for v in vals)
        # marca la corrección en riesgo para E1
        risk = IN_RISK_E1.get(var)
        risk_txt = f'<small class="risk">E1 en riesgo: {risk:.2f}</small>' if risk else ""
        auc_rows += f"<tr><td><b>{html.escape(var)}</b>{star}{risk_txt}</td>{cells}</tr>"

    # --- Ranking ------------------------------------------------------------
    ranked = sorted(ITEMS, key=lambda it: (-priority(it, cov)[0], it["var"]))
    rank_rows = ""
    for i, it in enumerate(ranked[:22], 1):
        prio, comp = priority(it, cov)
        src_tag = '<span class="srcmark">medida</span>' if comp["src"] == "medida" else '<span class="srcmark marco">marco</span>'
        w = var_w.get(it["var"], 0.0)
        w_txt = "—" if it["pillar"] in PILLAR_NON_SCORING else fmt_weight(w)
        rank_rows += (
            f"<tr><td class='num'>{i}</td>"
            f"<td><b>{html.escape(it['var'])}</b><small>{html.escape(it['plain'])}</small></td>"
            f"<td>{crit_badge(it['tier'])}</td>"
            f"<td class='num wt'>{w_txt}</td>"
            f"<td class='num prio'>{prio}</td>"
            f"<td class='num small'>{comp['strength']:.2f}{src_tag}</td>"
            f"<td class='num small'>{comp['cov_factor']:.2f}</td>"
            f"<td class='ev'>{html.escape(it['ev'][:120])}…</td></tr>"
        )

    # --- Vetoes -------------------------------------------------------------
    veto_rows = "".join(
        f"<tr><td><code>{html.escape(v[0])}</code></td><td><b>{html.escape(v[1])}</b></td><td>{html.escape(v[2])}</td></tr>"
        for v in VETOES
    )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>X-Ray · Back-engineering de variables a nivel de ítem</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero">
  <div class="eyebrow">EMBAT X-RAY · SCORING v8 · INGENIERÍA INVERSA</div>
  <h1>De los eventos adversos<br>a la variable de ítem que los anticipa.</h1>
  <p>Los hallazgos nuevos (<code>eventos_v2</code>, EDA, crosscheck y mapeo) cambian qué señal manda. Aquí se recorre el camino inverso: qué evento importa, qué variable lo discrimina, de qué ítem crudo sale, a qué pilar pertenece y cuánta prioridad merece. La criticidad no es uniforme: la caja que se evapora pesa más que un DSO que empeora tres días.</p>
  <div class="hero-meta"><span>Generado el {generated}</span><span>Corte 2026-09-01</span><span>Sin reescribir <code>data/</code></span></div>
  <div class="kpis">{kpi_html}</div>
</header>

<main>
  <section class="block">
    <h2>1 · Qué cambian los findings nuevos</h2>
    <p class="lead">Cada hallazgo reordena prioridades: sube unas variables, baja otras y añade filtros. Estos son los que mueven la aguja.</p>
    <div class="findings">{findings_html}</div>
  </section>

  <section class="block">
    <h2>2 · La diana: eventos y su viabilidad</h2>
    <p class="lead">No todos los eventos sirven para calibrar. Un evento que marca el 30 % de las filas o que se dispara por un artefacto de grupo no puede ser el objetivo del score.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Evento</th><th>Definición</th><th>Tasa</th><th>Casos</th><th>Veredicto</th><th>Qué implica</th></tr></thead>
      <tbody>{events_rows}</tbody>
    </table></div>
  </section>

  <section class="block">
    <h2>3 · Back-engineering ítem → variable → pilar → prioridad</h2>
    <p class="lead">Cada fila parte del ítem crudo de <code>data/</code> y llega a la variable, con <b>peso</b> (reparto de arranque dentro de su pilar), <b>prioridad</b>, <b>cobertura</b> y evidencia. La columna Score combina criticidad base, evidencia y cobertura: <code>100 × base × (0,55 + 0,45·evidencia) × (0,5 + 0,5·√cobertura)</code>. La evidencia es la mayor |AUC−0,5| medida (<span class="srcmark">medida</span>); cuando la variable no tiene AUC propia se usa la criticidad de marco (<span class="srcmark marco">marco</span>), porque el marco manda aunque no haya evento medible. Ni el peso ni el score son el peso final: se calibran con signo restringido (D12).</p>
    {''.join(pillar_blocks)}
  </section>

  <section class="block">
    <h2>4 · Prioridad por grupo (pilar) y reparto de pesos</h2>
    <p class="lead">El peso de cada variable sale del peso del pilar repartido por prioridad: <code>peso_var = peso_pilar × prioridad / Σ prioridad del pilar</code>. Los pilares puntuables se normalizan a 100; <b>GRP</b> es modificador y <b>OBS</b> no puntúa. Es un reparto de arranque: los pesos finales se calibran con signo restringido (D12).</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Pilar</th><th>Peso (banda / realizado)</th><th>Variables</th><th>Reparto dentro del pilar</th></tr></thead>
      <tbody>{pillar_rows}</tbody>
    </table></div>
    <p class="caveat-note">El pilar <b>GRP</b> actúa como modificador (filtro intragrupo, comparación con hermanas y régimen de negocio), así que sus variables no suman al score. <b>OBS</b> tampoco puntúa: ajusta la confianza. El resto reparte 100 % entre sus variables.</p>
  </section>

  <section class="block">
    <h2>5 · Matriz evento × variable (AUC medida)</h2>
    <p class="lead">AUC de cada variable frente a cada evento a 6 meses. <b>Verde</b> = |AUC−0,5| ≥ 0,10 (separa). En <i>churn</i> muchas features brillan porque detectan desconexión; contra E1/E2/E3 la cosa cambia. La etiqueta <span class="bs">brainstorm</span> marca las propuestas nuevas; <span class="risk">E1 en riesgo</span> es la corrección clave del sesgo de selección.</p>
    <div class="table-wrap"><table class="auc-table">
      <thead><tr><th>Variable</th><th>E1</th><th>E1_liq</th><th>E2</th><th>E3</th><th>E4</th><th>churn</th></tr></thead>
      <tbody>{auc_rows}</tbody>
    </table></div>
  </section>

  <section class="block">
    <h2>6 · Ranking de variables por prioridad</h2>
    <p class="lead">Las 22 primeras según el score transparente. Las que suben con los findings nuevos son, sobre todo, <code>lost_accel</code>, <code>payroll_cv</code>, <code>payee_concentration</code> e <code>hhi_ap_6m</code>; las que bajan, <code>net_margin_6m</code>, <code>refund_rate</code>, <code>tax_miss</code> y <code>billing_to_cash</code>.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>#</th><th>Variable</th><th>Prioridad</th><th>Peso</th><th>Score</th><th>Fuerza</th><th>Cobertura</th><th>Nota</th></tr></thead>
      <tbody>{rank_rows}</tbody>
    </table></div>
  </section>

  <section class="block warning">
    <h2>7 · Vetos: reglas que deciden por encima del score</h2>
    <p class="lead">El impago no es una feature continua: es una regla binaria que impide prestar hoy, aunque el score no se haya movido. Se aplican por encima del número.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Código</th><th>Disparador</th><th>Efecto</th></tr></thead>
      <tbody>{veto_rows}</tbody>
    </table></div>
    <div class="grid2 asym">
      <div><h3>Asimetría adversa / positiva</h3><p>El deterioro se detecta antes y mejor que la mejora. La cara positiva (E4) tiene filtros que quitan el 66,8 % de las expansiones brutas. Para Q2 no basta con subir el score: hace falta crecimiento sostenido y autofinanciado.</p></div>
      <div><h3>Bache frente a caída</h3><p>Con 1,66 baches por caída, la detección de bache es un pilar, no un adorno. Señales: persistencia operativa, volatilidad a la baja, stress multi-señal y <code>shock_vs_usual</code>. Es la mayor ganancia marginal pendiente (Q4).</p></div>
    </div>
  </section>

  <section class="block">
    <h2>8 · Especificación v8 recomendada</h2>
    <div class="grid2">
      <div>
        <h3>Subir</h3>
        <ul>
          <li><code>lost_accel</code> a P0 (0,74 churn · 0,65 E1 en riesgo).</li>
          <li><code>payroll_cv</code> a P0 (0,69 churn · 0,59 E1 en riesgo).</li>
          <li><code>payee_concentration</code> / <code>hhi_ap_6m</code> a P1 (0,76 / 0,60 churn).</li>
          <li><code>intragroup_dependency</code> a filtro obligatorio (32 % de E1).</li>
          <li>Pilar de bache a 8-12 % (Q4).</li>
          <li>Modular el umbral de liquidez por régimen de negocio inferido (voz Embat): el mismo runway no vale igual en todos.</li>
        </ul>
      </div>
      <div>
        <h3>Bajar o quitar</h3>
        <ul>
          <li><code>net_margin_6m</code>: AUC ≈ 0,50, persistencia 0,51 (revierte).</li>
          <li><code>refund_rate</code>: 88 % ceros, AUC ≈ 0,50.</li>
          <li><code>tax_miss</code> y <code>billing_to_cash</code>: se debilitan al controlar por apagado.</li>
          <li><code>debt_burden</code>: solo separa E2 (0,56) y E2 está contaminado.</li>
          <li>El nivel de caja como único motor de Q3: dentro del conjunto en riesgo no predice.</li>
        </ul>
      </div>
    </div>
    <h3 class="sub">Plan de validación</h3>
    <ul class="plan">
      <li>Etiquetar E1 <b>solo dentro del conjunto en riesgo</b> (sano hoy) y medir con eso.</li>
      <li>Trocear E2 por tipo (nómina, SS, IVA, cuota, AP>90) y exigir regularidad; usar la versión estricta (7,6 %).</li>
      <li>Excluir flujo intragrupo antes de etiquetar y de puntuar; reportar la tensión agregada del grupo aparte.</li>
      <li>Validar con <code>GroupKFold</code> por <code>group_id</code> y comprobar que ninguna variable nueva se explica por el apagado (control de desconexión).</li>
      <li>Objetivo por evento: E1 ≥ 0,65; E3 ≥ 0,65; E2 estricto ≥ 0,70; bache vs caída ≥ 0,65. Anticipación mediana ≥ 2 meses.</li>
      <li>Comparar el umbral de runway global contra el modulado por régimen: si no mejora E1/E3, no se añade complejidad.</li>
    </ul>
  </section>

  <section class="block caveat">
    <h2>Lo que este documento no resuelve</h2>
    <ul>
      <li>El score transparente de la sección 3 es una <b>guía de ordenación</b>, no un peso calibrado. Los pesos finales salen de la logística con signo restringido (D12).</li>
      <li>Varias evidencias (E1 con 75 casos, calendario con 40 empresas, factoring) tienen intervalos de confianza amplios.</li>
      <li>Falta cerrar si el leaderboard puntúa por <code>company_id</code> o <code>group_id</code>, y si hay etiquetas ocultas o el score debe ser no supervisado.</li>
      <li>La NLP de <code>description</code>/<code>concept</code> (palabras de refinanciación o aplazamiento) sigue sin explotar: es la vía natural para el impago futuro.</li>
    </ul>
  </section>

  <footer>
    <p>Reproducible con <code>uv run --python 3.12 --with duckdb --no-project python analysis/back_engineering_variables.py</code>. Fuentes: <code>research/reports/eventos_v2.md</code>, <code>docs/eventos.md</code>, <code>research/reports/eda.md</code>, <code>scripts/crosscheck.txt</code>, <code>src/mapping/ISSUES.md</code>, <code>context/scoring.md</code>, <code>research/src/events_v2.py</code>, <code>research/src/panel.py</code>. Los CSV de <code>data/</code> no se modifican.</p>
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
.hero h1 code{background:rgba(255,255,255,.12);color:#bcd6ff}
.hero p{max-width:900px;color:#c7d6ea;font-size:16px}
.hero-meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.hero-meta span{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);padding:5px 12px;border-radius:999px;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:26px}
.kpi{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:14px 16px}
.kpi small{display:block;color:#9db4d0;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.kpi strong{font-size:25px;font-weight:800}
main{max-width:1240px;margin:0 auto;padding:8px clamp(16px,4vw,40px) 60px}
.block{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px clamp(16px,3vw,32px);margin-top:26px;box-shadow:0 10px 30px -24px rgba(16,42,67,.5)}
.block h2{margin:0 0 6px;font-size:22px}
.block h3.sub{margin:20px 0 8px;font-size:16px}
.lead{color:#486581;max-width:1000px;margin:0 0 18px}
.findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.finding{border:1px solid var(--line);border-left:5px solid var(--blue);border-radius:12px;padding:16px;background:#fbfdff}
.finding .ftag{display:inline-block;font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--blue)}
.finding h3{margin:6px 0 8px;font-size:16px}
.finding p{margin:0;color:#334e68;font-size:13.5px}
.finding .impact{margin-top:10px;padding-top:10px;border-top:1px dashed var(--line);font-size:13px;color:#486581}
.finding .impact b{display:block;color:var(--navy);font-size:12px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}
.pblock{border-top:1px solid var(--line);padding-top:20px;margin-top:22px}
.phead{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;flex-wrap:wrap;margin-bottom:8px}
.ptag{display:inline-block;color:var(--pc);font-weight:800;font-size:12px;letter-spacing:.08em}
.phead h3{margin:2px 0 0;font-size:18px}
.pweight{font-size:12.5px;color:var(--slate)}
.pweight b{color:var(--pc);font-size:15px}
.pwhy{color:#486581;font-size:13.5px;max-width:1000px;margin:0 0 12px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin-top:10px}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:900px}
thead th{background:#f1f5fb;text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#486581;border-bottom:1px solid var(--line)}
td{padding:11px 12px;border-bottom:1px solid #eef2f7;vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafcff}
td small{display:block;color:#6b7c93;font-size:11.5px;margin-top:2px}
td.num{white-space:nowrap;font-variant-numeric:tabular-nums}
td.num.prio{font-size:16px}
td.num.prio b{color:var(--navy)}
td.num.w{font-weight:700}
td.small{font-size:12.5px;color:#486581}
td.dir{white-space:nowrap;color:#486581}
td.item code{font-size:11.5px;white-space:normal}
td.ev{color:#334e68;font-size:12.5px;max-width:420px}
td.def{color:#486581;font-size:12.5px;max-width:320px}
td.note{color:#6b7c93;font-size:12.5px;max-width:320px}
.crit{display:inline-block;background:color-mix(in srgb,var(--c) 14%,#fff);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 40%,#fff);font-weight:700;font-size:12px;padding:3px 10px;border-radius:999px;white-space:nowrap}
.vtag{display:inline-block;background:color-mix(in srgb,var(--c) 14%,#fff);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 40%,#fff);font-weight:700;font-size:12px;padding:3px 10px;border-radius:999px;white-space:nowrap}
.auc-table td.auc{text-align:center;font-weight:700;font-variant-numeric:tabular-nums}
td.auc.sig{color:var(--green);background:#f2fbf6}
td.auc.mild{color:var(--amber);background:#fffaf0}
td.auc.flat{color:var(--slate)}
.bs{background:#eef3fb;color:#234e70;border-radius:999px;font-size:10.5px;padding:2px 7px;margin-left:6px}
.risk{color:var(--red);font-size:11px}
.srcmark{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:1px 6px;border-radius:999px;background:#e6f6ec;color:#16794c;margin-left:5px}
.srcmark.marco{background:#eef1f6;color:#5b6b80}
td.num.wt{white-space:nowrap}
td.num.wt b{color:#0b3a6b;font-size:14px}
td.num.wt.noW{color:#8a97a8}
.wchip{display:inline-block;background:#e7f0fb;color:#1a4f86;border-radius:999px;font-size:11px;font-weight:700;padding:1px 7px;margin-left:4px}
.caveat-note{color:#6b7c93;font-size:13px;margin-top:12px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.grid2 h3{margin:0 0 6px;font-size:15px;color:#164f86}
.grid2 p{margin:0 0 8px;color:#486581;font-size:14px}
.grid2 ul{margin:0;padding-left:18px;color:#334e68;font-size:13.5px}
.grid2 li{margin:6px 0}
.plan{padding-left:18px;color:#334e68;font-size:13.5px}
.plan li{margin:8px 0}
.warning{background:linear-gradient(180deg,#fff,#fff8ef);border-color:#f6dfbe}
.asym{margin-top:20px}
.caveat{background:linear-gradient(180deg,#fff,#f5f8ff);border-color:#cfe0ff}
.caveat ul{margin:0;padding-left:20px;color:#486581}
.caveat li{margin:8px 0}
footer{padding:24px 6px 0;color:#6b7c93;font-size:13px;text-align:center}
@media(max-width:760px){.grid2{grid-template-columns:1fr}.pweight{text-align:left}}
"""


def main() -> None:
    cov = compute_coverage()
    OUTPUT.write_text(build_html(cov), encoding="utf-8")
    print(f"Escrito {OUTPUT.relative_to(ROOT)} ({len(ITEMS)} variables en {len(PILLARS)} pilares)")
    if cov:
        print(f"Coberturas calculadas: {len(cov)} métricas sobre {cov.get('companies_total', '?')} empresas")


if __name__ == "__main__":
    main()
