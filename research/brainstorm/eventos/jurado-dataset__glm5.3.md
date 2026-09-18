<!-- modelo: glm5.3 vía Helmcode · lente: jurado-dataset · 214s · uso: None -->

# Posición

Como el dataset es sintético y el leaderboard se corrige automáticamente contra 60–80 empresas ocultas, el target casi seguro vive **dentro del generador**: un arquetipo por empresa (sano, mejora, deterioro temprano, caída, bache/volátil, default) o una salud latente 0–100 por empresa-mes que condiciona cobros, pagos y caja. Los ejemplos del enunciado (45→65, 82→68) se leen como arquetipos scriptados, y la casi simetría de tasas (caída 17 % / crecimiento 16 %) huele a pesos de clase diseñados. Por tanto, los eventos no deben elegirse por conveniencia estadística sino para **reconstruir la máquina de estados del generador**: regímenes con puntos de cambio, muertes con ramp-down y transiciones persistentes. El evento actual "caída de cobros" es tardío y está casado con el apagado (69 % de solape): probablemente captura las muertes scriptadas, no el arquetipo Velasco que el reto premia. La palanca de mayor valor es convertir los eventos en **detectores de cambio de régimen con antelación medida**, usando las huellas del generador como pseudo-etiquetas.

## 1b. Target probable del leaderboard y huellas del generador

**Target probable, por orden de verosimilitud:** (1) correlación/ranking del score contra la salud latente; (2) AUC de clasificación de arquetipos, sobre todo deterioro vs mejora; (3) lead time contra el mes de cambio de régimen que el generador conoce (es la única forma objetiva de corregir "¿cuándo se vio venir?"); (4) bache-vs-caída como métrica propia. El script de scoring del viernes lo revelará; hay que diseñar para estos cuatro.

**Huellas y cómo buscarlas** (todo con `panel.parquet` + `targets.py`, scripts en `/tmp`):

| Huella | Qué buscar | Cómo |
|---|---|---|
| Arquetipos discretos | Clusters nítidos y equilibrados en trayectorias | Por empresa: pendiente de log(cobros) 12 m, pendiente de caja, volatilidad, morosidad → GMM k=2..8; BIC bajo con pesos equilibrados y silhouette alto = clases diseñadas |
| Rejilla de severidad | Ratios de caída en valores redondos | Detectar breaks (CUSUM) en `inflow` mensual; histograma de (mín post-break / mediana pre-break): picos en 0,5/0,6/0,7 = factores scriptados |
| Muerte scriptada | Pocas plantillas de ramp-down | Apilar cobros normalizados, meses −6..0, de los 121 apagados; si colapsan en 2–3 curvas, la muerte está dirigida |
| Turnarounds dirigidos | Flips de pendiente concentrados | Pendiente meses 1–12 vs 13–24 por empresa; flips raros y sincronizados en meses concretos = cambio de régimen scriptado (Northbrook/Velasco) |
| Exclusividad de clases | Caída y crecimiento casi nunca coexisten secuencialmente | Tabla cruzada de eventos en ventanas desplazadas; la exclusividad mutua delata clases del generador |
| Obligaciones como reloj | Nómina/IVA exactos | Importes y fechas repetidos año a año; si algún arquetipo los salta, es señal deliberada y valida "incumplimiento" |
| Configs de dificultad | `created_at` escalonado (31 % <12 m), 36 % sin ERP, mezcla de divisas | El test oculto vendrá de la misma distribución de configs: la robustez de los eventos a censura y OOD pesa tanto como el AUC |

Los artefactos ya documentados (`payment_date==due_date` en el 96 % de las overdue, año 7025, FX=1 en MZN / 0 en VND) prueban generación por reglas; si hay reglas, hay etiquetas.

## 2. Veredicto sobre cada evento actual

- **Apagado (3 %): separar como otro producto.** Es churn de datos (posible baja de Embat), no salud: el 36 % no mostró síntomas previos. Mantenerlo como etiqueta de censura y cobertura, y como huella del arquetipo "default".
- **Saldo negativo (5 %): redefinir** a primer paso (first passage) a negativo o runway <0,25 m tras ≥3 meses sanos, excluyendo crónicos (el 46 % persiste ≥3 m: probable artefacto de reconstrucción). Es el ancla de criticidad de la prueba de los 100.000 €. Ojo: el AUC 0,77 es parcialmente circular (la feature gemela predice su evento).
- **Caída de cobros (17 %): dividir.** La versión "mediana 6 m < 50 %" es tardía y está casada con el apagado. La versión profunda se degrada a resultado confirmatorio; se crea un evento de **deterioro temprano persistente** (pendiente, nivel aún alto) que sí captura a Velasco.
- **Crecimiento (16 %): redefinir.** ">130 % de la media anual" confunde ramp-up de altas recientes y picos estacionales con mejora genuina; usar pendiente sostenida excluyendo meses jóvenes.
- **Incumplimiento (propuesta): mantener como candidato, no como ancla**, hasta medir su frecuencia; puede ser otra etiqueta de muerte scriptada (el IVA omitido dio AUC 0,67 frente a apagado).
- **Entrada en tensión (propuesta): mantener, unificada** con el saldo-negativo de primer paso en una sola etiqueta.
- **Caída estructural vs bache (propuesta): mantener y operativizar como par de etiquetas**; hoy es la pregunta con peor evidencia (AUC 0,50).
- **Recuperación (propuesta): mantener con guardarraíles** (persistencia ≥3 m), o es regresión a la media, fallo ya documentado en este repo.
- **Sano sostenido (propuesta): mantener a 6 m, no 12** (el 31 % del panel tiene <12 m de historia).

## 3. Eventos recomendados

| Evento | Definición (columnas del panel) | Tipo | Preguntas | Frecuencia | Riesgos |
|---|---|---|---|---|---|
| **Deterioro temprano persistente** ⭐ ancla principal | En (t, t+6]: ≥3 meses con `inflow`/`oper_in` < 0,80 × mediana12, sin caída profunda (mediana 6 m ≥ 0,50 × mediana12), sin apagado | Transición / cambio de régimen | 3, 4, 6 | 12–18 % (est.) | Estacionalidad (mediana 12 m la absorbe), baches (exigir persistencia), censurar ramp-downs de apagados |
| **Entrada en tensión de caja** | Primer mes en (t, t+6] con `cash_end`<0 o meses de caja <0,25, tras ≥3 meses ≥0,5; excluir crónicos | Transición | 3, 4, 6 | 6–9 % (est. sobre el 5 % medido) | Artefactos de reconstrucción; circularidad parcial con la feature de meses de caja |
| **Bache** | Algún mes en (t, t+6] < 0,70 × mediana12 que recupera ≥0,90 × mediana12 en ≤2 meses, sin eventos 1–2 | Síntoma (clase "ruido" del par bache/caída) | 4, 6 | 8–12 % (est.) | Solape con deterioro temprano; definir antes que la caída |
| **Caída estructural** | Mediana 6 m < 0,50 × mediana12 o ≥3 meses seguidos <0,80 × mediana12 | Resultado tardío | 2 (negativa), 4 | 10–15 % (est.) | Casada con apagado: reportar tasas ex-churn |
| **Mejora sostenida** | Media de cobros de los 6 siguientes ≥ +15 % sobre mediana12 y `cash_end` al alza, excluyendo `month_idx`<5 y apagados | Estado positivo | 1, 2 | 10–15 % (est. sobre el 16 %) | Estacionalidad y reversión a la media |
| **Sano sostenido** | 6 m sin eventos adversos, meses de caja ≥2, morosidad AP/AR bajo | Estado positivo | 1 | 35–55 % (est.) | Censura por historia corta |
| **Obligación omitida** | `payroll` <0,3 × mediana tras ≥3 meses pagando; o `tax` <0,2 × mediana fiscal en mes fiscal; o `debt_service` caído con schedule | Síntoma de estrés (firma scriptada) | 3, 5, 6 | 2–6 % (est., sin medir) | Poca base; el generador puede no omitir nada; verificar antes de ponderar |
| **Apagado** | Sin cambios (`months_since_final_tx`) | Producto / cobertura | — | 3 % (medido) | No es salud; solo censura y churn |

**Ancla principal: deterioro temprano persistente**, con entrada en tensión como ancla de criticidad (caso préstamo) y mejora sostenida como ancla positiva. Calibrar con una logística por evento (como ahora, no compuesta: ya visteis que el declive domina) y publicar la curva de antelación a 3 y 6 meses.

## 4. Críticas a la propuesta actual

1. **"Incumplimiento" como evento principal sin medir frecuencia** es arriesgado: si queda en 1–3 %, no hay base para calibrar pesos; y su evidencia actual lo liga al apagado, con lo que repetiría el problema de solape del 69 %.
2. **Duplicidad** entrada-en-tensión / saldo-negativo: dos etiquetas del 5–8 % fragmentan la muestra; unificar.
3. **Bache vs caída está nombrado pero no operativizado** como par de etiquetas; es la pregunta 4 y hoy rinde a AUC 0,50.
4. **Degradar "caída de cobros" a mera feature** tira el único evento adverso frecuente (17 %); dividirlo en temprano (evento) y profundo (síntoma/resultado) conserva base estadística y añade anticipación.
5. **Crecimiento sin corregir ramp-up** premia empresas jóvenes; sesgo sistemático que el test oculto (con altas recientes, según las configs) castigará.
6. **Horizonte único de 6 m**: las preguntas piden anticipación; medir a 3 y 6 m.
7. **Nada del diseño mira el target latente**: sin validación por clusters y huellas, se afina contra proxies ruidosos.

## 5. Cómo validaría los eventos sin etiquetas

1. **Matriz convergente/discriminante**: AUC de cada familia de features (liquidez, disciplina de pagos, clientes, deuda) contra cada evento; un evento sano lo predice su pilar, no todos.
2. **Curvas de lead time**: AUC del score contra el evento a 0..6 meses de antelación; exigir señal ≥3 meses antes para el ancla; lo que solo aparece en el mes 0–1 es ruido.
3. **Pseudo-etiquetas por clusters**: GMM de trayectorias por empresa; información mutua evento↔cluster alta; los artefactos se reparten de forma uniforme entre clusters.
4. **Estabilidad temporal**: features de la 1ª mitad del panel prediciendo eventos de la 2ª con AUC similar (±0,05).
5. **Robustez a perturbación**: recalcular con FX ±10 %, sin categoría `-`, sin internas/intragrupo; exigir solape >90 % en la etiqueta.
6. **Coherencia de grupo**: solape de eventos intra-grupo (shocks compartidos) vs inter-grupo.
7. **Lectura manual/LLM de 20 series por evento**: la narrativa mensual debe cuadrar; barato y caza artefactos de reconstrucción.
8. **Viernes, el script de scoring como etiqueta débil**: pocas sondas, registrar cada envío, no sobreajustar.

## 6. Preguntas para la organización

1. ¿El leaderboard puntúa el score final, la serie mensual o decisiones/alertas, y contra qué (correlación, AUC por arquetipo)?
2. ¿El generador tiene arquetipos o salud latente por empresa-mes? ¿Cuántas clases, con qué pesos, y conoce el mes exacto de cada cambio de régimen?
3. ¿Las 60–80 ocultas comparten distribución de arquetipos y de configs (historia corta, sin ERP, divisa) con las visibles?
4. ¿Un "apagado" es cierre, baja de Embat o fin de muestreo? ¿Se scriptó deterioro previo a la desconexión?
5. ¿El generador omite obligaciones (nómina/IVA/cuota) en arquetipos de estrés, o las omisiones que veamos son ruido?
6. ¿Cómo se corrige "bache vs caída" y "cuándo se vio venir": con un umbral fijo de "cambio evidente" o con el punto de cambio interno del generador?

## 7. Verificaciones hechas

**No tengo acceso a herramientas ni a los parquet en esta sesión**: no he podido ejecutar clusters, detección de breaks ni ninguna de las comprobaciones propuestas; quedan especificadas como protocolo. Las cifras que cito (3 %, 5 %, 17 %, 16 %, 69 % de solape, AUC 0,77, 46 % crónicos, 22 % con >3 m de caja, 36 % sin síntomas previos, 31 % con <12 m, 36 % sin ERP, 121 apagados, 96 % `payment_date==due_date`) proceden de los documentos del repo (`brief_eventos.md`, `features.md`) y las doy por **documentadas, no verificadas hoy**. Todas las frecuencias de la tabla de eventos recomendados son **estimaciones** que deben medirse con `targets.py` antes de calibrar nada.