# Escala de la nota: relativa frente a absoluta

Generado por `src/analisis_escala.py` con `artifacts/xray.joblib` (v6). Meses activos del train. Discusión en `REFLEXIONES.md`.

## 1. Reparto de la nota según la población

| Población | P10 | Mediana | P90 | Riesgo (<35) | Vigilar | Sano (≥65) | % de meses |
|---|---|---|---|---|---|---|---|
| Todos los meses activos | 25 | 50 | 74 | 23% | 56% | 21% | 100 % |
| Caja > 0 | 27 | 51 | 75 | 20% | 57% | 23% | 93% |
| ≥ 3 meses de caja | 42 | 62 | 83 | 4% | 57% | 39% | 20% |
| ≥ 6 meses de caja | 43 | 63 | 83 | 4% | 56% | 40% | 12% |
| 220 empresas sanas · regla fija del train | 42 | 63 | 84 | 4% | 53% | 43% | — |
| 220 empresas sanas · regla reajustada solo con ellas | 25 | 46 | 73 | 23% | 61% | 16% | — |

## 2. Tamaño (volumen en EUR, quintiles)

Spearman nota ~ tamaño: -0.07

| Quintil | Nota mediana | Meses de caja (mediana) | Saldo negativo 6m | Caída de cobros 6m | Apagado 6m |
|---|---|---|---|---|---|
| Q1 (pequeñas) | 52 | 2.22 | 3.6% | 20.0% | 5.1% |
| Q2 | 52 | 0.91 | 7.2% | 17.5% | 1.9% |
| Q3 | 50 | 0.53 | 4.9% | 14.3% | 2.2% |
| Q4 | 49 | 0.34 | 5.7% | 16.3% | 2.3% |
| Q5 (grandes) | 46 | 0.21 | 5.7% | 16.9% | 3.5% |

Features con |Spearman| > 0,2 frente al tamaño:

- `runway`: -0.35
- `growth_vs_12m`: 0.20
- `payroll_burden`: -0.46
- `transfer_dep`: 0.34
- `net_vol_6m`: -0.37

## 3. Nota → probabilidad de evento adverso (saldo negativo o caída de cobros en 6 meses)

Tasa base: 21.8%. Logística de un parámetro sobre la nota sin suavizar.

| Nota | 10 | 30 | 50 | 70 | 90 |
|---|---|---|---|---|---|
| P(adverso) | 37% | 28% | 21% | 15% | 10% |

## 4. ¿Cuadra la caja reconstruida con los flujos?

Descuadre = |Δcaja − (cobros − pagos)| / max(cobros, pagos), en meses con flujo > 1.000.

- Mediana 0.01, P75 0.23, P90 0.77.
- Meses con descuadre > 50 % del flujo: 15.6%.
- Empresas con más de la mitad de sus meses descuadrados: 10.8%.
