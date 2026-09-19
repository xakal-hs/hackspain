# Radar verificado · números reales leídos de los repos (no del radar)

> Añadido 19/09 tras clonar los repos de los rivales. **Esto no es lo que dice el radar: son sus
> números, leídos de sus ficheros.** Sirve para R1 (¿Elkano separa mejor?) y para el encuadre (R8).
> Marca: **[repo]** = leído en su repo · **[ORG]** = ellos dicen haberlo confirmado con la organización.

## Elkano (`amarkosmarkos/Elkano_Embat`)

**Su evento** (`analytics/labels.py`): D1 factura recibida vencida **90 días** sin pagar ≥1 % de
salidas; D2 falta nómina/SS/tax que existía; D3 `checking < 0` **≥5 días** del mes; D4
`interest+fee > 3×` mediana y >2 % de salidas. `evento = D1∨D2∨D3∨D4`; `cura = ≥2 meses en evento y
≥3 sin él`. Tasa base esperada 5-20 %; con `<6` meses de historia: **19,1 %**.

**Sus resultados** (`docs/score-explicado.md:139-141`, `analytics/README.md:104-106`). Gini OOS
(fuera de muestra por grupo):

| versión | Gini h1 | Gini h3 | Gini **h6** | AUC h6 (= (G+1)/2) |
|---|---|---|---|---|
| v1 scorecard | 0,34 | 0,26 | 0,25 | 0,625 |
| v2 calibrado por Gini | 0,43 | 0,36 | 0,35 | 0,675 |
| **v3 GBM contra el evento** | **0,54** | **0,44** | **0,38** | **0,69** |

**Lo que ellos mismos admiten** (`docs/score-explicado.md:143-149`):
- Su **mínimo declarado es Gini 0,40 a 6 meses; están en 0,38** — **por debajo de su propio listón**.
- *«El score ordena muy bien quién está mal hoy y regular quién va a empezar a estar mal. Cuando se
  mira solo a empresas que hoy no tienen ningún evento, el Gini baja a **0,20**»* → **AUC 0,60 de
  anticipación**.
- *«El techo no está en el score, está en la definición del evento»* (D1 y D3 son estados que duran
  meses; el **46 %** de los pares empresa-mes tiene evento en los 6 meses siguientes).

## burn-rate (`danielkwapien/hackspain-2026`)

**Sus resultados** (`docs/lauren/ENGINE.md:112-118`), GroupKFold por grupo, 15 señales / 11 eventos
a 1/3/6 meses:
- **Coincidentes, no anticipadores:** `runway` AUC **0,83 en el mes del evento, 0,58 a 6 meses**;
  caja 0,70 → 0,48.
- **Con perfil de adelanto:** `inflow_cv` 0,55, `feeint_share` 0,53, `pay_ovd` 0,53, `recv_dayslate`
  0,57.
- **El composite equiponderado NO predice: AUC out-of-fold 0,44-0,53** (`LABEL-VIABILITY.md:106`).
- **Anticipación:** mediana **3 meses**, pero solo en **53 de 950 empresas** con evento duro (el 77 %
  lo tiene en sus primeros 6 meses); falsa alarma 0,17 vs base 0,19 *«no es mérito»*.
- **LABEL-VIABILITY:** *«AUC fuera de fold 0,44-0,53 no es un modelo malo, es la ausencia de un
  target.»* No hay factor latente; **no entrenar contra etiqueta sintética**.

## El hallazgo que cambia el marco — **[ORG]** y confirmado en **nuestro** brief

`docs/lauren/UNKNOWNS.md:40-52`:
> **No hay validación numérica contra etiqueta [ORG].** No se compara nuestro score contra un score
> de referencia. **Lo que se juzga son las conclusiones que extrae el sistema**, vistas en la
> aplicación. El leaderboard aparece una sola vez en §2.6 y **cero veces en la rúbrica**.

**Verificado en `context/challenge.md` (nuestro):**
- La sección **«Evaluación»** son **tres bloques que pesan igual** (acierta / llega a tiempo / vale
  algo) con **preguntas cualitativas** — «¿funciona en empresas nunca vistas?», «¿detecta el cambio
  antes de que sea evidente?», «¿se sabe quién paga y por qué?». **Ninguna es un AUC.**
- El **test oculto + leaderboard** es **obligatorio** (§Requisitos), pero la **rúbrica no lo puntúa**.

**Consecuencia:** el **PM/AUC es un instrumento interno del bucle, no la nota del jurado.** La cadena
que se juzga es **score → conclusión → pantalla**. Un score mediocre arruina las conclusiones, pero
un AUC alto sin conclusiones no gana nada.

## Qué implica para R1 y para `MEDICION.md`

1. **Elkano no nos gana en lo que importa.** Su 0,69 a 6 m es **estado** («quién está mal hoy»); su
   propia **anticipación = 0,60** (Gini 0,20). Nuestra anticipación desde sana (R6) = 0,55-0,61.
   **Estamos en el mismo sitio en el frente que cuenta.**
2. **Él llegó a nuestra conclusión:** el techo es **la definición del evento**, no el modelo. Es
   exactamente lo que el consejo dijo (Q1-Q3).
3. **El marco de medición cambia:** el número titular no lo puntúa el jurado. Hay que medir para
   **decidir internamente** (con honestidad) y para **sostener las conclusiones en la demo**, no para
   maximizar un promedio.
