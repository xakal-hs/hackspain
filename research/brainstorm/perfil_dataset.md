# Perfil del dataset (generado automáticamente)

## companies (1286 filas)

Esquema: company_id:String, group_id:String, country:String, currency:String, erp:String, created_at:Datetime(time_unit='us', time_zone=None)

Nulos (%): country 82, erp 42

```
shape: (4, 6)
┌────────────┬────────────┬─────────┬──────────┬────────────┬─────────────────────┐
│ company_id ┆ group_id   ┆ country ┆ currency ┆ erp        ┆ created_at          │
│ ---        ┆ ---        ┆ ---     ┆ ---      ┆ ---        ┆ ---                 │
│ str        ┆ str        ┆ str     ┆ str      ┆ str        ┆ datetime[μs]        │
╞════════════╪════════════╪═════════╪══════════╪════════════╪═════════════════════╡
│ COMP_0677  ┆ GROUP_0138 ┆ null    ┆ EUR      ┆ dynamicsAx ┆ 2026-04-08 10:34:39 │
│ COMP_0726  ┆ GROUP_0055 ┆ null    ┆ EUR      ┆ dynamicsAx ┆ 2024-02-16 09:59:35 │
│ COMP_0493  ┆ GROUP_0126 ┆ null    ┆ EUR      ┆ null       ┆ 2024-05-21 08:10:29 │
│ COMP_0359  ┆ GROUP_0110 ┆ null    ┆ EUR      ┆ netsuite   ┆ 2022-12-29 10:43:25 │
└────────────┴────────────┴─────────┴──────────┴────────────┴─────────────────────┘
```

erp: None (541), businessCentral (322), netsuite (143), businessOne (47), sage200 (47), dynamicsAx (42), sageX3 (30), m3Rosetta (21), distritoK (20), navision (18), a3 (14), etendo (11), r3 (10), libra (7), sageIntacct (4), ekon (3), fo (2), sage50 (1), datev (1), holded (1), sapByd (1)

## groups (250 filas)

Esquema: group_id:String, erp:String, n_companies_in_sample:Int64

Nulos (%): erp 64

```
shape: (4, 3)
┌────────────┬──────┬───────────────────────┐
│ group_id   ┆ erp  ┆ n_companies_in_sample │
│ ---        ┆ ---  ┆ ---                   │
│ str        ┆ str  ┆ i64                   │
╞════════════╪══════╪═══════════════════════╡
│ GROUP_0201 ┆ null ┆ 1                     │
│ GROUP_0186 ┆ null ┆ 1                     │
│ GROUP_0025 ┆ null ┆ 2                     │
│ GROUP_0187 ┆ null ┆ 8                     │
└────────────┴──────┴───────────────────────┘
```

erp: None (161), Microsoft Business Central (28), Netsuite (19), Microsoft Navision (6), SAP Business One (6), Sage 200 (5), Sage X3 (4), Sage 50 (3), A3 ERP (2), SAP R3 / S4 (2), Microsoft Dynamics - F&O (2), Microsoft Dynamics - AX 2012 (2), LIBRA (1), Microsoft Dynamics - AX 2009 (1), Distrito K (1), Oracle Cloud (1), Infor M3  (1), Odoo (1), MOVEX (1), Holded (1), Desarrollo propio (1), Etendo (1)

## banking_products (5987 filas)

Esquema: product_id:String, company_id:String, label:String, type:String, bank_name:String, service:String, currency:String, created_at:Datetime(time_unit='us', time_zone=None)

Nulos (%): 

```
shape: (4, 8)
┌───────────────┬────────────┬─────────────┬──────────┬──────────────────────────┬───────────────┬──────────┬─────────────────────┐
│ product_id    ┆ company_id ┆ label       ┆ type     ┆ bank_name                ┆ service       ┆ currency ┆ created_at          │
│ ---           ┆ ---        ┆ ---         ┆ ---      ┆ ---                      ┆ ---           ┆ ---      ┆ ---                 │
│ str           ┆ str        ┆ str         ┆ str      ┆ str                      ┆ str           ┆ str      ┆ datetime[μs]        │
╞═══════════════╪════════════╪═════════════╪══════════╪══════════════════════════╪═══════════════╪══════════╪═════════════════════╡
│ PRODUCT_06627 ┆ COMP_1181  ┆ CHECKING_03 ┆ checking ┆ ING                      ┆ ing           ┆ EUR      ┆ 2026-01-12 08:42:10 │
│ PRODUCT_06089 ┆ COMP_0258  ┆ CHECKING_03 ┆ checking ┆ Banco Sabadell Empresas  ┆ sabadell_emp  ┆ EUR      ┆ 2022-11-29 10:08:17 │
│ PRODUCT_00788 ┆ COMP_1223  ┆ CHECKING_01 ┆ checking ┆ Banco Santander          ┆ santander_emp ┆ EUR      ┆ 2024-05-10 09:49:28 │
│ PRODUCT_06084 ┆ COMP_0686  ┆ CHECKING_08 ┆ checking ┆ Banco Santander Empresas ┆ santander_emp ┆ EUR      ┆ 2026-01-15 11:32:05 │
└───────────────┴────────────┴─────────────┴──────────┴──────────────────────────┴───────────────┴──────────┴─────────────────────┘
```

type: checking (4854), card (796), investment (201), wallet (34), risk (25), tpv (25), expensesPlatform (23), lineofcomex (19), saving (10)

## debt_products (2239 filas)

Esquema: product_id:String, company_id:String, label:String, type:String, bank_name:String, service:String, currency:String, created_at:Datetime(time_unit='us', time_zone=None), granted:Float64, outstanding:Float64, liquidity:Float64

Nulos (%): granted 8, liquidity 64

```
shape: (4, 11)
┌───────────────┬────────────┬─────────────────┬──────────────┬──────────────────────────┬───────────────┬──────────┬─────────────────────┬──────────┬─────────────┬───────────┐
│ product_id    ┆ company_id ┆ label           ┆ type         ┆ bank_name                ┆ service       ┆ currency ┆ created_at          ┆ granted  ┆ outstanding ┆ liquidity │
│ ---           ┆ ---        ┆ ---             ┆ ---          ┆ ---                      ┆ ---           ┆ ---      ┆ ---                 ┆ ---      ┆ ---         ┆ ---       │
│ str           ┆ str        ┆ str             ┆ str          ┆ str                      ┆ str           ┆ str      ┆ datetime[μs]        ┆ f64      ┆ f64         ┆ f64       │
╞═══════════════╪════════════╪═════════════════╪══════════════╪══════════════════════════╪═══════════════╪══════════╪═════════════════════╪══════════╪═════════════╪═══════════╡
│ PRODUCT_06760 ┆ COMP_0909  ┆ GUARANTEE_19    ┆ guarantee    ┆ Banco Santander          ┆ santander_emp ┆ EUR      ┆ 2024-04-04 08:40:31 ┆ -2.8e6   ┆ -2.7978e6   ┆ 223.52    │
│ PRODUCT_06265 ┆ COMP_0919  ┆ CONFIRMING_13   ┆ confirming   ┆ Banco Santander Empresas ┆ santander_emp ┆ EUR      ┆ 2025-11-03 10:37:28 ┆ -1.25e6  ┆ -691198.56  ┆ 558801.44 │
│ PRODUCT_00924 ┆ COMP_0597  ┆ LINEOFCREDIT_01 ┆ lineofcredit ┆ iberCaja                 ┆ ibercaja      ┆ EUR      ┆ 2026-06-16 06:10:43 ┆ -1.2e6   ┆ -1.1408e6   ┆ 59178.21  │
│ PRODUCT_06264 ┆ COMP_0332  ┆ MORTGAGE_27     ┆ mortgage     ┆ Caixabank Empresas       ┆ caixa_emp     ┆ EUR      ┆ 2026-02-19 18:15:27 ┆ -50075.4 ┆ -48240.54   ┆ null      │
└───────────────┴────────────┴─────────────────┴──────────────┴──────────────────────────┴───────────────┴──────────┴─────────────────────┴──────────┴─────────────┴───────────┘
```

type: loan (1022), lineofcredit (536), confirming (229), leasing (179), guarantee (155), mortgage (60), renting (34), factoring (24)

## debt_schedule_config (87 filas)

Esquema: product_id:String, company_id:String, settlement_product_id:String, currency:String, amortization_type:String, interest_calc_method:String, amortising_frequency:String, granted_balance:Float64, outstanding_balance:Float64, total_periods:Int64, next_payment_date:Datetime(time_unit='us', time_zone=None), last_payment_date:Datetime(time_unit='us', time_zone=None), annual_interest_rate_or_spread:Float64, interest_type:String

Nulos (%): 

```
shape: (4, 14)
┌───────────────┬────────────┬───────────────────┬──────────┬───────────────────┬───────────────────┬───────────────────┬─────────────────┬───────────────────┬───────────────┬───────────────────┬───────────────────┬──────────────────┬───────────────┐
│ product_id    ┆ company_id ┆ settlement_produc ┆ currency ┆ amortization_type ┆ interest_calc_met ┆ amortising_freque ┆ granted_balance ┆ outstanding_balan ┆ total_periods ┆ next_payment_date ┆ last_payment_date ┆ annual_interest_ ┆ interest_type │
│ ---           ┆ ---        ┆ t_id              ┆ ---      ┆ ---               ┆ hod               ┆ ncy               ┆ ---             ┆ ce                ┆ ---           ┆ ---               ┆ ---               ┆ rate_or_spread   ┆ ---           │
│ str           ┆ str        ┆ ---               ┆ str      ┆ str               ┆ ---               ┆ ---               ┆ f64             ┆ ---               ┆ i64           ┆ datetime[μs]      ┆ datetime[μs]      ┆ ---              ┆ str           │
│               ┆            ┆ str               ┆          ┆                   ┆ str               ┆ str               ┆                 ┆ f64               ┆               ┆                   ┆                   ┆ f64              ┆               │
╞═══════════════╪════════════╪═══════════════════╪══════════╪═══════════════════╪═══════════════════╪═══════════════════╪═════════════════╪═══════════════════╪═══════════════╪═══════════════════╪═══════════════════╪══════════════════╪═══════════════╡
│ PRODUCT_07615 ┆ COMP_0420  ┆ PRODUCT_03435     ┆ EUR      ┆ constant quote    ┆ 30/360            ┆ monthly           ┆ 750000.0        ┆ 526094.54         ┆ 56            ┆ 2026-06-01        ┆ 2026-05-28        ┆ 0.04             ┆ fixed         │
│               ┆            ┆                   ┆          ┆                   ┆                   ┆                   ┆                 ┆                   ┆               ┆ 00:00:00          ┆ 18:19:36          ┆                  ┆               │
│ PRODUCT_07460 ┆ COMP_1068  ┆ PRODUCT_01564     ┆ EUR      ┆ constant quote    ┆ 30/360            ┆ monthly           ┆ 200.0           ┆ 10000.0           ┆ 12            ┆ 2026-02-10        ┆ 2026-02-10        ┆ 0.05             ┆ variable      │
│               ┆            ┆                   ┆          ┆                   ┆                   ┆                   ┆                 ┆                   ┆               ┆ 00:00:00          ┆ 13:20:20          ┆                  ┆               │
│ PRODUCT_04275 ┆ COMP_0203  ┆ PRODUCT_03737     ┆ EUR      ┆ constant quote    ┆ 30/360            ┆ monthly           ┆ 800000.0        ┆ 40685.98          ┆ 4             ┆ 2026-06-20        ┆ 2026-05-21        ┆ 0.02             ┆ fixed         │
│               ┆            ┆                   ┆          ┆                   ┆                   ┆                   ┆                 ┆                   ┆               ┆ 00:00:00          ┆ 09:02:04          ┆                  ┆               │
│ PRODUCT_02526 ┆ COMP_0770  ┆ PRODUCT_08228     ┆ EUR      ┆ constant quote    ┆ 30/360            ┆ monthly           ┆ 280000.0        ┆ 254247.73         ┆ 75            ┆ 2025-04-30        ┆ 2025-04-24        ┆ 0.05             ┆ fixed         │
│               ┆            ┆                   ┆          ┆                   ┆                   ┆                   ┆                 ┆                   ┆               ┆ 00:00:00          ┆ 15:41:13          ┆                  ┆               │
└───────────────┴────────────┴───────────────────┴──────────┴───────────────────┴───────────────────┴───────────────────┴─────────────────┴───────────────────┴───────────────┴───────────────────┴───────────────────┴──────────────────┴───────────────┘
```

amortization_type: constant quote (87)

amortising_frequency: monthly (79), quarterly (5), semiannually (3)

interest_type: fixed (58), variable (29)

## balances (7996 filas)

Esquema: product_id:String, company_id:String, date:Datetime(time_unit='us', time_zone=None), balance:Float64, available:String, granted:Float64, liquidity:Float64, countable:Float64

Nulos (%): available 100, granted 67, liquidity 76, countable 92

```
shape: (4, 8)
┌───────────────┬────────────┬─────────────────────┬──────────┬───────────┬─────────┬───────────┬───────────┐
│ product_id    ┆ company_id ┆ date                ┆ balance  ┆ available ┆ granted ┆ liquidity ┆ countable │
│ ---           ┆ ---        ┆ ---                 ┆ ---      ┆ ---       ┆ ---     ┆ ---       ┆ ---       │
│ str           ┆ str        ┆ datetime[μs]        ┆ f64      ┆ str       ┆ f64     ┆ f64       ┆ f64       │
╞═══════════════╪════════════╪═════════════════════╪══════════╪═══════════╪═════════╪═══════════╪═══════════╡
│ PRODUCT_07289 ┆ COMP_1036  ┆ 2026-09-01 00:00:00 ┆ 68030.78 ┆ null      ┆ null    ┆ null      ┆ null      │
│ PRODUCT_01796 ┆ COMP_0969  ┆ 2026-09-01 00:00:00 ┆ 246.87   ┆ null      ┆ null    ┆ null      ┆ null      │
│ PRODUCT_03580 ┆ COMP_0119  ┆ 2026-09-01 00:00:00 ┆ 0.0      ┆ null      ┆ -3000.0 ┆ 3000.0    ┆ null      │
│ PRODUCT_01840 ┆ COMP_0967  ┆ 2026-09-01 00:00:00 ┆ -1727.58 ┆ null      ┆ -4000.0 ┆ 2272.42   ┆ null      │
└───────────────┴────────────┴─────────────────────┴──────────┴───────────┴─────────┴───────────┴───────────┘
```

## transactions (2556437 filas)

Esquema: transaction_id:String, company_id:String, product_id:String, date:Datetime(time_unit='us', time_zone=None), value_date:Datetime(time_unit='us', time_zone=None), amount:Float64, exchange_rate:Float64, status:String, accounting_status:String, category:String, description:String, counterparty_id:String

Nulos (%): status 1, accounting_status 62, category 0, description 0, counterparty_id 90

```
shape: (4, 12)
┌───────────────────────────────────────┬────────────┬───────────────┬─────────────────────┬─────────────────────┬──────────┬───────────────┬────────┬──────────────────────────┬──────────┬───────────────────────────────────────────┬─────────────────┐
│ transaction_id                        ┆ company_id ┆ product_id    ┆ date                ┆ value_date          ┆ amount   ┆ exchange_rate ┆ status ┆ accounting_status        ┆ category ┆ description                               ┆ counterparty_id │
│ ---                                   ┆ ---        ┆ ---           ┆ ---                 ┆ ---                 ┆ ---      ┆ ---           ┆ ---    ┆ ---                      ┆ ---      ┆ ---                                       ┆ ---             │
│ str                                   ┆ str        ┆ str           ┆ datetime[μs]        ┆ datetime[μs]        ┆ f64      ┆ f64           ┆ str    ┆ str                      ┆ str      ┆ str                                       ┆ str             │
╞═══════════════════════════════════════╪════════════╪═══════════════╪═════════════════════╪═════════════════════╪══════════╪═══════════════╪════════╪══════════════════════════╪══════════╪═══════════════════════════════════════════╪═════════════════╡
│ 65yJ4EQB5XS399gynoJ3IZKor8qrMphm3d8PM ┆ COMP_0404  ┆ PRODUCT_00429 ┆ 2026-06-29 00:00:00 ┆ 2026-06-29 00:00:00 ┆ -396.78  ┆ 1.0           ┆ booked ┆ null                     ┆ utility  ┆ COUNTERPARTY_11882                        ┆ null            │
│ 215630d613d046a2b731bd2f2d8b3d46      ┆ COMP_0630  ┆ PRODUCT_01872 ┆ 2025-12-04 00:00:00 ┆ 2025-12-04 00:00:00 ┆ -29.9    ┆ 1.0           ┆ booked ┆ null                     ┆ -        ┆ PRECIO ABONO TRF.CITINL2X   -STRIPE       ┆ null            │
│ bpXJJNjMdNcnOY7gnoLVcNAK9vEdZZtPMpyJ4 ┆ COMP_0205  ┆ PRODUCT_01039 ┆ 2025-12-02 00:00:00 ┆ 2025-12-02 00:00:00 ┆ -128.35  ┆ 1.0           ┆ null   ┆ RECONCILIATION_COMPLETED ┆ -        ┆ PURCHASE 1201 COUNTERPARTY_17710          ┆ null            │
│                                       ┆            ┆               ┆                     ┆                     ┆          ┆               ┆        ┆                          ┆          ┆ XXXXX36687 CA XXXXX0253XXXX…              ┆                 │
│ 36e14f5a2543457b9c7735c8dab50d05      ┆ COMP_0576  ┆ PRODUCT_07136 ┆ 2026-03-24 00:00:00 ┆ 2026-03-24 00:00:00 ┆ 9.6454e6 ┆ 1.0           ┆ booked ┆ DISCARDED                ┆ -        ┆ AP.RET.DST: [ACCOUNT]    MV01 0182  [NUM] ┆ null            │
└───────────────────────────────────────┴────────────┴───────────────┴─────────────────────┴─────────────────────┴──────────┴───────────────┴────────┴──────────────────────────┴──────────┴───────────────────────────────────────────┴─────────────────┘
```

category: - (635530), collection (567417), payment (362276), utility (259430), fee (179500), transfer (152102), bulk_collection (65492), tax (55904), cash_settlement (48280), pos_settlement (47315), salary (42223), bulk_payment (41469), social_security (24158), debt_repayment (23044), cash_withdrawal (14096), collection_refund (11848), interest_charge (7822), pos_withdrawal (7506), investment_deployment (3923), investment_return (3458), payment_refund (3222), None (330), cash_settlements (90), tax_refund (2)

status: booked (2520019), None (29839), pending (6579)

accounting_status: None (1573869), RECONCILIATION_COMPLETED (528034), DISCARDED (308568), PENDING (95281), ACCOUNTING_COMPLETED (30995), ACCOUNTING_RECOMMENDATION (18064), RECONCILIATION_RECOMMENDATION (1626)

## invoices (897894 filas)

Esquema: operation_id:String, company_id:String, document_type:String, issuance_date:Datetime(time_unit='us', time_zone=None), due_date:Datetime(time_unit='us', time_zone=None), payment_date:Datetime(time_unit='us', time_zone=None), amount:Float64, pending_amount:Float64, currency:String, accounting_currency:String, exchange_rate:Float64, status:String, concept:String, counterparty_id:String

Nulos (%): due_date 0, payment_date 0, exchange_rate 0, concept 0, counterparty_id 1

```
shape: (4, 14)
┌──────────────────────┬────────────┬───────────────┬─────────────────────┬─────────────────────┬─────────────────────┬──────────┬────────────────┬──────────┬─────────────────────┬───────────────┬─────────┬─────────────────────┬─────────────────────┐
│ operation_id         ┆ company_id ┆ document_type ┆ issuance_date       ┆ due_date            ┆ payment_date        ┆ amount   ┆ pending_amount ┆ currency ┆ accounting_currency ┆ exchange_rate ┆ status  ┆ concept             ┆ counterparty_id     │
│ ---                  ┆ ---        ┆ ---           ┆ ---                 ┆ ---                 ┆ ---                 ┆ ---      ┆ ---            ┆ ---      ┆ ---                 ┆ ---           ┆ ---     ┆ ---                 ┆ ---                 │
│ str                  ┆ str        ┆ str           ┆ datetime[μs]        ┆ datetime[μs]        ┆ datetime[μs]        ┆ f64      ┆ f64            ┆ str      ┆ str                 ┆ f64           ┆ str     ┆ str                 ┆ str                 │
╞══════════════════════╪════════════╪═══════════════╪═════════════════════╪═════════════════════╪═════════════════════╪══════════╪════════════════╪══════════╪═════════════════════╪═══════════════╪═════════╪═════════════════════╪═════════════════════╡
│ b48ca518a8aaea5f19f8 ┆ COMP_1046  ┆ invoice       ┆ 2025-03-13 00:00:00 ┆ 2025-04-13 00:00:00 ┆ 2025-04-13 00:00:00 ┆ 4023.0   ┆ 4023.0         ┆ EUR      ┆ EUR                 ┆ 1.0           ┆ overdue ┆ Factura HT[NUM] de  ┆ COUNTERPARTY_104675 │
│ 0583636ddace         ┆            ┆               ┆                     ┆                     ┆                     ┆          ┆                ┆          ┆                     ┆               ┆         ┆ 13/03/2025          ┆                     │
│ 3ba0f28db9aafade8226 ┆ COMP_0343  ┆ invoice       ┆ 2025-05-31 00:00:00 ┆ 2025-07-30 00:00:00 ┆ 2025-07-30 00:00:00 ┆ -1819.95 ┆ -1819.95       ┆ EUR      ┆ EUR                 ┆ 1.0           ┆ overdue ┆ [X]25-012251        ┆ COUNTERPARTY_47690  │
│ 9bc90f5a4c54         ┆            ┆               ┆                     ┆                     ┆                     ┆          ┆                ┆          ┆                     ┆               ┆         ┆                     ┆                     │
│ 1b1e80a4001edc8e5028 ┆ COMP_1105  ┆ note          ┆ 2026-06-15 00:00:00 ┆ 2026-06-15 00:00:00 ┆ 2026-06-15 00:00:00 ┆ 17904.0  ┆ 0.0            ┆ CLP      ┆ CLP                 ┆ 1.0           ┆ paid    ┆ Comisiones          ┆ COUNTERPARTY_55529  │
│ ec3976f3e6ac         ┆            ┆               ┆                     ┆                     ┆                     ┆          ┆                ┆          ┆                     ┆               ┆         ┆                     ┆                     │
│ 0830e230f1ac6711d753 ┆ COMP_1185  ┆ invoice       ┆ 2025-11-19 00:00:00 ┆ 2025-11-19 00:00:00 ┆ 2026-02-18 00:00:00 ┆ -630.25  ┆ 0.0            ┆ EUR      ┆ EUR                 ┆ 1.0           ┆ paid    ┆ [X]                 ┆ COUNTERPARTY_07137  │
│ f0e76cc6ffc5         ┆            ┆               ┆                     ┆                     ┆                     ┆          ┆                ┆          ┆                     ┆               ┆         ┆ COUNTERPARTY_31386  ┆                     │
└──────────────────────┴────────────┴───────────────┴─────────────────────┴─────────────────────┴─────────────────────┴──────────┴────────────────┴──────────┴─────────────────────┴───────────────┴─────────┴─────────────────────┴─────────────────────┘
```

status: paid (660299), overdue (192556), pending (29717), cancel (13699), payment_in_progress (1216), paymentOrder (406), shipped (1)

document_type: invoice (760406), paymentDocument (53761), note (38154), deposit (21390), invoiceGroup (13775), deliveryNote (6380), refund (2018), purchaseOrder (1259), other (739), cheque (12)

## Ejemplos de description por categoría
- collection: [X]26/07/0032 [X]26/05/0061 COUNTERPARTY_27833 [GB] Pago general | [COMPANY], CONCEPTO N/F. [NUM]. | TRANSF OTRAS/GIACOMO [X]
- payment: Compra tarj. 5540xxxxxxxx7019 [X]-[URL] | Liquidacion De Las Tarjetas De Credito Del Contrato 0049 6774 532 [NUM] | Compra tarj. 5540xxxxxxxx2010 apple.com/COUNTERPARTY_93770-cork
- transfer: SCF-AJUS.SALDO C., DC: 8631.[NUM], DC: 8631.[NUM] | TRASPASO A CTA [ACCOUNT] | TRASPASO, , FACTURA HAM25-[NUM]
- -: [NUM]-[NUM] COUNTERPARTY_00161 [COMPANY] | CREDIT [X] INTEREST | /PT/DE/EI/BENEF [X] CORDEIRO DA [COMPANY] 0244 [ADDRESS] CPF [NUM]/BI/[NUM] 500+TED SENT 25
- debt_repayment: COUNTERPARTY_95206 SUC, [TAXID]000, [NUM] | PRES.[NUM] [NUM]PRS VTO. [COMPANY] | CARGO [COMPANY] 7422-000492-000 00-
- tax: RECIBO SUMA GESTION TRIBUTARIA NIF: [TAXID] AYUNT ORIHUELA IBI UR 2025 UR PAU-21 1 C S UE LO 0001 CSV:[NUM] [X]: 21033,06 [X]:[REF] Nº RECIBO 0049 6 | NRC. [REF] CARGO POR PAGO DE [COMPANY] - TRIBUTOS | [COMPANY], [TAXID] 010 2000
- salary: Nomina COUNTERPARTY_02936.- DocNum:[NUM] | Nomina [COMPANY].- DocNum:[NUM] | Nomina [COMPANY], sl- DocNum:[NUM]
- fee: COMISIONES [NUM] 03 [COMPANY] [NUM] | INTUIT [NUM] DES:TRAN FEE ID:XXXXXXXXXX31769 [X]:[COMPANY], INC. CO ID:XXXXX86202 CCD | MANTENIMIENTO TPV, 363.70348-9

## Ejemplos de concept (facturas)
- [REF] | Factura [X]/[NUM]. Factura FV_[NUM] | S.Fra /322 [COMPANY] Ef 117 | [X] COUNTERPARTY_31386 | 2508 REMESA CLIENTES | COBR-[X][NUM]

## panel.parquet (21538 filas)

```
shape: (9, 41)
┌────────────┬────────────┬────────────┬────────────┬────────────┬────────────┬───────────┬───────────┬───────────┬────────────┬───┬───────────┬────────────┬────────────┬───────────┬───────────┬────────────┬───────┬──────────┬────────────┬──────────┐
│ statistic  ┆ company_id ┆ group_id   ┆ month      ┆ months_sin ┆ n_tx       ┆ inflow    ┆ outflow   ┆ oper_in   ┆ transfer_i ┆ … ┆ n_cust_3m ┆ n_cust_12m ┆ lost_share ┆ ar_issued ┆ ap_issued ┆ first_inv  ┆ ccur  ┆ to_eur   ┆ months_sin ┆ has_erp  │
│ ---        ┆ ---        ┆ ---        ┆ ---        ┆ ce_final_t ┆ ---        ┆ ---       ┆ ---       ┆ ---       ┆ n          ┆   ┆ ---       ┆ ---        ┆ ---        ┆ ---       ┆ ---       ┆ ---        ┆ ---   ┆ ---      ┆ ce_last_tx ┆ ---      │
│ str        ┆ str        ┆ str        ┆ str        ┆ x          ┆ f64        ┆ f64       ┆ f64       ┆ f64       ┆ ---        ┆   ┆ f64       ┆ f64        ┆ f64        ┆ f64       ┆ f64       ┆ str        ┆ str   ┆ f64      ┆ ---        ┆ f64      │
│            ┆            ┆            ┆            ┆ ---        ┆            ┆           ┆           ┆           ┆ f64        ┆   ┆           ┆            ┆            ┆           ┆           ┆            ┆       ┆          ┆ f64        ┆          │
│            ┆            ┆            ┆            ┆ f64        ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆            ┆       ┆          ┆            ┆          │
╞════════════╪════════════╪════════════╪════════════╪════════════╪════════════╪═══════════╪═══════════╪═══════════╪════════════╪═══╪═══════════╪════════════╪════════════╪═══════════╪═══════════╪════════════╪═══════╪══════════╪════════════╪══════════╡
│ count      ┆ 21538      ┆ 21538      ┆ 21538      ┆ 21538.0    ┆ 21538.0    ┆ 21538.0   ┆ 21538.0   ┆ 21538.0   ┆ 21538.0    ┆ … ┆ 10895.0   ┆ 10895.0    ┆ 6812.0     ┆ 11352.0   ┆ 11352.0   ┆ 12748      ┆ 21538 ┆ 21538.0  ┆ 21538.0    ┆ 21538.0  │
│ null_count ┆ 0          ┆ 0          ┆ 0          ┆ 0.0        ┆ 0.0        ┆ 0.0       ┆ 0.0       ┆ 0.0       ┆ 0.0        ┆ … ┆ 10643.0   ┆ 10643.0    ┆ 14726.0    ┆ 10186.0   ┆ 10186.0   ┆ 8790       ┆ 0     ┆ 0.0      ┆ 0.0        ┆ 0.0      │
│ mean       ┆ null       ┆ null       ┆ 2025-10-24 ┆ 0.101681   ┆ 108.33225  ┆ 8.9737e6  ┆ 8.5110e6  ┆ 3.3903e6  ┆ 1.1969e6   ┆ … ┆ 24.646719 ┆ 48.3486    ┆ 0.386312   ┆ 2.8776e7  ┆ 2.3121e7  ┆ 2024-11-12 ┆ null  ┆ 0.969825 ┆ 0.194818   ┆ 0.638917 │
│            ┆            ┆            ┆ 00:56:53.7 ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 03:05:01.6 ┆       ┆          ┆            ┆          │
│            ┆            ┆            ┆ 98867      ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 00251      ┆       ┆          ┆            ┆          │
│ std        ┆ null       ┆ null       ┆ null       ┆ 0.848273   ┆ 222.554376 ┆ 1.2129e8  ┆ 1.0797e8  ┆ 5.4703e7  ┆ 3.7202e7   ┆ … ┆ 63.495724 ┆ 130.258031 ┆ 0.381224   ┆ 1.1610e9  ┆ 1.6158e9  ┆ null       ┆ null  ┆ 0.16559  ┆ 1.112774   ┆ null     │
│ min        ┆ COMP_0001  ┆ GROUP_0001 ┆ 2024-09-01 ┆ 0.0        ┆ 0.0        ┆ 0.0       ┆ 0.0       ┆ 0.0       ┆ 0.0        ┆ … ┆ 0.0       ┆ 1.0        ┆ 0.0        ┆ 0.0       ┆ 0.0       ┆ 2024-09-01 ┆ AED   ┆ 0.000032 ┆ 0.0        ┆ 0.0      │
│            ┆            ┆            ┆ 00:00:00   ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 00:00:00   ┆       ┆          ┆            ┆          │
│ 25%        ┆ null       ┆ null       ┆ 2025-06-01 ┆ 0.0        ┆ 10.0       ┆ 6549.03   ┆ 17512.26  ┆ 241.17    ┆ 0.0        ┆ … ┆ 1.0       ┆ 2.0        ┆ 0.031258   ┆ 798.01    ┆ 6404.28   ┆ 2024-09-01 ┆ null  ┆ 1.0      ┆ 0.0        ┆ null     │
│            ┆            ┆            ┆ 00:00:00   ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 00:00:00   ┆       ┆          ┆            ┆          │
│ 50%        ┆ null       ┆ null       ┆ 2025-12-01 ┆ 0.0        ┆ 41.0       ┆ 107213.85 ┆ 127702.76 ┆ 43617.21  ┆ 0.0        ┆ … ┆ 5.0       ┆ 10.0       ┆ 0.230056   ┆ 48538.07  ┆ 42983.39  ┆ 2024-09-01 ┆ null  ┆ 1.0      ┆ 0.0        ┆ null     │
│            ┆            ┆            ┆ 00:00:00   ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 00:00:00   ┆       ┆          ┆            ┆          │
│ 75%        ┆ null       ┆ null       ┆ 2026-04-01 ┆ 0.0        ┆ 117.0      ┆ 617668.14 ┆ 647481.05 ┆ 294424.52 ┆ 0.0        ┆ … ┆ 21.0      ┆ 38.0       ┆ 0.795318   ┆ 259423.38 ┆ 194794.76 ┆ 2024-12-01 ┆ null  ┆ 1.0      ┆ 0.0        ┆ null     │
│            ┆            ┆            ┆ 00:00:00   ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 00:00:00   ┆       ┆          ┆            ┆          │
│ max        ┆ COMP_1286  ┆ GROUP_0250 ┆ 2026-08-01 ┆ 16.0       ┆ 10000.0    ┆ 9.4844e9  ┆ 6.6014e9  ┆ 2.2261e9  ┆ 2.2221e9   ┆ … ┆ 2152.0    ┆ 2371.0     ┆ 1.0        ┆ 9.1248e10 ┆ 1.6020e11 ┆ 2026-08-01 ┆ XOF   ┆ 1.207668 ┆ 17.0       ┆ 1.0      │
│            ┆            ┆            ┆ 00:00:00   ┆            ┆            ┆           ┆           ┆           ┆            ┆   ┆           ┆            ┆            ┆           ┆           ┆ 00:00:00   ┆       ┆          ┆            ┆          │
└────────────┴────────────┴────────────┴────────────┴────────────┴────────────┴───────────┴───────────┴───────────┴────────────┴───┴───────────┴────────────┴────────────┴───────────┴───────────┴────────────┴───────┴──────────┴────────────┴──────────┘
```
