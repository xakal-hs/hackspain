# X-Ray · salud financiera de pymes desde la tesorería

**HackSpain 2026 · reto de Embat** · 18–20 de septiembre, ETSIT UPM (Madrid)

Embat da el rastro financiero de 1.286 empresas sintéticas (250 grupos, de septiembre de 2024 a
septiembre de 2026): movimientos bancarios, facturas del ERP, deuda y un saldo final. A partir de
ahí este repositorio construye **un score de salud de 0 a 100 por empresa y mes**, su **trayectoria
prevista a 1-3 meses** con intervalos de confianza, un **monitor de alertas** y un **simulador de
escenarios**, todo servido por una API y una SPA que se abre delante del jurado.

![Cartera de la demo: 140 empresas con score, banda, tendencia y cambio previsto a 3 meses](research/app/screenshots/01-cartera.png)

La pieza central es `research/`. El resto del repositorio es el contexto que la justifica: el
enunciado, el marco de decisión del equipo, la capa que corrige la suciedad de los CSV y los
informes exploratorios.

## Las seis preguntas del reto

El enunciado ([`context/challenge.md`](context/challenge.md)) no pide predecir quiebras, sino leer
el comportamiento en las dos direcciones y antes de que sea evidente: quién está sano, quién mejora
(45→65), quién empieza a torcerse aunque aún parezca sano (82→68), si es un bache o una caída
estructural, qué señal se movió y cuándo, y con cuántos meses de antelación se vio venir.

El marco con el que respondemos está en [`context/scoring.md`](context/scoring.md): el score se
diseña como un prestamista con 100.000 € que decidir. La criticidad no es uniforme (una caja que se
evapora pesa mucho más que un DSO que se mueve un poco, y la liquidez no pesa igual en todos los
sectores), y el resultado no es solo un número: para cada empresa y mes hay nivel, trayectoria,
explicación en lenguaje llano, bache frente a caída, el coste de no hacer nada y una mesa de
opciones. Cómo lo enseña Embat está en [`context/voz_embat.md`](context/voz_embat.md). Cómo se mueve
el dinero sin licencia propia y cómo se parte el préstamo por plazo está en
[`context/voz_capchase.md`](context/voz_capchase.md).

## Estructura

| Ruta | Qué contiene |
|---|---|
| [`context/`](context) | Enunciado, marco de scoring, monetización, oportunidades, voz de producto de Embat, voz de crédito de Capchase y auditoría comercial para el jurado, con versiones HTML autocontenidas |
| [`data/`](data) | Los CSV originales del reto y su diccionario. **No se modifican nunca.** `invoices.csv` y `transactions.csv` van por Git LFS |
| [`src/mapping/`](src/mapping) | Capa de mapeo: vistas DuckDB que corrigen la suciedad al leer (países no ISO, ERP en dos vocabularios, deuda con signo invertido, saldos absurdos…). El inventario de fallos y su regla está en [`ISSUES.md`](src/mapping/ISSUES.md) |
| [`analysis/`](analysis) | Exploración del dataset. Informes autocontenidos que se abren sin servidor (`report.html`, `features_analisis_automatico.html`, `features_challenge.html`), la reconstrucción del histórico de caja (`cash_history.py`) y un explorador interactivo de esa caja en Streamlit (`app.py`) |
| [`scripts/`](scripts) | Utilidades del panel de caja: materializarlo en `analysis/cash.duckdb` (`build_cash_db.py`), validarlo contra el saldo ancla (`validate_cash.py`) y comprobar que sale idéntico en tres construcciones (`check_determinism.py`) |
| [`research/`](research) | **El sistema.** Panel mensual, score, previsión, monitor, simulador, API y demo. Tiene su propio [README](research/README.md) |
| [`frontend/`](frontend) | Frontend de producción en Nuxt 4 + Vue 3/TypeScript, con Vite, Nitro, Pinia, TanStack Query y el sistema visual de X-Ray |
| [`features.md`](features.md) | Brief de brainstorming de features: el reto, las trampas del dataset y las 17 features actuales con su peso |
| [`AGENTS.md`](AGENTS.md) | Contexto permanente para agentes de código, más `.agents/skills/` y `skills-lock.json` |

Dentro de `research/`:

| Ruta | Qué hace |
|---|---|
| `src/ingest.py`, `src/fx.py`, `src/panel.py` | CSV → parquet, tipos de cambio reales (BCE + currency-api) y panel empresa × mes con la caja reconstruida hacia atrás |
| `src/features.py`, `src/targets.py` | Las 17 features adimensionales del score y los eventos ancla (apagado, tensión de caja, declive, crecimiento) que sustituyen a las etiquetas que el dataset no trae |
| `src/xray.py` | API estilo scikit-learn: `HealthScorer` (nivel, aditivo y explicable al céntimo) y `TrajectoryForecaster` (LightGBM cuantílico q10/q50/q90 con calibración conformal) |
| `src/service.py`, `app/server.py` | El modelo como servicio: FastAPI según [`app/API_CONTRACT.md`](research/app/API_CONTRACT.md), con simulador de escenarios |
| `app/static/index.html` | La SPA de un solo fichero. Su lenguaje visual está fijado en [`app/DESIGN.md`](research/app/DESIGN.md) |
| `src/evaluate.py`, `src/anticipation.py` | Validación GroupKFold por `group_id` × 3 cortes y medición de antelación fuera de fold |
| `src/predict_submission.py` | Scoring del test oculto de 60-80 empresas nunca vistas |
| `DECISIONS.md`, `METRICS.md`, `reports/` | Las 28 decisiones con su porqué y su evidencia, la definición de cada métrica y los resultados por versión |
| `brainstorm/` | Propuestas de features de cuatro modelos sobre el mismo brief, con su [síntesis](research/brainstorm/SINTESIS.md) |

## Arranque rápido

Los datos grandes van por Git LFS, así que lo primero es traerlos (si `data/transactions.csv` pesa
134 bytes, es un puntero):

```bash
git lfs pull
```

El sistema y la demo se levantan desde `research/` con [uv](https://docs.astral.sh/uv/):

```bash
cd research
uv sync
uv run python src/ingest.py     # CSV -> data/*.parquet
uv run python src/fx.py         # tipos de cambio reales -> data/fx/
uv run python src/panel.py      # panel empresa x mes -> data/panel.parquet
uv run python src/service.py    # entrena el modelo -> artifacts/xray.joblib
uv run uvicorn app.server:app --port 8080   # abrir http://localhost:8080
```

Los comandos de validación, tests y scoring del test oculto están en el
[README de `research/`](research/README.md).

Los informes de `analysis/` ya están generados y se abren con doble clic. `analysis/` y `scripts/`
son la parte exploratoria y tienen sus propias dependencias en [`requirements.txt`](requirements.txt),
independientes de `research/` (en Windows, `.venv\Scripts\python.exe`):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python analysis/generate_report.py        # -> analysis/report.html
.venv/bin/python analysis/feature_criticality.py    # -> analysis/features_analisis_automatico.html
.venv/bin/python scripts/build_cash_db.py           # panel de caja -> analysis/cash.duckdb (~30 s, no se commitea)
.venv/bin/python scripts/validate_cash.py           # cuadre del histórico contra el saldo de 2026-09-01
.venv/bin/python -m streamlit run analysis/app.py   # explorador interactivo de la caja (requiere streamlit)
```

`analysis/challenge_features.py` es la excepción: usa el mismo panel y las mismas features que el
score, así que se ejecuta desde el entorno de `research/`:

```bash
cd research && uv run python ../analysis/challenge_features.py   # -> analysis/features_challenge.html
```

El frontend moderno se ejecuta por separado. Sus dashboards son una narrativa de producto con
fixtures ficticios; `XRAY_API_BASE` solo conecta actualmente el adaptador de `/api/companies` y no
convierte el resto de la experiencia en un flujo real de backend:

```bash
cd frontend
nvm install && nvm use       # Node 22.22 (fijado en frontend/.nvmrc)
corepack enable
pnpm install
pnpm dev
```

La capa de mapeo se comprueba con sus propios tests (con fixtures, no necesitan el dataset) y con una
auditoría de la suciedad que queda sin corregir:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s src/mapping/tests -t src
PYTHONPATH=src .venv/bin/python -m mapping.audit
```

## Dónde está el resultado

La versión actual es **v7**. En validación fuera de grupo detecta caídas de ≥15 puntos a 3 meses
con AUC **0,725** (0,693 el AR(1)) y subidas con AUC **0,730** (0,692 el AR(1)). En el quintil de
empresas que aún parecen sanas, el AUC de deterioro es **0,604** frente a 0,538. El nivel discrimina
con AUC 0,657 la tensión de liquidez a seis meses. La anticipación longitudinal todavía procede de
la evaluación v5/v6: el 48 % de 229 caídas estructurales tuvo una alerta previa, con mediana de tres
meses. Bache frente a caída sigue sin resolverse (AUC 0,53) y el 23 % de las alertas parpadea.

La verdad comercial está en [`context/monetizacion.md`](context/monetizacion.md): con importes
convertidos y caja reconstruida, el escenario central es **4,2 M€/año** (rango 3,0–5,4), sobre
**344 M€ de excedente en 370 empresas**. Son escenarios sobre datos sintéticos, no una previsión de
ventas ni evidencia de disposición a pagar. Cómo se enseña el coste (dinero parado, divisa) y cómo
se ofrece deuda está en [`context/voz_embat.md`](context/voz_embat.md). Licencia de partner, rejilla
de plazos y retención están en [`context/voz_capchase.md`](context/voz_capchase.md). La tesis y los
puntos ciegos priorizados para el jurado están en [`context/auditoria_comercial.md`](context/auditoria_comercial.md).

La tabla completa, las referencias y las limitaciones están en el
[README de `research/`](research/README.md) y en [`research/METRICS.md`](research/METRICS.md).

Cada elección del sistema —por qué el score es por empresa y no por grupo, por qué los pesos salen
de una logística con signo restringido, por qué el suavizado es un EWMA con α = 0,5— está registrada
con su pregunta, su alternativa descartada y su evidencia en
[`research/DECISIONS.md`](research/DECISIONS.md) y en la pestaña «Decisiones» de la demo.
