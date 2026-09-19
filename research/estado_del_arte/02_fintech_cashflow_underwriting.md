# Estado del arte 02: cómo hacen credit risk las fintech con datos de cash-flow

Investigación de septiembre de 2026 para X-Ray (HackSpain 2026, reto de Embat). Pregunta: ¿cómo evalúan el riesgo de crédito los prestamistas y proveedores de datos que trabajan con movimientos bancarios, open banking y contabilidad, **sin balances**? Y ¿qué podemos copiar con nuestro dataset (bancos, facturas ERP, productos de deuda y saldos de 1.286 pymes sintéticas, 24 meses, sin etiqueta de default)?

Notación: **[I]** = estudio independiente o académico. **[V]** = cifra del propio proveedor (marketing, no auditada). **[S]** = fuente secundaria (reseñas, blogs de terceros).

---

## 0. Resumen en 10 puntos

1. **El núcleo de features es el mismo en toda la industria**: entradas (ingresos), salidas, saldo medio/mínimo, volatilidad de saldo y de entradas, eventos de estrés (saldo bajo o negativo, NSF/descubiertos), pagos a otros prestamistas (loan stacking, MCA) y ratios entre ellos. FinRegLab lo llama "baseline común entre fintechs" ([Sharpening the Focus, 2025](https://finreglab.org/wp-content/uploads/2025/06/FinRegLab_06-03-2025_Sharpening-the-Focus-Accessible-Text.pdf)).
2. **Sin bureau, el cash-flow solo ya discrimina bien.** En consumo, un modelo solo con cash-flow da AUC de 0,78 (logística) y 0,80 (ML) ([FinRegLab 2025](https://finreglab.org/wp-content/uploads/2025/07/FinRegLab_07-01-2025_Advancing-the-Credit-Ecosystem-Main.pdf)). En pymes de un banco francés, la actividad de la cuenta corriente da AUC de 0,80, frente a 0,76 con ratios financieros, y 0,84 combinando ambos ([arXiv 1707.00757](https://arxiv.org/abs/1707.00757)). **Para nosotros, sin bureau ni balances, el techo realista está en AUC ≈ 0,75-0,80.**
3. **Sobre un bureau fuerte, el lift es pequeño pero significativo**: +0,011 de AUC en 38.021 préstamos a pymes (0,652 → 0,663). Sube a +0,023 en empresas jóvenes con dueño de score bajo ([FinRegLab 2025](https://finreglab.org/wp-content/uploads/2025/06/FinRegLab_06-03-2025_Sharpening-the-Focus-Accessible-Text.pdf)). Los "+25-30 %" de Plaid, Prism y Experian son lift de KS o Gini declarado por el propio proveedor **[V]**.
4. **Las señales de la cuenta se adelantan unos 12 meses al default**: uso de la línea de crédito, excedidos y entradas de caja muestran patrones anómalos un año antes ([Norden & Weber, RFS 2010](https://academic.oup.com/rfs/article-abstract/23/10/3665/1566409)). En el banco francés, las mejores variables son **los excedidos (intentados o rechazados) de la línea de crédito**.
5. **Brex construyó un PD sin etiquetas de default**, que es justo nuestro caso. Previó el saldo de caja a la fecha de pago y definió PD = P(saldo futuro < importe debido) ("modelo estructural"). Con esa previsión y su intervalo fija el límite, y solo lo toca si la previsión sale de la banda: las bajadas de límite cayeron ~80 % sin más riesgo ([Brex Tech Blog, 2022](https://medium.com/brexeng/how-we-built-a-probability-of-default-model-without-default-labels-212415bbeef6)).
6. **Modelos**: GBM (XGBoost en Plaid LendScore, LightGBM en Revolut) o random forest, con reglas de knockout delante. El ML gana a la logística ~2 % de AUC y ~7 % de KS con los mismos datos (FinRegLab 2025). Con 20 variables colineales, boosting da 0,797 y logit 0,709 (banco francés).
7. **Explicabilidad obligatoria** en EE. UU. (ECOA/Reg B): la CFPB no acepta "el algoritmo es complejo" ([Circular 2022-03](https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/)). En la práctica son **3-5 reason codes** por decisión, sacados de SHAP (Plaid: 5; Prism: 3; Reg B: "más de 4 no suele ayudar").
8. **La monitorización continua es el producto**: límites que se recalculan a diario (Brex, Ramp), líneas que suben o bajan con el cash-flow (Kabbage, Fundbox), vigilancia de stacking y de tendencias de saldo (Plaid) y alertas de red cuando quiebra un cliente o proveedor (Defacto).
9. **En Europa y España** el mercado lo mueve la agregación PSD2 (BBVA, Afterbanks/Minsait, Tink, Equifax/Experian ES) más prestamistas como iwoca y Defacto (socio de Qonto). Revolut ES/FR publica que su propio dato transaccional sustituye casi por completo al open banking: +0,5 a +4 pp de AUC ([CRC Edimburgo 2025](https://www.crc.business-school.ed.ac.uk/sites/crc/files/2025-11/Evaluating-the-Contribution-of-Open-Banking-Data-to-Credit-Scoring-Performance-in-the-Spanish-and-French-Markets-paper.pdf)).
10. **Regulación UE**: el AI Act solo trata como alto riesgo el scoring de **personas físicas**. Eso incluye a los autónomos y excluye a las sociedades. Las obligaciones se aplazan al 2-dic-2027 ([Digital Omnibus](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)). Las guías de la EBA sobre concesión y seguimiento de préstamos exigen indicadores de alerta temprana y seguimiento continuo ([EBA/GL/2020/06](https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring)).

---

## 1. Prestamistas: qué datos usan y cómo deciden

### 1.1 EE. UU.

| Prestamista | Producto | Datos | Cómo decide / límites | Monitorización | Fuente |
|---|---|---|---|---|---|
| **Brex** | Tarjeta corporativa para startups | Saldo y transacciones de las cuentas conectadas (vía Plaid, 2 años de historia) | Al principio, límite del 5-20 % de la caja. Después, previsión del saldo a fin de ciclo con intervalo: límite = 50 % del P2,5 previsto. Más tarde, PD de clasificación | El límite se recalcula a diario, pero solo cambia si la previsión sale del intervalo inicial. Los datos desactualizados (conexión caída) alargan el horizonte y bajan el límite solos | [Brex Tech Blog](https://medium.com/brexeng/how-we-built-a-probability-of-default-model-without-default-labels-212415bbeef6), [Brex límites](https://www.brex.com/support/how-do-brex-credit-limits-work), [Plaid×Brex](https://plaid.com/customer-stories/brex/) |
| **Ramp** | Tarjeta corporativa | Saldo de la cuenta conectada y transacciones | Límite = % de la caja. Exige saldo estable ≥ 25.000 $ **[S]** | Vigila saldos a diario. Una nómina grande puede bajar el límite | [Ramp bank connections](https://support.ramp.com/ramp-bank-connections-overview), [Ramp limits](https://support.ramp.com/ramp-business-limits-business-limit-increases) |
| **OnDeck** | Préstamo y línea para pymes | Banco (3-6 meses vía Plaid o PDF), procesador de pagos, contabilidad, registros públicos, historial propio | "OnDeck Score" con más de 2.000 datos; mira saldo medio diario y consistencia de ingresos **[S]** | Publica con Ocrolus un informe trimestral de tendencias de cash-flow | [Journey Capital (licenciatario)](https://www.journeycapital.ca/ondeckscore/), [NerdWallet](https://www.nerdwallet.com/business/loans/reviews/ondeck) |
| **Kabbage (American Express)** | Línea de crédito de 2.000 a 250.000 $ | Banco, pagos, e-commerce, envíos, contabilidad | Requisito: 1 año operando e ingresos medios ≥ 4.200 $/mes en los últimos 3 meses. Disposiciones a 6, 12 o 18 meses | Descarga los datos de forma recurrente para ajustar las líneas | [FinRegLab SB Spotlight 2019](https://finreglab.org/wp-content/uploads/2023/12/FinRegLab_2019-09-06_Research-Report_Small-Business-Spotlight_The-Use-of-Cash-Flow-Data-in-Underwriting-Credit.pdf), [Amex](https://www.businesswire.com/news/home/20211208005617/en/Kabbage-from-American-Express-Launches-Kabbage-Funding-to-Help-Simplify-Funding-for-U.S.-Small-Businesses) |
| **Fundbox** | Línea revolving | QuickBooks, FreshBooks, Xero, banco: "decenas de miles de señales" y un "business graph" | Rechaza el enfoque por reglas: "no aprendes, te autolimitas". No tiene analistas, solo científicos de datos. "Hay que construir modelos que expliquen los modelos" | Sube o baja las líneas en tiempo real. Préstamos cortos (un trimestre) para aprender rápido | [PYMNTS 2019](https://www.pymnts.com/smbs/2019/fundbox-data-lending-credit/) |
| **Bluevine** | Línea de crédito | Cuenta conectada o 3 extractos, FICO | Knockouts: ≥ 10.000 $/mes de ingresos, ≥ 12 meses, **saldo medio ≥ 2.000 $**, FICO ≥ 625 | — | [Bluevine requisitos](https://www.bluevine.com/blog/business-line-of-credit-requirements) |
| **Stripe Capital** | Préstamo con devolución sobre ventas | Pagos de Stripe más pagos de fuera de Stripe (otros procesadores, efectivo, cheques) | Modelos de ML propios. El foundation model de pagos genera embeddings de comportamiento | "Vista en tiempo real de la salud financiera" | [Stripe docs](https://edge-docs.stripe.com/capital/import-non-stripe-data), [oferta ML Capital](https://stripe.com/jobs/listing/machine-learning-engineer-capital-underwriting/7952048) |
| **Shopify Capital** | Anticipo o préstamo con retención de ventas | Datos de la tienda (volumen de pedidos, historial de pagos) | ML sobre datos de la tienda, sin score de crédito. Retención diaria del 10-20 % de las ventas **[S]** | La devolución se ajusta sola a las ventas | [Shopify Help](https://help.shopify.com/en/manual/finance/shopify-capital/united-states), [SellersFi](https://sellersfi.com/resources/blog/shopify-capital-pros-cons-alternatives/) |
| **Square Loans** | Préstamo con devolución sobre ventas | Volumen procesado, antigüedad de la cuenta, frecuencia de pagos | Mínimo de 10.000 $ procesados en 12 meses **[S]**. Rechaza si las ventas **son inconsistentes o caen frente a su historial** | La devolución es un % fijo de las ventas diarias | [Square elegibilidad](https://squareup.com/help/us/en/article/6479-square-capital-loan-eligibility) |
| **Capchase / Pipe / Clearco** | Financiación sobre ingresos (SaaS, e-commerce) | MRR, NRR, churn, margen bruto, payback de CAC; Clearco añade ads y ROAS | Capchase adelanta varias veces el MRR según las cohortes de retención **[S]** | Límites dinámicos según el rendimiento conectado | [Capchase](https://www.capchase.com/blog/revenue-based-financing), [Elite Funders](https://elitefunders.com/compare/capchase-vs-pipe-vs-clearco) **[S]** |
| **Mercury, Tide, Payfit** | — | Poca información pública sobre sus modelos de riesgo | — | — | — |

Patrón común: **knockouts duros** (antigüedad, ingresos mínimos, saldo medio mínimo), después **un modelo** y un **límite proporcional a un flujo o saldo**, y por último **una revisión recurrente** del límite con datos frescos.

### 1.2 Europa y España

| Actor | Qué hace con datos transaccionales | Fuente |
|---|---|---|
| **iwoca** (Reino Unido, Alemania; antes también España) | Descarga "varios años de extractos, no 3 meses" por open banking. Ventaja: no penaliza a los negocios estacionales. Junta banco, declaraciones de IVA y software contable en un motor de ML. Más de 130.000 préstamos | [iwoca](https://www.iwoca.co.uk/finance-explained/anna-nava) |
| **Defacto** (FR, DE, IT, ES; socio de financiación de Qonto) | Cinco motores: datos (transformers y LLM para categorizar), scoring (**~40 métricas**, **130 KPI**), reglas (**52 puntos de validación**), fraude y producto. El 85 % de las decisiones es automático; el resto **se marca para revisión humana, sin rechazar**. Modelo "node-based": reconstruye clientes y proveedores desde banco, facturas y ERP y puntúa cada contraparte ("como el PageRank") | [Defacto underwriting](https://www.getdefacto.com/article/underwriting-defacto-automated-lending), [modelo de red](https://www.getdefacto.com/article/node-based-credit-model), [Qonto](https://thepaypers.com/fintech/news/qonto-launches-solutions-for-sme-cash-flow-gaps) |
| **Qonto** | Cede los movimientos de la cuenta a sus socios de crédito (Defacto, Karmen, Silvr, RiverBank) | [Qonto financing](https://qonto.com/en/financing) |
| **Revolut (ES/FR)** | LightGBM con *forced split* según haya o no open banking (dos submodelos en uno). Sin bureau, porque en ES y FR "el bureau no es un input convencional" | [CRC 2025](https://www.crc.business-school.ed.ac.uk/sites/crc/files/2025-11/Evaluating-the-Contribution-of-Open-Banking-Data-to-Credit-Scoring-Performance-in-the-Spanish-and-French-Markets-paper.pdf) |
| **BBVA** | Agrega cuentas de otros bancos con las credenciales del cliente para evaluar el préstamo sin documentos. Usa saldos, ingresos, pagos, transferencias, recibos y domiciliaciones | [BBVA scoring](https://www.bbva.es/finanzas-vistazo/ef/prestamos/scoring-concesion-prestamo.html) |
| **Equifax España** | *Risk Score Open Banking* (consumo/BNPL, combinable con ASNEF). *Risk Score SME Plus* (pymes, **sin open banking**: ASNEF Empresas y BORME; declara +32 % de "precisión" **[V]**) | [Equifax RS OB](https://soluciones.equifax.es/empresas/productos/risk-score-open-banking/), [Forbes ES](https://forbes.es/ultima-hora/1022297/equifax-aumenta-un-32-la-precision-predictiva-en-la-evaluacion-del-riesgo-de-las-pymes-con-su-nueva-solucion/) |
| **Afterbanks / Arcopay (Minsait, Indra)** | Agregación PSD2 y pagos A2A para bancos españoles. Poco scoring propio | [Arcopay](https://www.arcopay.io/en/company/) |
| **Novicap** | Factoring: precio según el riesgo del **deudor**, analizado en menos de 48 h | [Novicap](https://novicap.com/soluciones/cobros-de-clientes/factoring/) |
| **MytripleA** | Préstamo, factoring y confirming para pymes. No publica su modelo | [MytripleA](https://mytriplea.com/financiacion-pymes/) |
| **Silbo, Finteca** | No aplican: Silbo Money es dinero electrónico o pagos, y Finteca es crédito con garantía inmobiliaria | [Silbo](https://openhubnews.com/en-silbo-money-fintech-liderada-exejecutivos-bancarios-recibe-luz-verde-banco-espana/) |
| **Bankinter, Santander, Libra Internet Bank** | No encontramos documentación pública de sus modelos con open banking | — |

---

## 2. Proveedores de scores y atributos de cash-flow

### 2.1 Tabla resumen

| Proveedor | Producto | Nº de atributos | Familias | Lift declarado | Explicabilidad | Fuente |
|---|---|---|---|---|---|---|
| **Plaid** | LendScore (1-99, PD a 90+ días en 12 meses) | 145 elegidos entre cientos. El 81 % del poder viene del cash-flow y el 19 % de la red (apps conectadas) | Volatilidad de saldo, estabilidad del depósito (umbrales de saldo), regularidad de ingresos, constancia en pagos de préstamos, nº de conexiones con prestamistas o anticipos de nómina | KS +9,1 % global; +10,5 % en tarjeta; +6,9 % en préstamo personal **[V]** | **XGBoost + SHAP → 5 reason codes** ("alta volatilidad del saldo") | [How we built LendScore](https://plaid.com/blog/how-we-built-lendscore/) |
| **Prism Data** | CashScore (1-999), Insights | "Decenas de miles" de atributos tendenciales. Categorías: ingresos, saldos, gastos, facturas, comportamiento, recuentos, patrones, ratios | Ej.: "cambio en el gasto discrecional reciente", "importe de pagos recientes a préstamos", "ingresos recientes" | +30 % de KS sobre scores tradicionales **[V]**. v4: +28 % de aprobaciones con el mismo riesgo y −16 % de defaults frente a v3 **[V]** | 3 reason codes (FCRA/ECOA) | [CashScore](https://www.prismdata.com/cashscore/), [v4](https://www.prismdata.com/blog/prism-data-introduces-cashscore-v4-raising-the-bar-for-cash-flow-underwriting-tools-as-the-u-s-adopts-open-banking/) |
| **Nova Credit** | Cash Atlas, NovaScore Cash Flow | Más de 1.000 atributos probados contra rendimiento | Ingresos, gastos y activos tendenciales, asequibilidad | — | Adverse action codes por atributo | [Cash Atlas](https://www.novacredit.com/cash-atlas) |
| **FICO** | UltraFICO (con Plaid desde noviembre de 2025) | 4 factores | **Antigüedad de las cuentas; recencia y frecuencia de transacciones; caja disponible de forma consistente; historial de saldos positivos** | "7 de cada 10" con caja constante mejoran su score **[V]** | Factores FICO | [UltraFICO fact sheet](https://www.fico.com/en/latest-thinking/fact-sheet/ultrafico-score-fact-sheet), [FICO×Plaid](https://www.fico.com/en/newsroom/fico-partners-plaid-launch-next-generation-cash-flow-ultrafico-score) |
| **FICO SBSS** | Score de pyme (0-300) | Mezcla el bureau comercial y el personal del dueño, con financieros si los hay | — | La SBA dejó de exigirlo en 7(a) Small Loans el 1-mar-2026 (el mínimo había subido a 165) | — | [Nav](https://www.nav.com/blog/sba-to-sunset-fico-sbss-for-small-loans-what-does-this-mean-for-your-small-business/) |
| **Experian (EE. UU.)** | Cashflow Attributes, Cashflow Score | Más de 900 atributos de ingresos, cash-flow y asequibilidad | — | Atributos: hasta +20 % de Gini con el bureau. Score: hasta +25 % frente a scores convencionales **[V]** | — | [Cashflow Score](https://www.experianplc.com/newsroom/press-releases/2025/launch-of-experian-s-cashflow-score-signals-new-era-of-open-bank), [Attributes](https://www.experian.com/business/products/cashflow-attributes) |
| **Ocrolus** | Cash Flow Analytics (pymes/MCA) | Unos 80 grupos, mes a mes | Lista completa en 2.2 | — | — | [Ocrolus cash flow features](https://docs.ocrolus.com/reference/cash-flow-features) |
| **Flinks** (Canadá) | Business Analysis attributes | Más de 4.500 atributos en toda la plataforma | Ingresos operativos por canal, préstamos recibidos, gastos operativos, pasivos y pagos de préstamos, comisiones (incl. NSF) | — | — | [Flinks packages](https://docs.flinks.com/guides/enrich/attributes-packages) |
| **Codat** | Lending API y Credit Model | Contabilidad + banco (Plaid, TrueLayer) | P&L de caja reconstruido desde el banco, seguimiento de deuda, análisis de cobros y pagos, **knockout rules**, "key risks", calidad contable, indicador de libros cerrados | — | "Key highlights / key risks" | [Codat credit model](https://docs.codat.io/lending/premium-products/credit-model-overview/) |
| **Validis** (Reino Unido) | Datos contables estandarizados | P&L, balance, cobros y pagos pendientes, banco | Antigüedad de cobros, **concentración de deudores**, tendencias de circulante, **covenants**, fraude (facturas de importe redondo, deudores nuevos) | — | Alertas tempranas | [Validis](https://www.validis.com/) |
| **Tink (Visa)** | Risk Insights | Más de 200 insights y más de 300 features | Retiradas de cajero, **pagos a agencias de recobro**, saldo bajo o descubierto (nº de transacciones que dejan el saldo negativo y días en descubierto), actividad de la cuenta, juego | — | — | [Tink Risk Insights](https://tink.com/products/risk-insights/), [guía](https://tink.com/blog/open-banking/lenders-guide-risk-assessments/) |
| **Kontomatik** (CEE) | Financial Health Indicator (0-100), scoring A-F | Ingreso medio mensual, saldo total, **antigüedad y riqueza de la cuenta**, suma de préstamos de otros prestamistas | — | Tiers | [Kontomatik FHI](https://kontomatik.com/financial-health-indicator) |
| **Heron Data** | Parsing y análisis para MCA y pymes | Depósitos, **posiciones** (otros MCA), patrones de cash-flow, pagos recurrentes | — | — | [Heron](https://www.herondata.io/) |
| **Moneyhub** | Asequibilidad por open banking | Sobre todo consumo | — | — | [Moneyhub](https://moneyhub.com/solutions/banking-and-lending-solutions/) |

### 2.2 Listas reales de atributos (las que conseguimos)

**Ocrolus, cash-flow features de pymes** ([docs](https://docs.ocrolus.com/reference/cash-flow-features)):
- **Saldos**: saldo diario, flujo diario, saldo medio diario (también solo días laborables), mínimo y máximo por mes, flujo neto mensual, **tendencia de saldo y de flujo a 30, 60 y 90 días**.
- **Negativos**: fechas con saldo negativo por mes y su recuento (también en laborables).
- **Entradas**: ingresos del negocio, depósitos totales, depósitos de fuentes externas (sin traspasos internos), depósitos grandes, **préstamos recibidos** (fintech, banco, MCA, SBA), ingresos de nómina.
- **Salidas**: gastos, retiradas, nóminas, leasing, seguros, impuestos (nómina, estatales y federales).
- **Deuda**: fintech loans, **MCA**, préstamos bancarios, consolidadores, **factoring** (entradas y salidas), anticipos bancarios.
- **Incidencias**: nº de comisiones NSF y de descubierto, efectos devueltos (depósito o retirada), transacciones revertidas, "revenue deductions".
- **Patrones**: recurrentes probables, **importes redondos** (4 y 5 ceros), recuentos y ticket medio por mes, contrapartes principales (cobros y pagos), consultas de crédito, cuentas bancarias que faltan y días analizados.

**Plaid Asset Report attributes** (repo público, [github.com/plaid/assets-attributes](https://github.com/plaid/assets-attributes)):
- **OD/NSF**: nº, importe total, desglose mensual, mínimo, máximo, media, **recencia (días desde el último)**.
- **Saldo negativo**: nº de días que cierran en negativo, importe total, media y **recencia**.
- **Deuda**: nº, total, detalle mensual y recencia de los **préstamos recibidos** y de los **pagos a préstamos**.
- **Actividad inusual**: transacciones outlier.
- **Cash-flow**: nº y total de entradas y salidas y su desglose mensual; flujo neto.
- **Saldo histórico**: media, mínimo y máximo del saldo diario de cierre.

**Plaid Consumer Report** ([API](https://plaid.com/docs/api/products/check/)): `average_balance`, `average_monthly_balances`, `most_recent_thirty_day_average_balance`, `total_inflow/outflow_amount_30d/60d/90d`, `nsf_fee_transactions_30d/60d/90d`, `average_days_between_transactions`, `longest_gap_between_transactions`, `number_of_days_no_transactions`, `number_of_inflows/outflows`, `average_inflow/outflow_amount` e `is_primary_account` (con confianza).

**FinRegLab 2025, modelo de cash-flow para pymes** (tabla 7, random forest, [PDF](https://finreglab.org/wp-content/uploads/2025/06/FinRegLab_06-03-2025_Sharpening-the-Focus-Accessible-Text.pdf)). Son las features que llevan al +0,011 de AUC:

| Feature | Feature |
|---|---|
| Entradas (log) | Saldo (log) |
| Retiradas (log) | Nº de NSF |
| Nº de saldos bajos o negativos (< 0 o < 1.000 $) | ¿Tiene préstamo de pago diario (MCA)? |
| Desviación de las entradas | Desviación del saldo |
| **Entradas sin deuda nueva (log)** | Indicadores de dato faltante |
| **Ratio salidas / entradas** | Saldo × entradas |
| NSF × saldos bajos | **Uso bajo del crédito** |
| **CV del saldo** / **CV de las entradas** | Ratio MCA / saldo |
| **Nunca con saldo bajo o negativo** / **Nunca con NSF** | NSF > 5 |
| Ratio de volatilidad del saldo | **Ratio entradas / saldo** |

El baseline usa FICO, antigüedad, empleados, sector, región, importe pedido y tipo de préstamo. Los prestamistas usan 3 meses de extractos (A) o 6 meses (B), y "rara vez más de 6".

**FinRegLab 2025, consumo, feature engineering** ([PDF](https://finreglab.org/wp-content/uploads/2025/07/FinRegLab_07-01-2025_Advancing-the-Credit-Ecosystem-Main.pdf)):
- **Largo plazo**: activos totales, deuda / activos, ingreso y gasto como mediana mensual de entradas y salidas, tasa de ahorro.
- **Liquidez**: current ratio = saldo / mediana de salidas mensuales (= nuestros meses de caja) y gastos / ingresos.
- **Comportamiento**: tiempo desde la primera actividad por tipo de cuenta, recencia, frecuencia, ticket, **días con saldo negativo**, **desviación frente a la tendencia histórica del saldo**, **saldo actual / saldo medio** y **percentil del saldo reciente frente a su propia historia**.
- **Avanzado**:
  - **Traspasos internos** eliminados emparejando cargo y abono de igual importe en ±3 días.
  - **Recurrentes**: intervalo semanal, quincenal o mensual, ≥ 3 en un trimestre, más de 50 $, mismo importe o misma descripción.
  - Gastos de más a menos obligatorios: préstamos y alquiler → suministros y seguros → pagos indirectos → todo.
  - **NSF por palabra clave**, contando días con evento y días desde el último.
  - Ventanas de 30 a 365 días, flujo neto y **pagos recurrentes de deuda / ingresos**.

**Banco francés, 30 variables de la cuenta corriente de empresas** ([arXiv 1707.00757](https://arxiv.org/abs/1707.00757)):
- **Cuatro tipos de variable**: la diferencia de una característica entre el inicio y el fin del periodo (1 o 2 años), su valor actual, su desviación típica en el periodo y atributos de la empresa.
- **Normalización**: todo se divide por las **entradas mensuales acumuladas medias**, que hacen de proxy del tamaño.
- **Las que más pesan**: nº de excedidos intentados o rechazados de la línea en los últimos 12 meses (AUC individual 0,73) y estado actual.
- **Lección**: las 30 variables diseñadas con criterio económico ganan a 5.000 generadas automáticamente (0,797 frente a 0,781 con boosting).

---

## 3. Evidencia empírica: cuánto aporta la señal transaccional

| Estudio | Datos | Comparación | Resultado | Tipo |
|---|---|---|---|---|
| **FinRegLab, Howell y Matsumoto, *Sharpening the Focus* (2025)** | 38.021 préstamos a pymes de 2 fintechs (2015-2024); default = fallido, más de 60 días de impago o reestructurado (17 %) | RF: FICO y datos de la empresa frente a eso más cash-flow | AUC 0,652 → **0,663 (+0,011)**. FICO bajo: +0,015. **FICO bajo y empresa de menos de 5 años: 0,599 → 0,622 (+0,023)**. Con MCO, +1 DE de saldo (≈ 64.000 $) → −2 pp de default. Predicen default: retiradas altas, volatilidad de saldo y entradas, MCA y saldos bajos frecuentes | [I] [PDF](https://finreglab.org/wp-content/uploads/2025/06/FinRegLab_06-03-2025_Sharpening-the-Focus-Accessible-Text.pdf) |
| **FinRegLab, *Empirical Research Findings* (2019)** | 6 proveedores (Kabbage y Accion en pymes; Petal, Oportun, LendUp y Brigit en consumo) | Diferencia de medias y modelos combinados | Las métricas de cash-flow solas rinden **como los scores tradicionales** y aportan información distinta dentro de cada banda de score. No hacen de proxy de raza o género | [I] [PDF](https://finreglab.org/wp-content/uploads/2023/12/FinRegLab_2019-07-25_Research-Report_The-Use-of-Cash-Flow-Data-in-Underwriting-Credit_Empirical-Research-Findings.pdf) |
| **FinRegLab, *Advancing the Credit Ecosystem* (2025)** | Consumo, bureau + agregador | LR frente a ML; solo crédito, solo cash y combinado | **Solo cash: AUC 0,782 (LR) y 0,799 (ML)**. Solo crédito con ML: 0,883; con cash, 0,885 (+0,3 %). ML frente a LR: +2 % de AUC y +7 % de KS | [I] [PDF](https://finreglab.org/wp-content/uploads/2025/07/FinRegLab_07-01-2025_Advancing-the-Credit-Ecosystem-Main.pdf) |
| **Banco comercial francés (arXiv 2017)** | Empresas cliente; target: quiebra en 12 meses; 2 años de variables mensuales de la cuenta | Cuenta frente a ratios financieros y cuestionario | **Cuenta: 0,797-0,800** (boosting o RF balanceado). Financieros y gestión: 0,76. **Las tres fuentes: 0,842** | [I] [arXiv](https://arxiv.org/abs/1707.00757) |
| **Norden y Weber (RFS 2010)** | Cuentas corrientes y líneas de crédito de un banco alemán (pymes y particulares) | Actividad de la cuenta frente a información tradicional | El uso de la línea, los excedidos y las entradas se vuelven anómalos **~12 meses antes del default**. Mejora sustancial de la predicción, **sobre todo en pymes**. Las alertas llevan a más spread, recortes de límite y write-offs | [I] [RFS](https://academic.oup.com/rfs/article-abstract/23/10/3665/1566409) |
| **Mester, Nakamura y Renault (RFS 2007)** | Pymes de un banco canadiense | Saldos de la cuenta como monitorización | Las disposiciones por encima de la garantía predicen préstamos problemáticos. El banco ajusta el rating y la intensidad del seguimiento | [I] [WP Fed Filadelfia](https://www.philadelphiafed.org/-/media/frbp/assets/working-papers/2005/wp05-14.pdf) |
| **Revolut, ES y FR (CRC Edimburgo 2025)** | 16.626 solicitudes en FR y ~8.300 en ES; sin bureau | LightGBM con y sin open banking (forced split) | Open banking añade **+2,8 a +3,3 pp de AUC (FR)** y **+0,5 a +4 pp (ES)**. El dato transaccional propio lo sustituye casi del todo | [I/V] [PDF](https://www.crc.business-school.ed.ac.uk/sites/crc/files/2025-11/Evaluating-the-Contribution-of-Open-Banking-Data-to-Credit-Scoring-Performance-in-the-Spanish-and-French-Markets-paper.pdf) |
| **Hjelkrem et al., banco noruego (2022)** | 90 días de saldos y transacciones por open banking; 15.360 observaciones de test | Deep learning solo con open banking frente al scorecard del banco | Solo con open banking es "sorprendentemente" competitivo frente al scorecard convencional (AUC y Brier) | [I] [JRFM](https://doi.org/10.3390/jrfm15120597) |
| **Frost et al., BIS WP 779 (2019)** | Mercado Crédito (Argentina), pymes del marketplace | Rating interno (ML con datos de la plataforma) frente al bureau | El rating interno predice mejor las pérdidas y separa **5 grupos de riesgo frente a los 3 del bureau** | [I] [BIS](https://www.bis.org/publications/working-paper-779-bigtech-and-changing-structure-financial-intermediation.pdf) |
| **Gambacorta et al., BIS WP 834 (2019)** | Fintech china, 2017 | ML y datos no tradicionales frente a modelo tradicional | El ML con datos no tradicionales predice mejor pérdidas y defaults, **sobre todo tras un shock** de oferta de crédito | [I] [BIS](https://ideas.repec.org/p/bis/biswps/834.html) |
| **Ghosh, Vallée y Zeng (JF 2026)** | Fintech de India, pymes | Uso de pagos sin efectivo | Más cobros y pagos electrónicos → más acceso, menor tipo y **menos default**. Pesan más **las salidas** y las tecnologías más trazables | [I] [NBER](https://www.nber.org/papers/w34148) |
| **JPMorgan Chase Institute (2016)** | 597.000 pymes y 470 M de transacciones | Descriptivo | Mediana de **27 "cash buffer days"** (días que aguanta la caja sin entradas). Los sectores intensivos en mano de obra tienen menos | [I] [PDF](https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/institute/pdf/jpmc-institute-small-business-report.pdf) |
| **Plaid LendScore** | 1,44 M de tradelines | Frente a un benchmark de bureau | KS +9,1 % | [V] |
| **Prism CashScore** | Carteras de clientes | Frente a scores tradicionales | KS +30 % | [V] |
| **Experian Cashflow Score** | — | Frente a scores convencionales | Hasta +25 % | [V] |

**Cómo leerlo:**
- El lift **incremental** sobre un bureau fuerte es de centésimas de AUC. El poder **standalone** sin bureau está en AUC 0,78-0,80 (consumo y pymes). Nosotros estamos en el segundo caso.
- La señal es **más valiosa donde el resto de la información es pobre**: empresas jóvenes, sin historial de crédito o sin balances.
- Las variables **construidas con criterio económico** ganan a la generación masiva (banco francés), y la red de pagos o contrapartes añade señal (Plaid Network, Defacto, Fundbox).
- **Horizonte**: las anomalías de cuenta aparecen ~12 meses antes del default (Norden y Weber). Encaja con nuestro objetivo de "antelación".

---

## 4. Features concretas que usa la industria

Leyenda del estado en X-Ray: ✅ la tenemos · 🟡 en cola o parcial · 🆕 nueva · ⛔ no aplica o descartada.

| Familia | Feature de la industria | Quién la usa | Nuestro equivalente o cómo calcularla | Estado |
|---|---|---|---|---|
| **Ingresos** | Entradas medias; **entradas sin deuda nueva ni traspasos** | FinRegLab, Ocrolus, Flinks | `oper_in` (ya sin internas ni intragrupo). Falta excluir las **disposiciones de préstamo o póliza** que entran como abono | ✅ / 🟡 |
| | Tendencia y crecimiento de ingresos (30/60/90 d, interanual) | Ocrolus, Square ("ventas que caen frente a su historial"), Shopify | Tendencia 3m/12m e interanual (en cola) | ✅ |
| | **Volatilidad o CV de las entradas** | FinRegLab (DE y CV de las entradas), Plaid (regularidad de ingresos) | CV de `oper_in` en 6-12 meses, preferiblemente a la baja | 🟡 |
| | Recurrencia y persistencia de ingresos | Plaid Income, FinRegLab (recurrentes) | `oper_persistence_6m` (brainstorm, AUC 0,67 bache frente a caída) | 🟡 |
| **Saldo y liquidez** | **Saldo medio y mínimo** (diario) | Todos (Ocrolus, Plaid, UltraFICO, Bluevine con saldo medio ≥ 2.000 $) | Saldo diario reconstruido: mínimo intramensual (en cola, AUC ~0,79) | 🟡 |
| | **Días con saldo negativo o bajo, y su recencia** | Plaid (nº, total, recencia), Ocrolus, Tink, FinRegLab ("nº de saldos bajos o negativos", "nunca bajo") | Días con saldo < 0 o < X días de gasto, días desde el último y "nunca en 12 meses" | 🟡 prioridad 1 |
| | **Cash buffer days / current ratio** | JPMC (27 días de mediana), FinRegLab (saldo / mediana de salidas) | "Meses de caja" (peso 0,16, orden comprobado) | ✅ |
| | **Volatilidad y CV del saldo**, ratio de volatilidad | FinRegLab, Plaid (primer reason code) | Ojo: la volatilidad total ya salió mal (AUC 0,35: penaliza a quien tiene mucha caja). Mejor el **CV** (DE / media) o el percentil del saldo frente a su historia | 🆕 con cuidado |
| | Tendencia del saldo; saldo actual / medio; percentil frente a su propia historia | Ocrolus (tendencia 30/60/90), FinRegLab consumo | Tendencia de caja a 6 meses (en cola). Percentil de la caja actual frente a sus 12 meses | 🟡 / 🆕 |
| | Colchón fuera de la cuenta corriente (ahorro, inversión, CD) | FinRegLab ("savings and investment metrics") | `banking_products.type` ∈ {saving, investment} y flujos `investment_*` | 🆕 |
| **Estrés o incidencias** | **NSF y descubiertos** (nº, recencia, más de 5) | Todos. Es la variable de estrés más universal | No tenemos comisiones NSF explícitas. Proxys: **picos de `fee`**, `payment_refund` y `collection_refund`, y palabras clave en `description` (devolución, impagado, descubierto, excedido) | 🆕 |
| | **Excedidos o uso al límite de la línea** | Norden y Weber, banco francés (**la mejor variable**), Mester | `lc_drawn/lc_limit`: nº de meses con uso ≥ 95 %, máximo en 12 meses, tendencia del uso y "uso bajo" (FinRegLab). Hoy la feature pesa 0,01 y le falta el dato en el 86 % | 🟡 subir prioridad |
| | Pagos a agencias de recobro | Tink | Contrapartes o descripciones de recobro, si aparecen | 🆕 si hay texto |
| | Efectos devueltos o transacciones revertidas | Ocrolus | `payment_refund` y `collection_refund` | ✅ (devoluciones de cobro, sin orden) |
| **Deuda y stacking** | **Pagos a otros prestamistas** (nº, importe, recencia); **MCA o préstamos de pago diario** | FinRegLab (`1(Daily Pay Loan)`, MCA / saldo), Ocrolus, Heron, Plaid (stacking), Kontomatik (préstamos de otros) | `debt_repayment` + `interest_charge`. Nº de **financiadores distintos** (`debt_products.bank_name`). Aparición de factoring o confirming. Cuotas con cadencia diaria o semanal | 🟡 / 🆕 |
| | **Préstamos recibidos** (nº, recencia) | Plaid, Ocrolus | Abonos de disposición y alta de `debt_products` | 🆕 (ya se probó "deuda nueva con caja cayendo" y salió floja; probar la recencia y el recuento) |
| | **Pagos recurrentes de deuda / ingresos** (≈ DSCR de caja) | FinRegLab consumo, Codat, Flinks | "Carga de deuda" (sin orden). Alternativa estructural: **caja + cobros previstos frente a la próxima cuota** (`debt_schedule_config`) | 🟡 rediseñar |
| **Obligaciones recurrentes** | Nóminas, impuestos, seguros, alquiler, suministros | Ocrolus (nómina, impuestos), Flinks (pasivos), OBIE (nómina, impuestos, proveedores) | `salary`, `social_security`, `tax`, `utility`. Omisiones: `incumplimiento_6m`, `tax_miss` y `payroll_continuity` | ✅ / 🟡 |
| | Detección de recurrentes (± días, mismo importe o descripción) | FinRegLab (±3 días, ≥ 3 por trimestre) | Detectar las fechas habituales de nómina y cuota, y el **retraso del día de pago** | 🆕 |
| **Contrapartes y red** | **Concentración de clientes** | OBIE ("dependencia creciente de 1-2 clientes"), Validis, Ocrolus (top payors) | HHI de facturas AR (✅). `bank_cp_in_trend` | ✅ |
| | Concentración de proveedores | Ocrolus (top payees) | `payee_concentration`, `hhi_ap_6m` (brainstorm) | 🟡 |
| | **Salud de las contrapartes / red** | **Defacto** (node-based), **Fundbox** ("tu volatilidad depende de los de alrededor"), Plaid Network | Si un `counterparty_id` es otra empresa del panel, su score se propaga: **riesgo medio ponderado de clientes y proveedores**. Hay que verificar el solapamiento | 🆕 |
| **Actividad** | Recencia, frecuencia, **huecos más largos sin transacciones**, días sin actividad | Plaid Consumer Report, UltraFICO (recencia y frecuencia), FinRegLab | Tendencia de actividad (✅) y `months_since_last_tx`. Nuevo: **mayor hueco sin cobros** ("silencio de cobros") en días | ✅ / 🆕 |
| | **Antigüedad de la cuenta**, nº de cuentas, cuenta principal | UltraFICO, Kontomatik FHI ("antigüedad y riqueza"), Plaid (`is_primary_account`) | `banking_products.created_at` y nº de productos. **Mejor como contexto o confianza** que como score (evita castigar a los recién llegados) | 🟡 contexto |
| **Calidad del dato o fraude** | Importes redondos, depósitos grandes, outliers | Ocrolus, Plaid, Validis | % de entradas con importe redondo o outlier en el mes, relevante cerca de una solicitud | 🆕 baja prioridad |
| | Cuentas que faltan, datos desactualizados | Ocrolus, Brex (conexión caída → baja el límite) | Meses sin movimientos y cobertura de productos | ✅ contexto |
| **Forma de cobro** | **Peso de los cobros sin efectivo** | Ghosh, Vallée y Zeng (JF 2026) | Peso de `cash_settlement(s)` frente a `pos_settlement` y transferencias. Que suba el efectivo sería una señal de riesgo | 🆕 |
| **Facturas (ERP)** | Antigüedad de cobros y pagos, DSO/DPO, facturación frente a cobro | Fundbox, Validis, Codat | Tardíos AR y AP, vencido > 60 d, `dpo_3`, `billing_to_cash` | ✅ / 🟡 |
| **Estacionalidad** | Historia larga para no penalizar la estacionalidad | iwoca ("años, no 3 meses"), Plaid (ingresos previstos con estacionalidad) | Interanual y ventanas de 6-12 meses. Evitar ventanas de 1 mes por el IVA trimestral | ✅ |
| **No aplica** | Juego, cripto, BNPL, anticipos de nómina | Tink, Prism, Plaid | Son de consumo | ⛔ |

---

## 5. Modelos, reglas, explicabilidad y monitorización

### 5.1 Modelos

| Quién | Modelo | Comentario |
|---|---|---|
| Plaid LendScore | **XGBoost**, 145 features, PD a 90+ días en 12 meses | Elige las features equilibrando lift y complejidad |
| Revolut ES/FR | **LightGBM** con *forced split* en `has_open_banking` | Dos submodelos en un árbol: uno por embudo de datos, con SHAP para comparar |
| FinRegLab (pymes) | **Random forest** (sklearn), MDI; MCO y logit para interpretar | "RF da precisión similar a XGBoost y es más fácil en muestras pequeñas" |
| Banco francés | Logit, RF balanceado, boosting | Boosting ≫ logit con variables colineales (0,797 frente a 0,709). El logit gana si se eligen pocas variables no redundantes. La importancia de variables del boosting "hay que cogerla con pinzas" (una variable redundante sale con importancia baja aunque discrimine bien sola) |
| Brex (sin etiquetas) | **Modelo estructural**: previsión del saldo con intervalos → PD = P(saldo en el vencimiento < deuda) | Cubrió al ~65 % de los clientes (en el ~35 % restante la previsión era mala). Luego lo sustituyó un PD de clasificación cuando hubo impagos suficientes. Lo validaron a posteriori: el ratio caja / importe debido en el vencimiento es "un predictor muy fuerte" de mora |
| Stripe | Transformer "Payments Foundation Model" (embeddings) + modelos de underwriting | Escala que no nos aplica |
| Bancos (tradicional) | Scorecards logísticas por tramos (WoE) | Siguen siendo la referencia regulatoria y de explicabilidad |

**Reglas + modelo**: casi todos combinan **knockouts** (antigüedad ≥ 12 meses, ingresos mínimos, saldo medio mínimo, score mínimo) con un modelo y una **revisión manual de los casos marcados**. Ejemplos:
- Bluevine: ≥ 10.000 $/mes, ≥ 12 meses, saldo medio ≥ 2.000 $ y FICO ≥ 625.
- Lenders A y B de FinRegLab: FICO ≥ 600 o 660 y 1-2 años de antigüedad.
- Codat: "knockout rules".
- Defacto: 52 validaciones que **marcan el caso y avisan a una persona** en vez de rechazar.

Fundbox es la excepción declarada contra las reglas fijas.

### 5.2 Explicabilidad (reason codes)

- **EE. UU.** Con ECOA y Reg B, quien deniega o empeora condiciones debe dar **razones específicas y principales**. La [Circular 2022-03 de la CFPB](https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/) dice que la complejidad del modelo no exime y que "no cumple los criterios de nuestro modelo" no vale. El [comentario oficial a §1002.9](https://www.consumerfinance.gov/rules-policy/regulations/1002/interp-9/) indica que "más de cuatro razones no suele ser útil" y que las razones deben describir los factores realmente puntuados. Reg B también cubre el crédito a empresas, con reglas de notificación algo distintas según la facturación.
- **Práctica**:
  - Plaid: los 5 SHAP más negativos, traducidos a frases ("alta volatilidad en los saldos").
  - Prism: 3 razones.
  - Nova Credit: códigos por atributo.
  - FinRegLab evita las features de texto libre en parte por lo difícil que es explicarlas en las notificaciones de denegación.
- **UE**:
  - AI Act, anexo III 5(b): alto riesgo solo para personas físicas (**los autónomos entran; las sociedades no**), aplicable desde el 2-dic-2027 tras el Digital Omnibus ([anexo III](https://artificialintelligenceact.eu/annex/3/), [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)).
  - El RGPD (art. 22) exige explicar las decisiones automatizadas a personas físicas.
  - Las guías EBA LOM exigen documentar y controlar los modelos automatizados de concesión.

### 5.3 Monitorización continua de la cartera

| Práctica | Quién | Detalle |
|---|---|---|
| **Límite recalculado a diario sobre la caja** | Brex, Ramp | El límite es un % de la caja actual o prevista. Ramp puede bajarlo "sin aviso" tras una nómina grande |
| **Estabilizar con intervalos de predicción** | Brex | Solo se mueve el límite si la previsión sale de la banda del 95 % fijada al inicio del ciclo: **−80 % de bajadas** sin más riesgo ni menos gasto (A/B test) |
| Ajuste del riesgo por datos desactualizados | Brex | Una conexión rota alarga el horizonte, ensancha el intervalo y baja el límite solo |
| Líneas que suben o bajan con el cash-flow | Kabbage, Fundbox | Descargas periódicas de datos para revisar las condiciones de las líneas |
| Servicing: stacking, tendencias de ingresos y saldo | Plaid | Reevaluación "persistente" del riesgo de la cartera tras la originación |
| Covenants y alertas tempranas con contabilidad | Validis, Codat | Covenants, concentración de deudores y deudores nuevos |
| **Contagio por la red** | Defacto | Si un cliente o proveedor entra en insolvencia, se ven todos los prestatarios expuestos |
| Alerta temprana → acción sobre el límite | Norden y Weber | Las señales de la cuenta llevan a subir el spread, **recortar el límite** y hacer write-off |
| Marco regulatorio | EBA/GL/2020/06 | Indicadores de alerta temprana y watchlists, KRIs por cartera, revisiones periódicas |

---

## 6. Qué nos llevamos

### 6.1 Features priorizadas (calculables con nuestros datos)

El orden combina tres criterios: consenso de la industria, evidencia independiente y encaje con nuestros datos. Antes de incorporar cualquiera hay que medir cuánto mejora el score actual, según `features.md`.

| Prio. | Feature | Definición propuesta | Por qué (evidencia) | Datos |
|---|---|---|---|---|
| **1** | **Días con saldo bajo o negativo + recencia + "nunca"** | Con el saldo diario reconstruido, sobre 90 y 365 días: nº de días con saldo < 0; nº de días con saldo < 0,1 meses de gasto; días desde el último; indicador "ningún día negativo en 12 meses" | Es la variable de estrés más universal (Plaid, Ocrolus, Tink, UltraFICO, FinRegLab). "Nunca bajo o negativo" es feature explícita en FinRegLab. En cola con AUC ~0,79 | `transactions` + `balances` |
| **2** | **Mínimo intramensual y buffer days** | Mínimo diario del mes / gasto diario medio (días de colchón en el peor día) | JPMC (buffer days); Ocrolus (mínimo mensual). Mejora "meses de caja" a fin de mes, que puede esconder el valle | idem |
| **3** | **Tensión de la póliza (excedidos)** | Uso diario o mensual de la póliza: nº de meses con uso ≥ 95 %, uso máximo en 12 meses, tendencia a 3 meses, "uso bajo" (< 30 %) | **La mejor variable** en el banco francés; Norden y Weber y Mester la usan para alerta temprana. Hoy pesa 0,01 y le falta el dato en el 86 %: reconstruirla mejor y probarla solo donde hay póliza | `debt_products` (lineofcredit), `lc_drawn/lc_limit` |
| **4** | **Obligaciones recurrentes: retraso y omisión** | Detectar la fecha habitual (± días) de nómina, Seguridad Social, IVA y cuota. Medir el retraso en días frente a la habitual y las omisiones | FinRegLab (detección de recurrentes); Ocrolus (nómina, impuestos); OBIE. La omisión ya es evento (`incumplimiento_6m`); el **retraso** la anticipa | `salary`, `social_security`, `tax`, `debt_repayment`, `debt_schedule_config` |
| **5** | **Cobertura estructural de la próxima obligación** | (caja + cobros previstos de facturas AR no vencidas hasta la fecha) / (próxima cuota + nómina + IVA previstos) | Es el ratio que Brex valida como "predictor muy fuerte" de mora (caja / importe debido en el vencimiento). Sustituye a "carga de deuda", que no tenía orden | `proactive.py` ya lo proyecta de forma aritmética |
| **6** | **Stacking y financiación cara** | Nº de financiadores distintos; aparición reciente de factoring o confirming; cuotas con cadencia semanal o diaria; recencia de la última deuda nueva | FinRegLab (MCA como predictor), Ocrolus, Heron, Plaid, Kontomatik. "Deuda nueva con caja cayendo" salió floja: probar recuento y recencia, no el cruce | `debt_products`, `debt_repayment` |
| **7** | **CV de entradas y de saldo** (no la volatilidad total) | CV (DE / media) de `oper_in` y de la caja a 6-12 meses; percentil de la caja actual frente a sus 12 meses | FinRegLab (CV de saldo y de entradas); Plaid (primer reason code). El CV evita el sesgo de "mucha caja = mucha volatilidad" que hizo fallar la versión total | panel |
| **8** | **Proxy de NSF y descubierto** | Pico de `fee` frente a su mediana de 12 meses; `payment_refund` (cobros domiciliados devueltos); palabras clave en `description` (devol, impag, descub, excedid, recobro, embargo, aplaz) | NSF es feature en todos los proveedores; Tink usa los pagos a recobro. Hay que comprobar si el texto sintético contiene esas marcas | `transactions` |
| **9** | **Salud de la red de contrapartes** | Si los `counterparty_id` coinciden con empresas del panel: score medio ponderado por volumen de clientes y proveedores, y alerta si uno relevante entra en tensión | Defacto (node-based), Fundbox (business graph), Plaid Network (19 % del poder de LendScore). **Verificar solapamiento** antes | `invoices`, `transactions` |
| **10** | **Huecos sin cobros** | Mayor nº de días seguidos sin entradas operativas en 90 días frente a su norma | Plaid (`longest_gap_between_transactions`, días sin transacciones); "silencio de cobros" del brainstorm | `transactions` |
| **11** | **Peso de los cobros en efectivo** | `cash_settlement(s)` / entradas operativas y su tendencia | Ghosh, Vallée y Zeng: los cobros sin efectivo predicen menos default | `transactions` |
| **12** | **Colchón fuera de la cuenta corriente** | Saldo en ahorro o inversión / gasto mensual; retirada neta de inversión (`investment_return` > `deployment`) cuando baja la caja | FinRegLab ("savings and investment metrics"); descapitalizar el colchón es señal de estrés | `banking_products`, `investment_*` |
| Contexto | Antigüedad de la cuenta, nº de productos, meses de historia, % sin categorizar | UltraFICO y Kontomatik las puntúan, pero para nosotros son de **confianza u OOD**, no de salud | ya existe |

### 6.2 Prácticas de producto aplicables

1. **"PD estructural" sin etiquetas (Brex).** Ya tenemos el forecaster cuantílico (q10/q50/q90 + CQR) y la proyección aritmética de `proactive.py`. Proponemos publicar **P(caja a h meses < obligaciones previstas)** como probabilidad de tensión estructural, para cada empresa y horizonte:
   - Es interpretable ("probabilidad de no poder pagar la próxima nómina o cuota").
   - No necesita defaults y es coherente con nuestro evento `tension_6m`.
   - Se valida como hizo Brex: el ratio caja / obligación en la fecha debe separar a quienes luego incumplen (`incumplimiento_6m`).
2. **Límite dinámico con banda (Brex).**
   - "Límite sugerido" = k × P10 de la caja prevista a la fecha de repago (k = 50 %, como Brex), acotado por los flujos.
   - **Solo se recalcula si la previsión sale del intervalo del mes anterior.** Así el producto es estable y sigue reaccionando.
   - Encaja con la "prueba de los 100.000 €" de `context/scoring.md` y con prestar / vigilar / no prestar.
3. **Reason codes al estilo Reg B.**
   - Nuestro score es aditivo y la contribución por feature es exacta. Mostrar las **3-4 contribuciones más negativas**, en frases fijas por feature ("Tu saldo cayó por debajo de cero 6 días en los últimos 90"), y también las 2-3 positivas para el caso "mejora".
   - Evitar features de texto libre en los motivos principales (lección de FinRegLab).
4. **Reglas y flags separados del score (Codat, Defacto).**
   - Una capa de **knockouts o flags** que no mezcla con el score y **deriva a revisión humana** en vez de rechazar: historia < 3 meses, datos desactualizados (meses sin movimientos), omisión de IVA o nómina, uso de póliza ≥ 100 %, saldo negativo más de N días.
   - El jurado lo entiende mejor que meterlo todo en la media.
5. **Dos caminos según el dato disponible (Revolut, forced split).**
   - El 36 % de las empresas no tiene ERP. En vez de imputar 50 (neutro) a las features de facturas, evaluar un **segmento explícito `has_erp`**: pesos o calibración distintos por segmento, o un modelo con split forzado.
   - Revolut muestra que el camino sin la fuente extra compensa con las demás features y pierde poco (0,5-4 pp).
6. **Normalizar por tamaño de cuenta** (banco francés: todo dividido por las entradas mensuales medias). Ya lo hacemos con ratios y percentiles. Es buena práctica documentada y responde a la trampa de escala (de 10³ a 10⁹ €).
7. **Diseño económico mejor que fuerza bruta.** 30 variables con sentido superan a 5.000 automáticas (banco francés). Refuerza nuestra decisión de un score sencillo y explicable. Un GBM solo añade ~2 % de AUC y puede ser el "challenger" interno.
8. **Validación estilo FinRegLab.** Reportar AUC **y** KS (o H-measure) con intervalos por bootstrap, **por segmento** (empresas jóvenes o con poca historia, sin ERP, divisa). La ganancia de la señal de caja debería ser **mayor** en esos segmentos.
9. **Monitor de cartera como producto (EBA LOM).**
   - Watchlist con indicadores de alerta temprana (los de 6.1), revisión periódica y **acción asociada**: vigilar, recortar la línea, pedir información.
   - Norden y Weber ven la señal unos 12 meses antes: nuestra métrica de antelación debería mostrarlo por meses.
10. **Expectativas realistas.** Con solo tesorería, la literatura se queda en AUC ≈ 0,75-0,80 frente a default real. Nuestro 0,742 (caída ≥ 15 a 3 meses) está en rango. No hay que venderlo como un 0,9.
11. **Regulación.** Si Embat ofrece el score a prestamistas para **autónomos**, a partir de dic-2027 sería IA de alto riesgo (AI Act): logging, transparencia y supervisión humana. Para sociedades no aplica, pero sí las expectativas EBA de monitorización. Diseñar ya con trazabilidad (pesos congelados, explicación exacta, registro de decisiones) nos pone por delante.

---

## Fuentes principales

**Estudios independientes y académicos**
- FinRegLab, Howell, Matsumoto y Cochran (2025), *Sharpening the Focus* ([landing](https://finreglab.org/research/sharpening-the-focus-using-cash-flow-data-to-underwrite-financially-constrained-businesses/), [PDF](https://finreglab.org/wp-content/uploads/2025/06/FinRegLab_06-03-2025_Sharpening-the-Focus-Accessible-Text.pdf)).
- FinRegLab (2025), *Advancing the Credit Ecosystem* ([PDF](https://finreglab.org/wp-content/uploads/2025/07/FinRegLab_07-01-2025_Advancing-the-Credit-Ecosystem-Main.pdf)).
- FinRegLab (2019), *Empirical Research Findings* ([PDF](https://finreglab.org/wp-content/uploads/2023/12/FinRegLab_2019-07-25_Research-Report_The-Use-of-Cash-Flow-Data-in-Underwriting-Credit_Empirical-Research-Findings.pdf)) y *Small Business Spotlight* ([PDF](https://finreglab.org/wp-content/uploads/2023/12/FinRegLab_2019-09-06_Research-Report_Small-Business-Spotlight_The-Use-of-Cash-Flow-Data-in-Underwriting-Credit.pdf)).
- *Checking account activity and credit default risk of enterprises* ([arXiv 1707.00757](https://arxiv.org/abs/1707.00757)).
- Norden y Weber (2010), RFS ([OUP](https://academic.oup.com/rfs/article-abstract/23/10/3665/1566409)).
- Mester, Nakamura y Renault (2007), RFS ([WP](https://www.philadelphiafed.org/-/media/frbp/assets/working-papers/2005/wp05-14.pdf)).
- Mendonça y Ocariz, Revolut (2025), CRC Edimburgo ([PDF](https://www.crc.business-school.ed.ac.uk/sites/crc/files/2025-11/Evaluating-the-Contribution-of-Open-Banking-Data-to-Credit-Scoring-Performance-in-the-Spanish-and-French-Markets-paper.pdf)).
- Hjelkrem et al. (2022), JRFM ([DOI](https://doi.org/10.3390/jrfm15120597)).
- Frost et al. (2019), BIS WP 779 ([PDF](https://www.bis.org/publications/working-paper-779-bigtech-and-changing-structure-financial-intermediation.pdf)); Gambacorta et al. (2019), BIS WP 834 ([RePEc](https://ideas.repec.org/p/bis/biswps/834.html)).
- Ghosh, Vallée y Zeng, JF 2026 ([NBER](https://www.nber.org/papers/w34148)).
- JPMorgan Chase Institute, *Cash is King* ([PDF](https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/institute/pdf/jpmc-institute-small-business-report.pdf)).

**Proveedores y prestamistas**
- Plaid: [LendScore](https://plaid.com/blog/how-we-built-lendscore/), [ciclo de vida](https://plaid.com/blog/lending-lifecycle-with-cash-flow-data/), [API de Consumer Report](https://plaid.com/docs/api/products/check/), [atributos de Asset Report](https://github.com/plaid/assets-attributes).
- Prism: [CashScore](https://www.prismdata.com/cashscore/), [v4](https://www.prismdata.com/blog/prism-data-introduces-cashscore-v4-raising-the-bar-for-cash-flow-underwriting-tools-as-the-u-s-adopts-open-banking/).
- [Nova Credit](https://www.novacredit.com/cash-atlas); FICO: [UltraFICO](https://www.fico.com/en/latest-thinking/fact-sheet/ultrafico-score-fact-sheet), [con Plaid](https://www.fico.com/en/newsroom/fico-partners-plaid-launch-next-generation-cash-flow-ultrafico-score).
- Experian: [Cashflow Score](https://www.experianplc.com/newsroom/press-releases/2025/launch-of-experian-s-cashflow-score-signals-new-era-of-open-bank).
- [Ocrolus](https://docs.ocrolus.com/reference/cash-flow-features), [Codat](https://docs.codat.io/lending/premium-products/credit-model-overview/), [Flinks](https://docs.flinks.com/guides/enrich/attributes-packages), [Tink](https://tink.com/products/risk-insights/), [Kontomatik](https://kontomatik.com/financial-health-indicator), [Validis](https://www.validis.com/), [Heron](https://www.herondata.io/).
- Brex: [blog](https://medium.com/brexeng/how-we-built-a-probability-of-default-model-without-default-labels-212415bbeef6), [límites](https://www.brex.com/support/how-do-brex-credit-limits-work).
- [Ramp](https://support.ramp.com/ramp-bank-connections-overview), [Fundbox](https://www.pymnts.com/smbs/2019/fundbox-data-lending-credit/), [Bluevine](https://www.bluevine.com/blog/business-line-of-credit-requirements), [Square](https://squareup.com/help/us/en/article/6479-square-capital-loan-eligibility), [Shopify](https://help.shopify.com/en/manual/finance/shopify-capital/united-states), [Stripe](https://edge-docs.stripe.com/capital/import-non-stripe-data), [iwoca](https://www.iwoca.co.uk/finance-explained/anna-nava).
- Defacto: [underwriting](https://www.getdefacto.com/article/underwriting-defacto-automated-lending), [modelo de red](https://www.getdefacto.com/article/node-based-credit-model).
- [BBVA](https://www.bbva.es/finanzas-vistazo/ef/prestamos/scoring-concesion-prestamo.html), [Equifax ES](https://soluciones.equifax.es/empresas/productos/risk-score-open-banking/), [Open Banking UK](https://www.openbanking.org.uk/insights/how-lenders-are-getting-a-clearer-view-of-smes/).

**Regulación**
- CFPB: [Circular 2022-03](https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/), [comentario Reg B §1002.9](https://www.consumerfinance.gov/rules-policy/regulations/1002/interp-9/).
- [EBA/GL/2020/06](https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring).
- AI Act: [anexo III](https://artificialintelligenceact.eu/annex/3/), [Digital Omnibus](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/).
- SBA y SBSS: [Nav](https://www.nav.com/blog/sba-to-sunset-fico-sbss-for-small-loans-what-does-this-mean-for-your-small-business/).
