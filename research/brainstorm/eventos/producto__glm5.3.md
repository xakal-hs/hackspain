<!-- modelo: glm5.3 vía Helmcode · lente: producto · 206s · uso: None -->

# Panel de eventos: lente de producto de Embat

## 1. Posición

En este panel no hay una sola verdad: hay una familia corta de eventos, y la pregunta correcta no es "¿qué evento es la verdad?" sino "¿qué decisión mensual de qué comprador ancla cada evento?". Los eventos que propongo no son etiquetas arbitrarias: son la **escalera de criticidad de `scoring.md` convertida en hechos medibles** (caja que se evapora = crítica; deja de cobrar de forma persistente = alta; DSO/DPO = media, y por eso es feature y no evento; bache = no evento; hueco de observabilidad = no es salud). Sobre el producto: **un solo motor y un solo número público** (score de salud-trayectoria, pesos liquidez-primero), con **lecturas por comprador** (caja para el CFO, crédito para el banco, circulante para la aseguradora, potencial para el upsell) y **un modelo aparte de riesgo de baja para Embat**. El apagado no es salud financiera —sus empresas se van con *más* caja que las activas— pero es el label de negocio más limpio que tenemos: alimenta retención y la capa de abstención, nunca los pesos del score.

**Mapa comprador → decisión → eventos** (el núcleo de esta lente):

| Comprador | Decisión mensual concreta | Eventos que necesita | Lectura del score |
|---|---|---|---|
| Banco / financiador | ¿Renuevo, recorto o subo precio la línea? ¿Activo covenant? | Incumplimiento de cuota, entrada en negativo, quema de caja, deuda nueva con caja cayendo | Crédito |
| Aseguradora de crédito | ¿Límite y prima por deudor? ¿Renuevo la póliza? | Caída persistente de cobros, vencido AR antiguo, pérdida de clientes | Circulante |
| CFO de la pyme (usuario) | ¿Acelero cobros, dibujo la póliza, a quién pago esta semana? | Tensión de caja (runway), incumplimiento inminente, bache vs caída, recuperación | Panel de acción semanal |
| Embat (CS y comercial) | ¿A qué cuenta llamo? ¿A quién ofrezco financiación o el sello? | Apagado (churn), huecos de cobertura, escalamiento y mejora | Riesgo de baja + oportunidades |

Embat tiene doble papel: comprador interno (CS) y **vendedor de la señal al banco** (`scoring.md`: "el comprador obvio no es solo la pyme: es también el banco"). Por eso los eventos de crédito también son el producto comercial de Embat.

## 2. Veredicto sobre cada evento actual

| Evento actual | Veredicto | Motivo de producto |
|---|---|---|
| **Apagado** (3 %, medido por el equipo) | **Separar como otro producto** (modelo de churn + capa de abstención), fuera de la calibración de salud | No es salud: se van con mediana de 0,59 meses de caja frente a 0,48 de las activas y solo el 9 % con caja ≤ 0. Es un hecho de plataforma. Mezclarlo en la calibración arrastra los pesos hacia features de observabilidad, que `scoring.md` prohíbe imputar como salud. Aun así es valiosísimo para Embat: playbook de CS ("llama antes de que se apague", con tasa de salvación medible) y regla de abstención del score público (no puntuar lo que no se ve: es lo que mantiene la credibilidad del producto ante el banco). **Sí es un evento valioso, pero para otro producto** |
| **Saldo negativo** (5 %, medido) | **Redefinir** en dos: transición "primer mes en negativo tras ≥3 meses positivos" y estado "negativo persistente ≥3 meses" | El 23 % de los eventos ya estaban en negativo (es estado, no evento) y el 46 % dura >3 meses (posible artefacto de reconstrucción). "Algún mes < 0" confunde entrada, estado y ruido. El banco decide con la entrada (recorte) y la persistencia (reclamación); el CFO, con el mínimo intramensual |
| **Caída de cobros** (17 %, medido) | **Degradar a síntoma** para el score de salud; conservar una versión limpia como **ancla de la lectura de circulante** | El 69 % solapa con apagado y la definición hereda reversión a la media. Pero para quien financia o asegura contra recebibles, el deterioro de cobros es el *resultado* que decide la prima, no un síntoma |
| **Crecimiento** (16 %, medido) | **Redefinir** como "escalamiento sostenido autofinanciado" | Tal como está, premisa crecer con deuda dibujada: para el banco eso es riesgo, no salud. Es además el disparador de upsell (quien crece necesita circulante → marketplace) y del sello financiero |

## 3. Eventos recomendados

Añado una columna de comprador y decisión, que esta lente exige. Frecuencias nuevas = **estimaciones mías**, no medidas.

| Evento | Definición implementable (columnas del panel) | Tipo | Preguntas | Comprador y decisión | Frecuencia | Riesgos |
|---|---|---|---|---|---|---|
| **Entrada en tensión de caja** ⭐ ancla principal | Primer mes con meses de caja < 0,25 o `cash_end` < 0, tras ≥3 meses sin tensión; excluye primer mes parcial y meses truncados | Transición | 3, 4, 6 | Banco: recorta línea antes del descubierto. CFO: activa plan de caja | ~8-12 % por ventana de 6 m (est.) | Umbral arbitrario; estacionalidad de impuestos (usar gasto = máx(3m, 12m)); empresas con <3 meses quedan "no evaluables", no sanas |
| **Incumplimiento de obligación recurrente** | Categoría esperada (`tax` en meses fiscales, `payroll` mensual, `debt_service` según cuota) si aparece ≥2 veces en el patrón previo; incumplida si el mes dueño no aparece o queda <50 % del importe habitual; **guarda de observabilidad**: si `n_tx` del mes es bajo o el % sin categorizar alto, el evento se marca nulo | Resultado de alta severidad | 3, 5, 6 | Banco: la mora operativa (cuota que no se paga). CFO: nómina/IVA = crisis inmediata | ~2-5 % (est., no medida) | El 25 % de filas sin categoría puede simular omisiones (de ahí la guarda); solo 87 cuadros de amortización; pocos puntos de observación por empresa |
| **Caída estructural de actividad** | Mediana de `inflow` de los 6 meses siguientes < 50-60 % de la mediana de 12, **persistente ≥3 meses** y **sin apagado en la ventana** | Resultado | 3, 4, 5 | Banco y aseguradora: "deja de cobrar de forma persistente" (fila alta de criticidad) | ~8-12 % tras limpiar (est.; la versión actual mide 17 %) | Reversión a la media en picos; historia corta; estacionalidad |
| **Bache** (clase del monitor, no evento de calibración) | Mes(es) bajo umbral con recuperación ≤2 meses | Síntoma | 4, 5 | CFO: qué *no* hacer (no tratarlo como deterioro, fila "bache") | complementario a la caída | Con 21-24 meses, pocos episodios repetidos por empresa para validar la separación |
| **Escalamiento autofinanciado** | `inflow` medio de 2 trimestres >130 % de la base anual + `cash_end` al alza + sin deuda neta nueva | Estado positivo | 1, 2 | Embat upsell (oferta de financiación), financiador de crecimiento | ~6-10 % (est.; la versión laxa mide 16 %) | Solo 4-6 trimestres por empresa; estacionalidad anual |
| **Recuperación** | Tras tensión o negativo, ≥3 meses consecutivos con meses de caja ≥0,5 y sin incumplimientos | Estado positivo | 2, 4 | Banco: rehabilita límite. CFO: confirma que el plan funcionó | ~2-4 % (est.) | Pocos casos; depende de que el episodio inicial esté bien definido |
| **Sano sostenido (condicionado a edad)** | Toda la historia disponible (mín. 9-12 meses) sin eventos adversos y con meses de caja ≥1 | Estado positivo | 1 | Banco: a quién darle los 100.000 €. Embat: casos de éxito y sello | ~15-25 % (est.) | Sesgo de edad/supervivencia: condicionarlo a la historia disponible |
| **Baja de plataforma / apagado** (fuera del score) | `months_since_final_tx` > 0 definitivo; en producción, 30-60 días sin sincronizar ninguna fuente | Resultado de plataforma | Ninguna de las 6; retención y abstención | Embat CS: llamar antes de perder la cuenta | 3 % (medido; 121 empresas) | En sintético no distingue cierre real de desconexión |

**Ancla principal: la entrada en tensión de caja.** Es la fila "crítica" de `scoring.md`, se calcula sin ERP para el 100 % del panel (el incumplimiento depende de categorías con huecos) y el orden de su feature subyacente ya está probado (33 % → 0 % de saldo negativo por tramos). El incumplimiento es el ancla de la **lectura de crédito**, no del número público.

**¿Un score o varios?** Un número público + lecturas + un modelo aparte:

1. **Score base (0-100)**: salud-trayectoria, calibrado contra la familia adversa (tensión + incumplimiento + caída estructural), con capa de abstención por cobertura. Es el número del leaderboard y el que debe generalizar al test oculto.
2. **Lecturas** (mismas features, otros pesos y umbrales, barato de construir): caja (CFO), crédito (banco), circulante (aseguradora), potencial (upsell). Es exactamente lo que `scoring.md` ordena: "la métrica cambia según la oferta y según quién mira".
3. **Riesgo de baja**: logística pequeña sobre features de observabilidad (`n_tx`, % sin categorizar, huecos, ERP), contra el apagado. No sale en el número público.

## 4. Críticas a la propuesta actual

- **Anclar todo el score en el incumplimiento es frágil.** Depende de categorías con el 25 % de filas sin categorizar (45 % del importe de entradas): sin guarda de observabilidad, el evento mide en parte calidad del dato, que es justo lo que `scoring.md` llama "no es salud". Mejor ancla = tensión; incumplimiento = severidad y lectura de crédito.
- **La transición de tensión le falta higiene**: exclusión de meses truncados/parciales y regla de edad (sin 3 meses de historia no hay transición definible; hay que marcar "no evaluable", o reproducimos el sesgo de arranque que ya vieron al renormalizar pesos).
- **"Caída estructural frente a bache" sin regla de persistencia explícita no responde la pregunta 4.** Fijar: ≤2 meses = bache; ≥3 = estructural; y excluir apagados, si no reaparece el solape del 69 %.
- **"Sano sostenido 12 meses" tiene sesgo de edad**: las cohortes nuevas nunca pueden cumplirlo. Condicionarlo a la historia disponible.
- **La propuesta deja el crecimiento sin decidir.** Tal como está premisa crecer apalancado; para el comprador banco eso es riesgo. Redefinirlo autofinanciado.
- **Apagado aparte: de acuerdo, pero la propuesta no extrae el producto.** El modelo de churn y la capa de abstención son entregables con comprador (Embat CS) y alimentan el bonus del monitor. Apartarlo sin usarlo tira el único label de negocio real.
- **Falta la capa de quién mira.** La propuesta define eventos pero no lecturas por comprador; sin eso, la calibración vuelve a producir "un 72 para todos", que es lo que `scoring.md` prohíbe.

## 5. Cómo validarías los eventos sin etiquetas

1. **Backtest de decisión con P&L simulado**: para cada lectura, simular la decisión del comprador (prestar al decil superior, recortar bajo umbral, primar por tramos) y medir precisión, pérdida evitada y lead time contra los eventos a 6 m, siempre contra dos baselines: azar y "meses de caja" a secas. Un evento que no mejora ninguna decisión simulada es decoración.
2. **Curvas de anticipación (pregunta 6)**: distribución de meses entre la primera alerta y el evento. Un evento que solo se detecta el mes en que ocurre no vale para el producto; la promesa de Embat es adelantarse al rating ("lo adelanta con datos que el prestamista no ve").
3. **Orden monótono y ortogonalidad**: tasa de evento por decil + solape entre eventos + AUC marginal de cada evento en una logística multi-label. Si dos eventos comparten >50-70 % de casos y no aportan AUC marginal, fusionarlos.
4. **Placebo de ventana**: medir cada evento a h = 1, 3, 6, 9, 12. La señal real decae suave; el artefacto mecánico aparece plano o invertido (ya vieron el caso del orden invertido en el cambio de caja a 6 meses).
5. **Estabilidad por cohorte y corte temporal**: mitades de la serie y por edad (el 31 % tiene <12 meses). Un evento válido mantiene dirección y orden en ambos cortes.
6. **Sensibilidad de umbral**: recalibrar con umbrales alternativos (0,20/0,30; 40/60 %). Si los pesos del score cambian de signo, el evento mide ruido.
7. **Explotar al especialista de datos del reto** (localizable de noche): preguntar si el generador inyecta regímenes de estrés latentes y si el apagado se genera como churn independiente de la salud. Con datos sintéticos, el generador es la verdad más cercana, y casi ningún equipo la usará.
8. **Hold-out por `group_id`**, no por empresa (el ERP y el banco se comparten dentro del grupo), para imitar el test oculto.

## 6. Preguntas para la organización

1. **A Embat producto**: ¿cómo definís la baja en producción (30/60/90 días sin sincronizar ninguna fuente)? ¿El apagado del sintético se generó como churn independiente de la salud? ¿Podéis compartir, aunque sea agregada, la tasa real de bajas para calibrar frecuencias?
2. ¿Hay **10-20 casos reales anonimizados** (empresa que luego dejó de pagar una cuota, o que luego se dio de baja) para validar definiciones? Veinte ejemplos reales valen más que 21.538 filas sintéticas sin etiqueta.
3. Para la demo: ¿a quién le vendéis primero esta señal —al banco (early warning en marca blanca) o al CFO (módulo del producto)—? El héroe del pitch decide qué evento protagoniza.
4. ¿El script de scoring del test oculto evalúa solo el orden del score o admite salidas adicionales (alertas, lecturas)? ¿Habrá empresas que se apagan en el test?
5. ¿Qué ratio de falsos positivos tolera un equipo de CS o un banco antes de ignorar el monitor?
6. ¿Qué umbral de "meses de caja" refleja la realidad de vuestra base de pymes (¿0,25 es poco para sectores con ciclo largo?)?

## 7. Verificaciones hechas

**No tengo acceso a los datos ni a herramientas en esta sesión**: no he ejecutado nada y no hay verificaciones nuevas. Las cifras que cito como medidas vienen de los documentos del equipo (`brief_eventos.md`, `features.md`): apagado 3 %, saldo negativo 5 %, caída 17 %, crecimiento 16 %, solape apagado-caída 69 %, 36 % de apagados con síntomas previos, 22 % se va con >3 meses de caja, AUC 0,77 de los meses de caja, 23 % ya en negativo previo, 46 % persistente >3 meses, 25 % de filas sin categorizar, 121 empresas que dejan de moverse. Las frecuencias de los eventos nuevos (tensión, incumplimiento, caída estructural limpia, recuperación, sano sostenido, escalamiento autofinanciado) son **estimaciones mías** y están marcadas como tales; antes de calibrar pesos habría que medirlas con `research/src/targets.py` siguiendo las definiciones de la sección 3.