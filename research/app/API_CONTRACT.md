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
`?group_id=GROUP_0218`, la de todas sus empresas hermanas (`scope: "grupo"`), que se miran juntas
porque se prestan caja entre ellas antes que a un banco; `?month=2025-11` fuerza un mes (solo, o
combinado con los anteriores para acotarlos); sin parámetros, el último mes completo (`scope: "mes"`).

«Último mes completo» **no** es el último del panel: las etiquetas miran 6 meses hacia delante
(E1 necesita 3 más para confirmarse), así que los últimos meses están censurados y sólo tendrían
baches. `month` es el último mes en que las siete señales son observables; `last_observable` da el
corte de cada una y `last_month_panel` el final del panel.

```jsonc
{
  "month": "2025-11", "month_label": "noviembre de 2025",
  "scope": "mes" | "empresa" | "grupo",
  "company_id": null | "COMP_0001", "group_id": null | "GROUP_0218",
  "companies": ["COMP_0001"],                  // empresas presentes en esta respuesta
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
    "company_id": "COMP_0009", "group_id": "GROUP_0218", "month": "2025-11", "type": "E1_clean",
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

## GET /api/situaciones
Sala de situaciones: las premisas del consejo (fase 2) evaluadas contra el panel (fase 3). Sirve
`.devin/workflows/autoresearch/salida/situaciones.json` (`premisas.py export`). Si el fichero no existe responde **200** con lista vacía y `aviso`.
```jsonc
{
  "resumen": {"total": 270, "pasan": 123, "fallan": 54, "no_verificables": 93, "centrales": 54, "centrales_fallan": 19},
  "fuente": ".devin/workflows/autoresearch/salida/situaciones.json",
  "aviso": "string opcional (solo si no hay fichero)",
  "situaciones": [{
    "id": "P001", "rol": "prestamista" | "cfo" | "auditor-datos" | "riesgo-modelo" | "abogado-diablo" | "cobrador",
    "ambito": "liquidez" | "cobros" | "pagos" | "deuda" | "observabilidad" | "producto" | "recuperacion" | "calibracion" | "comportamiento" | "sesgos" | "estabilidad" | "gaming",
    "premisa": "string", "por_que": "string",
    "condicion": "si X entonces Y, salvo Z",          // opcional
    "verificable": true, "central": false, "fragil": false,
    "test": {"tipo": "auc" | "tasa_evento" | "condicional" | "correlacion" | "estadistico" | "banda" | "probabilidad" | "contribucion" | "ranking",
             "objetivo": "tension_6m", "variable": "runway", "esperado": "<0.5"},
    "evidencia": {"hecho": "H089", "fuente": "D09", "observado": "string", "n": 11193},
    "estado": "pasa" | "falla" | "no_verificable",
    "motivo_no_verificable": "string",                 // solo en no_verificable
    "resultado": null | {"valor": 0.2086, "n": 11121,
                         "ejemplos": [{"company_id": "COMP_0005", "month": "2025-03", "band": "riesgo", "...": 0}]},  // ≤ 6 filas empresa × mes
    "diagnostico": {"veredicto": "string", "texto": "string"},   // fase 3, opcional
    "iteracion": "iter_006"                                       // fase 3, opcional
  }]
}
```

## GET /api/situaciones/{id}
Una situación (mismo objeto que en la lista); 404 si no existe.

## GET /api/proactive?company_id=COMP_0004&month=2026-06&horizon=6
Motor proactivo: **proyección de tesorería aritmética** (sin LGBM ni forecaster) en el mes `T = month` (por defecto el último),
decisión y producto según la política de la fase 1, score del **modelo vigente sin reentrenar** y, si `T+2` está en el panel, el desenlace real.
`horizon` entre 1 y 12. 404 si la empresa o el mes no existen.
```jsonc
{
  "company_id": "COMP_0004", "month": "2026-06", "currency": "EUR", "has_erp": true,
  "meses_disponibles": ["2026-01", "..."],
  "score": 51.2, "band": "vigilar", "confidence": 0.89,
  "accion": "lend" | "watch" | "decline" | "sin_nota",
  "producto": "factoring" | "confirming" | "linea" | "refi" | "ninguna",
  "meses_antelacion": null | 2,                          // primer h con caja proyectada < 0 (o tensión)
  "decision": {
    "accion": "lend", "accion_label": "Prestar", "regla": "C2",   // regla de la política que manda (C0..C9)
    "producto": "ninguna", "producto_label": "Ninguna", "producto_texto": "string en lenguaje llano",
    "necesita_deuda_2m": false, "meses_antelacion": null,
    "razones": [{"codigo": "C2", "senal": "Meses de caja", "valor": "1,3 meses", "texto": "por qué importa, en llano"}],
    "recorte_importe": ["sin ERP: ... (importe × 0,5)"], "importe_max": 478473.1 | null
  },
  "proyeccion": {
    "modo": "facturas" | "bancario",                    // bancario = sin ERP: medianas bancarias en lugar de facturas
    "variante": "completa" | "estricta",
    "caja_inicial": 269235.7, "poliza_disponible": 1.0e6, "gasto_mensual": 956946.2, "umbral_tension": 239236.6, "meses_caja": 1.33,
    "cobertura_facturas": 0.49 | null,                   // facturas liquidadas 6m / flujos bancarios 6m
    "fiabilidad": "alta" | "media" | "baja" | "sin facturas" | "sin dato",   // alta = cobertura 0,4-1,0
    "formula": "caja(T+h) = caja(T) + cobros pendientes(T,T+h] − pagos pendientes(T,T+h] − nóminas×h − cuotas×h",
    "lineas": [{"clave": "cobros_pendientes", "signo": 1, "label": "string", "fuente": "de dónde sale el número",
                "por_mes": [114417.5, 267638.7], "total": 1414754.9, "n": 39 | null}],
    "meses": [{"h": 1, "month": "2026-07", "caja": 252626.5, "liquidez": 1252626.5, "rotura": false, "tension": false}],
    "rotura_h": null | 2, "tension_h": null | 1, "hueco": 0.0, "hueco_2m": 0.0,   // hueco = lo que falta para no romper/tensionar en el horizonte; hueco_2m, a 2 meses
    "anticipable": {"total": 1414754.9, "por_vencer_h": 1414754.9, "n": 39, "anticipo_estimado": 1131803.9, "n_contrapartes": 8},  // facturas emitidas NO vencidas
    "ap_pendiente": {"total": 423984.9, "n": 96},
    "efectos": {"n_6m": 65, "importe_6m": 4445.7, "share_cobros_6m": 0.0},   // «pagaré/efecto/remesa» en la descripción bancaria
    "productos_contratados": ["confirming", "loan"]
  },
  "panel_T": {"cash_end": 0, "inflow": 0, "outflow": 0, "payroll": 0, "debt_service": 0, "lc_drawn": 0, "lc_limit": 0, "...": 0},
  "senales": {"runway": {"valor": 0.25, "texto": "0,3 meses", "label": "Meses de caja"}, "mc": {"...": 0}},
  "contribuciones": [{"feature": "lc_util", "label": "string", "pillar": "liquidez", "puntos": 9.9, "valor": 0.0, "valor_texto": "0 %"},  // explain(): puntos frente al neutro
                     {"feature": "regla_liquidez", "label": "Regla: menos de medio mes de caja no es sano", "pillar": "regla", "puntos": -12.3, "valor": null, "valor_texto": "activa"}],  // reglas D15/D36 solo si actúan
  "explicacion": { /* igual que /api/company.explanation, en T */ },
  "desenlace": {"disponible": true, "rotura_real": false, "tension_real": false,
                "meses": [{"month": "2026-07", "caja_real": 79219.8, "liquidez_real": 1079219.8, "rotura": false, "tension": false,
                           "cobros_reales": 0, "pagos_reales": 0, "nominas_reales": 0, "cuotas_reales": 0, "score": 50.1}]}
                | {"disponible": false, "motivo": "T+2 no está en el panel"}
}
```

## GET /api/proactive/validation
Validación no circular: empresas de un fold de GroupKFold por `group_id`, puntuadas por un scorer que no las vio, recomendadas en cada
`T` sin ver el futuro y comprobadas en `T+1..T+2`. Sirve `salida/demo/validacion_proactiva.json` (`proactive.py validate`); si no existe, 200 con `aviso`.
```jsonc
{
  "fold": 0, "n_splits": 5, "h": 2, "n_empresas": 236, "n_grupos": 46, "n_empresa_mes": 3190,
  "lectura": "string: cómo leer las métricas",
  // cada métrica: {"n", "positivos_pred", "positivos_real", "tasa_base", "precision", "recall", "npv", "lift", "tp", "fp", "fn", "tn"}
  "metricas": {"tension_2m_sanas_hoy": {"n": 1833, "tasa_base": 0.0895, "precision": 0.2968, "recall": 0.2805, "npv": 0.9297, "lift": 3.32, "tp": 46, "fp": 109, "fn": 118, "tn": 1560},
               "tension_2m_todas": {}, "necesita_deuda_2m_vs_tension": {}, "rotura_2m_sanas_hoy": {}, "rotura_2m_todas": {},
               "variante_completa_tension_2m_sanas_hoy": {}, "baseline_mc<0.5_tension_2m_todas": {}, "baseline_mc<0.5_tension_2m_sanas_hoy": {}},
  "por_modo": {"facturas": {"tension_2m_sanas_hoy": {}, "tension_2m_todas": {}}, "bancario": {}},
  "por_fiabilidad": {"alta": {}, "media": {}, "baja": {}, "sin facturas": {}},   // tension_2m_sanas_hoy por fiabilidad de la proyección
  "error_caja_h_eur_estricta": {"mediana_abs": 0, "p75_abs": 0, "mediana": 0, "mediana_abs_en_meses_de_gasto": 0},
  "error_caja_h_eur_completa": {"mediana_abs": 0, "p75_abs": 0, "mediana": 0, "mediana_abs_en_meses_de_gasto": 0},
  "casos": [{"tipo": "acierto" | "control_sano" | "falsa_alarma" | "no_detectada", "company_id": "COMP_0001", "group_id": "GROUP_0001", "month": "2026-01",
             "modo": "facturas", "fiabilidad": "alta", "accion": "watch", "producto": "factoring", "mc_T": 0.4, "hueco": 12000.0, "score_oof": 41.2,
             "pred_tension": true, "pred_rotura": false, "real_rotura": false, "real_tension": true}],
  "empresas_held_out": ["COMP_0001"]
}
```
