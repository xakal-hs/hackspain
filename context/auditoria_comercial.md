# Auditoría comercial de X-Ray

**Decisión para el jurado · horizonte 24 horas · 19 de septiembre de 2026**

## Veredicto ejecutivo

X-Ray se vende como una **capa de decisión para la base instalada de Embat**. Embat es el comprador
e integrador; el CFO es el usuario. La cuña no es predecir caja —Embat ya lo hace—, sino ordenar
una cartera con un score comparable, explicar qué cambió y transformar la señal en la siguiente
acción con un colchón dinámico.

La frase central es:

> **Embat ya ve el dinero. X-Ray le dice a qué CFO atender primero, por qué y qué decisión puede
> tomar antes de que el cambio sea evidente.**

La historia comercial es viable para una demo, pero todavía no está validada como negocio. El
escenario central corregido es **4,2 M€/año** sobre el dataset (3,0–5,4 M€), con **344 M€ de
excedente en 370 empresas**. Adopción, pricing y disposición a pagar siguen siendo hipótesis.

## Lo que se vende

### Comprador, usuario y trabajo a resolver

| Papel | Quién | Trabajo |
|---|---|---|
| Comprador e integrador | Embat | Aumentar valor y expansión sobre cuentas conectadas |
| Usuario | CFO / tesorería | Saber qué cambió, cuánto importa y qué hacer ahora |
| Ejecutor opcional | Banco, bróker o BaaS | Ejecutar cuando Embed One no cubre el riel. Intermediar no es lo ideal; la suscripción sí |

### La experiencia mínima

1. **Detectar antes:** la cartera se ordena por cambio esperado, criticidad y confianza.
2. **Explicar:** el CFO ve la señal, el momento y los puntos que movieron la nota.
3. **Calcular:** la caja se separa entre colchón necesario y exceso o déficit accionable.
4. **Recomendar:** vigilar, acelerar cobros, conservar caja, colocar excedente o preparar un
   **mix de financiación**. Varias opciones en la mesa, no un SKU único.
5. **Cuantificar:** se muestra el **coste de no hacer nada** (dinero parado, divisa sin convertir)
   y, cuando exista, el resultado posterior.

### Diferencia frente a Embat hoy

Embat ya anuncia previsión adaptativa, detección anticipada de riesgos, desviaciones, déficit y
excedente, riesgo de contraparte y pagos internacionales. X-Ray no debe duplicar esos módulos.

La aportación incremental es **comparabilidad + explicación aditiva + priorización de cartera +
siguiente acción**. El producto deja de ser una colección de gráficos por empresa y se convierte
en una cola de decisiones transversal.

Fuentes consultadas el 19-09-2026:

- [Gestión de tesorería de Embat](https://www.embat.io/es/gestion-tesoreria)
- [Módulos y pricing de Embat](https://www.embat.io/pricing)
- [Pagos internacionales de Embat](https://www.embat.io/es/pagos-corporativos/pagos-internacionales)

## Registro de afirmaciones

| Afirmación | Clase | Evidencia | Uso permitido |
|---|---|---|---|
| 344 M€ de excedente, 370 empresas | Medida | `analysis/monetizacion.html` | “Hemos medido…” |
| 4,2 M€/año; rango 3,0–5,4 | Escenario | Bases medidas + adopción/precio supuestos | “Si asumimos…” |
| AUC 0,725 deterioro y 0,730 mejora | Validación v7 | `research/reports/metrics_v7.json` | Con split fuera de grupo y AR(1) |
| AUC 0,657 frente a tensión a 6 meses | Validación v7 | `metrics_v7.json` | Como discriminación moderada, no probabilidad causal |
| 48 % avisado antes; mediana 3 meses | Validación anterior | `anticipation_v5.json` | Identificar expresamente como v5/v6 |
| 12,1 M€/año | Descartada | Brief antiguo sin FX limpio | Solo para explicar la corrección |
| El CFO pagará 350 €/mes | Hipótesis | Sin entrevistas ni contratos | No afirmarlo como hecho |
| Más de 500 equipos usan Embat | Externa | Web pública de Embat | Contexto; no escalar ingresos |
| El exceso y el FX son costes ocultos; el agente no se usa | Testimonio | PM de Embat, 19-09-2026 (`voz_embat.md`) | Condiciona la UI, no el P&L |
| Mover dinero no exige licencia propia; partner bancario basta | Testimonio | Cofundador de Capchase, 19-09-2026 (`voz_capchase.md`) | Condiciona el riel, no el P&L |
| Deuda = sector × tenor; quien tiene caja también pide | Testimonio | Mismo (`voz_capchase.md`) | Condiciona productos y score |

## Puntos ciegos priorizados

| Prioridad | Punto ciego | Evidencia actual | Riesgo ante el jurado | Mitigación en 24 h |
|---|---|---|---|---|
| **P0** | El relato antiguo usa 12,1 M€ | `context/monetizacion.md` anterior frente al cálculo corregido | Una pregunta de unidades invalida el bloque de valor | Usar solo 4,2 M€ y separar medida de supuesto |
| **P0** | La propuesta se solapa con productos actuales de Embat | Web oficial: forecasting, alertas, riesgo y pagos | “Esto ya lo hacemos” | Liderar con priorización comparable y siguiente acción |
| **P0** | El Nuxt parece producto real, pero usa fixtures | `frontend/app/data/demo.ts`; solo `/api/companies` tiene adaptador | Pérdida de confianza si se descubre en directo | Etiquetarlo como visión; demostrar el motor en la SPA FastAPI |
| **P0** | Unidad, labels y formato del leaderboard siguen abiertos | `AGENTS.md`, `research/REFLEXIONES.md` | No poder enviar o medir la entrega | Preguntar a organización y preparar un adaptador aislado |
| **P1** | Los eventos son proxies construidos por el equipo | No hay etiquetas oficiales; `targets.py` | Confundir autoconsistencia con verdad externa | Decir “validado contra eventos observables”, no “predice insolvencia” |
| **P1** | Poder predictivo moderado y alertas débiles | AUC 0,58–0,66 por evento; recall mejora 5 % | Sobreprometer precisión | Comparar con AR(1), mostrar intervalos y abstención |
| **P1** | Bache frente a caída no está resuelto | AUC 0,53 | Incumplir una de las seis preguntas | Presentarlo como limitación y no simular certeza |
| **P1** | El 23 % de alertas parpadea | Evaluación de anticipación v5/v6 | Fatiga de alertas | Roadmap de histéresis; no cambiarla horas antes del pitch |
| **P1** | Sesgo de tamaño y liquidez de grupo | `REFLEXIONES.md` R03/R08 | Penalizar empresas grandes o filiales de cash pooling | Mostrar cobertura/confianza y llevarlo al agregado de grupo |
| **P1** | Score relativo al train y casos OOD | `REFLEXIONES.md` R01/R14 | Interpretar 70 como riesgo absoluto | Mostrar probabilidad de evento y confianza junto al score |
| **P1** | Dos cajas, eventos/features duplicados y dos apps | `research/ESTADO.md` | Reproducibilidad y mantenimiento | Congelar hoy; consolidar la semana siguiente |
| **P2** | Pricing y adopción no validados | 25/35/45 %, 350 €, 100/15 pb son supuestos | Caso de negocio presentado como venta segura | Preparar discovery y piloto, no añadir decimales |
| **P2** | Partner bancario no nombrado | Licencia propia no hace falta; falta el partner concreto | Prometer riel sin quién lo ejecuta | X-Ray recomienda; un banco partner con licencia existente ejecuta |

## Qué demo usar

### Demo oficial del jurado

Usar la SPA servida por FastAPI en `research/app/static/index.html`, porque recorre datos del motor:
cartera → empresa → trayectoria → explicación → escenario → alerta. Es la prueba funcional.

El frontend Nuxt se puede enseñar solo como **visión de experiencia por roles con datos
ficticios**, nunca como integración end-to-end. No se alternan dos aplicaciones durante los cinco
minutos: la SPA FastAPI es el recorrido principal y una única captura de Nuxt puede ilustrar el
futuro del producto si sobra tiempo.

### Recorrido de cinco minutos

| Tiempo | Mensaje | Pantalla / prueba |
|---|---|---|
| 0:00–0:35 | Un score de hoy no distingue 45→65 de 82→68 | Cartera ordenada por cambio, no solo nivel |
| 0:35–1:15 | Embat ya tiene el rastro; X-Ray prioriza dónde actuar | Empresa sana que empieza a deteriorarse |
| 1:15–2:15 | Explicar antes de recomendar | Drivers, puntos y trayectoria con intervalo |
| 2:15–3:05 | Del diagnóstico a la acción | Escenario: cambio de cobros/pagos/caja y nueva decisión |
| 3:05–3:45 | Evidencia honesta | v7 frente a AR(1), validación por `group_id` |
| 3:45–4:25 | Valor | 344 M€ medidos; 4,2 M€ solo bajo supuestos explícitos |
| 4:25–5:00 | Cierre | Embat compra la capa; el CFO recibe la siguiente decisión |

## Objeciones y respuestas

### “Embat ya hace previsiones y alertas”

Correcto. X-Ray no sustituye esa previsión: usa el rastro para comparar toda la cartera, explicar
qué cambió y priorizar una acción. El valor incremental se mide en decisiones atendidas y resultado,
no en otra gráfica de cash flow.

### “No tenéis etiquetas reales”

No afirmamos predecir quiebra. Calibramos y validamos fuera de grupo contra eventos observables de
tensión, incumplimiento operativo, caída de cobros y expansión. La validación externa con decisiones
reales es el siguiente paso.

### “¿Los 4,2 M€ son ingresos reales?”

No. Son un escenario sobre bases medidas del dataset. El excedente y la exposición están medidos;
la adopción, el precio y los márgenes están asumidos. Sirve para dimensionar, no para hacer forecast
de ventas.

### “¿Por qué no vender primero a bancos?”

El crédito es una cola menor en este dataset y alarga el ciclo comercial. Embat ya tiene la relación,
los conectores y el dato. El banco puede ser canal o ejecutor cuando una recomendación exige capital.

### “¿La demo está conectada?”

La SPA FastAPI sí usa el motor de investigación. El frontend Nuxt es un prototipo con fixtures y se
presenta como tal. La integración de una empresa completa es el objetivo de la próxima semana.

### “El dinero parado no es un problema”

Justo: el CFO no lo siente. Por eso la ficha enseña el coste oculto antes del SKU. La divisa
igual —la operación asusta y el agente no se usa—. Fuente: [voz de producto](voz_embat.md).

### “¿Hace falta que Embat sea banco para mover el dinero?”

No. Se apalanca la licencia de un banco partner. La suscripción sigue siendo el producto; el riel
no espera a que Embat tenga ficha bancaria. Fuente: [voz de Capchase](voz_capchase.md).

### “¿Distingue un bache de una caída?”

Todavía no con suficiente discriminación: AUC 0,53. Lo mostramos como un punto ciego y evitamos una
decisión automática cuando la señal no es fiable.

## Roadmap

### Hoy: credibilidad y foco

- Una sola cifra comercial, un solo comprador y un solo recorrido de demo.
- SPA FastAPI como evidencia; Nuxt etiquetado como visión con fixtures.
- Métricas v7 con baseline y limitaciones en la misma slide.
- Confirmar con la organización unidad, labels, formato y envío del leaderboard.
- Ensayar el pitch y las seis objeciones anteriores.

### Próxima semana: una vertical real

- Conectar una empresa de extremo a extremo en Nuxt: cartera, ficha, explicación, colchón y acción.
- Convertir el adaptador parcial en un contrato tipado y añadir pruebas de endpoints y estados vacíos.
- Elegir una reconstrucción de caja, una definición de eventos y una ruta oficial de features.
- Medir histéresis de alertas, tamaño, liquidez de grupo y calibración absoluta.
- Instrumentar acción recomendada → aceptación → resultado.

### Post-hackathon: evidencia de negocio

- Entrevistar CFOs y equipo comercial/producto de Embat; validar problema, precio y workflow.
- Pilotar con una cohorte y predefinir activación, acción tomada, caja liberada y eventos evitados.
- Definir partners y límites regulatorios para depósito, FX y financiación.
- Separar scores y umbrales por producto cuando exista evidencia de decisión.
- Revalidar con datos reales, grupos completos y outcomes posteriores.

## Criterio de éxito

El jurado debe poder repetir tres frases sin mirar una slide:

1. **Embat compra; el CFO usa.**
2. **X-Ray prioriza y explica la siguiente decisión, no duplica el forecast.**
3. **344 M€ están medidos; 4,2 M€ es un escenario explícito; 12,1 M€ fue descartado.**

Y, si preguntan por producto: el módulo es **suscripción**; el upsell es una **mesa de opciones**;
la deuda, una **rejilla sector × tenor**. El riel lo ejecuta un partner con licencia; no hace falta
que Embat sea banco. El dinero parado y la divisa se enseñan como coste oculto.
