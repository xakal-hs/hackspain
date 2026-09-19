# Estado del arte: cómo se mide el riesgo de crédito de una empresa

Hasta el 19-sep-2026 el score se había diseñado desde la analogía de los 100.000 € (`context/scoring.md`) y los brainstorms entre modelos, sin revisar cómo lo hacen los bancos, los burós, las fintech y la literatura. Esta carpeta cubre ese hueco. Hay tres informes con fuentes (cada uno termina con una sección "Qué nos llevamos"):

| Informe | Qué cubre |
|---|---|
| [01 · Bancos, regulación y burós](01_bancos_regulacion_buros.md) | Basilea IRB (PD/LGD/EAD), definición de default (EBA, Circular 4/2017 anejo 9), guías de alerta temprana (BCE, EBA LOM), rating interno de pymes, Altman/Ohlson/Merton/RiskCalc, Informa, Axesor, D&B (PAYDEX), Experian |
| [02 · Fintech y cash-flow underwriting](02_fintech_cashflow_underwriting.md) | OnDeck, iwoca, Brex, Revolut, Defacto…; atributos reales de Plaid, Ocrolus, Flinks, FICO, Prism; estudios de FinRegLab; reason codes (Reg B); monitorización |
| [03 · Literatura académica](03_literatura_academica.md) | ML frente a logística en pymes, datos de cuenta corriente (Norden & Weber, Yao et al.), pago comercial, hazard en tiempo discreto, cambio de régimen, etiquetas proxy, validación y explicabilidad |

Esta página cruza lo encontrado con lo que ya tenemos (`features.md`, `research/REFLEXIONES.md`). La entrada abierta es la **R21**.

## 1. Lo que ya hacemos bien (y ahora tiene respaldo)

- **Los eventos no son inventados.** Impago de nómina, SS o IVA = anejo 9, 107.f de la Circular 4/2017 ("compromisos vencidos con organismos públicos o empleados"). Tensión = 107.c ("flujos insuficientes"). Caída de cobros = 94.b y EBA/GL/2020/06 §274.c. Veto de grupo = 94.o. Frase para el pitch: *usamos los indicadores de default de la Circular 4/2017 y de la EBA que se pueden observar en tesorería.*
- **La cura con 3 meses limpios** es el periodo de prueba de la EBA para salir de default.
- **La logística por evento sobre el panel empresa-mes** es un modelo de hazard en tiempo discreto (Shumway 2001), el estándar en pymes.
- **Modelo sencillo.** El GBM gana a la logística 0-2,6 pp de AUC; los datos de comportamiento suben unos 10 pp a todos los modelos (Moscatelli et al. 2020, Banco de Italia). Es lo que medimos en R09. 30 variables con sentido económico superan a 5.000 automáticas (banco francés).
- **Ratios, no importes.** Yao et al. normalizan todo por las entradas medias de 24 meses de la propia cuenta.
- **Nuestro AUC está en el rango esperable.** Con datos de cuenta solos la literatura da 0,75-0,80 (0,80 en pymes de Société Générale; 0,78-0,80 en FinRegLab). No hay que prometer 0,9.
- **Validación por grupo** en vez de CV aleatoria por filas, que es uno de los errores más citados.

## 2. Qué nos falta, por retorno esperado

| # | Qué | Por qué (fuente) | Con nuestros datos | Relación |
|---|---|---|---|---|
| 1 | **Señales EWS de texto**: embargos y diligencias AEAT/TGSS, recibos propios impagados, aplazamientos con Hacienda/SS, intereses de descubierto | Catálogo del BCE (anejo 4), anejo 9 108.a (reclamación judicial = factor automático) | Barrido de `description`: ~164 empresas con embargos, ~76 con aplazamientos, ~132 con descubierto (regex sin validar) | Candidatas a veto o evento grave |
| 2 | **Saldo diario: días en negativo, mínimo intramensual, amplitud máx−mín, excedidos de póliza** | La señal más documentada: Norden & Weber (≈12 meses antes), Yao (excedidos = variables 1-3), Moody's (uso de póliza 76 % frente al 52 % dos años antes), toda la industria fintech | Saldo diario reconstruido + `lc_drawn/lc_limit` | Ya en cola; la literatura dice que va primero. Uso de póliza hoy pesa 0,01 y falta en el 86 % |
| 3 | **Retraso (no solo omisión) de nómina, SS, IVA y cuota** | FinRegLab, Ocrolus: la detección de recurrentes; el retraso anticipa la omisión | Día habitual de cada obligación y días de desvío | Anticipa `incumplimiento_6m` |
| 4 | **Cobertura de la próxima obligación** = (caja + cobros AR previstos) / (cuota + nómina + IVA previstos) | Brex construyó una PD **sin etiquetas de default** con P(saldo previsto < lo debido) | `proactive.py` y el forecaster cuantílico ya proyectan | Sustituye a "carga de deuda", que no ordena (R16); da una PD interpretable (R02) |
| 5 | **Retraso a proveedores ponderado por importe (tipo PAYDEX)** y "severamente moroso" (≥ 10 % del AP a más de 90 días, D&B) | El retraso sobre el vencimiento es de los mejores predictores no financieros: AUC 0,64 → 0,76 en micro (Altman, Sabato & Wilson 2010) | Hoy `late_share_ap` cuenta facturas sin ponderar | Mejora de la feature 4 |
| 6 | **Modelo con ERP y sin ERP** en vez de imputar 50 | Informa pondera 55/16/29 con cuentas y 40/60 sin ellas; Axesor y Revolut tienen dos caminos | Segmento `has_erp` (el 36 % no tiene facturas) | Nuevo |
| 7 | **El crecimiento no es monótono** | RiskCalc: crecer muy deprisa y caer muy deprisa suben el riesgo | "Tendencia de actividad" por tramos o en U | Explica su ⚠️ "solo la mitad baja" |
| 8 | **Revisar el signo de pagar antes de plazo** | PAYDEX lo premia (100 = paga antes) | `ap_early_3` lo leía como sacar caja pronto | Validar por tramos |
| 9 | **Horizontes 3, 6 y 12 meses** | Las señales llegan escalonadas: amplitud del saldo ~5 meses, póliza ~9, cobros 12-18, excedidos 18 | Con 24 meses, 12 es el máximo honesto | Pregunta 6 del reto ("cuándo se vio venir") |
| 10 | **Bache o caída como cambio temporal frente a escalón** | Chen & Liu 1993; BOCPD (Adams & MacKay 2007); por defecto un shock es bache (Gorbenko & Strebulaev) | Fracción del shock recuperada a 1-3 meses; meses desde el último cambio de régimen; caída solo si persiste **y** sube la póliza o se estiran pagos | R11 (AUC 0,50) |
| 11 | **Banda publicada con histéresis** | Las agencias solo migran si el desvío supera un umbral durante k meses (Altman & Rijken 2004) | Nota reactiva (α 0,5) + banda estable | R12 (parpadeo) |
| 12 | **Escala absoluta tipo scorecard** | Puntos = offset + factor·ln(odds), PDO fijo; escala maestra ≥ 7 grados (el Banco de España publica PD de 0,1 % a 5 %) | Calibrar isotónica fuera de grupo | R01, R02 |

**Ideas con menos prioridad:** coste de la financiación (intereses / deuda), número de bancos y altas en bancos nuevos, CV de las entradas (no la volatilidad total), mayor hueco sin cobros, colchón en ahorro e inversión, peso de cobros en efectivo, salud de la red de contrapartes (primero comprobar si los `counterparty_id` coinciden con empresas del panel), momentum del propio score.

## 3. Validación y explicación al estilo banco

- **Kit del BCE para modelos internos:** AUC sobre los grados, test de Jeffreys por grado, matriz de migración (responde a "quién mejora" y "quién empeora"), PSI del score y de cada feature, tasa de vetos (equivale a la de overrides).
- **Diferencias de AUC menores de 1-2 pp no son significativas** con nuestros positivos (Stein 2007). El autoresearch no debería aceptar iteraciones por diferencias dentro del IC bootstrap por grupo.
- **Grupo × tiempo:** GroupKFold por `group_id` combinado con walk-forward.
- **Reason codes:** las 3-4 features que más puntos quitan frente a la mediana de las empresas sanas (explican el nivel), además de la descomposición mes a mes que ya tenemos (explica el cambio). Frases fijas por feature, nada de texto libre.
- **Comprobar las explicaciones con perturbaciones sintéticas** (Alonso & Carbó, Banco de España 2022): inyectar una caída de cobros conocida y medir si la explicación la señala.

## 4. Lo que no podemos replicar

Ratios de balance (Altman Z/Z'', Ohlson, Zmijewski), Merton/KMV (no hay precios), CIRBE, RAI, ASNEF y el módulo cualitativo. Tampoco recortes de límite de pólizas: `granted` es una foto final. Es precisamente el hueco que cubre Embat: **el banco rellena con balance anual lo que nosotros vemos cada día en tesorería.**

No encontramos papers que usen la facturación electrónica (SII español o SDI italiano) para predecir default de empresas: se puede presentar como novedad.
