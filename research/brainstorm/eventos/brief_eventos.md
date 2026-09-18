# Brief del panel: ¿qué eventos deben ser la "verdad" del score X-Ray?

Proyecto: reto X-Ray de HackSpain 2026 (Embat). Repo en `/home/balalo/repos/hackspain`. Documentos de contexto:
- `context/challenge.md`: enunciado. Pide un score de salud por empresa y mes y responder seis preguntas: quién está sano, quién mejora, quién se tuerce aunque parezca sano, bache frente a caída, por qué cambió y con cuánta antelación. Hay un test oculto de 60-80 empresas nunca vistas y hay que construir un producto con comprador identificado.
- `context/scoring.md`: marco del equipo ("la prueba de los 100.000 €").
- `features.md`: brief del dataset, trampas conocidas, features actuales y descartadas.
- `research/src/targets.py`: definición actual de los eventos.

Datos: `research/data/*.parquet` (transactions, invoices, balances, companies, banking_products, debt_products, debt_schedule_config) y `research/data/panel.parquet` (panel empresa × mes).

## El problema

No hay etiquetas. Como "verdad" usamos 4 eventos en los 6 meses siguientes, que sirven para calibrar los pesos del score y para validar:

| Evento | Definición | Frecuencia |
|---|---|---|
| Apagado | La empresa deja de tener movimientos para siempre | 3 % |
| Saldo negativo | La caja reconstruida pasa a negativa algún mes | 5 % |
| Caída de cobros | La mediana de cobros de los 6 meses siguientes queda por debajo del 50 % de la mediana de los 12 anteriores | 17 % |
| Crecimiento | Cobros medios >130 % de la media anual y caja al alza | 16 % |

Todo el sistema (pesos, AUC, alertas) se optimiza contra estos eventos.

## Hallazgos ya medidos

1. **Apagado.** En su último mes activo, las empresas que se apagan tienen una mediana de 0,59 meses de caja, frente a 0,48 de las activas. El 22 % se va con más de 3 meses de caja y solo el 9 % con caja ≤ 0. Solo el 36 % mostró síntomas (saldo negativo o caída de cobros) en los 6 meses previos. ¿Es desconexión de Embat más que cierre?
2. **Solapamiento mecánico.** El 69 % de los apagados cuenta también como caída de cobros.
3. **Saldo negativo.** Los meses de caja de hoy lo predicen con AUC 0,77, en parte de forma circular.
   - El 23 % de los eventos ocurre en empresas que ya estaban en negativo en los 3 meses previos.
   - El 20 % de esas empresas tiene póliza de crédito.
   - El 46 % de las empresas con algún mes negativo sigue así más de 3 meses seguidos (¿artefacto de reconstrucción?).
   - Solo un 3 % tiene saldos implausibles (más de 50 veces el volumen mensual).
4. **Poco solapamiento entre eventos.** El saldo negativo es casi independiente del resto.
5. **No es un problema de linealidad.** Una logística lineal y un LightGBM sobre las 17 features dan el mismo AUC frente a cada evento: el límite es la información, no la forma del modelo.

## Propuesta actual (critícala)

- **Evento principal "incumplimiento":** una obligación recurrente omitida (nómina, IVA trimestral o cuota de préstamo que tocaba y no aparece) o proveedores con más de 90 días vencidos que crecen.
- **"Entrada en tensión de caja" como transición:** primer mes con menos de 0,25 meses de caja o en negativo, tras 3 meses o más en buena situación.
- **"Caída estructural" frente a "bache".**
- **"Recuperación":** pasa de riesgo a sano y se mantiene.
- **"Sano sostenido":** 12 meses sin eventos adversos.
- **Apagado aparte**, como posible baja de Embat.
- **Caída de cobros** pasa a ser una feature (un síntoma), no un objetivo.

## Formato de respuesta (Markdown, en español)

1. **Posición**: tu tesis en 3-5 frases.
2. **Veredicto sobre cada evento actual**: mantener, redefinir, degradar a feature, eliminar o separar como otro producto, con el motivo.
3. **Eventos recomendados**, en tabla: nombre, definición implementable con las columnas del dataset, tipo (resultado, síntoma, transición o estado positivo), preguntas del reto que cubre, frecuencia estimada o medida y riesgos. Indica cuál sería el ancla principal.
4. **Críticas a la propuesta actual.**
5. **Cómo validarías los eventos sin etiquetas.**
6. **Preguntas para la organización.**
7. **Verificaciones hechas** con los datos, si tienes acceso. Si no tienes acceso, dilo y marca las cifras como estimaciones.
