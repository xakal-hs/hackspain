# Fase 5 · Documento técnico del score, cuestionado por subagentes

Eres el **orquestador** del workflow de autoresearch. Esta es la fase de cierre documental. Produces un **documento técnico y detallado de cómo se calcula el score** (`salida/documento_score.md`) y lo sometes a un **consejo adversarial** de subagentes que lo cuestionan con preguntas del estilo del reto (¿y si…? ¿bajo qué condiciones? ¿qué pasa si esto está mal?).

Entradas: el código (`research/src/xray.py`, `features.py`, `targets.py`, `service.py`), `research/DECISIONS.md`, y `salida/politica_prestamo.md`. **La fuente de verdad de los números es `score_datos.py`**, no tu memoria.

## Paso 1 · Los números reales

```bash
cd research && uv run python ../.devin/workflows/autoresearch/score_datos.py --out ../.devin/workflows/autoresearch/salida/score_datos.md
```

Eso vuelca del artefacto servido: features con pilar/dirección/peso, la escala publicada, las bandas, la calibración por evento y los coeficientes de probabilidad. Todo número que aparezca en el documento debe venir de aquí o de una línea de código citada; nada inventado.

## Paso 2 · Escribe `salida/documento_score.md`

Documento técnico, en español, con `file:line` en cada paso. Debe cubrir, en orden, la cadena completa:

1. **Qué es el score y qué mide** (y qué no: es relativo al train, R01).
2. **Datos de entrada**: panel, reconstrucción de caja, FX, exclusiones (internas, intragrupo), facturas.
3. **Features**: las 17 de `features.py`, con fórmula, pilar, dirección económica y el tratamiento del cero (two-part, D10) y del suelo relativo de escala (D16).
4. **Sub-scores**: percentiles orientados y congelados en train; qué pasa si falta el dato (neutro 50, D17).
5. **Pesos**: la logística por evento con signo restringido (D12), la calibración y el promedio; **los pesos reales** de `score_datos.py`.
6. **Escala publicada**: `score_bruto = recorte(0,100, a + b · Σ peso·sub)`; los valores reales de `a` y `b`; por qué es lineal (D18).
7. **Suavizado**: EWMA α (D14) y por qué la explicación sigue siendo exacta.
8. **Regla de inactividad** (D15) y **bandas** riesgo/vigilar/sano (D19).
9. **Probabilidades** `prob_*` a 6 meses (R02), con sus coeficientes reales.
10. **La explicación Y, Z, K**: `explain()` paso a paso, con un ejemplo trabajado de una empresa real (cita `company_id`, mes, `delta` y las contribuciones).
11. **OOD y confianza** (D16): qué es cobertura, qué es OOD, cómo se combinan.
12. **Los eventos ancla** (`targets.py`): tensión, incumplimiento, caída, expansión; y por qué el apagado no calibra (R06).
13. **Cómo se valida**: GroupKFold por grupo × cortes, la métrica **PM** (`puntuacion.py`) y sus guardarraíles.
14. **Límites conocidos y sesgos**: tamaño (R03), intragrupo (R08), bache vs caída (R11), ruido de alertas (R12), OOD (R14).

Requisito de exactitud: si un paso del documento no coincide con el código, **manda el código**; corrige el documento.

## Paso 3 · El consejo adversarial sobre el documento

Lanza en paralelo subagentes que **ataquen el documento**, cada uno desde su rol: `riesgo-modelo` (¿es defendible y estable?), `auditor-datos` (¿el dato sostiene cada paso? ¿coincide con el código?), `abogado-diablo` (¿dónde miente o se rompe?), `prestamista` (¿sirve para decidir un crédito?), `cfo` (¿lo entendería el cliente?), `cobrador` (¿qué falta del después?).

Cada subagente produce **preguntas del estilo del reto** (falsables, con condición «si X entonces Y, salvo Z»), por ejemplo: «si una empresa lleva 3 meses con la caja rota, ¿el documento explica por qué la banda es riesgo y bajo qué condiciones se prestaría?», «¿la fórmula del sub-score trata el cero igual que el código en `xray.py:_sub`?», «¿qué pasa con una empresa sin ERP en cada paso?».

Objetivo: **≥ 40 preguntas nuevas** sobre el documento, además de las >100 de la fase 2. Distingue las que el documento ya responde (y dónde) de las que descubren un hueco.

## Paso 4 · Incorpora y realimenta

- Añade al documento una sección **«Cuestionado por»**: cada objeción con su veredicto (aceptada / rechazada) y, si se acepta, qué cambia en el documento o en el código.
- Las preguntas que **no** responde el documento y que son verificables se añaden a `salida/premisas.jsonl` (con el esquema de `premisas.py`). Después:
  ```bash
  cd research && uv run python ../.devin/workflows/autoresearch/premisas.py validate
  cd research && uv run python ../.devin/workflows/autoresearch/premisas.py run
  ```
- Si alguna objeción descubre un **error en el modelo** (no en el documento), no lo arregles aquí: anótalo como premisa fallida para la fase 3 (o, si la fase 3 ya cerró, abre una iteración nueva).

## Criterios de aceptación

- `salida/documento_score.md` existe, cubre los 14 puntos y **cada número coincide con `score_datos.py`**.
- Cada paso cita su `file:line`; hay un ejemplo trabajado de explicación Y/Z/K con una empresa real.
- El documento tiene la sección «Cuestionado por» con **≥ 40 objeciones** de ≥ 5 subagentes, con veredicto.
- Las preguntas nuevas verificables están en `premisas.jsonl` y pasan `validate` sin errores.

## Reglas

- Escribes en `.devin/workflows/autoresearch/salida/` y, si una objeción exige corregir código, en `research/src/` (en la rama activa).
- No toques `data/`, ni los CSV, ni `analysis/`. Nada de secretos.
- Escribe en español. Cada afirmación sobre el código o los datos lleva su referencia (`file:line` o `score_datos.py`).
- Termina con: ruta del documento, nº de objeciones y veredictos, nº de premisas nuevas y si el documento coincide con el código.
