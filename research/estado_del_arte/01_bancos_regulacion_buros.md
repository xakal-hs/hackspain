# Cómo miden el riesgo de crédito de empresas los bancos, los reguladores, las agencias y los burós

Estado del arte para X-Ray (HackSpain 2026, reto de Embat). Fecha: 19-sep-2026.
Pregunta: qué hacen los profesionales para puntuar a una empresa, qué features usan, cómo validan y cómo explican, y qué de todo eso podemos replicar con **solo tesorería** (movimientos bancarios, facturas ERP, productos de deuda y saldos, sin balances ni etiqueta de default).

---

## 0. Resumen en 12 puntos

1. **La regulación ya define "default" con señales de tesorería.** Además de los 90 días de mora, la EBA y el Banco de España enumeran señales de *unlikeliness to pay* que podemos observar en el banco: fuentes de ingresos recurrentes que desaparecen, flujos insuficientes, caída de la cifra de negocios, retrasos generalizados en pagos y, sobre todo, **"compromisos vencidos de importe significativo frente a organismos públicos o a empleados"** (Circular 4/2017, anejo 9, punto 107.f). Es exactamente nuestro impago de nómina, Seguridad Social o IVA.
2. **Hay dos niveles de alarma regulatoria.** El primero es el aumento significativo de riesgo (IFRS 9 *stage 2*, "normal en vigilancia especial", presunción a los **30 días** de impago). El segundo es el dudoso o *default* (*stage 3*, **90 días** o UTP). Para salir del default hace falta un periodo de prueba de **3 meses**, o de 1 año si hubo reestructuración.
3. **Los EWS bancarios son casi todos transaccionales**: uso de la póliza, meses en descubierto o con excedido, recibos devueltos, caída de ingresos, reducción del disponible, retrasos y embargos. La lista de ejemplos del BCE (NPL Guidance, anejo 4) y la de la EBA (GL/2020/06, párr. 274) sirven de catálogo.
4. **La evidencia académica respalda nuestro enfoque.** Norden y Weber (RFS 2010) encuentran que el uso de la línea, los excedidos y las entradas de caja se comportan de forma anómala unos **12 meses antes** del default y que ayudan sobre todo en pymes pequeñas. En Société Générale, los datos de cuenta corriente dan un **AUC de 0,80 frente a 0,76** con ratios financieros, y de **0,84 combinados** (Yao et al. 2017).
5. **La póliza avisa pronto.** En Moody's CRD, las empresas que acaban en default llegan a un uso medio de la línea del 76 % dos años antes (mediana 92 %). Las sanas se quedan en el 52 % de media.
6. **Los ratings de pyme son modulares**: un bloque financiero, uno de comportamiento (cuenta y CIRBE/buró), uno cualitativo y reglas de override. **El peso del comportamiento sube cuanto más pequeña es la empresa o cuanta menos información financiera hay.** Informa D&B pondera 55/16/29 (financiero/características/comportamiento) si hay cuentas y 40/60 (características/comportamiento) si no las hay.
7. **La técnica estándar es una scorecard logística** con binning monótono, WoE e IV, una escala de puntos (PDO) y *reason codes*. RiskCalc (Moody's) usa transformaciones no paramétricas monótonas, un modelo aditivo generalizado encubierto. S&P usa una logística ridge que llama "glass box".
8. **El crecimiento es un arma de doble filo**: según RiskCalc, tanto crecer muy deprisa como caer muy deprisa suben la PD. No hay que modelarlo como una variable monótona.
9. **La salida es una escala maestra**: al menos 7 grados sanos más 1 de default, cada uno con su PD. El ICAS del Banco de España mapea a los escalones del Eurosistema (PD ≤ 0,1 %, 0,4 %, 1 %, 1,5 %, 3 %, 5 %, > 5 %).
10. **La validación tiene tres patas y test estándar**. La discriminación se mide con AUC o Gini (y KS). La calibración, con el test de Jeffreys o el binomial por grado. La estabilidad, con PSI, matrices de migración y concentración (HHI) por grado. A eso se suma el backtesting *out-of-time*. Como referencia, la cotización de Banque de France tiene un Gini a 1 año del 71-77 % y RiskCalc un *accuracy ratio* a 1 año del 54 %.
11. **Los burós viven del comportamiento de pago comercial.** Miden los *days beyond terms* ponderados por importe (PAYDEX, DBT de Experian, Creditsafe, Payline de Cerved), las incidencias (RAI, ASNEF Empresas, embargos, juicios), la antigüedad, el sector y el tamaño. D&B define "severamente moroso" como **≥ 10 % del importe con más de 90 días de retraso**.
12. **Qué nos llevamos**: casi todo lo que no dependa del balance. En nuestros datos hay además señales EWS de manual que aún no usamos: **embargos y diligencias de AEAT/TGSS (164 empresas), recibos propios impagados, intereses y reclamaciones de descubierto (132 empresas) y aplazamientos con TGSS/AEAT (76 empresas)** (sección 6).

---

## 1. Marco regulatorio

### 1.1 Basilea IRB: PD, LGD, EAD y la pérdida esperada

- **Parámetros.** La PD es la probabilidad de default a 1 año del grado de rating. La LGD es la pérdida en % de la exposición si hay default. La EAD es el importe expuesto en el default (dispuesto más la parte previsible del no dispuesto, vía CCF). M es el vencimiento efectivo. La **pérdida esperada** es EL = PD · LGD · EAD, y se cubre con provisiones. El capital cubre la pérdida inesperada. [BCBS, *An Explanatory Note on the Basel II IRB Risk Weight Functions*, 2005](https://www.bis.org/bcbs/irbriskweight.htm).
- **Función de ponderación de empresas.** Viene del modelo de un factor de Vasicek al 99,9 %:
  - K = [LGD · N( G(PD)/√(1−R) + √(R/(1−R)) · G(0,999) ) − PD · LGD] · (1 + (M − 2,5)·b) / (1 − 1,5·b)
  - R = 0,12·(1−e^(−50·PD))/(1−e^(−50)) + 0,24·[1 − (1−e^(−50·PD))/(1−e^(−50))], con un ajuste de pyme de −0,04·(1 − (S−5)/45) para ventas S entre 5 y 50 M€
  - b = (0,11852 − 0,05478·ln PD)². Los activos ponderados por riesgo son RWA = 12,5 · K · EAD.
  - Las pymes con exposición pequeña pueden tratarse como **minoristas**, con otra correlación y sin ajuste de vencimiento.
- **F-IRB y A-IRB.** En el F-IRB el banco estima solo la PD, y la LGD y la EAD son supervisoras: una LGD del 45 % para deuda senior no garantizada en Basilea II, que Basilea III final baja al 40 % para empresas. En el A-IRB el banco estima los tres parámetros. La PD tiene un suelo del 0,03 % en Basilea II y del 0,05 % en Basilea III/CRR3.
- **Requisitos del sistema de rating** (CRR arts. 170 y 180, [Basel Framework CRE36](https://www.bis.org/basel_framework/chapter/CRE/36.htm)):
  - Al menos **7 grados para deudores sanos y 1 para los que están en default**.
  - PD calibrada a la **media de largo plazo de las tasas de default anuales**, con al menos 5 años de datos.
  - Criterios de rating documentados, overrides controlados y validación periódica.

### 1.2 Definición de default: 90 días más *unlikeliness to pay* (CRR art. 178, EBA/GL/2016/07)

Fuente: [EBA/GL/2016/07](https://www.bde.es/f/webbde/INF/MenuHorizontal/Normativa/guias/EBA-GL-2016-07-EN.pdf), en vigor desde el 1-ene-2021, y el [Reglamento Delegado (UE) 2018/171](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32018R0171) sobre el umbral de materialidad. El BCE lo aplica con el [Reglamento (UE) 2018/1845](https://eur-lex.europa.eu/eli/reg/2018/1845/oj/eng).

| Elemento | Qué dice |
|---|---|
| Criterio de mora | Más de **90 días** de retraso en una obligación **material**. Para empresas, la materialidad es una parte absoluta de **500 €** (100 € en minorista) y una parte relativa del **1 %** de la exposición. Los días se cuentan desde que se superan ambas |
| Factoring (párr. 27-28) | Sin recurso en balance: los días cuentan desde el vencimiento de cada factura cedida. Con cuenta de factoring: desde que la cuenta queda deudora por encima del % acordado |
| UTP obligatorios (art. 178.3) | Contabilidad sin devengo de intereses, provisión específica, venta con pérdida material, **reestructuración forzosa** (pérdida de valor actual neto > 1 %), concurso o protección similar solicitados |
| UTP con información interna (párr. 59) | a) **las fuentes de ingresos recurrentes ya no alcanzan para pagar las cuotas**; b) dudas justificadas sobre la capacidad futura de **generar flujos estables y suficientes**; c) apalancamiento que sube significativamente; d) incumplimiento de *covenants*; e) ejecución de garantías; h) exposición clasificada como dudosa (*non-performing*) |
| UTP con información externa (párr. 60) | a) **retrasos significativos con otros acreedores en el registro de crédito** (CIRBE); b) crisis del sector junto con una posición débil en él; d) un tercero ha pedido la quiebra del deudor |
| Reestructuración (párr. 53) | Es indicio de UTP un pago global grande al final (*bullet*), cuotas iniciales mucho menores, carencia larga al principio o haber reestructurado más de una vez |
| Salida del default (párr. 71-73) | **3 meses** sin disparadores, teniendo en cuenta el comportamiento y la situación financiera en ese periodo; **1 año** si hubo reestructuración |

### 1.3 España: Circular 4/2017 del Banco de España, anejo 9 (IFRS 9 en la práctica)

Fuente: [BOE-A-2017-14334](https://www.boe.es/buscar/doc.php?id=BOE-A-2017-14334) (anejo 9, copia en [Cesgar](https://cesgar.es/wp-content/uploads/2023/03/9.-Circular-4-2017-ANEJO-9-riesgo-de-credito.pdf)). Es la traducción española más concreta de "señal temprana" y "default subjetivo".

**Riesgo normal en vigilancia especial (*stage 2*).** El **punto 94** fija los indicadores mínimos de aumento significativo del riesgo:
- a) más endeudamiento y ratios de servicio de la deuda (deuda / flujos de explotación);
- b) **caídas significativas de la cifra de negocios o de los flujos de efectivo recurrentes**;
- c) estrechamiento de márgenes;
- f) rebaja del rating interno o **de la puntuación de comportamiento**;
- i) peores condiciones de financiación o **reducción del apoyo de terceros**;
- j) ralentización del negocio;
- m) **cambios significativos en el comportamiento de pago**;
- **o) dificultades de entidades del mismo grupo** o con dependencia económica;
- q) litigios.

El **punto 95** añade que, salvo prueba en contrario, el riesgo pasa a vigilancia especial con **importes vencidos de más de 30 días**.

**Dudoso por razones distintas de la morosidad (*stage 3* subjetivo).** El **punto 107** enumera los indicadores:
- a) patrimonio neto negativo o caído ≥ 50 %;
- b) pérdidas continuadas o **descenso significativo de la cifra de negocios o de los flujos recurrentes**;
- c) **retraso generalizado en los pagos o flujos de efectivo insuficientes para atender las deudas**;
- d) estructura inadecuada o **imposibilidad de obtener financiación adicional**;
- e) rating que indica impago;
- **f) compromisos vencidos de importe significativo frente a organismos públicos o a empleados.**

El **punto 108** fija los factores automáticos de dudoso: reclamación judicial, ejecución de garantías, concurso y refinanciación que vuelve a fallar durante el periodo de prueba.

### 1.4 PIT frente a TTC y la escala maestra

- **Filosofía de rating** ([EBA/GL/2017/16](https://www.eba.europa.eu/documents/10180/2033363/6b062012-45d6-4655-af04-801d26493ed0/Guidelines%20on%20PD%20and%20LGD%20estimation%20(EBA-GL-2017-16).pdf), sección 5.2.4, párr. 66-69):
  - Un sistema **point-in-time (PIT)** usa drivers sensibles al ciclo. Las empresas **migran de grado** cuando cambia la economía y la tasa de default de cada grado se mantiene estable.
  - Un sistema **through-the-cycle (TTC)** es poco sensible. Los grados quedan estables y lo que se mueve con el ciclo es la tasa de default de cada grado.
  - La EBA deja elegir, pero exige aplicar la filosofía de forma coherente, entender su efecto en la volatilidad del capital y **tenerla en cuenta en el backtesting**.
  - Basilea calibra a la media de largo plazo, lo que sesga hacia TTC. IFRS 9 pide PD PIT y *forward-looking* (a 12 meses y para toda la vida del crédito).
- **Escala maestra.** Es una tabla de grados con PD central y rangos que no se solapan, común a todos los modelos del banco. Un ejemplo público es el mapeo del ICAS del Banco de España a la escala armonizada del Eurosistema ([Gavilá, Maldonado y Marcelo, *Revista de Estabilidad Financiera* nº 38, 2020](https://www.bde.es/f/webbde/GAP/Secciones/Publicaciones/InformesBoletinesRevistas/RevistaEstabilidadFinanciera/20/mayo/en/Banco_Espana_in_house_credit.pdf)):

| Escalón (CQS) | 1-2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| PD a 1 año | ≤ 0,10 % | 0,10-0,40 % | 0,40-1,00 % | 1,00-1,50 % | 1,50-3,00 % | 3,00-5,00 % | > 5 % y D |
| Nota ICAS BE | 1 a 3− | 4+, 4, 4− | 5+, 5 | 5− | 6+ | 6, 6− | 7+ a 8 y D |

Otro ejemplo es la cotización de Banque de France: 22 escalones, horizonte de 3 años y una definición de default propia que incluye los **impagos de efectos comerciales**, algo muy parecido a nuestro RAI (sección 4).

### 1.5 EBA/GL/2020/06 (concesión y seguimiento de préstamos): qué exige y qué EWS lista

Fuente: [EBA/GL/2020/06, Final Report](https://www.eba.europa.eu/sites/default/files/document_library/Publications/Guidelines/2020/Guidelines%20on%20loan%20origination%20and%20monitoring/884283/EBA%20GL%202020%2006%20Final%20Report%20on%20GL%20on%20loan%20origination%20and%20monitoring.pdf), aplicable desde el 30-jun-2021.

- **Marco de EWI (párr. 269-273).** Los indicadores de alerta temprana deben ser cuantitativos y cualitativos y tener soporte de IT y datos. Cada uno lleva **umbrales de disparo definidos** y **procedimientos de escalado** con responsables, y puede llevar a una *watch list*. Hay que documentar la relevancia de cada indicador según el tipo de deudor. Cuando uno se dispara, se aumenta la frecuencia de revisión (párr. 275-277).
- **Señales de deterioro que deben considerarse (párr. 274, selección):**
  - b) aumento significativo del endeudamiento o del servicio de la deuda;
  - **c) caída significativa de la facturación o, en general, del flujo de caja recurrente (incluida la pérdida de un contrato, cliente o arrendatario principal)**;
  - d) estrechamiento de márgenes;
  - h) **peores condiciones de financiación** o menos apoyo de terceros;
  - i) ralentización del negocio;
  - **l) aumento del riesgo en otras operaciones del mismo deudor o cambios en su comportamiento de pago esperado**;
  - m) dificultades del grupo o del sector;
  - n) acciones legales;
  - o) incumplimiento o entrega tardía de *covenants*;
  - q) bajada del rating interno o **del behavioural scoring**;
  - **s) una o más operaciones con 30 días de impago.**
- **Covenants como EWI (párr. 267).** Deuda neta / EBITDA, cobertura de intereses y DSCR.
- **Datos para evaluar a una pyme (anejo 2.B).** Estados financieros, **informes de antigüedad de cuentas a cobrar** (*aged debtor reports*), plan de negocio, proyecciones, situación fiscal, **datos de registros de crédito y burós (pasivos y retrasos)**, rating externo, *covenants* y litigios.
- **Métricas para empresas (anejo 3.B).** Ratio de fondos propios, deuda/fondos propios, EBITDA, deuda con coste/EBITDA, **DSCR (EBITDA / servicio total de la deuda)**, **cobertura de caja de la deuda (flujo operativo / pasivo corriente medio)**, cobertura (activo corriente / deuda a corto), **análisis de flujos de caja futuros**, ROA, ROE, margen neto, **evolución de la facturación** y cobertura de intereses.
- **Modelos automatizados (párr. 53-55).** El banco debe entender el modelo y detectar sesgos. Los inputs y outputs tienen que ser trazables y auditables, el output debe **someterse a backtesting** y tiene que haber **overrides y escalado** con juicio experto. "Si se requieren explicaciones durante el uso del modelo, debería considerarse **desarrollar un modelo interpretable**" (53.d).

### 1.6 BCE, NPL Guidance (2017), anejo 4: ejemplos de EWI usados por los bancos

Fuente: [ECB, *Guidance to banks on non-performing loans*, 2017](https://www.bankingsupervision.europa.eu/ecb/pub/pdf/guidance_on_npl.en.pdf), anejo 4. Es la lista más "transaccional" publicada por un supervisor.

| Tipo | EWI para empresas |
|---|---|
| Internos | Tendencia negativa del rating interno; **cheques impagados**; **cambio significativo del perfil de liquidez**; apalancamiento (fondos propios/total < 5-10 %); **días de impago**; **número de meses con descubierto o con excedido**; BAI/ingresos < −1 %; pérdidas continuadas; **exceso continuado en el descuento de papel comercial**; fondos propios negativos; **retrasos en pagos**; **caída de la facturación**; **reducción de las líneas ligadas a cuentas a cobrar** (variación interanual, media de 3 meses / media de 1 año); **reducción inesperada del disponible** (no dispuesto / límite); tendencia negativa del **behavioural scoring** y de la PD |
| Externos | **Más deuda y más garantías en otros bancos**; morosidad en otros bancos; default del avalista; deuda en registros privados; procedimientos judiciales; concurso; cambios societarios (fusión, reducción de capital); rating externo y su tendencia; **noticias negativas sobre los clientes o proveedores principales** |
| Personas (útil por analogía) | Caída del saldo acreedor > 95 % en 6 meses; **caída de la nómina en 3 meses**; mora temprana de 5 a 30 días; **reducción de las transferencias recibidas**; más cuota sobre nómina |

---

## 2. Modelos internos de rating de pymes en bancos

### 2.1 Arquitectura: módulos y pesos

| Módulo | Contenido típico | Comentario |
|---|---|---|
| Financiero (balance y cuenta de resultados) | Liquidez, estructura de capital, rentabilidad, cash flow, actividad, tamaño, crecimiento | Mira hacia atrás y llega con retraso (cuentas anuales). Es el que pesa más en empresas medianas y grandes |
| Comportamiento interno (cuenta y productos) | **Saldos máximo y mínimo, varianzas, número y tamaño de transacciones, excedidos de la línea**, días de impago, devoluciones | Se actualiza cada mes y predice bien a unos 12 meses. "Un gran banco británico" dice que es muy eficaz en las pymes más pequeñas ([CSES para la Comisión Europea, *Evaluation of Market Practices and Policies on SME Rating*](https://webgate.ec.europa.eu/circabc-ewpp/rest/download/c1e85d1f-e3f3-4604-9344-bdb812ced48a), tabla 3.1 y § 3.2.1) |
| Comportamiento externo (CIRBE y burós) | Riesgo dispuesto y disponible en todo el sistema, número de entidades, morosidad o dudosos en otras entidades, RAI, ASNEF, embargos, juicios | En España, la CIRBE devuelve a las entidades el riesgo agregado de los titulares con más de 1.000 € ([BdE, CIRBE](https://clientebancario.bde.es/pcb/es/menu-horizontal/podemosayudarte/cirbe/)) |
| Cualitativo | Gestión, estrategia, posición competitiva, sector, relación con el banco | Según CSES, en la banca generalista pesa entre el **20 % y el 40 %** del rating; en bancos públicos o especializados en pyme, entre el **60 % y el 80 %** |
| Overrides y ajustes | Apoyo del grupo, alertas (CIRBE, prensa), juicio del analista | Se documentan y se monitoriza su tasa |

Evidencia sobre la combinación de módulos:
- **Grunert, Norden y Weber (2005)**, con datos de 4 grandes bancos alemanes: combinar factores financieros y no financieros predice el default mejor que cada bloque por separado ([JBF 29(2)](https://ideas.repec.org/a/eee/jbfina/v29y2005i2p509-531.html)).
- **ICAS del Banco de España.** Tiene dos etapas ([Gavilá et al., 2020](https://www.bde.es/f/webbde/GAP/Secciones/Publicaciones/InformesBoletinesRevistas/RevistaEstabilidadFinanciera/20/mayo/en/Banco_Espana_in_house_credit.pdf)).
  - Estadística: una **logística** con una ventana amplia elige ratios y pesos. La variable a explicar es el default en todo el sistema bancario español (art. 178 CRR), no el de un solo banco. Después, la puntuación se agrupa en tramos y se **calibra** a la PD a 1 año por tramo.
  - Experta, en cinco áreas: validar el dato, perfil financiero, riesgo de negocio, gestión e información adicional. Después se ajusta por **apoyo implícito del grupo** y por **alertas de la Central de Información de Riesgos** y divergencias con ECAI/IRB.
  - Para **pymes** (más de 150.000), el modelo es solo estadístico y se complementa con el **historial de pagos mensual de la CIRBE**.
  - Ratios del modelo general: activos de explotación (tamaño), reservas/activo, deuda financiera neta/activos de explotación, **(flujo operativo − variación del circulante) / gastos financieros**, gastos financieros / deuda financiera, (activo corriente − caja) / activos de explotación, **(caja + activos financieros corrientes) / pagos a corto** y EBITDA / activos de explotación.
- **Moody's: ensemble financiero más comportamental.** Combina el EDF de RiskCalc (financiero) con un score de su *Credit Behavioral Database* (uso de líneas, comportamiento de pago de préstamos; default a 90 días). **El peso del comportamiento es mayor en la pequeña empresa que en la mediana**, y el valor añadido del modelo de pagos también es mayor cuanto más pequeña es la empresa ([Moody's Analytics 2017](https://www.moodysanalytics.com/articles/2017/combining-financial-and-behavioral-information); [*Advances in default detection and early warning*](https://www.moodys.com/web/en/us/insights/credit-risk/advances-in-default-detection-and-early-warning.html)).

### 2.2 Técnica: scorecard logística (WoE/IV), escalado, *reason codes* y overrides

| Paso | Práctica estándar |
|---|---|
| Diana | Default a 12 meses (mora de 90 días o UTP), con ventana de observación y ventana de rendimiento separadas |
| Binning | *Fine classing* (unos 20 tramos) y *coarse classing* agrupando tramos hasta lograr **WoE monótono** y con sentido económico, con al menos un 5 % de la población por tramo |
| WoE | WoE_i = ln(%buenos_i / %malos_i) |
| IV | IV = Σ (%buenos_i − %malos_i) · WoE_i. Regla de Siddiqi: < 0,02 inútil, 0,02-0,1 débil, 0,1-0,3 media, 0,3-0,5 fuerte y > 0,5 sospechosa de fuga de información ([Siddiqi, *Credit Risk Scorecards*, Wiley 2006/2017](https://www.amazon.com/Credit-Risk-Scorecards-Implementing-Intelligent/dp/047175451X)) |
| Modelo | Logística sobre las variables WoE, con selección *stepwise* o regularizada y control de correlación y VIF. S&P CreditModel usa una logística **ridge** con selección *greedy forward* en k-fold ([S&P, *Machine Learning and Credit Risk Modelling*, 2020](https://www.spglobal.com/content/dam/spglobal/mi/en/documents/general/Machine_Learning_and_Credit_Risk_Modelling_November_2020.pdf)) |
| Alternativa GAM | RiskCalc: EDF = F(Φ(Σ β_i·T_i(x_i) + Σ γ_j·I_j)), con T_i **transformaciones no paramétricas** de cada ratio, indicadores de sector y una transformación final F. Se comprueba que cada T_i es **monótona** donde debe serlo, para que "más apalancamiento" nunca baje la PD ([Stein et al., RiskCalc v3.1](http://www.rogermstein.com/wp-content/uploads/RiskCalc-v3-1-Model.pdf)) |
| Escalado | Puntos = offset + factor · ln(odds). La convención es fijar los **PDO** (*points to double the odds*), por ejemplo 20 PDO y 600 puntos para odds de 50:1. Cada atributo suma unos puntos que se leen directamente |
| *Reason codes* | Las 3-4 características en las que el cliente **pierde más puntos** frente al máximo o la media. En EE. UU., la Regulation B obliga a dar las razones de una denegación también en crédito a empresas; si la facturación es > 1 M$, basta con darlas cuando se piden ([12 CFR 1002.9](https://www.ecfr.gov/current/title-12/chapter-X/part-1002/subpart-A/section-1002.9)) |
| Overrides | Reglas de política (*knock-out*) y ajustes del analista con motivo codificado. Se monitorizan su tasa y su resultado (EBA GL/2017/16; en el informe de validación del BCE, "occurrence of overrides") |

### 2.3 Behavioural scoring y EWS transaccionales: la evidencia

| Estudio | Datos | Hallazgo útil |
|---|---|---|
| [Norden y Weber, RFS 2010](https://academic.oup.com/rfs/article-abstract/23/10/3665/1566409) | Clientes de bancos alemanes (pymes y particulares) | **El uso de la línea, los excedidos y las entradas de caja se vuelven anómalos unos 12 meses antes del default.** La actividad de la cuenta mejora mucho la predicción, sobre todo en pymes pequeñas. Las alertas acaban en más *spread*, recortes de límite y fallidos |
| [Mester, Nakamura y Renault, RFS 2007](https://academic.oup.com/rfs/article-abstract/20/3/529/1563872) | Banco canadiense, pymes con línea garantizada | Las cuentas transaccionales reflejan cada mes la evolución de las cuentas a cobrar. **Dibujar por encima del colateral predice rebajas de rating y saneamientos**, y el banco intensifica entonces el seguimiento |
| [Yao, Levy-Chapira y Margaryan, 2017](https://arxiv.org/pdf/1707.00757) | Société Générale, empresas francesas, quiebra a 1 año | 30 variables mensuales de cuenta con 24 meses de historia. **AUC de test**: cuenta 0,80 (boosting) frente a ratios financieros y cuestionario 0,76, y **0,84 combinando ambos**. Las variables más importantes son los excedidos (número, rechazados, importe aceptado frente a rechazado), el **coeficiente de variación de las entradas mensuales** y la entrada actual frente a la media. **Todo se normaliza por la media de entradas mensuales de 24 meses** ("el equivalente de las ventas") |
| [Jiménez, López y Saurina, RFS 2009](https://academic.oup.com/rfs/article/22/12/5069/1577140) | CIRBE, todas las líneas de crédito de empresas españolas | **El uso de la línea sube a medida que empeora la situación de la empresa**. Las empresas con defaults previos acceden menos, por el efecto del seguimiento bancario. El uso cae un 10 % por año de vida de la línea |
| [Moody's, *Corporate Credit Lines: Usage and EAD*](https://www.moodys.com/web/en/us/insights/credit-risk/usage-and-exposures-at-default-of-corporate-credit-lines.html) | 19 bancos de EE. UU., 4,97 M de observaciones trimestrales, 53.000 préstamos en default | Uso en el default: media del 81 % (mediana 97 %). **Dos años antes, 76 % de media (mediana 92 %)**, frente al 52 % de las sanas. Las empresas que acaban en default llegan a un uso alto unos 8 trimestres antes |
| [FinRegLab, 2025](https://finreglab.org/research/sharpening-the-focus-using-cash-flow-data-to-underwrite-financially-constrained-businesses/) | 38.000 préstamos a pequeñas empresas de 2 fintech | Añadir cash flow de la cuenta al *score* personal del dueño mejora el modelo en todos los segmentos. **Los depósitos y el saldo son lo más potente**; los reintegros, la volatilidad del saldo y los **episodios de saldo bajo o negativo** también predicen ([nota de prensa](https://finreglab.org/press-releases/finreglab-study-shows-cash-flow-data-can-expand-small-business-lending/)) |
| [Altman, Sabato y Wilson, J. Credit Risk 2010](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1320612) | 5,8 M de cuentas de pymes británicas, 66.000 quiebras | Las **acciones legales de acreedores para cobrar deudas**, el historial de depósito de cuentas (retrasos), la opinión de auditoría y la antigüedad añaden poder predictivo sobre los ratios |

Variables de cuenta de Yao et al. (Société Générale), directamente replicables. Operaciones: X_t, ΔX = X_t − X_{t−11}, ΔΔX = X_t − X_{t−23}, y media y desviación en [t−11, t].

| Grupo | Variable | Normalizada por la media de entradas de 24 meses |
|---|---|---|
| Saldo | ΔΔ de saldo mínimo, medio, acreedor medio y deudor medio | Sí |
| Excedidos | Número de excedidos intentados y rechazados en 12 meses; (importe intentado − rechazado) / intentado | No |
| Vitalidad | Δ(saldo máx − mín); Δ de entradas y salidas totales | Sí |
| Entradas y salidas | Δ(entradas/salidas) | No |
| Estabilidad | sd/media del saldo medio; **sd/media de las entradas mensuales** (12 meses) | No |
| Nivel actual | Saldo medio, acreedor y deudor; entradas y salidas del mes; saldo mínimo y máximo del mes | Sí |
| Atributos | Sector (codificado por su tasa de default) y ventas | No |

---

## 3. Modelos clásicos

| Modelo | Forma y variables | Notas |
|---|---|---|
| **Altman Z (1968)** | Z = 1,2·X1 + 1,4·X2 + 3,3·X3 + 0,6·X4 + 1,0·X5, con X1 = circulante/activo, X2 = reservas/activo, X3 = EBIT/activo, X4 = **valor de mercado** del capital/pasivo y X5 = ventas/activo. Zonas: > 2,99 sana, < 1,81 en dificultades | Análisis discriminante con 66 manufactureras cotizadas ([Altman, J. Finance 1968](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1968.tb00843.x)) |
| **Z' (empresas privadas)** | 0,717·X1 + 0,847·X2 + 3,107·X3 + 0,420·X4' + 0,998·X5, con X4' = **valor contable** del capital / pasivo. Zonas: > 2,9 y < 1,23 | [Altman 2000, *Revisiting the Z-score and ZETA models*](https://www.researchgate.net/publication/2413921_Predicting_Financial_Distress_Of_Companies_Revisiting_The_Z-Score_And_Zeta) |
| **Z''** (no manufactureras y emergentes) | 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4', sin rotación de ventas. Zonas: > 2,6 y < 1,1. La versión para emergentes suma 3,25 y se mapea a la escala de rating | Es la versión más usada con pymes. Con datos de 31 países rinde razonablemente fuera de muestra y mejora al reestimarla por país ([Altman et al., JIFMA 2017](https://onlinelibrary.wiley.com/doi/abs/10.1111/jifm.12053)) |
| **Ohlson O-score (1980)** | Logit: −1,32 − 0,407·SIZE + 6,03·TL/TA − 1,43·WC/TA + 0,076·CL/CA − 1,72·OENEG − 2,37·NI/TA − 1,83·FFO/TL + 0,285·INTWO − 0,521·CHIN. SIZE es el log del activo deflactado; OENEG = 1 si pasivo > activo; INTWO = 1 si hubo pérdidas los 2 últimos años; CHIN es la variación normalizada del resultado neto | Fue el primer modelo probabilístico (logit) ([J. Accounting Research 18(1)](https://www.jstor.org/stable/2490395)) |
| **Zmijewski (1984)** | Probit: −4,3 − 4,5·ROA + 5,7·TL/TA − 0,004·CA/CL | Pone de relieve el **sesgo de muestreo emparejado**: con la muestra emparejada acierta el 92,5 % de las quiebras y sin ella el 62,5 % ([resumen](https://metricgate.com/docs/zmijewski-bankruptcy-score/)) |
| **Merton / KMV (EDF)** | La deuda es una opción sobre el activo. DD = [ln(V/D) + (μ − σ²/2)T] / (σ√T). En KMV: DD = (V − DP) / (V·σ_V), con DP = **pasivo a corto + ½ del pasivo a largo**. V y σ_V se infieren de la capitalización y la volatilidad de la acción, y **la DD se convierte en EDF con una tabla empírica** (más de 250.000 empresa-año y 4.700 defaults) | Necesita precios de mercado, así que no sirve directamente con privadas ([Crosbie y Bohn, KMV 2002/2003](http://marshallinside.usc.edu/dietrich/KMVModellingDefaultRisk2002.pdf)) |
| **Moody's RiskCalc v3.1** | Unos 10 ratios a partir de 17 partidas, con al menos uno por grupo: rentabilidad, apalancamiento, **cobertura de deuda (cash flow/intereses)**, liquidez (caja/activo, ratio corriente), actividad (existencias/ventas, **proveedores/ventas, Δclientes/ventas**), **crecimiento de ventas** y tamaño. Transformaciones no paramétricas y probit. Tiene dos modos: **FSO** (solo estados financieros, estable) y **CCA** (añade la **DD sectorial** del modelo de cotizadas para capturar el ciclo, PIT) | Está hecho para **privadas**: la señal de mercado entra a nivel de sector, no de empresa. CRD con más de 1,5 M de empresas privadas y 97.000 defaults en el mundo. AR a 1 año del 54,3 % en FSO frente al 49,5 % de la v1.0; el modo CCA suma casi 8 puntos. **El crecimiento es no monótono** (crecer rápido o caer rápido suben la PD). **Con un ratio de cash flow en el modelo, el efecto del tamaño casi desaparece** ([Stein et al.](http://www.rogermstein.com/wp-content/uploads/RiskCalc-v3-1-Model.pdf)) |
| **S&P CreditModel / PD Model Fundamentals** | Ratios financieros más factores macro, sector y país. Logística ridge basada en utilidad esperada máxima y tratamiento robusto de extremos. La salida es un score en letras (tipo "bb+") o una PD | Es "glass box": muestra la contribución y la sensibilidad de cada input ([S&P 2020](https://www.spglobal.com/content/dam/spglobal/mi/en/documents/general/Machine_Learning_and_Credit_Risk_Modelling_November_2020.pdf)) |

---

## 4. Burós, proveedores y registros

| Proveedor o registro | Producto: qué predice y en qué escala | Inputs | Explicación |
|---|---|---|---|
| **Dun & Bradstreet** | **PAYDEX** (1-100): días de pago frente a plazo, **ponderados por importe**, con experiencias de los últimos 24 meses. 100 anticipa, 80 paga en plazo, 70 con **15 días de retraso**, 60 con 22, 50 con 30, 40 con 60, 30 con 90 y 20 con 120 ([ficha](https://www.dnb.co.uk/content/dam/web/data-and-ai/cross/content/paydex-score-factsheet/DnB_Paydex_Score_Factsheet.pdf)) | Programa *Trade Exchange*: los proveedores envían su cartera de clientes (plazos, importes, vencido) | Se lee directamente como días de retraso |
| | **Failure Score** (1.001-1.875, percentil y clase 1-5): probabilidad de pedir protección frente a acreedores o cerrar sin pagarles en 12 meses | % e importe de experiencias de pago satisfactorias, tipo de empresa, **antigüedad**, ratios frente al sector, **pleitos, embargos y juicios**, patrimonio neto ([D&B](https://www.dnb.com/en-us/smb/resources/credit-scores/failure-score.html)) | Clase, percentil y factores clave |
| | **Delinquency Predictor** (101-670, clase 1-5): pago severamente moroso, definido como **≥ 10 % del importe con más de 90 días de retraso**, o quiebra, en 12 meses | Pagos comerciales con **tendencia mes a mes**, datos de la empresa, registros públicos y datos financieros ([D&B](https://www.dnb.com/en-us/smb/resources/credit-scores/delinquency-predictor-score.html)) | |
| **Informa D&B (España y Portugal)** | **Nota Informa** (0-20): cese de actividad o deudas impagadas en 12 meses ([eInforma](https://www.einforma.com/ayuda/informacion-de-empresas/rating-informa)). En Portugal también **Failure Score**, **Delinquency Score** (pagos con más de 90 días de retraso en 12 meses, clases 1-5) y **Paydex**, este con al menos 3 experiencias de proveedores distintos en 12 meses ([Informa D&B PT](https://www.informadb.pt/es/nuestra-informacion/modelos-de-evaluacion-de-riesgo/)) | Cuatro bloques: situación financiera, características (forma jurídica, capital, antigüedad, tamaño, empleados), experiencia y trayectoria (Paydex, incidencias judiciales, reclamaciones administrativas, concursos) y entorno (sector, geografía). **Pesos: 55/16/29 con cuentas y 40/60 sin cuentas.** El RAI y la morosidad bancaria se valoran **en relación con los fondos propios** ([eInforma](https://einforma.com/documentacion/rating-informa)) | Nota más desglose por bloques |
| **Axesor** | Score 0-10 y **PD a 12 meses** (0-100 %), comparada con la del sector ([Axesor](https://www.axesor.es/explicaciones/sociedades-mercantiles/prediccion-calificacion-credito-avanzada.aspx)). Axesor Rating es una agencia registrada en ESMA | **Dos modelos según haya cuentas**: variables contables cuando existen y solo variables "extracontables" (comportamiento comercial, pagos, incidencias) cuando no | Informe con "fundamentos del scoring" (indicadores más influyentes), evolución y límite de crédito recomendado |
| **Experian (EE. UU.)** | **Intelliscore Plus V3** (300-850) | Más de 140 variables: trades, saldos, hábitos de pago, uso de crédito y tendencias; registros públicos (embargos, juicios, quiebras, con su recencia, frecuencia e importe); **años en fichero**, SIC y tamaño. **DBT** = días de retraso ponderados por importe en los trades de los **últimos 3 meses** ([Experian](https://www.experian.com/business-information/credit-risk-management); [glosario](https://www.smartbusinessreports.com/pdp.aspx?pg=HelpReportGlossary)) | Factores clave del score |
| **Creditsafe** | Score y **PD a 12 meses**. Fallo = pago con **más de 90 días de retraso** o insolvencia | Estados financieros, **pagos comerciales (DBT y tendencia)**, datos de la empresa, sector, registros judiciales (CCJ: número, importe y recencia), estructura de grupo y tamaño ([Creditsafe](https://www.creditsafe.com/us/en/more/about/creditsafe-scorecard-update.html)) | Límite de crédito recomendado |
| **Cerved (Italia)** | **Cerved Group Score** | Perfil económico-financiero (CeBi-Score 4 sobre balance), módulo "andamentale" (comportamiento), módulo estructural, eventos negativos, **Payline** (hábitos de pago a proveedores de más de 3 M de empresas; da inmediatez posterior al balance) y consultas recibidas ([Cerved](https://www.cerved.com/risk-intelligence/rischio-di-credito/business-information/payline/)) | Score por componentes |
| **CRIF (Italia)** | **EURISC**: buró positivo y negativo de solicitudes y créditos de particulares y empresas, con más de 500 participantes ([CRIF](https://www.crif.it/business/servizi/information/credito-data-business-crif/informazioni-finanziamenti-crif/)) | Solicitudes, créditos vivos, cuotas y retrasos | |
| **Equifax España** | **ASNEF Empresas**: impagos financieros y **facturas comerciales impagadas** de empresas y autónomos, incluidas deudas con Administraciones Públicas ([Equifax](https://soluciones.equifax.es/empresas/productos/asnef-empresas/)) | | |
| **RAI** | Registro de Aceptaciones Impagadas: **solo personas jurídicas**, impagos **≥ 300 €** en efectos con fuerza ejecutiva (letras aceptadas, pagarés, cheques) ([RAI](https://www.ficherorai.com/RaiWeb/Informacion)) | | |
| **CIRBE (Banco de España)** | No es un fichero de morosos. Recoge el riesgo directo e indirecto por entidad, con dispuesto, disponible, situación (normal, dudoso, fallido), garantías y plazos | Las entidades reciben cada mes el agregado de sus clientes en todo el sistema. Es la fuente de las alertas del ICAS y de variables como "deuda en otros bancos" o "número de entidades" | |
| **Banque de France (analogía)** | Cotización en 22 escalones con horizonte de 3 años. **El default incluye los impagos de efectos comerciales (IPE) acumulados en 6 meses por encima del 10 % de las compras o de 45.000 €**. Gini (tasa de default a 1 año) de 71-77 % entre 2014 y 2024, y de 59-66 % a 3 años ([BdF, *Performances de la cotation*, 2025](https://www.banque-france.fr/system/files/2025-12/FR_Eval_performances_cotation_2025_VClean.pdf)) | Solvencia, liquidez, rentabilidad, autonomía financiera y análisis cualitativo | Matriz de transición publicada |

---

## 5. Cómo se valida y cómo se explica

| Dimensión | Métrica o test | Uso y umbrales |
|---|---|---|
| Discriminación | **AUC**, **Gini = AR = 2·AUC − 1** (curva CAP) y **KS** | Test del BCE: se compara el **AUC actual con el AUC de la validación inicial**. S = (AUC_ini − AUC_act)/s con p = 1 − Φ(S), y se pueden agregar 3 años si hay pocos defaults. Se calcula **sobre los grados de la escala maestra**, no sobre el score continuo ([ECB, *Instructions for reporting the validation results*, 2019](https://www.bankingsupervision.europa.eu/activities/internal_models/shared/pdf/instructions_validation_reporting_credit_risk.en.pdf), § 2.5.4) |
| Calibración | **Test de Jeffreys** por grado y total: el p-valor es la Beta(D+½, N−D+½) evaluada en la PD, con hipótesis nula de que la PD no está infraestimada. También binomial, Hosmer-Lemeshow, semáforo y Brier | BCE § 2.5.3. Hay que tener en cuenta la filosofía de rating (PIT o TTC) (EBA GL/2017/16). [BCBS WP14 (2005)](https://academia.edu/40975366/Basel_Committee_on_Banking_Supervision_Working_Paper_No_14_Studies_on_the_Validation_of_Internal_Rating_Systems) revisa los tests y sus límites con pocos defaults |
| Estabilidad | **Matriz de migración** con MWB (*matrix weighted bandwidth*) de subidas y bajadas; estabilidad de la matriz; **concentración por grado (HHI)**; **PSI** = Σ(A−E)·ln(A/E) | BCE § 2.5.5. PSI: < 0,10 estable, 0,10-0,25 vigilar, > 0,25 cambio relevante (Siddiqi) |
| Proceso | **Tasa de overrides**, ratings desactualizados, *technical defaults* y datos faltantes | BCE § 2.5.2 |
| Backtesting | *Out-of-sample* y **out-of-time** con *walk-forward*: se reentrena hasta el año t y se predice t+1 | RiskCalc lo hace año a año y combina las predicciones. La EBA (LOM 54.c) lo exige para cualquier modelo automatizado |
| Valores de referencia | Gini y AR publicados | Banque de France: Gini del 71-77 % a 1 año y del 59-66 % a 3. RiskCalc FSO: AR del 54 % a 1 año y del 36 % a 5 años (EE. UU.). Société Générale: AUC de 0,80 (cuenta) y 0,84 (combinado) |
| Explicación | *Reason codes* por los puntos perdidos; transformaciones monótonas visibles (RiskCalc); contribuciones de cada input (S&P); factores clave (D&B y Experian); fundamentos del scoring (Axesor) | La EBA pide modelos interpretables si hay que dar explicaciones (LOM 53.d) y cada EWI debe tener umbral, responsable y escalado (LOM 270) |

---

## 6. Qué nos llevamos

### 6.1 Ideas trasladables a un score basado solo en tesorería

1. **Tenemos respaldo regulatorio para nuestras dianas.** Nuestros eventos son, casi literalmente, indicadores de *unlikeliness to pay* y de aumento significativo del riesgo:
   - `impago_nomina`, `impago_ss` e `impago_iva` corresponden al **anejo 9, punto 107.f** ("compromisos vencidos de importe significativo frente a organismos públicos o a empleados").
   - `tension` corresponde al **107.c** ("flujos de efectivo insuficientes para atender las deudas") y a la **EBA/GL/2016/07, párr. 59.a-b**.
   - `caida` corresponde al **94.b / 107.b** y a la **EBA/GL/2020/06, párr. 274.c** (caída de la facturación o del flujo recurrente, incluida la pérdida de un cliente principal).
   - `veto_grupo_en_estres` corresponde al **94.o** (dificultades de entidades del grupo).

   Podemos citarlo en la presentación: *"no nos inventamos la diana: usamos los indicadores de la Circular 4/2017 y de la EBA que se pueden observar en tesorería"*.
2. **Conviene tener dos niveles de alerta, como el regulador.** Una alerta temprana, equivalente a *stage 2* o vigilancia especial (retrasos de más de 30 días, caídas significativas, peor comportamiento de pago). Y una grave, equivalente a *stage 3* o UTP (impagos a empleados o a Hacienda, flujos insuficientes persistentes, embargos). Para la **cura**, un periodo de prueba de **3 meses**, igual que la EBA, lo que coincide con nuestro `cura_3m`. Y un **umbral de materialidad** (absoluto más relativo, del estilo 500 € y 1 %) para que no disparen importes triviales.
3. **Pesos que dependen de la información disponible.** Informa pondera 55/16/29 con cuentas y 40/60 sin ellas. Moody's da más peso al comportamiento cuanto más pequeña es la empresa. Axesor tiene dos modelos según haya balance. **Para nosotros: una variante con ERP y otra sin ERP (el 36 % no tiene facturas), no una única media con huecos.** Encaja con lo que ya pasa: las features de ERP faltan en el 40-70 % de las filas.
4. **Arquitectura bancaria**: módulos (liquidez y caja, comportamiento de pago a proveedores, calidad de cobro de clientes, deuda y financiación, actividad), después **overrides** (nuestros vetos equivalen a los "factores automáticos" del punto 108) y al final **ajuste por grupo** (el apoyo implícito del ICAS). El orden importa: el veto va por encima del score.
5. **Binning monótono con WoE e IV como control de calidad.** Nuestra tabla "¿orden comprobado?" es exactamente el test de monotonía del WoE. El IV da una regla estándar para descartar features (< 0,02). Y la no monotonía conocida del crecimiento (RiskCalc) indica que la **tendencia de actividad** y la **expansión** deberían entrar con forma de U o por tramos, no como "más es mejor". Eso explicaría por qué la feature 1 solo ordena en la mitad baja.
6. **Normalizar por la "vitalidad" de la cuenta.** Yao et al. dividen todo por la **media de entradas mensuales de 24 meses** para neutralizar el tamaño y la dispersión entre bancos. Es la versión profesional de nuestra regla de "ratios o percentiles, nunca importes", y ataca directamente el sesgo de tamaño de la R03.
7. **Horizonte.** Las señales de comportamiento se adelantan unos 12 meses (Norden y Weber), el uso de la línea es alto unos 8 trimestres antes (Moody's) y los predictores de comportamiento "funcionan bien alrededor de un año" (CSES). Nuestro horizonte de 6 meses es prudente. **Merece la pena medir también a 12 meses** para el mensaje de "con cuántos meses de antelación".
8. **Escala maestra y PD por grado** (enlaza con R01 y R02): al menos 7 grados más 1 de evento, con la tasa de evento observada y monótona por grado. Validación con **Jeffreys** por grado y **AUC sobre los grados**, no sobre el score continuo.
9. **Kit de validación bancario aplicable tal cual**:
   - AUC y Gini por evento, con *walk-forward out-of-time* mes a mes;
   - calibración por grado;
   - **matriz de migración con MWB** (responde a "quién mejora" y "quién empeora");
   - **PSI** del score y de cada feature entre meses y entre train y test (la preocupación OOD de la R14);
   - **HHI de la concentración por grado**;
   - **tasa de vetos**, el equivalente a la tasa de overrides.
10. **Explicación por *reason codes*.** Para cada empresa, las 3 features que más puntos le quitan frente a la mediana, más el EWI que se disparó, con fecha y umbral. Es lo que piden la EBA (umbral, responsable, escalado) y lo que dan D&B, Experian y Axesor.
11. **PIT consciente.** Nuestro score es PIT por construcción, porque es mensual y conductual. La EBA pide saberlo y tenerlo en cuenta al hacer backtesting. Las tasas por grado variarán con el ciclo; la nota "con curva" (R01) es en parte una elección de filosofía de rating.

**Qué no es trasladable (o solo con un proxy).**
- Ratios de balance (apalancamiento, fondos propios, reservas, Z, Z', Z'', Ohlson, Zmijewski). Proxy parcial: deuda viva / entradas anualizadas, aunque solo con la **foto final** de `outstanding`.
- Merton y DD, porque no tenemos precios.
- CIRBE y burós (deuda en otros bancos, RAI, ASNEF).
- El módulo cualitativo.

Lo más cercano a la CIRBE que tenemos es `debt_products` más `banking_products` (número de bancos y altas recientes).

### 6.2 Señales EWS bancarias que podemos calcular con nuestros datos

Estado: **ya** (está en el score o en el panel), **cola** (idea ya en cola), **nueva** (no la tenemos) y **mejora** (tenemos una versión más débil).

Los recuentos de empresas por palabra clave salen de un barrido rápido de `transactions.description` (regex sin validar, sin comprobar causalidad ni signos). Hay que revisarlos antes de usarlos.

| # | Señal EWS | Fuente que la respalda | Cómo calcularla con nuestros datos | Estado |
|---|---|---|---|---|
| 1 | **Uso de la póliza**: nivel, tendencia y meses por encima del 90 % | Norden y Weber; Moody's (76 % dos años antes frente al 52 % de las sanas); Jiménez et al. (CIRBE); BCE anejo 4 | `lc_drawn/lc_limit`: nivel, pendiente a 6 meses y nº de meses por encima del 90 % en 12. Hoy pesa 0,01 y falta en el 86 % de las filas: es una señal fuerte limitada por la cobertura | mejora |
| 2 | **Descubiertos y excedidos**: meses con descubierto y días con saldo por debajo de −límite | BCE anejo 4 ("number of months with any overdraft/overdraft exceeded"); Yao (los excedidos son las variables nº 1-3) | Saldo diario reconstruido: días con saldo < 0, días por debajo del disponible de la póliza y meses con algún descubierto en 12. Refuerzo textual: **"INTERES.DESCUBIERTO", "GASTOS/RECLAMACIÓN DE DESCUBIERTO"** (unas 132 empresas) | cola y nueva (el texto) |
| 3 | **Recibos propios devueltos o impagados** (no hay saldo para un adeudo) | BCE anejo 4 ("unpaid cheques"); es el análogo del RAI | `category = payment_refund` más texto **"IMPAGADO DÉBITOS…SEPA", "GASTOS IMPAG. DÉBITOS", "RECOBRO DE COMISIONES IMPAGADAS"**: número en 3 y en 12 meses. Hay que separarlo de los recibos devueltos **por clientes** (`collection_refund`) | nueva |
| 4 | **Embargos y diligencias de AEAT/TGSS** | Anejo 9, 108.a (reclamación judicial, factor automático); EBA/GL/2016/07, párr. 60; LOM 274.n; D&B y Experian (embargos y juicios) | Texto **"EMBARGO", "DOC. DE INGRESOS ASOCIADOS EMBARGOS", "DILIGENCIA"** (unas 164 empresas; sobre todo `category = tax`). Indicador de "embargo en 12 meses" y su recencia. **Candidato a veto o evento UTP** | nueva |
| 5 | **Aplazamientos con Hacienda o Seguridad Social** | Anejo 9, 107.f (compromisos vencidos con organismos públicos); señal de *forbearance* (EBA/GL/2016/07, párr. 49-53) | Texto **"APLAZAMIENTOS", "CARGO APLAZAMIENTOS VENCIDOS", "TGSS. APLAZAMIENTOS"** (unas 76 empresas): aplazamiento activo y aplazamiento vencido | nueva |
| 6 | Nómina, Seguridad Social, IVA o cuota omitidos | Anejo 9, 107.f; EBA/GL/2016/07, 59.a | Ya son eventos y vetos | ya |
| 7 | **Caída de la facturación o del flujo recurrente** | LOM 274.c; anejo 9, 94.b | `oper_in` de 3 meses frente a 12; interanual; persistencia | ya |
| 8 | **Volatilidad de las entradas** (CV mensual) | Yao var24 (7.ª en importancia y significativa en la logística) | sd/media de `oper_in` o `inflow` en 12 meses. Hoy usamos la semidesviación del flujo neto; el CV de las **entradas** es otra señal | nueva |
| 9 | **Saldo mínimo, medio y máximo** normalizados por la media de entradas; cambios a 12 y 24 meses | Yao var1-7 y var33-34; FinRegLab (saldo y episodios de saldo bajo) | Saldo diario reconstruido / media de `inflow` de 24 meses | cola (caja mínima intramensual) y mejora (normalización) |
| 10 | **Entradas / salidas** y su cambio interanual | Yao var20-21 | `inflow/outflow`, Δ a 12 meses | mejora de la #17 |
| 11 | **Coste de la financiación**: intereses / deuda | ICAS ("coste del endeudamiento"); LOM 274.h (peores condiciones) | `interest_charge` / (`lc_drawn` + deuda viva estimada); tendencia a 6 meses; peso de las comisiones | nueva |
| 12 | **Cobertura de cash flow**: (cobros − pagos operativos) / (intereses + cuotas) | ICAS ("cash flow coverage"); RiskCalc (cash flow/intereses); LOM anejo 3 (DSCR) | Con `oper_in`, `payment`, `salary`, `tax`, `debt_repayment` e `interest_charge`. Nuestra "carga de deuda" (#11) no ordena (R16); probar solo con intereses y por tramos | mejora |
| 13 | **DBT ponderado por importe y tipo PAYDEX** en proveedores | D&B, Experian (DBT de 3 meses), Creditsafe | Por empresa y mes: Σ(importe × días de retraso) / Σ importe, sobre facturas AP pagadas o vencidas. Mapeo a PAYDEX (80 en plazo, 70 = 15 días, 50 = 30…) y tramos de 15, 30, 60, 90 y 120 días. Hoy `late_share` cuenta facturas con más de 15 días sin ponderar | mejora |
| 14 | **"Severamente moroso" = ≥ 10 % del importe AP con más de 90 días** | Definición del Delinquency Predictor de D&B | `overdue_90_ap` / total AP abierto ≥ 10 %. Sirve como feature y **como evento adicional para las empresas con ERP** | nueva |
| 15 | **Antigüedad de clientes** (*aged debtor report*) por tramos | LOM anejo 2.B.4 | Tramos de vencido AR: 0-30, 31-60, 61-90 y más de 90 días / cobros mensuales | cola y mejora de la #13 |
| 16 | **Pérdida del cliente principal** | LOM 274.c; BCE anejo 4 (noticias negativas de clientes o proveedores principales) | Indicador de "el cliente top-1 de hace 3-12 meses ya no factura" y su peso | mejora de la #3 |
| 17 | **Reducción del disponible y recorte de líneas** | BCE anejo 4 | Solo tenemos la foto final de `granted` y `available`. Solo se puede aproximar si una póliza deja de aparecer. **No es fiable** | no calculable |
| 18 | **Saturación de factoring o confirming** y aparición de financiación nueva | BCE anejo 4 ("continued excess in commercial paper discount"); LOM 274.h | Primera aparición de factoring o confirming en `debt_products` o en las transacciones; uso / límite si existe | nueva (baja cobertura) |
| 19 | **Relaciones bancarias**: número de bancos y altas de cuentas en bancos nuevos | Jiménez et al. (número de relaciones); BCE anejo 4 ("more debt in other banks") | `banking_products` por `bank_name` y `created_at`: bancos distintos y altas en 6 meses | nueva |
| 20 | **Contagio de grupo** | Anejo 9, 94.o; ICAS (apoyo implícito) | Score o tensión mediana del grupo; dependencia de fondos intragrupo | ya (veto) y mejora |
| 21 | **Crecimiento extremo en las dos colas** | RiskCalc (el crecimiento no es monótono) | Crecimiento de `oper_in` de 12 meses en tramos, con penalización en ambas colas | mejora de la #1 |
| 22 | **Tamaño y antigüedad** como contexto | RiskCalc (el tamaño pierde peso con cash flow en el modelo); D&B y Informa (antigüedad) | log(media de entradas en EUR) y meses desde la primera transacción o `created_at` | ya (contexto) |
| 23 | **Pagar antes de plazo** | PAYDEX premia anticipar (100) | Nuestro `ap_early_3` lo leía como sacar caja antes de tiempo. **Los burós lo leen como fortaleza**: validar el signo por tramos antes de usarlo | revisar |

### 6.3 Siguientes pasos sugeridos (por orden de retorno esperado)

1. Crear las señales textuales 3, 4 y 5 (embargos, recibos propios impagados y aplazamientos con AEAT/TGSS) y medir su tasa de evento a 6 y 12 meses. Pueden ser **vetos o eventos con base regulatoria directa** (anejo 9, 107.f y 108.a).
2. Mejorar la 1 y la 2 (uso de la póliza, meses en descubierto y días con saldo negativo). Son la señal más documentada en la literatura.
3. Crear el DBT ponderado por importe y la regla del ≥ 10 % con más de 90 días (13 y 14) en la variante con ERP.
4. Separar el modelo con ERP del modelo sin ERP y comparar su AUC con la media actual.
5. Añadir al informe de validación el test de Jeffreys por grado, la matriz de migración con MWB, el PSI y la tasa de vetos.
