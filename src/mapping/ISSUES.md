# Inventario de fallos y reglas de mapeo

Los CSV de `data/` no se modifican. Cada fila sucia se corrige al cargar en las vistas `*_mapped` (y en los alias públicos `companies`, `transactions`, …). El original queda en `*_raw`.

Leyenda de acción: **canonizar** = sinónimo → valor único; **enriquecer** = columna o flag nuevo; **no inventar** = nulo + cobertura.

## Empresas y grupos

| Fallo | Evidencia | Acción | Salida |
|---|---|---|---|
| País no ISO-2 | `ESPAÑA` 14, `España` 9, `España ` 1, `ESPANYA` 2, `Espanya` 1, `Spain` 1, `Portugal` 5, `Italia` 1, `Alemania` 1, `Malaysia` 1; 1056 nulos | Canonizar nombres → ISO; nulos se quedan nulos; 2 letras se pasan a mayúsculas; resto `_unmapped` | `country`, `country_raw`, `dq_country_unmapped` |
| ERP en dos vocabularios | Grupos: `Microsoft Business Central`; empresas: `businessCentral`. `Infor M3 ` con espacio. `Desarrollo propio` sin código | Crosswalk a código + etiqueta | `erp_code`, `erp_label`, `erp` (= código), `erp_raw`, `dq_erp_unmapped` |
| Alta fuera de ventana | 357 empresas con `created_at` < 2024-09-01 | Enriquecer inicio de observación | `observation_start = max(2024-09-01, mes de created_at)` |
| Sin checking / sin facturas / sin saldo | 4 sin checking; 501 sin facturas; 13 sin balances | No inventar; flags de cobertura. Sin facturas = ERP no conectado, no AR=0 | `has_checking`, `has_invoices`, `erp_connected`, `balance_missing` |

## Productos bancarios y deuda

| Fallo | Evidencia | Acción | Salida |
|---|---|---|---|
| Tipos bancarios fuera del diccionario | `wallet` 34, `risk` 25, `lineofcomex` 19 | Conservar `type`; añadir familia | `type_family`: cash_like / operating / credit_adjacent |
| Banco con casing/espacio | `Paypal` vs `PayPal`; `iberCaja`; `Qonto `; `BANCO SANTANDER TOTTA SA`; `Otros` | Canonizar alias listados; trim; no fusionar `Caixabank` con `Caixabank Empresas` | `bank_name`, `bank_name_raw` |
| Service `_` / `_others` / `ins_*` | `_payhawk`, `_others` 3, `ins_127317` | Quitar `_` inicial; `_others`→`custom`; `ins_*` se queda | `service`, `service_raw`, `service_kind` (`custom` / `connector_id` / `bank_service`) |
| Productos huérfanos | 28 ids solo en txns (p.ej. `PRODUCT_08229`–`08257`); 29 solo en balances (`08230`, `08258`–`08285`); 1 en txn+balance sin catálogo; 2 settlements (`08227`, `08228`) | Registro unificado, no borrar movimientos. Prioridad: catálogo > txn > balance > settlement | `products.catalog_status`: `in_catalog` / `txn_only` / `balance_only` / `settlement_only` |
| Deuda con signo invertido | `granted` negativo 2043/2070; `outstanding` negativo 1351, positivo 145 | Pasivo canónico = valor absoluto; no pisa `granted`/`outstanding` originales | `granted_liability`, `outstanding_liability`, `granted_raw`, `outstanding_raw`, `dq_positive_outstanding`, `dq_granted_outstanding_sign_mismatch`, `dq_outstanding_exceeds_granted` |
| Schedule vs `debt_products` | Magnitud de granted coincide en 19/87 | Exposición desde `debt_products`; schedule solo plazos | `dq_schedule_amount_mismatch` |
| Settlement huérfano | 2 filas | `settlement_product_id` canónico = null | `settlement_product_id`, `settlement_product_id_raw`, `dq_settlement_orphan` |
| `constant quote` | 87/87 | Canonizar (cuota constante) | `amortization_type = constant_installment` |
| `semiannually` | 3 filas | Canonizar | `amortising_frequency = semi_annual` |
| Alta de producto tras el corte | banking 44, debt 19 | Flag | `connected_after_cutoff`, `observation_start` |

## Saldos

| Fallo | Evidencia | Acción | Salida |
|---|---|---|---|
| Saldos absurdo | 17 saldos con \|balance\| > 1e8 en moneda cruda, pero **11 son COP/AOA/VND/CLP/XOF** (1e8 COP ≈ 23 k€). En EUR equivalentes quedan 4 de caja (`PRODUCT_00001` 1e11, COMP_0420 −999 999 999 ×2, COMP_0604 1e9) y 2 préstamos plausibles (COMP_0415 −3e8, COMP_0630 −1,25e8) | No recortar; marcar **en EUR aproximados** (`CURRENCY_PER_EUR_APPROX`, orden de magnitud) y **solo en productos de caja** (`CASH_LIKE_TYPES`); sin catálogo se asume caja en EUR | `balance_quality` (`ok`/`suspect`), `dq_balance_suspect`, `balance_eur_approx`, `product_currency` |
| Foto no el 2026-09-01 | 16 filas 25–29 ago | Aceptar como as-of (diccionario) | `date` sin cambiar |

## Transacciones

| Fallo | Evidencia | Acción | Salida |
|---|---|---|---|
| Categoría `-` / null | `-` 635 530; null 330 | Canonizar a `uncategorized` | `category`, `category_raw` |
| Typo `cash_settlements` | 90 vs `cash_settlement` 48 280 | Canonizar | `category` |
| `value_date` 2099 o gap > 30d | 8 en 2099-12-31; 793 anteriores a la ventana | Usar `date` | `value_date_clean`, `value_date_raw` |
| `exchange_rate` ≤ 0 | 77 (todas de COMP_0440, productos EUR/USD de una empresa en VND) | Null | `exchange_rate`, `exchange_rate_raw` |
| `counterparty_id` ancho variable | **No es suciedad.** Los 59 856 ids de 19 caracteres son números reales 100 000–129 701; ningún número aparece con dos anchos; el cruce tx∩facturas con las cadenas crudas ya da 42 125 de 47 796 | El `lpad` a 6 se conserva por compatibilidad: es inocuo (se aplica igual a ambas tablas) pero innecesario | `counterparty_id`, `counterparty_id_raw` |
| Importe centinela | 491 tx con \|amount\| > 1e8 en moneda cruda, pero 478 son AOA/COP/VND/CLP (COMP_0900: 3,1e9 AOA = 2,9 M€). En EUR: **13 tx en 7 empresas**, importes redondos (1e9, 3e8, 1,575e8, 1,05e8) | Marcar en EUR aproximados por la moneda del producto; no borrar | `dq_amount_sentinel`, `product_currency` |

## Facturas

| Fallo | Evidencia | Acción | Salida |
|---|---|---|---|
| Status mezclado | `cancel` 13 699; `paymentOrder` 406 | Canonizar snake_case | `status` (`cancelled`, `payment_order`), `status_raw` |
| Overdue con `payment_date` = `due_date` | ~186 638 | `payment_date` canónico null (era alias del vencimiento) | `payment_date`, `payment_date_raw`, `payment_date_was_due_alias` |
| Fechas imposibles | `due < issuance` 18 389; `payment < issuance` 22 302 | Flag, no reescribir | `dq_due_before_issuance`, `dq_paid_before_issuance` |
| Pending vs amount | \|pending\| > \|amount\| 114; signos opuestos 888 | Flag | `dq_pending_exceeds_amount`, `dq_pending_sign_mismatch` |
| Importe centinela | 159 con \|amount\| > 1e8 en moneda cruda, casi todas COP (COMP_1244, COMP_0629); **14 en EUR** (COMP_0042 cancel, COMP_0521, COMP_0994) | Flag en EUR aproximados por `currency` | `dq_amount_sentinel` |
| Emitidas el día de la foto | 4 642 con `issuance_date` = 2026-09-01 00:00 y 591 con hora dentro de ese día; **0 posteriores al día** | Flag defensivo (día > foto); el panel las excluye de los cierres anteriores por construcción | `dq_issued_after_snapshot` |
| Importe cero / sin contraparte | `amount = 0` 1 183 (todas `paid`); `counterparty_id` nulo 11 457 (81 M€ AR y 511 M€ AP reales) | Flag; las sin contraparte cuentan en AR/AP total pero no en concentración ni clientes perdidos | `dq_amount_zero`, `dq_counterparty_missing` |

## Fuera de esta capa

- Conversión FX a moneda de empresa (aquí solo `CURRENCY_PER_EUR_APPROX`, para flags de orden de magnitud).
- Reconstrucción histórica de saldos. Sus flags de calidad viven en `research/src/panel.py`: `dq_cash_sentinel`, `has_drift`, `dq_cash_implausible` (suelo en EUR), `dq_edge_month`, `intragroup_share_3m`, `ar_id_coverage`, `n_sentinel_tx`. El veredicto del consejo está en `.devin/workflows/autoresearch/salida/datos_limpieza.md`.
- `research/data/companies.parquet` se genera con `research/src/ingest.py` directamente desde los CSV, sin pasar por estas vistas: conserva `ESPAÑA` (14) junto a `ES` (142). El país no es feature, pero la trazabilidad diverge.
- Mojibake en `description` / `concept`.
- `accounting_status` en SCREAMING_SNAKE.
- `transaction_id` heterogéneo (se trata como string opaco).
