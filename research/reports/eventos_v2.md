# Eventos v2: medición
Definiciones del panel multi-modelo (`research/brainstorm/eventos/SINTESIS_glm5.3.md`), implementadas en `src/events_v2.py`. Etiqueta a 6 meses: 1 si el evento ocurre en (m, m+6], vacía si el futuro no es observable o la empresa se apaga en la ventana (censura).

## 1. Frecuencia y cobertura

| Evento | Filas etiquetadas | Tasa (empresa-mes) | Empresas con ≥1 evento |
|---|---|---|---|
| Entrada en tensión de caja persistente (solo caja) | 10278 | 2,7 % | 7,2 % |
| E1 contando la póliza disponible como liquidez | 10278 | 2,4 % | 6,4 % |
| Incumplimiento estricto (cualquier componente) | 13341 | 29,6 % | 43,4 % |
|   · nómina regular que desaparece | 13341 | 6,0 % | 12,5 % |
|   · cuota de deuda regular que desaparece | 13341 | 8,4 % | 13,3 % |
|   · IVA ausente 2 trimestres seguidos | 13341 | 1,1 % | 3,1 % |
|   · deuda >90 días con proveedores que se dispara (ERP) | 13341 | 17,1 % | 25,1 % |
| Caída estructural de cobros (sin apagado ni rebote) | 5721 | 10,2 % | 26,6 % |
|   · sin exigir 'sin rebote' | 5721 | 15,9 % | 32,0 % |
| Expansión sostenida autofinanciada | 8219 | 5,9 % | 21,9 % |
|   · sin filtros de autofinanciación ni puntualidad | 8219 | 17,8 % | 50,8 % |
| v1 · Apagado | 8261 | 3,0 % | 9,1 % |
| v1 · Saldo negativo | 7746 | 5,4 % | 10,1 % |
| v1 · Caída de cobros | 8261 | 17,0 % | 38,7 % |
| v1 · Crecimiento | 8261 | 16,3 % | 48,6 % |

## 2. ¿Son eventos reales? Persistencia, rebote y posibles artefactos

- **E1 (arranques de tensión)**: 196 arranques en bruto; 75 confirmados (≥2 de los 3 meses siguientes en tensión) = 38,3 %. De los confirmados: en jul/ago-2026 (borde) 0,0 %; empresa con póliza 17,3 %; con póliza disponible que cubriría el hueco (E1 no se daría con liquidez) 12,0 %; empresa que se apaga en los 3 meses siguientes 6,7 %.
- **E7 recuperación tras E1**: 9,7 % de los arranques de tensión se recuperan con 3 meses seguidos de ≥0,5 meses de caja.
- **E2 (incumplimientos, meses)**: 1988 meses con incumplimiento. Por componente: nómina 291, cuota 394, IVA 37, AP>90 1342. Nómina o cuota que **se retoma al mes siguiente** (posible ruido de calendario o categoría): 38,6 %. En jul/ago-2026: 13,7 %.
- **E3 (caídas limpias)**: 581 filas; rebotan después del horizonte (m+7..m+9 ≥ 80 % de la base): 15,0 %. Exigir 'sin rebote' quita 36,2 % de las caídas brutas.
- **E4 (expansiones limpias)**: 486 filas; revierten después (m+7..m+9 < 1,1× base): 16,9 %. Los filtros quitan 66,8 % de las expansiones brutas.
- **E5 bache** (cobros < 70 % de su mediana y recuperan ≥ 80 % en ≤ 2 meses): 71,6 % de las empresas con ≥ 12 meses tienen alguno; meses con caída que NO se recupera en 2 meses: 45,9 % de las empresas. Ratio bache/caída de meses: 1,66.
- **E6 sano sostenido**: 7,9 % de las empresas (102); con ERP 7,6 %, sin ERP 8,4 %.

## 3. Solapamiento: P(columna = 1 | fila = 1), en 3526 filas con todos observables

| | E1 | E1_liq | E2 | E3 | E4 | churn_6m |
|---|---|---|---|---|---|---|
| **E1** | 100,0 % | 84,1 % | 23,9 % | 12,5 % | 8,0 % | 0,0 % |
| **E1_liq** | 96,1 % | 100,0 % | 24,7 % | 13,0 % | 3,9 % | 0,0 % |
| **E2** | 1,8 % | 1,6 % | 100,0 % | 9,1 % | 5,0 % | 0,0 % |
| **E3** | 3,3 % | 3,0 % | 31,5 % | 100,0 % | 0,0 % | 0,0 % |
| **E4** | 3,8 % | 1,6 % | 31,4 % | 0,0 % | 100,0 % | 0,0 % |
| **churn_6m** | — | — | — | — | — | — |

Censura por apagado: 12,2 % de las caídas de cobros v1 eran apagados; en E3 esa fracción es 0 por construcción.

## 4. AUC de cada feature frente a cada evento

AUC de la feature tal cual (>0,5: más valor → más evento; <0,5: más valor → menos evento). **Negrita**: |AUC − 0,5| ≥ 0,10. Entre paréntesis, la distancia a 0,5 orientada, para leer la fuerza sin mirar el signo. Las filas son empresa-mes con etiqueta observable; n entre 1.000 y 9.000 según feature y evento.

| Feature | E1 | E1_liq | E2 | E3 | E4 | churn_6m |
|---|---|---|---|---|---|---|
| `runway` | **0,68** | **0,66** | 0,49 | 0,49 | 0,44 | 0,51 |
| `lc_util` | **0,30** | 0,40 | 0,48 | 0,44 | 0,46 | **0,30** |
| `net_margin_6m` | 0,51 | 0,49 | 0,52 | 0,52 | 0,47 | 0,48 |
| `growth_vs_12m` | 0,46 | 0,43 | 0,52 | 0,41 | 0,59 | 0,48 |
| `debt_burden` | 0,48 | 0,49 | 0,56 | 0,47 | 0,47 | 0,45 |
| `payroll_burden` | 0,48 | 0,55 | 0,47 | 0,47 | 0,52 | 0,44 |
| `ap_late_share` | 0,49 | 0,45 | **0,61** | 0,52 | 0,50 | **0,70** |
| `ar_late_share` | 0,54 | 0,50 | 0,57 | 0,55 | 0,48 | **0,62** |
| `ap_overdue_ratio` | 0,51 | 0,50 | **0,72** | 0,53 | 0,52 | 0,53 |
| `ar_overdue_90_ratio` | 0,49 | 0,48 | 0,58 | 0,48 | 0,48 | 0,50 |
| `refund_rate` | 0,49 | 0,47 | 0,51 | 0,48 | 0,51 | 0,50 |
| `activity_trend` | 0,49 | 0,48 | 0,51 | **0,36** | 0,60 | 0,41 |
| `transfer_dep` | 0,48 | 0,48 | 0,50 | 0,47 | 0,51 | 0,43 |
| `hhi_ar_6m` | 0,52 | 0,51 | 0,46 | 0,54 | 0,50 | 0,54 |
| `net_vol_6m` | 0,56 | 0,58 | 0,50 | 0,53 | 0,46 | 0,48 |
| `cust_trend` | 0,48 | 0,49 | 0,51 | 0,46 | 0,53 | **0,39** |
| `lost_share` | 0,48 | 0,46 | 0,45 | **0,60** | 0,44 | **0,72** |
| `payee_concentration` *(brainstorming)* | 0,59 | 0,54 | 0,51 | **0,62** | **0,39** | **0,76** |
| `lost_accel` *(brainstorming)* | **0,66** | **0,65** | 0,53 | 0,56 | 0,51 | **0,74** |
| `payroll_cv` *(brainstorming)* | 0,58 | 0,52 | 0,53 | **0,62** | 0,57 | **0,69** |
| `payroll_continuity_6m` *(brainstorming)* | **0,37** | **0,39** | 0,53 | 0,41 | 0,49 | **0,34** |
| `tax_miss` *(brainstorming)* | 0,51 | 0,49 | 0,50 | 0,52 | 0,55 | **0,62** |
| `billing_to_cash` *(brainstorming)* | 0,49 | 0,44 | 0,54 | 0,43 | 0,57 | **0,33** |
| `oper_persistence_6m` *(brainstorming)* | 0,50 | 0,49 | 0,48 | **0,39** | 0,56 | 0,53 |
| `yoy_inflow` *(brainstorming)* | 0,54 | 0,52 | 0,53 | **0,39** | 0,56 | 0,42 |
| `multi_signal_stress` *(brainstorming)* | 0,54 | 0,55 | 0,55 | **0,60** | 0,45 | 0,54 |
| `hhi_ap_6m` *(brainstorming)* | 0,59 | 0,58 | 0,49 | **0,61** | 0,46 | **0,60** |

## 5. Features del brainstorming: ¿su señal era desconexión?

| Feature | AUC frente a apagado | Mejor |AUC−0,5| frente a E1-E4 | ¿Sobrevive? |
|---|---|---|---|
| `payee_concentration` | 0,76 (fuerza 0,26) | 0,12 | sí |
| `lost_accel` | 0,74 (fuerza 0,24) | 0,16 | sí |
| `payroll_cv` | 0,69 (fuerza 0,19) | 0,12 | sí |
| `payroll_continuity_6m` | 0,66 (fuerza 0,16) | 0,13 | sí |
| `tax_miss` | 0,62 (fuerza 0,12) | 0,05 | débil |
| `billing_to_cash` | 0,67 (fuerza 0,17) | 0,07 | débil |
| `oper_persistence_6m` | 0,53 (fuerza 0,03) | 0,11 | sí |
| `yoy_inflow` | 0,58 (fuerza 0,08) | 0,11 | sí |
| `multi_signal_stress` | 0,54 (fuerza 0,04) | 0,10 | sí |
| `hhi_ap_6m` | 0,60 (fuerza 0,10) | 0,11 | sí |

## 6. Circularidad

- Meses de caja de hoy frente a E1: AUC 0,32 (frente a 'saldo negativo' v1: 0,77). Si baja, el nuevo evento es menos circular: exige entrar en tensión desde una situación sana.
- Tendencia de cobros de hoy frente a E3: AUC 0,59 (frente a 'caída de cobros' v1: 0,57).

## 7. Casos para revisar a mano (3 por evento, aleatorios)


**E1 arranque confirmado** · COMP_1155 · 2026-02 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-10     1.0      1.0      14.0     37.27       NaN       NaN     -0.0          -0.0 -0.0     7                      0
2025-11     0.0      0.0      14.0     35.44       NaN       NaN     -0.0          -0.0 -0.0     1                      0
2025-12     0.0      0.0      14.0     31.83       NaN       NaN     -0.0          -0.0 -0.0     5                      0
2026-01    43.0     43.0      14.0      0.95       NaN       NaN     -0.0          -0.0 -0.0    23                      0
2026-02  1875.0   2282.0      14.0      0.02       NaN       NaN    912.0          -0.0  0.0    85                      0
2026-03  3895.0   3376.0      14.0      0.01       NaN       NaN    654.0          -0.0 -0.0   128                      0
2026-04  1491.0   1515.0      14.0      0.01       NaN       NaN    243.0          -0.0  0.0    56                      0
2026-05   845.0    724.0      14.0      0.01       NaN       NaN    213.0          -0.0 -0.0    33                      0
2026-06   198.0    103.0      14.0      0.02       NaN       NaN     24.0          -0.0 -0.0    21                      0
2026-07    24.0    175.0      14.0      0.02       NaN       NaN      6.0          -0.0  0.0    21                      0
2026-08     9.0     11.0      22.0      0.03       NaN       NaN      2.0           0.0 -0.0     8                      0
```

**E1 arranque confirmado** · COMP_0645 · 2025-06 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-03   695.0   5247.0    3804.0      0.72       NaN       NaN     -0.0          -0.0 -0.0    14                      0
2025-04     9.0      0.0    3812.0      1.45       NaN       NaN     -0.0          -0.0  0.0     4                      0
2025-05     0.0      0.0    3812.0      2.18       NaN       NaN      0.0           0.0  0.0     0                      0
2025-06   586.0   7751.0     147.0      0.05       NaN       NaN     -0.0          -0.0 -0.0    14                      0
2025-07     4.0      4.0     148.0      0.06       NaN       NaN     -0.0          -0.0  0.0     6                      0
2025-08     0.0      0.0     148.0      0.06       NaN       NaN      0.0           0.0  0.0     0                      0
2025-09   486.0   5053.0     130.0      0.05       NaN       NaN     -0.0          30.0 -0.0    14                      0
2025-10     1.0      8.0     124.0      0.05       NaN       NaN     -0.0          -0.0 -0.0     4                      0
2025-11     1.0      5.0     120.0      0.06       NaN       NaN     -0.0           3.0 -0.0     3                      0
2025-12   465.0   4979.0     106.0      0.05       NaN       NaN     -0.0          -0.0 -0.0    14                      0
2026-01     0.0      2.0     104.0      0.05       NaN       NaN     -0.0           2.0  0.0     6                      0
```

**E1 arranque confirmado** · COMP_0760 · 2026-05 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2026-01   225.0     83.0     290.0      4.10       NaN       NaN     19.0          26.0 14.0   136                      0
2026-02   234.0    330.0     195.0      1.25       NaN       NaN     20.0          -0.0 -0.0   153                      0
2026-03    60.0     62.0     193.0      1.22       NaN       NaN     20.0          -0.0 -0.0   172                      0
2026-04    41.0     73.0     160.0      1.03       NaN       NaN     23.0           0.0  5.0   168                      0
2026-05    88.0    287.0     -39.0     -0.27       NaN       NaN     38.0          -0.0  1.0   243                      0
2026-06    86.0     91.0     -44.0     -0.29       NaN       NaN     39.0           0.0  0.0   245                      0
2026-07    55.0     99.0     -88.0     -0.55       NaN       NaN     37.0           0.0  9.0   223                      0
2026-08    83.0     59.0     -64.0     -0.61       NaN       NaN     34.0          -0.0  0.0    79                      0
```

**E2 incumplimiento** · COMP_1069 · 2025-08 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-04     0.0      5.0       1.0      0.26       NaN       NaN     -0.0          -0.0 -0.0     2                      0
2025-05     2.0      6.0       2.0      0.35       NaN       NaN     -0.0           2.0 -0.0     4                      0
2025-06     0.0      1.0       1.0      0.18       NaN       NaN     -0.0          -0.0 -0.0     1                      0
2025-07    17.0     27.0      19.0      1.75       NaN       NaN     -0.0          -0.0 -0.0     6                      0
2025-08     0.0     37.0       7.0      0.32       NaN       NaN     -0.0          -0.0 37.0     2                      0
2025-09     0.0      3.0       2.0      0.07       NaN       NaN     -0.0          -0.0 -0.0     3                      0
2025-10     0.0      1.0       2.0      0.13       NaN       NaN     -0.0          -0.0 -0.0     1                      0
2025-11     0.0     34.0       2.0      0.18       NaN       NaN     -0.0          -0.0 -0.0     3                      0
2025-12     0.0    133.0       2.0      0.04       NaN       NaN     -0.0          -0.0  4.0    12                      0
2026-01   214.0     30.0       5.0      0.08       NaN       NaN     -0.0          -0.0  1.0    16                      0
2026-02     3.0     11.0       2.0      0.03       NaN       NaN     -0.0          -0.0 -0.0    26                      0
2026-03     1.0     12.0       6.0      0.24       NaN       NaN     -0.0          -0.0 -0.0    31                      0
```

**E2 incumplimiento** · COMP_0324 · 2026-08 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service    tax  n_tx  months_since_final_tx
2026-04  5642.0   3821.0     645.0      0.15       NaN       NaN     31.0         138.0 1274.0   959                      0
2026-05  3995.0   3711.0     286.0      0.07       NaN       NaN     32.0         434.0  440.0   886                      0
2026-06  4546.0   3853.0     523.0      0.13       NaN       NaN     38.0         260.0  493.0   893                      0
2026-07  3170.0   2668.0     385.0      0.10       NaN       NaN     36.0          24.0  348.0   858                      0
2026-08  3731.0   3771.0     602.0      0.16       NaN       NaN     33.0          -0.0  874.0   723                      0
```

**E2 incumplimiento** · COMP_0993 · 2026-02 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-10   308.0    481.0     370.0      1.00     175.0       0.0     73.0           5.0 53.0    82                      0
2025-11    54.0     94.0     265.0      0.95     175.0       0.0     14.0           5.0 -0.0    55                      0
2025-12    32.0     45.0     218.0      0.98     175.0       0.0      5.0           5.0 -0.0    53                      0
2026-01   104.0     49.0     180.0      0.82     175.0       0.0     -0.0           6.0 18.0    45                      0
2026-02    10.0     33.0     169.0      0.81     175.0       0.0     -0.0           5.0 -0.0    50                      0
2026-03   108.0     99.0     183.0      0.89     175.0       0.0     -0.0           5.0 -0.0    85                      0
2026-04   115.0     92.0     227.0      1.12     175.0       0.0     15.0           6.0 24.0   172                      0
2026-05   296.0    165.0     477.0      2.47     175.0     102.0     32.0           5.0  0.0   186                      0
2026-06   266.0    254.0     232.0      1.19     175.0       0.0     43.0          10.0 -0.0   227                      0
2026-07   491.0    399.0     265.0      0.97     175.0       0.0     72.0           8.0 19.0   277                      0
2026-08   472.0    328.0     354.0      1.08     175.0       0.0     84.0           5.0  0.0   229                      0
```

**E3 caída limpia (fila de referencia m)** · COMP_1130 · 2025-09 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service    tax  n_tx  months_since_final_tx
2025-05  1433.0    876.0    1283.0      0.82       0.0      -0.0     12.0          -0.0  221.0    30                      0
2025-06  2721.0   5382.0    1196.0      0.55       0.0      -0.0      9.0          -0.0  581.0    55                      0
2025-07     3.0    818.0    1502.0      0.64       0.0      -0.0     10.0          -0.0  801.0    49                      0
2025-08   470.0     36.0    1502.0      0.72       0.0      -0.0     10.0          -0.0 -456.0    12                      0
2025-09     3.0    643.0    1502.0      0.87       0.0      -0.0     10.0          -0.0  599.0    35                      0
2025-10     3.0    728.0    1502.0      1.00       0.0      -0.0     10.0          -0.0  670.0    58                      0
2025-11    33.0    404.0    1502.0      0.99       0.0      -0.0     10.0          -0.0  390.0    27                      0
2025-12  3291.0   3650.0    1502.0      0.94       0.0      -0.0     11.0          -0.0  899.0    50                      0
2026-01   526.0    208.0    1567.0      1.10       0.0      -0.0     13.0          -0.0    9.0    34                      0
2026-02     0.0    140.0    1567.0      1.18       0.0      -0.0     11.0          -0.0  128.0    11                      0
2026-03     3.0    247.0    1567.0      1.40       0.0      -0.0     51.0          -0.0  195.0    17                      0
2026-04    34.0    291.0    1567.0      1.40       0.0      -0.0     10.0          -0.0  247.0    39                      0
```

**E3 caída limpia (fila de referencia m)** · COMP_1170 · 2026-01 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service    tax  n_tx  months_since_final_tx
2025-09     0.0    321.0      28.0      0.05       NaN       NaN      0.0          -0.0  276.0     8                      0
2025-10    49.0    114.0      13.0      0.02       NaN       NaN      0.0          26.0   21.0    12                      0
2025-11     0.0   1081.0       2.0      0.00       NaN       NaN      0.0          -0.0   -0.0     5                      0
2025-12   466.0    131.0     337.0      0.56       NaN       NaN      3.0          -0.0   -0.0    10                      0
2026-01     0.0    144.0      65.0      0.14       NaN       NaN      0.0           2.0    1.0     6                      0
2026-02     7.0    268.0       3.0      0.01       NaN       NaN      0.0          16.0   -0.0     7                      0
2026-03     0.0    454.0      77.0      0.27       NaN       NaN      0.0          -0.0   -0.0     6                      0
2026-04     1.0      9.0      69.0      0.28       NaN       NaN      0.0          -0.0    1.0     6                      0
2026-05     0.0     11.0      58.0      0.26       NaN       NaN      0.0          -0.0    1.0     6                      0
2026-06     0.0     42.0      15.0      0.07       NaN       NaN      0.0          -0.0   -0.0     3                      0
2026-07     0.0   1055.0      75.0      0.20       NaN       NaN      0.0          -0.0 1050.0     6                      0
2026-08     0.0      2.0      73.0      0.20       NaN       NaN      0.0          -0.0   -0.0     2                      0
```

**E3 caída limpia (fila de referencia m)** · COMP_0438 · 2025-11 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-07   134.0     61.0     310.0      0.81       NaN       NaN     -0.0          -0.0 25.0    21                      0
2025-08     0.0     33.0     277.0      0.78       NaN       NaN     -0.0          -0.0 -0.0    18                      0
2025-09    60.0      4.0     333.0      0.95       NaN       NaN     -0.0          -0.0  1.0    13                      0
2025-10    35.0     99.0      20.0      0.06       NaN       NaN     -0.0          -0.0 26.0    25                      0
2025-11   105.0     17.0     108.0      0.36       NaN       NaN     -0.0          -0.0 -0.0    13                      0
2025-12   203.0    304.0       7.0      0.02       NaN       NaN     -0.0          -0.0  0.0    23                      0
2026-01    55.0     55.0       7.0      0.03       NaN       NaN     -0.0          -0.0  2.0    63                      0
2026-02    29.0     29.0       7.0      0.04       NaN       NaN     -0.0          -0.0 -0.0    33                      0
2026-03    95.0     95.0       7.0      0.06       NaN       NaN     -0.0          -0.0  2.0    29                      0
2026-04    30.0     31.0       7.0      0.08       NaN       NaN     -0.0          -0.0  2.0    21                      0
2026-05     6.0      6.0       7.0      0.11       NaN       NaN     -0.0          -0.0 -0.0    18                      0
2026-06     5.0      5.0       7.0      0.11       NaN       NaN     -0.0          -0.0 -0.0    14                      0
```

**E4 expansión limpia (fila de referencia m)** · COMP_0186 · 2025-04 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2024-12   537.0    601.0     342.0      1.69       NaN       NaN     -0.0         500.0 -0.0    13                      0
2025-01     0.0      9.0      31.0      0.15       NaN       NaN      2.0           0.0  1.0    10                      0
2025-02     0.0     32.0       9.0      0.04       NaN       NaN      3.0           0.0 -0.0    14                      0
2025-03     0.0     34.0       4.0      0.03       NaN       NaN      3.0           0.0 -0.0    14                      0
2025-04     1.0     67.0       8.0      0.07       NaN       NaN      5.0           0.0  3.0    24                      0
2025-05   127.0    275.0      46.0      0.36       NaN       NaN      6.0           0.0  0.0    39                      0
2025-06     1.0    127.0      19.0      0.12       NaN       NaN     21.0           0.0  0.0    37                      0
2025-07    97.0    231.0      16.0      0.07       NaN       NaN     41.0           0.0  6.0   130                      0
2025-08    93.0    196.0      13.0      0.07       NaN       NaN     51.0           0.0 -0.0   127                      0
2025-09    77.0    199.0      22.0      0.11       NaN       NaN     48.0           0.0  0.0   148                      0
2025-10    64.0    114.0      11.0      0.06       NaN       NaN     42.0           0.0  9.0   133                      0
2025-11    54.0     94.0      47.0      0.29       NaN       NaN     34.0           0.0  0.0   116                      0
```

**E4 expansión limpia (fila de referencia m)** · COMP_1098 · 2025-09 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-05   110.0     97.0     101.0      1.04       NaN       NaN      1.0          -0.0 -0.0    22                      0
2025-06    52.0     92.0      70.0      0.73       NaN       NaN      1.0          -0.0 -0.0    11                      0
2025-07   223.0    155.0     146.0      1.28       NaN       NaN      1.0          -0.0  3.0    26                      0
2025-08    86.0    138.0     105.0      0.82       NaN       NaN      1.0          -0.0 -0.0    24                      0
2025-09    62.0     89.0      78.0      0.61       NaN       NaN      1.0          -0.0 -0.0    28                      0
2025-10   107.0    108.0      76.0      0.68       NaN       NaN      1.0          -0.0  2.0    34                      0
2025-11   140.0     59.0     157.0      1.52       NaN       NaN      1.0          -0.0 -0.0    24                      0
2025-12    72.0     38.0     190.0      1.96       NaN       NaN      3.0          -0.0 -0.0    14                      0
2026-01    90.0    179.0     102.0      0.98       NaN       NaN      1.0          -0.0  4.0    31                      0
2026-02   156.0    140.0     118.0      0.99       NaN       NaN      1.0          -0.0 -0.0    37                      0
2026-03   153.0    133.0     144.0      0.96       NaN       NaN      1.0          -0.0 -0.0    18                      0
2026-04   148.0    136.0     156.0      1.15       NaN       NaN      1.0          -0.0  3.0    26                      0
```

**E4 expansión limpia (fila de referencia m)** · COMP_1122 · 2025-11 (importes en miles)

```
  month  inflow  outflow  cash_end  runway_m  lc_limit  lc_drawn  payroll  debt_service  tax  n_tx  months_since_final_tx
2025-07   123.0     86.0     171.0      1.47       NaN       NaN     -0.0          -0.0 -0.0    23                      0
2025-08   199.0    200.0     170.0      1.34       NaN       NaN     -0.0          -0.0 -0.0    22                      0
2025-09   219.0    119.0     269.0      1.99       NaN       NaN     -0.0          -0.0 -0.0    24                      0
2025-10    96.0    103.0     263.0      1.87       NaN       NaN     -0.0          -0.0 -0.0    19                      0
2025-11   105.0    277.0      91.0      0.54       NaN       NaN     -0.0          -0.0 -0.0    25                      0
2025-12   241.0     76.0     255.0      1.68       NaN       NaN     -0.0          -0.0 -0.0    27                      0
2026-01   134.0    127.0     262.0      1.64       NaN       NaN     -0.0          -0.0 -0.0    22                      0
2026-02   786.0    448.0     600.0      2.76       NaN       NaN     -0.0          -0.0 -0.0    38                      0
2026-03   108.0    486.0     222.0      0.63       NaN       NaN     -0.0          -0.0 -0.0    25                      0
2026-04   245.0    122.0     344.0      0.98       NaN       NaN     -0.0          -0.0 -0.0    30                      0
2026-05   173.0    275.0     242.0      0.82       NaN       NaN     -0.0          -0.0 -0.0    41                      0
2026-06   142.0    130.0     254.0      1.24       NaN       NaN     -0.0          -0.0 -0.0    24                      0
```

## 8. Hallazgos de la revisión y correcciones

1. **E1 hay que medirlo dentro del conjunto en riesgo.** Solo puede "entrar en tensión" quien hoy está sano (≥0,5 meses de caja y caja ≥0). Medido sobre todas las filas, tener más caja parece predecir más tensión (AUC 0,68), un sesgo de selección. En el conjunto en riesgo (5.722 empresas-mes, 255 con evento, 4,5 %):
   - Los meses de caja actuales **casi no predicen** la entrada en tensión (|AUC − 0,5| < 0,03).
   - Las mejores señales son: aceleración en la pérdida de clientes, 0,65; uso de póliza, 0,35 (usarla protege); continuidad de la nómina, 0,40; nómina irregular, 0,59.
2. **E2, tal como lo define el panel, no discrimina.**
   - Marca el 29,6 % de las empresas-mes, dominado por el componente de deuda >90 días con proveedores (17 %).
   - El 38,6 % de las nóminas o cuotas "desaparecidas" reaparecen al mes siguiente.
   - El 31 % de las expansiones (E4) también tienen "incumplimiento".

   **Versión estricta** (nómina o cuota regular ausente 2 meses seguidos, con feed activo, sin el componente de proveedores): 7,6 % de las filas y 13,7 % de las empresas. Solapa un 3 % con E4 y un 11 % con E3.
3. **Artefacto de E1: financiación intragrupo (cash pooling).**
   - Ejemplo: COMP_1155, feb-2026. Flujo externo neto de −407.000 € compensado con 1,75 M€ intragrupo; la caja no se mueve.
   - Las filiales que operan con la caja justa porque las financia el grupo "entran en tensión" sin estar en riesgo individual.
   - El 32 % de los arranques de E1 tiene más del 20 % de su flujo intragrupo (el 24 % en el panel). Si se excluyen, quedan 51 de 75.
   - La hipótesis alternativa, flujos por productos sin saldo reconstruido, queda **descartada**: el 99 % del volumen pasa por cuentas corrientes con saldo.
4. **E1 es muy raro.** Hay 196 arranques en bruto, 75 confirmados y 51 si se excluyen los financiados por el grupo. Solo el 9,7 % se recupera. Con tan pocos casos, un AUC contra E1 tiene intervalos de confianza amplios.
5. **Las señales del brainstorming no eran solo desconexión.**
   - Siguen teniendo señal frente a los nuevos eventos: concentración de pagos (0,62 frente a E3), aceleración en la pérdida de clientes (0,66 frente a E1), nómina irregular y continuidad de nómina, concentración de proveedores (0,61 frente a E3).
   - `tax_miss` y `billing_to_cash` se debilitan: eran sobre todo apagado.
6. **Los baches son muy frecuentes.** El 72 % de las empresas con más de 12 meses tiene al menos un mes con cobros por debajo del 70 % de su mediana que se recupera en 2 meses. Por cada caída que no se recupera hay 1,66 baches. Confirma que la pregunta 4 es central.
