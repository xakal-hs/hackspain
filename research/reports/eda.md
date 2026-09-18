# EDA X-Ray

## Historia por empresa (meses)
```
shape: (9, 2)
┌────────────┬───────────┐
│ statistic  ┆ value     │
│ ---        ┆ ---       │
│ str        ┆ f64       │
╞════════════╪═══════════╡
│ count      ┆ 1286.0    │
│ null_count ┆ 0.0       │
│ mean       ┆ 16.902799 │
│ std        ┆ 6.536033  │
│ min        ┆ 1.0       │
│ 25%        ┆ 10.0      │
│ 50%        ┆ 19.0      │
│ 75%        ┆ 24.0      │
│ max        ┆ 24.0      │
└────────────┴───────────┘
```

```
Empresas con <6 meses: 5 · <12: 397
```

## Estacionalidad (inflow relativo a la media de la empresa, mediana)
```
shape: (12, 3)
┌─────┬────────────────┬───────────────┐
│ moy ┆ inflow_rel_med ┆ tax_share_med │
│ --- ┆ ---            ┆ ---           │
│ i8  ┆ f64            ┆ f64           │
╞═════╪════════════════╪═══════════════╡
│ 1   ┆ 0.763429       ┆ 0.02178       │
│ 2   ┆ 0.689623       ┆ -0.0          │
│ 3   ┆ 0.762928       ┆ -0.0          │
│ 4   ┆ 0.856106       ┆ 0.022636      │
│ 5   ┆ 0.775712       ┆ -0.0          │
│ …   ┆ …              ┆ …             │
│ 8   ┆ 0.681242       ┆ -0.0          │
│ 9   ┆ 0.704496       ┆ -0.0          │
│ 10  ┆ 0.818693       ┆ 0.037663      │
│ 11  ┆ 0.670868       ┆ -0.0          │
│ 12  ┆ 0.885925       ┆ -0.0          │
└─────┴────────────────┴───────────────┘
```

## Distribución de features
```
shape: (11, 16)
┌───────────┬───────────┬───────────┬───────────┬───┬───────────┬───────────┬───────────┬──────────┐
│ statistic ┆ net_margi ┆ runway_lo ┆ cash_nega ┆ … ┆ ar_overdu ┆ top_clien ┆ net_vol_6 ┆ activity │
│ ---       ┆ n_3m      ┆ g         ┆ tive      ┆   ┆ e_ratio   ┆ t_share   ┆ m         ┆ _log     │
│ str       ┆ ---       ┆ ---       ┆ ---       ┆   ┆ ---       ┆ ---       ┆ ---       ┆ ---      │
│           ┆ f64       ┆ f64       ┆ f64       ┆   ┆ f64       ┆ f64       ┆ f64       ┆ f64      │
╞═══════════╪═══════════╪═══════════╪═══════════╪═══╪═══════════╪═══════════╪═══════════╪══════════╡
│ count     ┆ 21737.0   ┆ 21565.0   ┆ 21565.0   ┆ … ┆ 5915.0    ┆ 6218.0    ┆ 19166.0   ┆ 21737.0  │
│ null_coun ┆ 0.0       ┆ 172.0     ┆ 172.0     ┆ … ┆ 15822.0   ┆ 15519.0   ┆ 2571.0    ┆ 0.0      │
│ t         ┆           ┆           ┆           ┆   ┆           ┆           ┆           ┆          │
│ mean      ┆ -0.041968 ┆ 1.02997   ┆ 0.060839  ┆ … ┆ 1.597715  ┆ 0.707731  ┆ 0.961579  ┆ 4.682749 │
│ std       ┆ 0.330866  ┆ 1.313936  ┆ 0.239041  ┆ … ┆ 4.364129  ┆ 0.288965  ┆ 1.925497  ┆ 1.648178 │
│ min       ┆ -1.0      ┆ 0.0       ┆ 0.0       ┆ … ┆ 5.3969e-8 ┆ 0.034459  ┆ 0.0       ┆ 0.0      │
│ …         ┆ …         ┆ …         ┆ …         ┆ … ┆ …         ┆ …         ┆ …         ┆ …        │
│ 5%        ┆ -0.951292 ┆ 0.0       ┆ 0.0       ┆ … ┆ 0.001172  ┆ 0.182095  ┆ 0.000419  ┆ 1.791759 │
│ 50%       ┆ -2.4668e- ┆ 0.528094  ┆ 0.0       ┆ … ┆ 0.244274  ┆ 0.771664  ┆ 0.369925  ┆ 4.85203  │
│           ┆ 16        ┆           ┆           ┆   ┆           ┆           ┆           ┆          │
│ 95%       ┆ 0.40719   ┆ 4.635095  ┆ 1.0       ┆ … ┆ 8.146633  ┆ 1.0       ┆ 4.018272  ┆ 7.24065  │
│ 99%       ┆ 0.974353  ┆ 5.0       ┆ 1.0       ┆ … ┆ 24.0      ┆ 1.0       ┆ 10.0      ┆ 7.922624 │
│ max       ┆ 1.0       ┆ 5.0       ┆ 1.0       ┆ … ┆ 24.0      ┆ 1.0       ┆ 10.0      ┆ 9.335474 │
└───────────┴───────────┴───────────┴───────────┴───┴───────────┴───────────┴───────────┴──────────┘
```

## Tasa de nulos
```
shape: (15, 2)
┌──────────────────┬──────────┐
│ column           ┆ column_0 │
│ ---              ┆ ---      │
│ str              ┆ f64      │
╞══════════════════╪══════════╡
│ net_margin_3m    ┆ 0.0      │
│ runway_log       ┆ 0.007913 │
│ cash_negative    ┆ 0.007913 │
│ growth_3m        ┆ 0.177393 │
│ debt_burden      ┆ 0.0      │
│ …                ┆ …        │
│ ap_overdue_ratio ┆ 0.649768 │
│ ar_overdue_ratio ┆ 0.727883 │
│ top_client_share ┆ 0.713944 │
│ net_vol_6m       ┆ 0.118278 │
│ activity_log     ┆ 0.0      │
└──────────────────┴──────────┘
```

## Escala (log inflow mensual)
```
shape: (9, 2)
┌────────────┬───────────┐
│ statistic  ┆ value     │
│ ---        ┆ ---       │
│ str        ┆ f64       │
╞════════════╪═══════════╡
│ count      ┆ 21737.0   │
│ null_count ┆ 0.0       │
│ mean       ┆ 11.01559  │
│ std        ┆ 4.466608  │
│ min        ┆ 0.0       │
│ 1%         ┆ 0.0       │
│ 50%        ┆ 12.050101 │
│ 99%        ┆ 19.137916 │
│ max        ┆ 22.973226 │
└────────────┴───────────┘
```

```
Meses con caja reconstruida negativa: 0.061; null caja: 0.008
```

```
Meses con inflow=0 (actividad esporádica): 0.096
```

## Eventos ocasionales: meses con pago de impuestos por empresa
```
shape: (9, 2)
┌────────────┬──────────┐
│ statistic  ┆ value    │
│ ---        ┆ ---      │
│ str        ┆ f64      │
╞════════════╪══════════╡
│ count      ┆ 1142.0   │
│ null_count ┆ 0.0      │
│ mean       ┆ 9.915061 │
│ std        ┆ 6.813322 │
│ min        ┆ 1.0      │
│ 25%        ┆ 4.0      │
│ 50%        ┆ 8.0      │
│ 75%        ┆ 15.0     │
│ max        ┆ 24.0     │
└────────────┴──────────┘
```

```
Empresas con servicio de deuda algún mes: 717
```

## Top correlaciones Spearman
```
runway_log        net_vol_6m          0.578549
ap_overdue_ratio  ar_overdue_ratio    0.463408
ap_late_share     ar_late_share       0.435561
net_vol_6m        activity_log       -0.431634
runway_log        cash_negative      -0.406651
                  activity_log       -0.401757
ar_overdue_ratio  activity_log       -0.396321
top_client_share  activity_log       -0.383981
ar_late_share     ar_overdue_ratio    0.375300
ap_late_share     ap_overdue_ratio    0.342555
payroll_burden    activity_log        0.339543
net_margin_3m     growth_3m           0.304048
```

## Persistencia (Spearman lag-1)
```
net_margin_3m: 0.51
runway_log: 0.87
cash_negative: 0.77
growth_3m: 0.57
debt_burden: 0.93
payroll_burden: 0.95
refund_rate: 0.82
oper_share: 0.85
ap_late_share: 0.65
ar_late_share: 0.67
ap_overdue_ratio: 0.83
ar_overdue_ratio: 0.82
top_client_share: 0.69
net_vol_6m: 0.93
activity_log: 0.97
```