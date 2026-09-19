# Radar del track Embat · Lo que hacen los otros equipos (insumo del debate)

> Fuente: `github.com/xakal-hs/radar` (radar de competidores del track Embat "X Ray", HackSpain 2026),
> ramas `insights/*`. Es **material de terceros**, no verificado por nosotros: entra al debate como
> **enfoques a evaluar**, no como verdad. Cada afirmación lleva su equipo y su repo.

## Estado del track (según el radar, 19/09)

16 equipos; 10 con repo público. **Demo ante el jurado: domingo 11:00.** Dos escuelas:

1. **Determinista / scorecard** (`burn-rate`, `Elkano`, `airbenders`): fórmulas con pesos, anclas de
   dominio, explicabilidad exacta por aditividad, nulos honestos. Fuerte ante Embat (auditabilidad);
   débil en potencia.
2. **ML supervisado** (`Quantum Churros`): CatBoost contra un target propio. Riesgo: circularidad y caja negra.

El radar sostiene que **la posición ganadora combina señal rica + explicabilidad defendible + anticipación
medida con honestidad**. Y que **nadie tiene etiquetas oficiales**: todos se inventan el target.

## Los equipos y sus decisiones (lo que importa para nuestro debate)

### Elkano (`amarkosmarkos/Elkano_Embat`) — el rival metodológico

- **Evento de impago observable D1-D4** (estilo banca, «default = 90+ días sin pagar»):
  D1 factura recibida vencida 90+ días sin pagar ≥1 % de las salidas; D2 falta de nómina/SS/tax;
  D3 saldo *checking* < 0 cinco días del mes; D4 comisiones/intereses anómalos. Incluye **cura**
  (salida del evento). *Es un comportamiento observable, no una etiqueta de salud inventada.*
- **Validación**: Gini + **lead time**, out-of-sample por grupo, horizontes y_1/y_3/y_6.
- **Tabla anti-leakage explícita**: no usar `invoices.status` (foto de extracción), no anclar saldos a
  `balances.csv`, percentiles por mes (no globales), control de «feature gemela» del evento.
- Tres scorers: scorecard, variante calibrada por Gini, y **GBM entrenado contra el evento**
  (`100·(1−P(evento))`, `trained_without_fold` = cada fila predicha sin su grupo).
- 105 columnas por empresa/mes.

### burn-rate (`danielkwapien/hackspain-2026`) — el equipo a batir

- **Forense del dataset antes de modelar** (hallazgos ejecutados, no leídos):
  - `payment_date` solo es fiable si `status='paid'`; recalculan la **mora «as-of»** cada mes y descubren
    **122.006 facturas tardías ocultas**.
  - 39 % del universo sin facturas correlaciona con **no tener ERP**, no con salud → **dos ramas de cobertura**.
  - **Intragrupo real**: 25,9 % de las transferencias son **espejo** (importe opuesto al céntimo, ±2 días,
    mismo grupo; 0,2 % en placebo) → **netean antes de agregar al grupo**.
  - PELT: 1 breakpoint mediano por empresa; 79 % de los saltos >3σ persisten → trayectoria por escalones.
- **LABEL-VIABILITY**: construyeron 3 indicadores de tensión (caja < 0 dos meses, parada de SS/deuda,
  >35 % facturas vencidas) y el test de co-movimiento da «observado ≈ esperado bajo independencia» →
  **no existe un factor latente de salud** explotable como etiqueta. Veredicto: **no entrenar contra
  etiqueta sintética.**
- **La unidad pasa a ser el GRUPO (250)**; la sociedad es *drill-down*. Usuario = inversor/prestamista con
  **cartera ordenada**. «Ranking explicable > número exacto».
- **Nulos honestos**: sin actividad bilateral o <3 meses → `score = null` con motivo, no cero.
- Publican **AUC honestos**: anticipación a 6 meses apenas **0,53-0,58**; falsa alarma 0,17 vs base 0,19
  «no es mérito».

### Quantum Churros (`hackspain-2026-team1/quantum-churros`) — la escuela que se pliega

- Entrenaban CatBoost contra `future_health` = su propio baseline heurístico. **Pivote (19/09 09:59):**
  «El dataset no tiene etiquetas. El objetivo que entrenaba `modeling.py` era **circular**» → abandonan el
  ML y pasan a un **motor determinista**. La escuela supervisada se pliega.

### Byte_Me (`JJavierBS/Hackspain-2026---Embat-track`) — el producto

- **Multi-comprador**: el **mismo score re-ponderado por comprador** (BANK | FUND | INSURER), con perfil en
  la URL. Score 0-100 mensual dividido en **Level** y **Trajectory**; separa bache de declive estructural;
  mide meses de antelación; alertas con replay.
- **Rollup de sociedades a grupo sin filas intragrupo**.

### airbenders — scorecard TS (12 indicadores) + backtest con lead time (recall, falsas alarmas, p25).

### Lo que el radar dice que **nadie** ha resuelto

- **Consolidación multidivisa de verdad** (burn-rate puntúa por moneda; QC usa moneda como categórica).
- El **formato del leaderboard** (unidad grupo vs empresa) sigue sin confirmar.

## La propuesta propia del radar («Frankenstein»)

Scorecard aditivo y explicable (lo que ve el jurado) + **evento de impago observable D1-D4** como verdad +
ML que predice ese evento (no la salud) como capa de anticipación. Unidad = grupo; usuario = inversor;
ranking explicable; FX declarado como limitación.

## Qué corrobora y qué desafía a nuestro debate (esto es lo que hay que dirimir)

**Corrobora** nuestras conclusiones del debate anterior:
- **Q12 (unidad = grupo)**: burn-rate y Byte_Me ya lo hacen; el método de neteo espejo (25,9 %) es concreto.
- **Q2 (target circular)**: Quantum Churros pivota por exactamente eso; el radar lo llama «munición del jurado».
- **Q4 (una nota promedia y diluye)**: Byte_Me re-pondera **por comprador** sobre el mismo score.
- **Q5 (ranking explicable > ajuste)**: burn-rate lo hace bandera.

**Desafía** nuestras conclusiones:
- **Q1/Q2/Q3 (nuestras anclas)**: frente a `tension_6m`/`expansion_6m` (estado, circular, no medible en
  empresas nuevas), Elkano propone un **evento de impago observable** que existe desde el mes 0, no es
  circular y es estándar de banca. ¿Es mejor ancla que las nuestras?
- **LABEL-VIABILITY**: si no hay factor latente de salud (indicadores independientes), ¿tiene sentido
  calibrar una nota contra **cuatro** anclas, o hay que medir cada comportamiento por separado?
- **Mora as-of**: su recálculo (122.006 facturas ocultas) es exactamente la clase de fuga que nosotros
  encontramos en `late_share` (D05/alias). ¿Cuánto cambia nuestro score si aplicamos su recálculo?
- **Nulos honestos**: `score = null` con motivo (no cero). ¿Coincide con nuestra decisión de
  `tension_6m = null` en `group_funded`?
- **Anticipación honesta**: publican 0,53-0,58 a 6 meses. ¿Es el techo realista o nuestro 0,62-0,70 es
  inflado por la circularidad de la etiqueta?
- **Los «big NO» como ancla (R7)**: Elkano convierte las reglas de exclusión (no pagar nómina/SS/tax, caja
  negativa 5+ días, facturas vencidas 90+ días) en un **evento observable D1-D4** y lo valida. Nosotros
  tenemos los mismos vetos **codificados en la decisión** (C1 caja rota, C5 nómina ausente, C4 póliza
  agotada) pero el **score se calibra contra `tension_6m`**, no contra ellos. ¿Deberían ser el ancla
  medible, con el falso positivo trimestral (Q8: 49/209 episodios duran 3 meses) sobre la mesa?
  **Métrica: AUC es la base; el Gini es un extra (2·AUC − 1), no la métrica titular.**
