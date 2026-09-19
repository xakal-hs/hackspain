# Plan de Ejecución 24h — X-Ray Score

**Objetivo:** Demo funcionando a las 24h que demuestre valor real.

---

## PRINCIPIO RECTORY

**No construir sobre un modelo que no existe.**

1. Primero: `python src/service.py` → `xray.joblib` (baseline v6 funcionando)
2. Segundo: Mejorar features v7 sobre lo que funciona
3. Tercero: Colchón + recomendaciones en la SPA

---

## FASE 0 — Baseline (DÍA 1, hora 0-2) → DEPENDEN DE NADIE

**Objetivo:** Tener el modelo v6 entrenado y la SPA corriendo con datos reales.

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Álvaro** | Ejecutar `python src/service.py`. Verificar que `xray.joblib` se genera. Correr `python src/server.py` y abrir SPA en `http://127.0.0.1:8099/`. | `src/service.py`, `src/server.py` | Modelo entrenado, API corriendo, SPA visible |
| **Jorge** | Verificar que los datos existen: `git lfs pull`. Confirmar que `panel.parquet` tiene 21,538 filas. | `data/` | Datos accesibles |

**Checkpoint Fase 0:**
- [ ] `artifacts/xray.joblib` existe
- [ ] SPA se abre y muestra 1,286 empresas
- [ ] Click en empresa muestra score, historia, forecast

**Si algo falla aquí: parar y arreglar. No avanzar hasta que el baseline funcione.**

---

## FASE 1 — Mejora del Modelo (DÍA 1, hora 2-10) → PARALELO

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Jorge** (features) | Añadir 10 nuevas features a `src/features.py`. Quitar 3 canceladas. Medir AUC real de al menos 3 features nuevas contra `targets.py`. | `src/features.py`, `src/targets.py` | 27 features calculadas, 3 con AUC verificado |
| **Jorge** (infra) | Añadir `group_id` al panel (`src/panel.py`) para `runway_vs_group`. | `src/panel.py` | Panel con group_id |
| **Álvaro** (model) | Actualizar SPEC dict en `src/xray.py` con las 27 features. Quitar 3 canceladas. Actualizar PRIOR_W. | `src/xray.py` | SPEC dict con 27 features, pesos v7 |
| **Álvaro** (calibración) | Verificar que `calibrate=True` funciona con las nuevas features. Correr `run(tag="v7")` y medir si AUC mejora respecto a v6. | `src/xray.py`, `src/evaluate.py` | Métricas v7 vs v6 comparadas |

**Fichas de features con AUC medido (las 3 priorizadas):**

| Feature | AUC medido | Cobertura | ¿Por qué la primero? |
|---|---|---:|---|
| `payee_concentration` (HHI) | 0.75 vs apagado | 40% | AUC más alto de todas. Define HHI simple sobre counterparty_id. |
| `lost_accel` | 0.74 vs apagado | 24% | Delta simple: `lost_share_m − lost_share_{m-3m}`. 2 líneas de código. |
| `oper_persistence_6m` | 0.67 vs caida_6m | 76% | Clave para bache vs estructural. 76% cobertura. |

**Código mínimo viable para las 3:**
```python
# lost_accel: 2 líneas
p = p.with_columns(lost_accel=(pl.col("lost_share") - pl.col("lost_share").shift(3)).over("company_id"))

# payee_concentration: 5 líneas (HHI sobre counterparty_id)
# oper_persistence_6m: 4 líneas (% de meses con oper_in >= 50% mediana 12m)
```

**Total código nuevo para 3 features: ~11 líneas**

**Si tiempo: añadir el resto de 7 features (2B de plan_mejora_scoring.md)**

---

## FASE 2 — Colchón + Recomendaciones (DÍA 1, hora 4-12) → PARALELO CON FASE 1

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Producto** | Añadir `get_colchon(cid)` a `XRayService`: lee `cash_end`, `median_outflow` del panel, calcula `cash_needed = 2 × median_outflow`, `cash_excess = cash_end - cash_needed`, `runway`. Añadir `get_recommendations(cid)`: genera lista de alertas priorizadas. | `src/service.py` | 2 endpoints nuevos: `/api/company/{cid}/colchon` y `/api/company/{cid}/recommendations` |
| **Frontend** | En `static/index.html` viewEmpresa(), añadir panel "Tu colchón este mes" con barra visual. Añadir sección "Recomendaciones" con cards (urgente=rojo, prevención=amarillo, oportunidad=verde). | `static/index.html` | Colchón visible, recomendaciones visibles |

**API Contract:**
```json
// GET /api/company/{cid}/colchon
{ "cash_needed_eur": 45000, "cash_actual_eur": 62000, "cash_excess_eur": 17000,
  "runway_current": 3.2, "runway_h3": 2.1 }

// GET /api/company/{cid}/recommendations
{ "urgent": [{"action": "...", "detail": "...", "impact": "-5.2 pts"}],
  "prevention": [...], "opportunity": [...], "monitoring": [...] }
```

**Código mínimo viable para el colchón (en service.py, dentro de get_colchon):**
```python
def get_colchon(self, cid):
    panel = self.raw[self.raw.company_id == cid].sort("month").to_pandas()
    cur = panel.iloc[-1]
    median_outflow = panel.outflow.median() if len(panel) else 10000
    cash_needed = 2 * median_outflow
    cash_excess = cur.cash_end - cash_needed
    # runway viene de la feature ya calculada
    return {
        "cash_needed_eur": round(cash_needed, 2),
        "cash_actual_eur": round(cur.cash_end, 2),
        "cash_excess_eur": round(cash_excess, 2),
        "runway_current": round(float(cur.get("runway", 0)), 1),
        "runway_h3": round(float(self.forecast.loc[self.forecast.unique_id == cid, "q50"].values[0]), 1)
    }
```

**Código mínimo viable para recomendaciones (en service.py, dentro de get_recommendations):**
```python
def get_recommendations(self, cid):
    fr = self.feats[self.feats.company_id == cid].sort_values("month").iloc[-1]
    cur = self.scored[self.scored.company_id == cid].sort_values("month").iloc[-1]
    fr3 = self.feats[self.feats.company_id == cid].sort_values("month").iloc[-3] if len(self.feats[self.feats.company_id == cid]) > 2 else fr
    
    urgent, prevention, opportunity, monitoring = [], [], [], []
    
    # Reglas simples basadas en features del score
    if cur.score < 55:
        urgent.append({"action": "Score bajo", "detail": f"Score {cur.score:.0f} (< 55)", "impact": f"{cur.band}"})
    if fr.get("runway", 99) < 1:
        urgent.append({"action": "Caja por agotarse", "detail": f"Runway {fr.get('runway'):.1f} meses", "impact": "CRÍTICO"})
    if fr.get("lost_share", 0) > 0.15:
        prevention.append({"action": "Pérdida de clientes", "detail": f"lost_share {fr.get('lost_share'):.0%}", "impact": f"-{fr.get('lost_share') * 50:.1f} pts"})
    if fr.get("cash_end", 0) > fr.get("outflow", 1) * 3:
        opportunity.append({"action": "Colocar excedente", "detail": f"{fr.get('cash_end') - fr.get('outflow') * 2:.0f}€ ociosos", "gain": "+250€/año"})
    if self.forecast.loc[self.forecast.unique_id == cid, "q50"].values[0] < cur.score - 10:
        monitoring.append({"action": "Forecast deterioro", "detail": "Score bajará a 3m", "warning": "Monitorear"})
    
    return {"urgent": urgent, "prevention": prevention, "opportunity": opportunity, "monitoring": monitoring}
```

**Código mínimo viable para la SPA en index.html (dentro de viewEmpresa, después de renderProducts):**
```javascript
// 1. Llamar al endpoint de colchón
const colchon = await fetch(`/api/company/${cid}/colchon`).then(r => r.json());

// 2. Renderizar panel colchón
colchonDiv.innerHTML = `
  <h3>Tu colchón este mes</h3>
  <div style="background:#f0f7ff; padding:16px; border-radius:8px;">
    <div><strong>Colchón necesario:</strong> ${fmtEuros(colchon.cash_needed_eur)} (2 meses de gasto)</div>
    <div><strong>Colchón actual:</strong> ${fmtEuros(colchon.cash_actual_eur)}</div>
    <div><strong>Excedente:</strong> ${fmtEuros(colchon.cash_excess_eur)}</div>
    <div><strong>Runway:</strong> ${colchon.runway_current} meses → h3: ${colchon.runway_h3} meses</div>
  </div>
`;

// 3. Llamar al endpoint de recomendaciones
const recs = await fetch(`/api/company/${cid}/recommendations`).then(r => r.json());

// 4. Renderizar recomendaciones
recsDiv.innerHTML = `
  <h3>Recomendaciones</h3>
  ${recs.urgent.map(r => `<div style="background:#ffe0e0; padding:12px; border-radius:4px; border-left:4px solid red;">
    <strong>URGENTE:</strong> ${r.action} — ${r.detail} (${r.impact})</div>`).join('')}
  ${recs.opportunity.map(r => `<div style="background:#e0ffe0; padding:12px; border-radius:4px; border-left:4px solid green;">
    <strong>OPORTUNIDAD:</strong> ${r.action} — ${r.detail} (${r.gain})</div>`).join('')}
`;
```

---

## FASE 3 — Integración y Demo (DÍA 1, hora 18-24) → DEPENDE DE 1 Y 2

| Persona | Qué hace | Entregable |
|---|---|---|
| **TODO** | Unir: re-entrenar modelo v7, correr SPA con datos reales, verificar que colchón y recomendaciones se ven, practicar presentación de 5 min con la demo | Demo lista para presentar |

**Script de presentación (5 minutos):**
1. **Min 0-1:** "El score X-Ray responde a 6 preguntas del reto. Lo mostramos en la SPA."
2. **Min 1-2:** "Aquí está la cartera: 1,286 empresas. Score 0-100 con bandas. El color indica riesgo."
3. **Min 2-3:** "Aquí está el colchón dinámico: caja real vs lo que necesita. El excedente genera rendimiento."
4. **Min 3-4:** "Aquí las recomendaciones: urgentes, prevención, oportunidad. Cada una vinculada a una feature del score."
5. **Min 4-5:** "Aquí el forecaster: predecimos score a 3 meses. Aquí el simulador: si cobro un 20% más, ¿qué pasa?"

---

## RESUMEN DE PRIORIDADES

| Prioridad | Qué | Por qué |
|---|---|---|
| **P0 — CRÍTICO** | Entrenar modelo v6 | Sin modelo, no hay demo. Todo depende de esto. |
| **P0 — CRÍTICO** | Colchón dinámico en SPA | Es el producto estrella. Sin colchón visible, no hay monetización. |
| **P1 — ALTO** | Recomendaciones accionables | Es lo que diferencia "un score" de "un producto". |
| **P1 — ALTO** | 3 features con AUC verificado | Demuestra que el modelo mejora con datos, no solo con teoría. |
| **P2 — MEDIO** | Resto de 7 features v7 | Mejora el score, pero no es necesario para la demo. |
| **P3 — BAJO** | Panel colchón prolijo, animaciones, etc. | Pulido estético. Viene después de P0 y P1. |

---

## RIESGOS

| Riesgo | Probabilidad | Mitigación |
|---|---:|---|
| `git lfs pull` falla (datos faltantes) | Media | `python src/panel.py` genera panel.parquet si no existe |
| `train_and_save()` falla (datos sucios) | Media | El código ya maneja NaN, inf, OOD. Si falla, identificar columna problemática y añadir NaN handling |
| Colchón: `median_outflow` es NaN | Baja | Si no hay datos, usar fallback de 10,000€ |
| 24h no suficientes para 27 features | Alta | Priorizar 3 primeras (payee_concentration, lost_accel, oper_persistence_6m) |
| El modelo no mejora con v7 features | Esperado | v7 es mejor. Para la demo, v6 funciona y demuestra el valor. |

---

## QUÉ NO HACER EN 24h (para no perder tiempo)

- No añadir todas las 20 features de brainstorming (b-C de features.md)
- No reescribir la SPA completa (ya tiene 6 pestañas)
- No entrenar TimeGPT-2 (necesita API key de Nixtla)
- No implementar marketplace de crédito (0.9% del revenue)
- No añadir alertas por email/SMS (fuera de scope)
- No intentar replicar los AUC de los brainstormings con LLMs (no tienen sentido)

---

*Este plan asume que el código base ya existe (service.py, xray.py, features.py, index.html) y que el modelo necesita ser entrenado. El colchón dinámico ya está parcialmente implementado como producto "yield" en service.py — la tarea principal es exponerlo en la SPA de forma visible.*