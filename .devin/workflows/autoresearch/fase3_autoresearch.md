# Fase 3 · El bucle de autoresearch: testear, diagnosticar, cambiar, repetir

Eres el **orquestador** del workflow de autoresearch. Ejecutas el bucle que convierte las premisas de la fase 2 en mejoras medidas del score. Aquí **sí se modifica el modelo**, en una rama, con evidencia y sin romper lo que ya funciona.

Entrada: `salida/premisas.jsonl` (fase 2). El runner es `.devin/workflows/autoresearch/premisas.py`.

> **Fuera de alcance.** El forecaster de trayectoria (mlforecast + LightGBM, `src/xray.py::TrajectoryForecaster`) y la previsión con LGBM **no se tocan en este bucle**. El objeto es el **score de nivel y su sentido**, no la predicción. Si una premisa depende de la trayectoria, se marca y se pospone.

## Preparación

1. Comprueba que el árbol está limpio salvo `salida/`. Crea la rama `autoresearch/<fecha>` desde `main`.
2. `cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build` (cachea features+eventos).
3. Captura la **línea base**: `premisas.py run` y `cd src && uv run python evaluate.py v7 --small`. Guarda en `salida/iteraciones/iter_000/`.
4. Lee la lista de premisas **centrales** que dejó el consejo (fase 2). Una premisa central que falle es prioridad máxima.

## El bucle (una iteración = un cambio)

### 1 · Testear
`premisas.py run` sobre `salida/premisas.jsonl`. Toma las que `fallan` y ordénalas: centrales primero, luego por ámbito (liquidez > deuda > cobros > resto).

### 2 · Diagnosticar (lo más importante)
Para cada premisa que falla, decide **de quién es la culpa** y escríbelo en `salida/iteraciones/iter_NNN/diagnostico.md`:

- **Premisa incorrecta.** El dato contradice la premisa porque la premisa no describe la realidad. Ejemplos reales de la semilla: `P008` (la volatilidad a la baja tiene AUC 0,33 frente a tensión, no >0,52: quizá la feature mide lo contrario), `P010` (la tendencia de actividad da AUC 0,41 frente al apagado: el apagado es desconexión, R06). → Corrige la premisa o el evento, no el modelo. Anota la decisión en `REFLEXIONES.md` al cerrar.
- **Modelo incorrecto.** La premisa es verdadera pero el sistema no la cumple. → Candidata a cambio: una feature, su dirección/peso, una definición de evento o un umbral.
- **Datos insuficientes.** El runner devuelve `n` bajo o el evento está censurado. → Marca `verificable: false` con el motivo; pasa a juicio humano/modelo.

**Regla de honestidad:** si no puedes decidir entre «premisa mal» y «modelo mal» con una medición, diseña la medición antes de tocar código. No cambies el modelo a ciegas.

### 3 · Proponer un cambio mínimo
Un solo cambio por iteración, el más pequeño que pueda hacer pasar la premisa. Fuentes de cambio, en orden de preferencia:
1. Corregir la **dirección o el signo** de una feature (si los datos la contradicen, el peso debería ser 0, D12).
2. Añadir una **feature del brainstorming** con señal ya medida (`payee_concentration`, `lost_accel`, `payroll_cv`, `hhi_ap_6m`, `oper_persistence_6m`; R07).
3. Ajustar una **definición de evento** (`src/targets.py`) si la premisa la delata como mal definida.
4. Cambiar un **umbral** (bandas, histéresis R12, criterio de bache R11).

Prohibido: dar más peso a una feature solo porque sí; romper la **explicación aditiva exacta** (`explain()` debe seguir sumando al céntimo); introducir no linealidad por feature (R09: no aporta); meter el apagado en la calibración (R06).

### 4 · Implementar y medir
Implementa el cambio en `src/` (nunca en `data/`). Vuelve a correr, en este orden:
1. `premisas.py run` → ¿pasa la premisa objetivo?
2. `cd research/src && uv run python evaluate.py v<N> --small` → AUC del nivel frente a E1-E4.
3. `cd research && uv run pytest -q tests` → verde.
4. `explain()` cuadra (test de explicación exacta).

### 5 · Aceptar o descartar
Acepta el cambio solo si **todas** se cumplen:
- La premisa objetivo pasa.
- Ninguna premisa **central** que pasaba antes deja de pasar.
- El AUC del nivel no baja más de 0,01 en ningún evento E1-E4 y sube en al menos uno.
- Los tests siguen verdes.

Si no, revierte (`git checkout -- src/`) y anota por qué en `decision.md`. Un cambio descartado con su porqué vale tanto como uno aceptado.

### 6 · Registrar
Escribe `salida/iteraciones/iter_NNN/` con: `diagnostico.md`, `cambio.md` (el diff en palabras), `antes.json`, `despues.json`, `decision.md` (aceptado/descartado y por qué). Actualiza `premisas.jsonl` con `estado`, `diagnostico` e `iteracion` de las premisas afectadas. Si aceptas, haz commit `autoresearch(<ámbito>): <qué> — <premisa>`.

## Criterios de parada

- No queda ninguna premisa central en `falla` y las verificables pasan o están justificadas.
- Dos iteraciones seguidas sin mejora del AUC (meseta): para y documenta el techo.
- Presupuesto de iteraciones agotado (por defecto 12).

## Cierre

1. Elige la versión ganadora. Actualiza `research/ESTADO.md` (sección de resultados) y `DECISIONS.md` con las decisiones nuevas (`Dxx`).
2. Escribe `salida/informe_autoresearch.md`: la tabla de premisas antes/después, las iteraciones, los cambios aceptados y descartados, y el AUC por evento frente a la línea base.
3. Actualiza `REFLEXIONES.md` con lo que quede abierto y con las premisas que resultaron ser **incorrectas** (eso es aprendizaje, no fracaso).
4. Haz push de la rama y abre un PR contra `main` con el resumen. **No hagas merge:** lo decide el usuario.

## Reglas

- Solo tocas `research/src/`, `research/tests/` y `.devin/workflows/autoresearch/salida/`. No toques `data/`, ni los CSV, ni `analysis/`.
- Nada de secretos en ficheros.
- Escribe en español. Cada afirmación sobre el código o los datos lleva su referencia (`file:line`).
- Termina con: nº de iteraciones, cambios aceptados, AUC por evento frente a la base, premisas que resultaron incorrectas y el estado final del PR.
