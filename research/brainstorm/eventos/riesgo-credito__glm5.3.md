<!-- modelo: glm5.3 vía Helmcode · lente: riesgo-credito · 197s · uso: None -->

# Eventos como "verdad" del score — lente: analista senior de riesgo de crédito pyme

## 1. Posición

Para un banco, la verdad no es "va justa de caja" sino **"no paga lo que debe cuando lo debe"**: el estándar regulatorio es mora ≥90 días o improbable que pague, y con tesorería lo más cercano medible son las **obligaciones recurrentes omitidas** (cuota de deuda, nómina, mora de proveedores ≥90d). Los eventos actuales miden estados de liquidez y mecánica del dato: la caída de cobros está contaminada por el apagado (69 % de solape, medido por el equipo) y el apagado parece baja de Embat, no quiebra — de hecho, quien se va tenía *más* caja (0,59 frente a 0,48), así que como etiqueta de malestar invertiría el ranking. La propuesta de "incumplimiento de obligaciones recurrentes" es la dirección correcta y el mejor proxy de default disponible, pero tal como está mezcla componentes de fiabilidad muy distinta y confunde "no pagó" con "no hay dato". Propongo una arquitectura de dos cabezas: un **ancla de resultado** (impago de servicio de obligaciones, estilo 90 DPD) para calibrar gravedad, y un **ancla de transición** (entrada en tensión de caja, estilo Stage 2 de IFRS 9) para calibrar anticipación y alertas.

## 2. Veredicto sobre cada evento actual

| Evento | Veredicto | Motivo (lente prestamista) |
|---|---|---|
| Apagado | **Separar como otro producto** (churn/retención de Embat) y usarlo como **censura**, no como verdad | Es evento de pérdida solo si va con deuda viva; aquí parece offboarding de clientes sanos (36 % sin síntomas previos, más líquidos que la media). Como etiqueta de distress, envenena todo lo que toca |
| Saldo negativo | **Redefinir** (persistencia ≥2-3 meses o póliza agotada) y **degradar a síntoma/transición** | Circular con la feature de meses de caja (AUC 0,77 parcialmente circular); el 23 % ya estaba en negativo antes; el 46 % de persistencia >3 meses sugiere artefacto de reconstrucción. Una cuenta sin póliza no debería poder quedar negativa |
| Caída de cobros | **Degradar a síntoma** (versión causal) y **eliminar como evento** | Solape mecánico del 69 % con apagado; y su definición mira 6 meses de futuro, así que ni siquiera puede ser feature tal cual (la versión causal ya existe: tendencia de cobros 3m vs 12m) |
| Crecimiento | **Redefinir** como "mejora sostenida" | La definición actual celebra también al que deja de gastar (caja sube cuando la actividad se apaga) y mezcla nivel con tendencia; exige actividad mantenida y base no-techo |

## 3. Eventos recomendados

Todas las definiciones usan columnas del panel y son causales. "Mes activo" = `months_since_last_tx == 0` ∧ `n_tx` ≥ 50 % de la mediana de los 3 meses previos (condición de *feed vivo*, clave para no confundir impago con desconexión).

| Evento | Definición implementable | Tipo | Preguntas | Frecuencia | Riesgos |
|---|---|---|---|---|---|
| **E1. Impago de servicio de deuda** ⭐ ancla de gravedad | Cuota esperada e(m) = mediana de `debt_service` >0 en m-6…m-1 (o importe de `debt_schedule_config` si existe). Fallo(m) = mes activo ∧ `debt_service` < 0,5·e(m). **Mora** = 2 fallos seguidos (≈60 DPD); **default** = 3 fallos en 6 meses (≈90 DPD) o 1 fallo con cuota trimestral | Resultado (proxy de mora regulatoria) | 3, 4, 5, 6 | No medida; estimo 2-5 % de empresa-mes elegibles | Cobertura (solo empresas con deuda y pauta detectable; 87 cuadros frente a 2.239 productos), refinanciaciones que disfrazan el fallo, cuotas clasificadas fuera de `debt_repayment` |
| **E2. Quiebra de nómina** | `payroll` >0 en ≥3 de los últimos 4 meses; fallo = mes activo con `payroll` < 0,5×mediana previa; grave si ≥2 meses | Resultado (insolvencia operativa) | 3, 4, 5, 6 | Estimo 1-3 % de elegibles | 43 % sin dato; variación de plantilla; censura por apagado |
| **E3. Mora proveedores ≥90d persistente** | r(m) = `overdue_90_ap` / máx(`ap_issued` 3m, suelo 0,1 % volumen); evento: r > 0,15 durante ≥3 meses, o r subiendo 2 meses con r > 0,10 | Resultado / EWS fuerte ("improbable que pague") | 3, 4, 5 | Estimo 5-10 % | ERP-dependiente (~42-44 % faltan); deriva mecánica (mitigada con ventana 12m) |
| **E4. Entrada en tensión de caja** ⭐ ancla de anticipación | Primer mes con `cash_end` <0 o meses de caja <0,25, tras ≥3 meses con meses de caja ≥0,5 | Transición | 3, 4, 6 | ~5-8 % (el saldo negativo actual es 5 %, equipo) | Umbral arbitrario → sensibilizar; circularidad parcial con la feature de liquidez |
| E5. Póliza al límite sostenida | `lc_drawn`/`lc_limit` ≥0,95 durante ≥3 meses con cobros a la baja | Transición ("vive al límite de la tarjeta") | 3, 4 | Baja (86 % sin dato) | Sesgo de selección; solo señal de refuerzo |
| E6. Caída estructural (no bache) | Condicionada a no-apagado en 6m: mediana de cobros t+1…t+3 < 0,7×mediana(12 previos) ∧ ningún mes posterior ≥0,8×baseline | Resultado | 4, 5, 6 | Estimo 8-12 % (la tasa actual 17 % menos el solape con apagado) | Hereda censura si no se condiciona a supervivencia |
| E7. Bache | Caída que se revierte: recuperación ≥0,8×baseline en ≤2 meses | Síntoma / clase contraria (no objetivo) | 4 | Estimo 10-15 % | Frontera con E6 difusa: separar por duración, no por magnitud |
| E8. Mejora sostenida | Mediana de cobros t+1…t+3 ≥1,15×baseline ∧ caja estable/al alza ∧ actividad mantenida ∧ base por debajo del P75 | Estado positivo | 1, 2 | Estimo 10-15 % | Baja base; silencio que infla caja mecánicamente |
| E9. Sano sólido | ≥6 meses sin E1-E3 ∧ meses de caja ≥P50 del panel, con tenencia mínima de 6 meses | Estado positivo | 1 | — | Sesgo de tenencia; ajustar por meses de historia |
| E10. Mora clientes ≥90d creciente | `overdue_90_ar` / `ar_issued` 3m en aumento ≥2 meses | Resultado **para la póliza** (impago de clientes), no para el banco | 3, 5 | — | Cambia el comprador: aseguradora, no banco |

**Ancla principal:** E1 como ancla de gravedad (es lo más parecido a "mora con el banco" que el dataset permite) y E4 como ancla de timing/alertas. Si al medirla la prevalencia de E1 resulta demasiado baja, combinar **E1 ∪ E2 ∪ E3** como "deterioro del servicio de obligaciones" — compuesto distinto del que falló antes, porque aquel incluía la caída de cobros, que dominaba por prevalencia. E3 es además el ancla natural para la variante aseguradora.

## 4. Críticas a la propuesta actual

1. **"Incumplimiento" como OR de cuatro mecanismos mezcla fiabilidades**: cuota de préstamo (alta), nómina (alta), IVA (baja), proveedores (media). El ruido del IVA diluye la señal limpia de las cuotas. Componentes separados, calibrados por separado, combinados con pesos.
2. **El confunder de observabilidad no está resuelto**: la omisión solo es interpretable con feed vivo ese mes. Sin esa condición, "no pagó IVA" y "se desconectó" son el mismo bit. La evidencia reabierta (AUC 0,67 del IVA omitido *frente a apagado*) huele exactamente a eso: probablemente mide desconexión, no impago.
3. **El IVA además sufre ruido propio**: `tax` mezcla impuestos, hay devoluciones y regímenes distintos por país. Úsalo como confirmación del estado, no como disparador.
4. **"Caída estructural" no está definida**: faltan horizonte y criterio de persistencia, y sin condicionar a supervivencia hereda el solape con apagado que ya envenena el evento actual.
5. **"Sano sostenido" a 12 meses es casi vacío**: 24 meses de historia, el 31 % de empresas con <12 meses y primeros meses parciales → sesgo de tenencia. Reducir a 6 meses o condicionar a tenencia mínima.
6. **Falta un evento parecido a la pérdida del prestamista**. Con los anclas actuales de liquidez tiene sentido que "carga de deuda" (lo más parecido a un DSCR) salga sin orden: para un analista eso indica que los anclas miden liquidez, no crédito.
7. **"Caída de cobros como feature" tiene un problema de causalidad**: la definición actual mira 6 meses de futuro. En producción debe ser la versión causal (3m vs 12m, ya existente).
8. Lo de **apagado como posible baja de Embat** es correcto; hay que aceptar la consecuencia: deja de ser etiqueta de malestar y pasa a ser censura + producto de churn.
9. Ojo con recrear un compuesto `adverse` grande: ya falló una vez por dominancia del declive; si se hace, solo con E1-E3 y revisando prevalencias.

## 5. Cómo validaría los eventos sin etiquetas

- **Estructura de hazards y lead time**: las transiciones (E4, E5) deben preceder a los resultados (E1-E3). Medir P(E1 | transición reciente) frente a tasa base y la distribución de meses de antelación. Si las transiciones no elevan el riesgo posterior, no son EWS.
- **Confirmación multi-señal**: cada resultado debe ir precedido de deterioro en señales que no lo definen (E1: subida de `lc_drawn`, caída de meses de caja; E3: caída de cobros). La tasa de confirmación es un proxy de validez de constructo.
- **Descarte de artefactos de observabilidad**: recalcular tasas excluyendo meses con feed degradado (n_tx bajo, pico de `-`, pico de internas) y comprobar si los eventos agrupan por `group_id`, ERP o banco: si agrupan por infraestructura, es dato, no empresa.
- **Estabilidad por tenencia y cohortes**: tasas por `month_idx` y por `created_at`; picos en los bordes de la historia = truncamiento.
- **Sensibilidad de umbrales**: re-estimar cada evento con umbrales ±20 %; las prevalencias y el orden de AUC deben ser estables.
- **Coherencia de ranking**: la tasa de cada resultado debe caer monótona por deciles del score; y la logística lineal debe igualar al LightGBM (ya medido por el equipo): un evento que solo se predice con no linealidades es sospechoso.
- **Split por grupos**: fijar definiciones y umbrales en un subconjunto de `group_id` y evaluar en el resto (simula el test oculto).
- **Auditoría manual**: 20-30 casos por evento inspeccionando la serie; cada evento debe contarse en la analogía del consumidor ("dejó de pagar la cuota", "se le paró la nómina").

## 6. Preguntas para la organización

1. ¿Qué es el apagado en el generador: baja de Embat, cierre o fin de muestra? ¿Hay alguna marca de baja?
2. ¿El generador siembra estados latentes (deterioro, crecimiento) que determinan las dinámicas? Si existen, son la verdad real y deberían documentarse.
3. ¿`debt_repayment` cubre principal + intereses de todas las modalidades? ¿Cómo se codifica una refinanciación o un traspaso entre entidades?
4. ¿El IVA es trimestral en todos los países y regímenes? ¿`tax` mezcla IVA, Seguridad Social y retenciones?
5. ¿Es posible caja negativa sin póliza en el generador (sobregido tácito) o es artefacto de reconstrucción?
6. ¿Hay fechas de fin de contrato de los productos de deuda para acotar la última cuota esperada? (`debt_schedule_config` tiene 87 filas frente a 2.239 productos.)
7. ¿El test oculto comparte generador, horizonte y monedas? ¿Habrá historias más cortas?
8. ¿Para quién se califica el score en la evaluación final (banco, churn de Embat, CFO)? Cambia la verdad y los pesos.

## 7. Verificaciones hechas

**No tengo acceso a los datos ni a herramientas en esta conversación: no he ejecutado ninguna consulta.** Las cifras que cito como medidas (prevalencias 3/5/17/16 %, solape 69 %, AUC 0,77, caja 0,59 vs 0,48, 36 % sin síntomas, 46 % de persistencia negativa, etc.) proceden del brief del equipo. Todas las frecuencias de los eventos que propongo (E1-E10) son **estimaciones a priori** pendientes de medir con `research/src/targets.py` y el panel. Las tres comprobaciones que haría primero: (a) prevalencia y cobertura de E1-E3 con las reglas de feed vivo, (b) lead time de E4→E1, y (c) agrupación del "IVA omitido" por grupo/ERP para confirmar o descartar la contaminación por desconexión.