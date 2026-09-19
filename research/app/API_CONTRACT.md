# Contrato de la API X-Ray (backend FastAPI ↔ SPA)

El backend sirve la SPA en `/` (`app/static/index.html`) y la API JSON en `/api/*`. Los meses van en formato `"YYYY-MM"`, los scores en escala 0-100 y todo el texto en español.

## Tipos comunes

```jsonc
// Band: "sano" | "vigilar" | "riesgo"
// Trend: "mejora" | "estable" | "deterioro"
// Chart (gráfica genérica para decisiones y métricas):
{
  "type": "bar" | "line" | "scatter",
  "title": "string",
  "x_label": "string", "y_label": "string",
  "labels": ["..."],               // eje X categórico (bar/line); se omite en scatter
  "datasets": [{"label": "string", "data": [1, 2, 3] /* o [{"x":..,"y":..}] en scatter */}],
  "note": "string opcional"
}
```

## GET /api/companies
```jsonc
{"companies": [{
  "company_id": "COMP_0001", "group_id": "GROUP_0001", "currency": "EUR", "has_erp": true,
  "n_months": 24, "last_month": "2026-08",
  "score": 71.3, "band": "sano",
  "delta3_q10": -6.1, "delta3_q50": -1.2, "delta3_q90": 3.9,   // cambio previsto a 3 meses (cuantiles)
  "trend": "estable", "alert": null | "string", "dormant": false, "confidence": 0.82  // 0-1
}]}
```

## GET /api/company/{company_id}
```jsonc
{
  "company": { /* igual que el item de /api/companies + */ "country": "ES", "erp": "sap" },
  "history": [{
    "month": "2025-01", "score": 68.2, "score_raw": 66.0,
    "pillars": {"liquidez": 70.1, "rentabilidad": 55.0, "solvencia": 80.0, "disciplina": null, "estabilidad": 61.2},
    "features": {"runway_log": 0.8, "...": 0.1},     // valores de las features (null si no aplica)
    "drivers": {"inflow": 1.0e5, "outflow": 9.0e4, "cash_end": 2.0e5, "payroll": 3.0e4, "debt_service": 5.0e3,
                "overdue_ap": 1.0e4, "overdue_ar": 2.0e4, "late_share_ap": 0.1, "late_share_ar": 0.2, "n_tx": 120}
  }],
  "forecast": [{"month": "2026-09", "h": 1, "q10": 60.1, "q50": 66.0, "q90": 71.2}],  // h=1..3
  "explanation": {
    "month": "2026-08", "prev_month": "2026-07", "delta": -4.2,
    "contributions": [{"feature": "runway_log", "label": "Meses de caja", "pillar": "liquidez",
                       "delta_points": -3.1, "value_prev": 0.9, "value_now": 0.6, "text": "Meses de caja 2,5 → 1,8: −3,1 pts"}],
    "summary_text": "El score baja 4,2 puntos, sobre todo por ..."
  },
  "alerts": [{"month": "2026-06", "type": "deterioro" | "mejora" | "bache" | "caida" | "inactividad",
              "severity": "alta" | "media" | "baja", "text": "string"}],
  "pillar_weights": {"liquidez": 0.3, "...": 0.1},
  "feature_meta": {"runway_log": {"label": "Meses de caja (log)", "pillar": "liquidez", "direction": 1,
                                  "description": "string"}}
}
```

## GET /api/company/{company_id}/treasury
Series mensuales para la pestaña «Tesorería». Importes en la moneda de la empresa; `null` = sin dato (p. ej. facturas sin ERP).
```jsonc
{
  "company": {"company_id": "COMP_0004", "group_id": "GROUP_0058", "currency": "EUR", "has_erp": true, "last_month": "2026-08"},
  "months": [{
    "month": "2026-08",
    "inflow": 2.9e5, "outflow": 4.1e5, "net": -1.2e5,               // flujo de caja sin internas ni intragrupo
    "oper_in": 2.5e5, "payroll": 4.5e4, "tax": 1.8e4, "debt_service": 2.6e4,
    "cash_end": 1.2e5,                                              // caja a fin de mes (reconstruida hacia atrás)
    "lc_drawn": 0, "lc_limit": 1.0e6, "credit_available": 1.0e6,     // póliza de crédito (null si no tiene)
    "liquidity": 1.1e6,                                             // cash_end + credit_available
    "ar_issued": 3.5e5, "ap_issued": 1.3e5,                         // facturado a clientes / por proveedores en el mes
    "overdue_ar": 1.2e4, "overdue_ap": 2.6e4, "overdue_90_ar": 0, "overdue_90_ap": 1.1e3
  }],
  "debt": {                                                         // solo la foto final; no se proyecta hacia atrás (D11)
    "as_of": "2026-09-01", "total_owed": 9.6e5,                     // suma sin los avales (contingentes)
    "items": [{"type": "loan", "label": "Préstamos", "owed": 5.8e5, "granted": 1.1e6, "n_products": 5, "contingent": false}]
  }
}
```

## GET /api/scenario/drivers
```jsonc
{"drivers": [{"key": "inflow", "label": "Cobros / entradas", "kind": "mult" | "add",
              "min": 0, "max": 2, "step": 0.05, "default": 1, "unit": "×" | "pp", "description": "string"}],
 "months": {"min": 1, "max": 12, "default": 3}}
```

## POST /api/scenario
Petición:
```jsonc
{"company_id": "COMP_0001", "months": 3,           // se aplica a los últimos N meses de la historia
 "drivers": {"inflow": 0.8, "late_share_ap": 0.2}}  // solo los drivers movidos; mult: ×, add: +puntos (0-1)
```
Respuesta:
```jsonc
{
  "baseline": {"history": [{"month": "2026-06", "score": 70.0}], "forecast": [{"month": "2026-09", "h": 1, "q10": 0, "q50": 0, "q90": 0}]},
  "scenario": {"history": [...], "forecast": [...]},
  "band_before": "sano", "band_after": "vigilar",
  "delta_now": -8.4,                       // score del último mes: escenario − base
  "contributions": [ /* igual que en explanation: escenario frente a base en el último mes */ ],
  "summary_text": "string",
  "alerts_after": [ /* alertas del último mes en el escenario */ ]
}
```

## GET /api/monitor
```jsonc
{"month": "2026-08", "alerts": [{"company_id": "COMP_0001", "month": "2026-08", "type": "deterioro", "severity": "alta",
                                "text": "string", "score": 62.0, "delta3_q50": -9.1}]}
```

## GET /api/events

Eventos v2 (`src/events_v2.py`, exportados por `src/export_events.py`). Alimenta la vista «Eventos».

Parámetros: `?company_id=COMP_0001` devuelve toda la historia de esa empresa (`scope: "empresa"`);
`?month=2025-11` fuerza un mes; sin parámetros, el último mes completo (`scope: "mes"`).

«Último mes completo» **no** es el último del panel: las etiquetas miran 6 meses hacia delante
(E1 necesita 3 más para confirmarse), así que los últimos meses están censurados y sólo tendrían
baches. `month` es el último mes en que las siete señales son observables; `last_observable` da el
corte de cada una y `last_month_panel` el final del panel.

```jsonc
{
  "month": "2025-11", "month_label": "noviembre de 2025",
  "scope": "mes" | "empresa", "company_id": null | "COMP_0001",
  "summary": {"E1_clean": 20, "E2_strict": 62, "E3": 71, "E4": 38, "E5_bache": 166,
              "E1_group_funded": 0, "E1_onset": 2, "empresas": 300, "eventos": 359},  // del mes de referencia
  "rates_6m": {"E1_clean": {"n": 10278, "positivos": 171, "tasa": 1.66}},  // sobre filas no censuradas, toda la historia
  "last_observable": {"E1_clean": "2025-11", "E2_strict": "2026-02"},
  "last_month_panel": "2026-07",
  "censura": "string",
  "counts": {"E1_clean": 20, "...": 0},        // eventos devueltos en esta respuesta, por tipo
  "total": 359,
  "catalog": [{
    "type": "E1_clean", "code": "E1", "label": "Tensión de caja",
    "severity": "riesgo" | "mejora" | "ruido",
    "horizon": "próximos 6 meses" | "este mes",
    "short": "Se queda sin colchón de caja",
    "desc": "string", "why": "string", "excl": "string"     // divulgativo, en español
  }],
  "events": [{
    "company_id": "COMP_0009", "month": "2025-11", "type": "E1_clean",
    "text": "COMP_0009 se quedó sin colchón de caja",
    "month_label": "noviembre de 2025",
    "severity": "riesgo", "label": "Tensión de caja"
  }]
}
```

Tipos: `E1_clean` (tensión de caja, sin cash pooling), `E2_strict` (impago de obligación fija),
`E3` (caída de cobros), `E4` (expansión), `E5_bache` (bache pasajero),
`E1_group_funded` (tensión que paga el grupo, contexto) y `E1_onset` (mes de arranque de la tensión).

Errores: `503` si faltan `data/events_export.parquet` o `reports/eventos_export.json`
(hay que ejecutar `uv run python src/export_events.py`).

## GET /api/metrics
```jsonc
{"iterations": [{"tag": "v1", "description": "string", "metrics": {"mae_h3": 6.4, "...": 0}}],
 "final": {"...": 0},
 "charts": [ /* Chart */ ]}
```

## GET /api/decisions
```jsonc
{"decisions": [{
  "id": "D01", "category": "datos" | "score" | "modelo" | "validación" | "producto" | "ood",
  "title": "string", "question": "string", "decision": "string", "why": "string",
  "alternatives": "string", "evidence": "string",
  "status": "decidido" | "a confirmar con la organización",
  "chart": null | { /* Chart */ }
}]}
```
