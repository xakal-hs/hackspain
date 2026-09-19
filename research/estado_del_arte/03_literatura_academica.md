# 03 · Literatura académica y metodológica

Revisión de la literatura para el score de salud financiera de pymes a partir del rastro de tesorería (HackSpain 2026, reto de Embat). Seis bloques: (1) ML para default de pymes, (2) datos transaccionales bancarios y de pagos, (3) comportamiento de pago comercial, (4) trayectoria y dinámica, (5) etiquetas sin default observado y (6) validación y explicabilidad. Al final, **Qué nos llevamos** para X-Ray.

**Cómo leer las cifras.** Las marcadas con † las he sacado del texto completo del paper (tablas o cuerpo). Las demás vienen del abstract o de la página del editor. Cuando un dato no está verificado lo digo.

---

## 0. En diez líneas

1. **La información pesa más que el algoritmo.** Con ratios financieros, el GBM gana unos 2-3 puntos de AUC a la logística. Con datos de comportamiento, la ventaja baja a ~1 punto, y con muestras pequeñas desaparece (Moscatelli et al., 2020†). Añadir datos de comportamiento sube ~10 puntos a todos los modelos.
2. **La cuenta corriente adelanta el default unos 12 meses.** El uso de la póliza, los excesos de límite y la caída de cobros se mueven de forma anormal alrededor de 12 meses antes. Cada señal tiene su propia antelación: excesos desde −18 meses, cobros/límite de −18 a −12 y amplitud de la cuenta desde −5 (Norden & Weber, 2010†).
3. **Los datos de cuenta solos igualan o superan a los ratios contables** (AUC ~0,80 frente a 0,76), y juntos llegan a 0,84 (Yao et al., 2017†). Normalizan por los cobros mensuales medios de la propia cuenta, igual que nuestras features invariantes a escala.
4. **El retraso en los pagos comerciales es de los mejores predictores no financieros** (Back, 2005; Wilson et al., 2000; Altman, Sabato & Wilson, 2010†: AUC de 0,71 a 0,78). El crédito comercial es **financiación de último recurso** (Petersen & Rajan, 1997), pero también un **seguro de liquidez ante shocks transitorios** (Cuñat, 2007). Estirar a proveedores es, por tanto, una señal ambigua.
5. **Los modelos de riesgo modernos son hazards en tiempo discreto** (Shumway, 2001): una logística sobre el panel empresa-periodo con covariables que cambian en el tiempo. Rinden mejor que el Cox continuo con datos censurados por intervalos (Gupta et al., 2018).
6. **Las calificaciones tienen momentum:** quien acaba de bajar tiene más probabilidad de volver a bajar (Lando & Skødeberg, 2002). Las agencias consiguen estabilidad con una política de migración: solo mueven la nota si el desvío supera un umbral, y la mueven solo en parte (Altman & Rijken, 2004). Es justo lo que necesitamos para el parpadeo.
7. **La separación bache/caída ya existe en series temporales:** *temporary change* frente a *level shift* (Chen & Liu, 1993) y la «duración de la racha» del BOCPD (Adams & MacKay, 2007). En regulación bancaria es el periodo de prueba de 3 meses para salir de default (EBA/GL/2016/07).
8. **Sin etiqueta, la literatura usa proxies de distress** (EBITDA < gastos financieros dos años seguidos, 90 días de mora con umbral de materialidad). El peligro es la circularidad: si el evento se define con las mismas variables que las features, el AUC sube por construcción (Kaufman et al., 2012; Balcaen & Ooghe, 2006).
9. **Hay que validar por bloques:** fuera de grupo **y** fuera de tiempo, con walk-forward (Stein, 2007; Roberts et al., 2017). Hay que medir la calibración (Brier, curvas) además del AUC, y el umbral de PSI depende del tamaño de muestra (Yurdakul & Naranjo).
10. **Las restricciones monótonas en GBM cuestan entre 0 y ~3 % de AUC** (menos cuanto mayor la muestra). Un modelo interpretable puede igualar a la caja negra (Chen, Rudin et al., FICO 2018). Con datos sintéticos, las explicaciones SHAP se pueden **comprobar contra la verdad conocida** (Alonso & Carbó, 2022).

---

## 1. Predicción de default de pymes con ML

### 1.1 Revisiones sistemáticas

| Revisión | Alcance | Conclusión útil |
|---|---|---|
| Ciampi, Giannozzi, Marzi & Altman (2021), *Scientometrics* 126. [PMC7844786](https://pmc.ncbi.nlm.nih.gov/articles/PMC7844786/) | Bibliometría de la literatura sobre default de pymes; 5 corrientes | Entre las variables financieras, el **apalancamiento** discrimina más que la liquidez y la rentabilidad. Crecen las no financieras: comportamiento de pago, gobierno corporativo, relación banco-empresa. ML y big data, poco explorados en pymes |
| Cheraghali & Molnár (2023), *J. Small Business Management*. [doi:10.1080/00472778.2023.2277426](https://www.tandfonline.com/doi/full/10.1080/00472778.2023.2277426) | 145 estudios (1972-2023) | Más de 1.200 predictores, 80 métodos de estimación y 54 técnicas de selección de variables. Mucha heterogeneidad y poca validación comparable |
| Cheraghali et al. (2024), *JSBM* 63(4). [doi:10.1080/00472778.2024.2390500](https://www.tandfonline.com/doi/full/10.1080/00472778.2024.2390500) | Más de 6.100 combinaciones modelo × submuestra, pymes de EE. UU. | **LightGBM es el mejor fuera de muestra, seguido de XGBoost.** Los dos rinden más con su selección de variables interna y **sin rebalanceo**. La logística mejora mucho con buena selección de variables y rebalanceo |
| Dasilas & Rigani (2024), *Expert Systems with Applications* 255, 124761. [doi:10.1016/j.eswa.2024.124761](https://dl.acm.org/doi/10.1016/j.eswa.2024.124761) | Unos 200 estudios empíricos (2012-2023), PRISMA | Random forest y gradient boosting son los que más veces quedan primeros; los modelos híbridos se presentan como más precisos y robustos |

### 1.2 ¿Cuánto gana el ML de verdad?

| Estudio | Datos | Logística | Mejor ML | Ganancia |
|---|---|---|---|---|
| Moscatelli, Parlapiano, Narizzano & Viggiano (2020), *ESWA* 161. [doi:10.1016/j.eswa.2020.113567](https://www.sciencedirect.com/science/article/abs/pii/S0957417420303912) · [WP Banca d'Italia 1256](https://www.bancaditalia.it/pubblicazioni/temi-discussione/2019/2019-1256/en_Tema_1256.pdf) | ~300.000 sociedades italianas no financieras, 2011-17, PD a 1 año; out-of-sample por año | Solo ratios: AUC 72,3-73,9 %† | RF/GBT: 73,9-77,3 %† | **+2,6 pp**† |
| (mismo) | + 8 indicadores de comportamiento de la Centrale dei Rischi (uso dispuesto/concedido, morosidad), con 2 meses de retardo | 81,6-84,0 %† | GBT 82,7-84,7 %† | **~+1 pp**†. Añadir comportamiento: **~+10 pp** a todos los modelos† |
| (mismo) | 10 % de la muestra | 80,8-82,9 %† | 80,8-83,9 %† | **≈ 0**† (en algún año gana la logística) |
| Barboza, Kimura & Altman (2017), *ESWA* 83. [doi:10.1016/j.eswa.2017.04.006](https://dl.acm.org/doi/10.1016/j.eswa.2017.04.006) | ~10.000 empresa-año de EE. UU.; train 1985-2005, test 2006-13 (out-of-time) | — | Bagging, boosting, RF | ~+10 pp de AUC (según la reseña de Moscatelli). Añaden variables de **crecimiento** a las de Altman |
| Fuster et al. (2018/2022), hipotecas EE. UU. (citado por Moscatelli†) | — | — | RF | +1,2 pp de AUC |
| Gunnarsson, vanden Broucke, Baesens, Óskarsdóttir & Lemahieu (2021), *EJOR* 295. [doi:10.1016/j.ejor.2021.03.006](https://www.sciencedirect.com/science/article/abs/pii/S037722172100196X) | Varios datasets reales de scoring | — | XGBoost | **El deep learning no compensa**; XGBoost es la opción preferente |
| Lessmann, Baesens, Seow & Thomas (2015), *EJOR* 247. [doi:10.1016/j.ejor.2015.05.030](https://www.sciencedirect.com/science/article/abs/pii/S0377221715004208) | 41 clasificadores, 8 datasets | Referencia competitiva | Ensembles heterogéneos, RF | Los ensembles ganan con regularidad. La logística sigue siendo la referencia que hay que batir |
| Alonso Robisco & Carbó (2022), *Financial Innovation* 8. [doi:10.1186/s40854-022-00366-1](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-022-00366-1) · [BdE DT 2032](https://www.bde.es/wbe/en/publicaciones/analisis-economico-investigacion/documentos-trabajo/machine-learning-credit-risk-measuring-dilemma-between-prediction-and-supervisory-cost.html) | Banco de España | — | — | Ganancias de hasta el 20 % en clasificación, frente a **13 fuentes de coste supervisor** (validación IRB). Proponen ajustar el rendimiento por riesgo de modelo |
| Fantazzini & Figini (2009), pymes alemanas (citado por Moscatelli†) | — | Gana fuera de muestra | RF | **La logística supera al RF fuera de muestra**: el RF sobreajusta |

**Lectura.** Hand (2006), «Classifier technology and the illusion of progress», *Statistical Science* 21(1) ([doi:10.1214/088342306000000060](https://projecteuclid.org/journals/statistical-science/volume-21/issue-1/Classifier-Technology-and-the-Illusion-of-Progress/10.1214/088342306000000060.full)), ya lo advertía: las diferencias entre clasificadores suelen ser menores que la incertidumbre por no estacionariedad, definición del objetivo y muestreo. Moscatelli lo confirma con datos a gran escala. **Cuando la información es buena, la logística roza el techo alcanzable.** Donde el ML sí gana: con variables **no lineales o no monótonas**. En Moscatelli†, el **crecimiento de ventas** tiene forma de U (crecer poco y crecer mucho son malas señales), y la rotación de proveedores y la de clientes pesan más en los árboles que en la logística.

### 1.3 Familias de features que importan

| Familia | Evidencia | Nota |
|---|---|---|
| Apalancamiento / solvencia | La más discriminante en pymes (Ciampi et al., 2021). Fondos propios/activo, lineal con la tasa de default (Moscatelli†) | Sin balance, lo más cercano es la deuda o el servicio de deuda frente a los cobros |
| Liquidez / caja | Campbell, Hilscher & Szilagyi (2008), *J. Finance* 63(6) ([doi:10.1111/j.1540-6261.2008.01416.x](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2008.01416.x)): menos caja → más quiebra | Nuestra `runway` |
| Rentabilidad | Principal contribuyente en las fases finales del fracaso (Lukason & Laitinen, 2019) | Proxy: margen de caja operativo |
| Volatilidad | Campbell et al. (2008): la volatilidad pasada predice quiebra. Yao et al. (2017†): la desviación típica de los cobros mensuales mide la inestabilidad de los ingresos | Nuestras `payroll_cv` y `net_vol` |
| Tamaño | No lineal (Altman, Sabato & Wilson, 2010†) | Cuidado con el sesgo de tamaño (nuestra R03) |
| Edad | Relación negativa con el fracaso; el tramo de 3-9 años es el de más riesgo (ASW 2010†) | No la tenemos salvo por el inicio de la actividad |
| Comportamiento de pago / crédito | **+10 pp de AUC** (Moscatelli†; Bacham & Zhao 2017, según Moscatelli). Retrasos de pago, *County Court Judgments* (CCJ, sentencias judiciales por impago) y presentación tardía de cuentas: de 0,71 a 0,78 en medianas, de 0,74 a 0,80 en pequeñas y de 0,64 a 0,76 en micro (ASW 2010†, 5,8 millones de cuentas y 66.000 quiebras en el Reino Unido, 2000-07) | Es la familia en la que nuestros datos son ricos |
| Crecimiento / dinámica | Barboza et al. (2017) añaden variables de crecimiento; Campbell et al. (2008) usan medias móviles ponderadas | Véase §4 |

---

## 2. Datos transaccionales bancarios y de pagos

### 2.1 Estudios clave

| Estudio | Datos | Qué encuentran | Antelación |
|---|---|---|---|
| **Norden & Weber (2010)**, *Review of Financial Studies* 23(10):3665-99. [doi:10.1093/rfs/hhq061](https://academic.oup.com/rfs/article-abstract/23/10/3665/1566409) · [WP](https://madoc.bib.uni-mannheim.de/2983/1/SSRN_id1101548_pub137.pdf) | Banco universal alemán, 2002-06, más de 3 millones de observaciones cuenta-mes, 67.215 prestatarios, **1.009 defaults**† | **Uso de la póliza** (saldo/límite): los que acaban en default parten del 60 % a −36 meses y llegan a ~100 % en el default; la subida principal va de −36 a −16 y hay un acelerón en los últimos 9 meses†. **Excesos de límite acumulados**: la mediana pasa de 5 a 20, con más pendiente desde −18†. **Cobros/límite y pagos/límite**: caen de golpe entre −18 y −12†. **Amplitud de la cuenta** (máximo − mínimo): cae a partir de −5†. En pequeñas empresas, el R² de McFadden pasa de **1,2 % a 7,0 %** al añadir la actividad de cuenta; en grandes, de 9,2 % a 9,7 %†. Las alertas tempranas acaban en diferenciales más altos, recortes de límite y fallidos | **~12 meses** en conjunto; cada señal escalonada (−18, −12, −9, −5) |
| **Mester, Nakamura & Renault (2007)**, *RFS* 20(3):529-56. [OUP](https://academic.oup.com/rfs/article-abstract/20/3/529/1563872) · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=606681) | Banco canadiense, pequeñas empresas, datos mensuales (1988-92) | Los cambios mensuales en cuentas a cobrar **se ven en la cuenta corriente**. Disponer por encima del colateral predice rebajas de rating y saneamientos, y el banco intensifica la vigilancia | Meses |
| **Jiménez, Lopez & Saurina (2009)**, *RFS* 22(12):5069-98. [doi:10.1093/rfs/hhp061](https://academic.oup.com/rfs/article-abstract/22/12/5069/1577140) · [BdE DT 0821](https://ideas.repec.org/p/bde/wpaper/0821.html) | **CIRBE (España)**, 1984-2005 | El uso de la línea **sube a medida que la empresa se acerca al default**, sobre todo en los 12 meses previos (según Norden & Weber†). **Paradoja:** las empresas con más riesgo *ex ante* usan *menos* su línea. Efecto antigüedad: el uso baja ~10 % por año de vida de la línea | ~12 meses |
| **Yao, Levy-Chapira & Margaryan (2017)**, [arXiv:1707.00757](https://arxiv.org/abs/1707.00757) | Clientes empresa de un gran banco francés. Default = quiebra al año siguiente; features de los 24 meses previos† | AUC con boosting: **cuenta sola ~0,80**; ratios financieros + cuestionario ~0,76; **juntos 0,84**†. Con 11 variables de cada lado, 0,79 frente a 0,76†. Las variables definidas **con intuición económica** (diferencias a 12/24 meses, nivel, desviación típica) ganan a las generadas automáticamente por combinación aritmética†. **Normalizan por los cobros mensuales medios de la cuenta en 2 años**, porque el tamaño de la cuenta no es el de la empresa (multibanco)† | 12 meses |
| **Kou, Xu, Peng, Shen, Chen, Chang & Kou (2021)**, *Decision Support Systems* 140. [doi:10.1016/j.dss.2020.113429](https://www.sciencedirect.com/science/article/pii/S0167923620301846) | Pymes chinas (alianza de bancos comerciales de Shandong); **sin datos contables** | Las variables de transacciones y de **red de pagos** (quién paga a quién) mejoran la predicción de quiebra, tanto en test offline como online | — |
| **Tobback & Martens (2019)**, *JRSS A* 182(4). [doi:10.1111/rssa.12469](https://doi.org/10.1111/rssa.12469) | 183 millones de transacciones de 2,6 millones de clientes (particulares) | Los datos de pago de grano fino mejoran el AUC de forma significativa y se mantienen interpretables | — |
| **Gambacorta, Huang, Qiu & Wang (2019/2024)**, [BIS WP 834](https://www.bis.org/publ/work834.pdf); *J. Financial Stability* 73 | Fintech china, datos a nivel de transacción | El ML con datos no tradicionales predice mejor pérdidas y defaults **cuando hay un shock** de oferta de crédito | — |
| **Ghosh, Vallee & Zeng (2026)**, *J. Finance* 81(2). [doi:10.1111/jofi.70003](https://onlinelibrary.wiley.com/doi/10.1111/jofi.70003) | Prestamista fintech indio para pequeñas empresas | Pagar con medios electrónicos predice **menos default**. El efecto es mayor con las tecnologías más precisas y **en las salidas de caja** («colateral digital») | — |
| **FinRegLab (2019)**, [informe pequeña empresa](https://finreglab.org/wp-content/uploads/2023/12/FinRegLab_2019-09-06_Research-Report_Small-Business-Spotlight_The-Use-of-Cash-Flow-Data-in-Underwriting-Credit.pdf) | 6 prestamistas no bancarios; análisis independiente de Charles River Associates | Las variables de flujo de caja predicen el riesgo en todas las poblaciones y productos, y complementan al bureau | — |
| **Tobback, Bellotti, Moeyersoms, Stankova & Martens (2017)**, *DSS* 102. [doi:10.1016/j.dss.2017.07.004](https://www.sciencedirect.com/science/article/abs/pii/S0167923617301380) | Pymes belgas; red de administradores comunes | Los datos relacionales detectan las empresas más arriesgadas y complementan a los financieros | — |

### 2.2 Señales transaccionales y su antelación

| Señal | Cómo se construye | Antelación | Fuente |
|---|---|---|---|
| Uso de la póliza | saldo dispuesto / límite, nivel y Δ12m | Deriva de −36 a −16; acelera en −9 | Norden & Weber†; Jiménez et al. |
| Excesos de límite acumulados | nº de meses con mínimo < límite; Δ12m | Más pendiente desde −18 | N&W†; Mester et al. |
| Caída de cobros | cobros / límite (o / cobros medios propios) | Caída brusca de −18 a −12 | N&W†; Yao† |
| Amplitud de la cuenta | máximo − mínimo del saldo en el mes | Colapsa desde −5 | N&W† |
| Inestabilidad de cobros | desviación típica de los cobros mensuales | 12 meses | Yao† |
| Disponer por encima del colateral / cobertura | dispuesto frente a cuentas a cobrar | Meses | Mester et al. |
| Red de pagos | concentración y calidad de contrapartes | — | Kou et al. |

**Lectura.** Las señales aparecen **escalonadas**: primero la estructura (uso y excesos, a 12-36 meses), luego los flujos (cobros, a 12-18 meses) y al final la actividad de la cuenta (amplitud, a ~5 meses). Un horizonte único de 6 meses mezcla señales lentas y rápidas.

**Datos de facturación electrónica (SII, SdI).** No he encontrado papers publicados que usen el SII español ni el SdI italiano para predecir default de empresas. Lo más parecido: invoice lending y factoring (Sigrist & Hirnschall, §3) y los datos de pagos comerciales de la Banque de France (CIPE, §3). Es un hueco que podemos contar como novedad.

---

## 3. Comportamiento de pago comercial

| Estudio | Hallazgo |
|---|---|
| **Petersen & Rajan (1997)**, *RFS* 10(3):661-91. [doi:10.1093/rfs/10.3.661](https://academic.oup.com/rfs/article-abstract/10/3/661/1635350) | Las empresas usan **más crédito comercial cuando el bancario no está disponible**. El crédito comercial a medio plazo es **financiación de último recurso**: con condiciones «2/10 neto 30», renunciar al descuento cuesta más del 40 % anual. El proveedor presta porque obtiene información barata del cliente y puede recuperar la mercancía |
| **Cuñat (2007)**, *RFS* 20(2):491-527. [doi:10.1093/rfs/hhl015](https://academic.oup.com/rfs/article-abstract/20/2/491/1573565) | El proveedor actúa como **asegurador de liquidez ante shocks transitorios** para proteger la relación. El alto tipo implícito incluye primas de seguro y de default |
| **Molina & Preve (2012)**, *Financial Management* 41(1). [RG](https://www.researchgate.net/publication/259480155_An_Empirical_Analysis_of_the_Effect_of_Financial_Distress_on_Trade_Credit) | Las empresas en distress **aumentan sus cuentas a pagar**: estiran a proveedores. En su trabajo de 2009 (*FM* 38(3)), las empresas en distress **reducen sus cuentas a cobrar** (cobran antes o venden menos a crédito), lo que les hace perder ventas y agrava el coste del distress |
| **Boissay & Gropp (2013)**, *Review of Finance* 17(6):1853-94. [doi:10.1093/rof/rfs045](https://academic.oup.com/rof/article-abstract/17/6/1853/1591419) | Con datos franceses: las empresas con restricción de crédito que sufren un shock de liquidez (un cliente que no paga) **dejan de pagar a sus proveedores**, trasladándoles una parte considerable del shock. La cadena se detiene al llegar a una empresa sin restricción |
| **Jacobson & von Schedvin (2015)**, *Econometrica* 83(4). [doi:10.3982/ECTA12148](https://onlinelibrary.wiley.com/doi/abs/10.3982/ECTA12148) | Suecia: el riesgo de quiebra del proveedor **crece con la pérdida sufrida por la quiebra de sus clientes** (pérdida de crédito más caída de demanda). Una parte relevante de las quiebras agregadas se explica por esta propagación |
| **González & Dietsch (2022)**, [Bulletin de la Banque de France 227/8](https://www.banque-france.fr/en/publications-and-statistics/publications/do-late-customer-payments-impact-companies-probability-default) | Que los clientes paguen tarde sube la PD un **25 %**, y un **40 %** si el retraso pasa de 30 días. Una estructura financiera deteriorada la multiplica **por 4 como mínimo**. Solo 8 de cada 100 quiebras están materialmente expuestas: los retrasos de clientes son un factor **secundario** frente a la debilidad propia |
| **Back (2005)**, *European Accounting Review* 14(4):839-68. [doi:10.1080/09638180500141339](https://www.tandfonline.com/doi/full/10.1080/09638180500141339) | Pymes finlandesas: un modelo **solo con variables no financieras** (historial de pagos, perfil de los gestores) clasifica **mejor** que el de ratios, sobre todo a las quebradas y a las que tienen retrasos. **El número de retrasos de pago es la variable más importante** |
| **Wilson, Summers & Hope (2000)**, *Int. J. Economics of Business* 7(3):333-46. [RG](https://www.researchgate.net/publication/24081545_Using_Payment_Behaviour_Data_for_Credit_Risk_Modelling) | El comportamiento de pago pasado predice el comportamiento de pago futuro **y** mejora de forma incremental los modelos de fracaso con datos contables |
| **Altman, Sabato & Wilson (2010)**, *J. Credit Risk* 6(2):95-127. [PDF](https://eprints.whiterose.ac.uk/id/eprint/219715/1/SME%20Risk%20Altman-Sabbato-Wilson.pdf) | Las sentencias por impago (CCJ, en número e importe), la presentación tardía de cuentas y la edad suben el AUC entre 6 y 12 puntos según el tamaño (§1.3)†. En las micro, las CCJ predicen mejor que en las más grandes† |
| **Hirshleifer, Li, Lourie & Ruchti (2019)**, [NBER w25553](https://www.nber.org/papers/w25553) | Pagar tarde a proveedores anticipa **peor rendimiento futuro y más riesgo de default**, sobre todo en empresas con poca liquidez. El mercado no incorpora del todo esta información |
| **Sigrist & Hirnschall (2019)**, «Grabit», *J. Banking & Finance* 102:177-92. [arXiv:1711.08695](https://arxiv.org/abs/1711.08695) | Pymes suizas que adelantan el cobro de sus facturas (Advanon). Un préstamo con más de 60 días de retraso es default; el resto registra **los días de retraso**†. Modelan los días de retraso como **variable latente censurada** (Tobit con gradient boosting), con censura en 0 y en 60. El AUROC es **significativamente mayor** que el de los clasificadores binarios (DeLong, 5 %)†. SMOTE y el sobremuestreo **no mejoran**† |
| Moscatelli et al. (2020)† | La **rotación de proveedores y de clientes** tiene relación no lineal con el default y pesa más en los árboles |

**Lectura para nosotros.**
- **El DPO sube por dos motivos opuestos.** Puede ser poder de negociación (empresa grande o sana) o *stretching* (empresa en apuros). Lo que distingue un caso del otro es el **contexto**: si la subida viene con cobros a la baja y más uso de la póliza, es distress (Molina & Preve; Norden & Weber). Si viene con cobros estables, es gestión.
- **El atraso sobre el vencimiento informa más que el nivel de DPO.** Días de retraso respecto a la fecha de vencimiento, porcentaje de facturas recibidas vencidas y aún pendientes: lo que Back y Wilson miden con «retrasos». El DPO mezcla condiciones pactadas con impago.
- **Un estiramiento puntual puede ser un bache** que el proveedor financia (Cuñat). El que se prolonga y va a más es deterioro. De nuevo, la clave es la persistencia.
- **Los retrasos de clientes son un factor secundario** (González & Dietsch): suben la PD un 25-40 %, pero la estructura propia la multiplica por 4 o más. Nuestro DSO debe pesar menos que la liquidez propia.
- **La severidad es un objetivo mejor que el evento binario** (Grabit): días de retraso en nómina, IVA o proveedores como variable continua censurada.

---

## 4. Trayectoria y dinámica

### 4.1 Hazard y supervivencia

| Estudio | Aportación |
|---|---|
| **Shumway (2001)**, *J. Business* 74(1):101-24. [JSTOR 10.1086/209665](https://www.jstor.org/stable/10.1086/209665) | Los modelos estáticos de un solo periodo son **inconsistentes**. Un **hazard en tiempo discreto** equivale a una logística sobre el panel empresa-periodo con covariables que cambian, siempre que se corrijan los estadísticos por la dependencia entre observaciones de una misma empresa. Pronostica mejor fuera de muestra |
| **Campbell, Hilscher & Szilagyi (2008)**, *J. Finance* 63(6) | Logit dinámico con **medias ponderadas geométricamente** de la rentabilidad y de la rentabilidad bursátil pasadas (el peso se reduce a la mitad cada trimestre). A horizontes más largos ganan peso las características **más persistentes** (tamaño, volatilidad) y pierden peso las transitorias |
| **Duffie, Saita & Wang (2007)**, *J. Financial Economics* 83(3). [doi:10.1016/j.jfineco.2005.10.011](https://doi.org/10.1016/j.jfineco.2005.10.011) | **Estructura temporal de la PD** (1-5 años) modelando también la dinámica de las covariables. La PD a varios horizontes sale de un modelo coherente, no de modelos independientes |
| **Gupta, Gregoriou & Ebrahimi (2018)**, *Quantitative Finance* 18(3):437-66. [doi:10.1080/14697688.2017.1307514](https://www.tandfonline.com/doi/abs/10.1080/14697688.2017.1307514) | En pymes de EE. UU., **el hazard discreto (logit o clog-log) supera al Cox continuo** cuando los datos están censurados por intervalos |
| **Dirick, Claeskens & Baesens (2017)**, *JORS* 68(6):652-65. [doi:10.1057/s41274-016-0128-9](https://link.springer.com/article/10.1057/s41274-016-0128-9) | Benchmark de supervivencia en 10 datasets de crédito: **Cox con splines** y **modelos de cura** (una parte de la población nunca llega al evento) rinden bien |
| Bellotti & Crook (2013), *Int. J. Forecasting* 29(4). [doi:10.1016/j.ijforecast.2013.04.003](https://doi.org/10.1016/j.ijforecast.2013.04.003) | Modelos dinámicos con covariables de comportamiento que cambian cada periodo; mejoran la predicción y permiten stress test |

### 4.2 Migraciones de rating y estabilidad

| Estudio | Aportación |
|---|---|
| Jarrow, Lando & Turnbull (1997), *RFS* 10(2). [doi:10.1093/rfs/10.2.481](https://doi.org/10.1093/rfs/10.2.481) | Matrices de transición markovianas entre calificaciones |
| **Lando & Skødeberg (2002)**, *J. Banking & Finance* 26:423-44. [doi:10.1016/S0378-4266(01)00228-X](https://www.sciencedirect.com/science/article/abs/pii/S037842660100228X) | Estimación en tiempo continuo. **Efectos no markovianos: momentum a la baja** (quien acaba de bajar tiene más probabilidad de volver a bajar) y **dependencia de la duración** en la misma calificación |
| **Altman & Rijken (2004)**, *JBF* 28:2679-714. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1294485) | Las agencias consiguen estabilidad sobre todo con su **política de migración**, más que con el horizonte *through-the-cycle*. Solo mueven la nota si el desvío frente a la del modelo **supera un umbral**, y la **ajustan solo en parte**, lo que genera autocorrelación |

### 4.3 Procesos de fracaso: ¿súbito o gradual?

| Estudio | Aportación |
|---|---|
| **Lukason & Laitinen (2019)**, *J. Business Research* 98:380-90. [doi:10.1016/j.jbusres.2018.06.025](https://www.sciencedirect.com/science/article/abs/pii/S0148296318303126) | 1.234 quiebras europeas; salen 3 procesos de fracaso. **En el dominante (73 %), el riesgo se dispara muy poco antes de la quiebra.** Los procesos graduales son minoría. En la fase final, lo que más contribuye es la rentabilidad anual y la acumulada |
| **du Jardin (2015)**, *EJOR* 242(1):286-303. [doi:10.1016/j.ejor.2014.09.059](https://www.sciencedirect.com/science/article/abs/pii/S037722171400798X) | Clasifica las trayectorias de fracaso («terminal failure processes») y ajusta un modelo por tipo. Mejora la predicción a horizontes de más de un año frente a un único modelo |
| du Jardin (2017), *ESWA* 75:25-43. [doi:10.1016/j.eswa.2017.01.016](https://www.sciencedirect.com/science/article/abs/pii/S0957417417300258) | Variables que miden **la evolución** de la situación financiera (no solo su nivel) |
| Balcaen & Ooghe (2006), *British Accounting Review* 38:63-93. [doi:10.1016/j.bar.2005.09.001](https://www.sciencedirect.com/science/article/abs/pii/S0890838905000636) | Crítica clásica: los modelos estáticos **ignoran la dimensión temporal** y suponen un único camino hacia el fracaso |

**Implicación.** Una buena parte de los deterioros serán **abruptos**: con cualquier modelo hay un techo de antelación. Nuestro 48 % de caídas alertadas con 3 meses de mediana hay que leerlo con eso en mente.

### 4.4 Shock transitorio o deterioro persistente

| Herramienta | Idea | Uso en X-Ray |
|---|---|---|
| **Análisis de intervención y outliers** (Chen & Liu, 1993, *JASA* 88(421):284-97, [doi:10.1080/01621459.1993.10594321](https://www.tandfonline.com/doi/abs/10.1080/01621459.1993.10594321); Tsay, 1988, *J. Forecasting* 7) | Cuatro tipos: *additive outlier* (un solo mes), *temporary change* (decae con tasa δ), *level shift* (escalón permanente) e *innovational outlier*. Se decide cuál es por verosimilitud | **Bache = additive outlier o temporary change; caída = level shift.** Se aplica a los cobros operativos o a la caja de cada empresa |
| **BOCPD** (Adams & MacKay, 2007, [arXiv:0710.3742](https://arxiv.org/abs/0710.3742)) | Distribución online de la **longitud de la racha**: cuánto hace del último cambio de régimen | Feature de «probabilidad de cambio de régimen reciente» y de meses desde el último cambio |
| **Change points offline** (Truong, Oudre & Vayatis, 2020, *Signal Processing* 167, [arXiv:1801.00718](https://arxiv.org/abs/1801.00718); librería `ruptures`) | Coste + búsqueda (PELT, binseg) + penalización | Etiquetar caídas estructurales *ex post* de forma reproducible |
| **CUSUM** (Page, 1954, *Biometrika* 41) | Suma acumulada de desvíos frente a la referencia | Alarma con memoria: menos parpadeo que un umbral puntual |
| **Teoría: shocks temporales frente a permanentes** (Gorbenko & Strebulaev, 2010, *RFS* 23(7), [OUP](https://academic.oup.com/rfs/article-abstract/23/7/2591/1589460)) | La mayoría de los shocks de caja de las empresas son **temporales**; la flexibilidad financiera (colchón) existe para absorberlos | Hipótesis por defecto ante un shock: bache. Hace falta evidencia de persistencia para declarar caída |
| **Regla regulatoria de cura** (EBA/GL/2016/07, §71-72) | Para salir de default hacen falta **al menos 3 meses de prueba** sin disparadores (1 año si hubo reestructuración) | Histéresis: una alerta no se apaga hasta pasar k meses limpios |

---

## 5. Etiquetas sin default observado

### 5.1 Definiciones proxy en la literatura y en la regulación

| Definición | Fuente | Riesgo |
|---|---|---|
| **90 días de mora** en una obligación material (umbral relativo del 1 % y absoluto: 100 € minorista / 500 € resto, Reglamento Delegado UE 2018/171) + indicios de «improbabilidad de pago» (*unlikeliness to pay*) | EBA/GL/2016/07, art. 178 CRR. [PDF](https://www.eba.europa.eu/documents/10180/1721448/052c260f-da9a-4c86-8f0a-09a1d8ae56e7/Guidelines%20on%20default%20definition%20(EBA-GL-2016-07)_EN.pdf) | Hace falta un **umbral de materialidad** para no disparar por céntimos, y un periodo de prueba para la cura |
| **30 días de mora** como indicio de aumento significativo del riesgo (stage 2) | NIIF 9, 5.5.11 | Evento «temprano», útil como alerta intermedia |
| **EBITDA < gastos financieros dos periodos seguidos** (+ caída de valor de mercado) | Tinoco & Wilson (2013), *Int. Review of Financial Analysis* 30:394-419. [doi:10.1016/j.irfa.2013.02.013](https://ideas.repec.org/a/eee/finana/v30y2013icp394-419.html); Pindado, Rodrigues & de la Torre (2008), *J. Business Research* 61:995-1003. [doi:10.1016/j.jbusres.2007.10.006](https://www.sciencedirect.com/science/article/abs/pii/S0148296307003281) | **Circular** si luego se usa la cobertura de intereses como feature |
| **Días de retraso como severidad continua**, con censura en el umbral de default | Sigrist & Hirnschall (2019)† | Aprovecha la información de los casos no-default: retrasos leves y moderados |
| **Rebajas de rating interno** como evento | Norden & Weber (2010)†: 5.515 subidas y 7.288 bajadas de calificación interna; Mester et al. (2007) | Más eventos que defaults, pero más ruido y un componente subjetivo |

### 5.2 Métodos para trabajar sin etiqueta

| Método | Referencia | Cuándo sirve | Riesgo |
|---|---|---|---|
| **Weak supervision / labeling functions** | Ratner et al. (2017), «Snorkel», *VLDB* 11(3). [arXiv:1711.10160](https://arxiv.org/abs/1711.10160) | Varias reglas ruidosas (tensión, impago de nómina, impago de IVA, caída). Un modelo generativo estima la precisión de cada regla a partir de sus acuerdos y desacuerdos y produce una etiqueta probabilística | Si las reglas comparten variables con las features, el discriminativo **aprende las reglas**, no el riesgo |
| **PU learning** (solo positivos + no etiquetados) | Elkan & Noto (2008), KDD. [doi:10.1145/1401890.1401920](https://doi.org/10.1145/1401890.1401920) | Cuando los positivos son fiables pero un negativo solo significa «no observado» (p. ej., filiales rescatadas por el grupo) | Hay que suponer que los positivos etiquetados son una muestra al azar de todos los positivos |
| **Anomalías / isolation forest** | Liu, Ting & Zhou (2008), ICDM. [doi:10.1109/ICDM.2008.17](https://doi.org/10.1109/ICDM.2008.17). Aplicado a alerta temprana de distress con más de 3 millones de empresas de la OCDE: *Singapore Economic Review* (2025), [doi:10.1142/S021759082550033X](https://www.worldscientific.com/doi/10.1142/S021759082550033X) | Detector de lo raro, complementario al score | **Raro ≠ malo**: una expansión también es anómala. Sirve para la confianza y el fuera-de-distribución, no como score |
| **Reject inference** | Hand & Henley (1993), *IMA J. Management Math.* 5; Crook & Banasik (2004), *JBF* 28(4). [doi:10.1016/j.jbankfin.2003.10.010](https://doi.org/10.1016/j.jbankfin.2003.10.010) | Análogo a nuestras filas censuradas (filial financiada por el grupo) | Imputarles etiqueta aporta poco y puede sesgar. Dejarlas sin etiqueta (nuestra D32) es lo que avala la literatura |

### 5.3 Leakage y circularidad

- **Kaufman, Rosset, Perlich & Stitelman (2012)**, «Leakage in data mining», *ACM TKDD* 6(4):15 ([doi:10.1145/2382577.2382579](https://dl.acm.org/doi/10.1145/2382577.2382579)). La solución es la **separación aprender/predecir**: todo lo que entra como feature debe estar disponible en *t* y no contener información del objetivo. Si un AUC es «demasiado bueno», probablemente hay leakage.
- **Circularidad de la etiqueta.** Si el evento es «caja < X durante 3 meses» y una feature es la caja actual, el AUC mide persistencia, no capacidad de predicción. Remedios:
  1. un **hueco temporal** entre la ventana de features (hasta *t*) y la de la etiqueta (*t+1…t+h*);
  2. **jueces definidos con otra fuente**: etiqueta con ERP y pagos fiscales, features con flujos bancarios, o al revés;
  3. **ablación**: quitar las features que entran en la definición del evento y medir cuánto cae el AUC;
  4. evaluar **entradas** en el evento («desde sana»), no la prevalencia.
- **Balcaen & Ooghe (2006)** listan los problemas clásicos: definición arbitraria del fracaso, **muestreo por elección** que sobrerrepresenta a los fracasados (Zmijewski, 1984, *J. Accounting Research* 22, [doi:10.2307/2490859](https://doi.org/10.2307/2490859)), no estacionariedad, selección de variables *ad hoc* e ignorar el tiempo.

---

## 6. Validación y explicabilidad

### 6.1 Métricas

| Métrica | Qué mide | Nota |
|---|---|---|
| AUC / Gini (= 2·AUC − 1) | Capacidad de ordenar | No sirve para la calibración. Con pocos positivos, IC amplios (bootstrap por grupo) |
| KS | Separación máxima entre distribuciones acumuladas | Estándar en scorecards; da un punto de corte |
| H-measure | Alternativa al AUC que no depende de los costes implícitos del modelo | Hand (2009), *Machine Learning* 77. [doi:10.1007/s10994-009-5119-5](https://doi.org/10.1007/s10994-009-5119-5) |
| **Brier** y descomposición | Precisión probabilística (calibración + resolución) | Murphy (1973). Imprescindible si publicamos `prob_*` |
| Curvas de calibración / Hosmer-Lemeshow | ¿El 10 % predicho ocurre el 10 % de las veces? | Van Calster et al. (2019), «Calibration: the Achilles heel of predictive analytics», *BMC Medicine* 17:230. [doi:10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7). El boosting sale **mal calibrado**; se corrige con Platt o isotónica (Niculescu-Mizil & Caruana, 2005, ICML) |
| **PSI** | Estabilidad de la población frente al periodo de desarrollo | Las reglas 0,10/0,25 **no tienen en cuenta el tamaño de muestra ni el número de bins**. Con B = 10 y n ≈ 100-200, 0,25 es razonable; con muestras grandes es demasiado conservador (Yurdakul & Naranjo, *J. Risk Model Validation*. [risk.net](https://www.risk.net/journal-of-risk-model-validation/7725371/statistical-properties-of-the-population-stability-index)) |
| Estabilidad de la calificación | Matriz de migración mes a mes y % de reversiones | Práctica de agencias (Altman & Rijken, 2004) |

### 6.2 Esquemas de validación

- **Walk-forward out-of-time.** Sobehart, Keenan & Stein (2000, Moody's, [PDF](http://www.rogermstein.com/wp-content/uploads/53621.pdf)); Stein (2007), *J. Risk Model Validation* 1(1):77-113 ([PDF](http://www.rogermstein.com/wp-content/uploads/BenchmarkingDefaultPredictionModels_TR030124.pdf)). Se entrena con datos hasta *T* y se evalúa después de *T*, repitiendo con *T* móvil. Es robusto a la no estacionariedad en el tiempo **y** en la composición de la cartera. Stein avisa de que, con pocos defaults, las diferencias de AUC entre modelos no suelen ser significativas.
- **Block CV.** Roberts et al. (2017), *Ecography* 40:913-29 ([doi:10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881)). Con dependencia temporal, jerárquica o espacial, la CV aleatoria **subestima el error** aunque los residuos no parezcan correlados. Aquí el grupo empresarial es el bloque natural, y hay que **combinarlo** con un corte temporal.
- **Marco supervisor.** BCBS WP14 (2005), «Studies on the validation of internal rating systems» ([bis.org](https://www.bis.org/publ/bcbs_wp14.htm)): discriminación, calibración y estabilidad. La Fed SR 11-7 (2011) añade la validación independiente y la documentación de las limitaciones.

### 6.3 Explicabilidad

| Enfoque | Referencia | Lectura |
|---|---|---|
| SHAP / TreeSHAP | Lundberg & Lee (2017), NeurIPS; Lundberg et al. (2020), *Nature Machine Intelligence* 2:56-67. [doi:10.1038/s42256-019-0138-9](https://doi.org/10.1038/s42256-019-0138-9) | Atribución local aditiva y exacta para árboles |
| SHAP en crédito a pymes | Bussmann, Giudici, Marinelli & Papenbrock (2021), *Computational Economics* 57:203-16. [doi:10.1007/s10614-020-10042-0](https://link.springer.com/article/10.1007/s10614-020-10042-0) | 15.000 pymes: agrupan a los prestatarios por la **similitud de sus explicaciones SHAP** (redes de correlación). Salen perfiles de riesgo interpretables |
| **Comprobar las explicaciones con datos sintéticos** | Alonso & Carbó (2022), [BdE DT 2222](https://ideas.repec.org/p/bde/wpaper/2222.html) | Generan datos con importancias conocidas y miden si SHAP y la importancia por permutación las recuperan en XGBoost y deep learning. **Nuestro dataset es sintético: podemos hacer lo mismo** |
| Restricciones monótonas en GBM | XGBoost, LightGBM y CatBoost las soportan. Koklev (2025), «What's the price of monotonicity?», [arXiv:2512.17945](https://arxiv.org/abs/2512.17945) (preprint) | Coste en AUC entre ~0 y 2,9 %. **Casi gratis con muestras grandes** (< 0,2 %); más caro con muestras pequeñas y muchas restricciones |
| Modelo interpretable en lugar de caja negra | Chen, Lin, Rudin, Shaposhnik, Wang & Wang (2018/2021), FICO Explainable ML Challenge, *DSS*. [arXiv:1811.12615](https://arxiv.org/abs/1811.12615); Rudin (2019), *Nature Machine Intelligence* 1:206-15 | Un modelo aditivo de dos capas con subescalas **iguala a las redes** y da explicaciones globalmente consistentes |
| Scorecards WoE y escalado por PDO | Siddiqi (2017), *Intelligent Credit Scoring*, 2.ª ed., Wiley | Binning + peso de la evidencia (WoE) + logística. Puntos = offset + factor·ln(odds); **PDO** = puntos que doblan las odds. Los **reason codes** son las variables con más puntos perdidos frente al máximo o la referencia (práctica de *adverse action*, ECOA/Reg B) |

---

## 7. Qué nos llevamos

### 7.1 Definición de eventos

1. **Anclar los eventos a una definición tipo regulatoria.** Un evento necesita tres cosas: **materialidad** (umbral relativo del 1 % de la obligación **y** un mínimo absoluto), **persistencia** (el análogo a los 90 días: ≥ 3 meses) y una **regla de cura con periodo de prueba** (3 meses limpios para salir). Así se reduce el ruido de etiquetas que en la ronda 2 nos costó D32 y D35.
2. **Añadir un objetivo de severidad continuo al estilo Grabit.** Por ejemplo, días de retraso ponderados por importe en nómina, IVA y proveedores, censurados en 0 y en el umbral de incumplimiento. Aprovecha la información de las empresas que se retrasan sin llegar al evento, y con 1.286 empresas eso importa (con pocos positivos, las ganancias de Moscatelli desaparecen).
3. **Jerarquía de eventos, como en NIIF 9 y EBA:** alerta temprana (≈ 30 días / stage 2) → tensión → incumplimiento. La alerta temprana da más positivos para entrenar; el incumplimiento, la verdad final.
4. **Mantener los jueces no circulares y hacerlo sistemático.** Por cada evento, ablación de las features que entran en su definición, informando del AUC con y sin ellas. Evaluar **entradas desde sana** (ya lo hacemos con `entrada_estres_2m`), no la prevalencia.

### 7.2 Horizonte

5. **Varios horizontes (3, 6 y 12 meses) y AUC por horizonte**, como una estructura temporal de la PD (Duffie et al.). La literatura muestra señales escalonadas: amplitud a ~5 meses, uso de póliza a ~9, cobros a 12-18 y excesos a 18. Con 24 meses de panel, 12 meses es el máximo que se puede evaluar con honestidad.
6. **Asumir el techo de antelación.** El 73 % de los fracasos europeos son abruptos (Lukason & Laitinen). Hay que comunicar la antelación como «porcentaje de eventos alertados con ≥ k meses», no prometer detectarlo todo.

### 7.3 Features de trayectoria

7. **Portar el kit de Norden & Weber a nuestros datos,** con Δ a 12 meses además del nivel:
   - uso de la póliza y su Δ12m;
   - excesos de límite (o días con caja < 0) acumulados y su Δ12m;
   - **amplitud del saldo** en el mes (máximo − mínimo, sobre el diario): la señal más rápida, a unos 5 meses;
   - cobros/límite y pagos/límite.
   Normalizar por los **cobros mensuales medios propios de 24 meses** (Yao et al.). Eso resuelve buena parte del sesgo de tamaño (R03) sin percentiles por tamaño.
8. **Medias con peso geométrico** (vida media de 1-3 meses, como Campbell et al.) de la rentabilidad de caja, más la **volatilidad a la baja** y la **pendiente**. Ya tenemos el EWMA; conviene tratar la vida media como hiperparámetro **por feature**, no un único α para toda la nota.
9. **Momentum del propio score** (Lando & Skødeberg): «bajó ≥ X puntos en los últimos 3 meses» y «meses en la banda actual» como covariables del modelo de probabilidad. Quien acaba de caer tiene más riesgo que quien lleva tiempo en la misma nota.
10. **Pagos comerciales:** usar **el atraso sobre el vencimiento** (días de retraso, % de facturas recibidas vencidas y pendientes) en vez del DPO a secas. Interpretar la subida de DPO **junto con** los cobros y la póliza: con cobros a la baja, *stretching*; con cobros estables, poder de negociación. El DSO pesa menos (González & Dietsch).

### 7.4 Bache frente a caída (nuestro AUC de 0,53) y parpadeo (23 %)

11. **Clasificar cada shock como *temporary change* o *level shift*** (Chen & Liu) sobre los cobros operativos y la caja de cada empresa. Añadir dos features:
    - la **longitud de racha del BOCPD**, es decir, la probabilidad de que haya habido un cambio de régimen en los últimos k meses;
    - la **fracción del shock recuperada a 1, 2 y 3 meses**.
    Por defecto, un shock es bache (Gorbenko & Strebulaev). Se declara caída cuando hay persistencia **y** coincide con una subida del uso de la póliza o con *stretching* (Norden & Weber; Molina & Preve).
12. **Política de migración como las agencias** (Altman & Rijken): la banda publicada solo cambia si la nota del modelo se aleja más de un umbral **durante k meses**, y el ajuste es parcial. Salir de «riesgo» exige 3 meses limpios (el periodo de prueba de la EBA). Así se separa **la nota** (reactiva, EWMA 0,5, que la iter_109 nos pidió mantener) de **la banda o alerta publicada** (estable). Resuelve el dilema de R19 sin tocar α.

### 7.5 Modelo

13. **Hazard en tiempo discreto** (Shumway): logística sobre el panel empresa-mes con covariables que cambian en el tiempo, errores agrupados por grupo empresarial y un término de duración (meses desde el último evento o la última cura). Es lo que ya hacemos de facto con «una logística por evento». Ahora tiene respaldo formal.
14. **GBM monótono como aspirante, no como sustituto.** La literatura predice +0 a +1 pp con datos de comportamiento y muestra modesta, y es lo que hemos medido (R09). Solo compensa si aparecen features **no monótonas** con base económica: la U del crecimiento de Moscatelli, que en nuestro caso encaja con la expansión frente a la adversa.
15. **Escala absoluta al estilo scorecard** para R01/R02: puntos = offset + factor·ln(odds a 6 meses), con un PDO fijo (p. ej., 20 puntos doblan las odds). Las bandas se fijan por PD (master scale) y se calibran con isotónica o Platt fuera de grupo.

### 7.6 Validación

16. **Grupo × tiempo:** GroupKFold por `group_id` **combinado** con walk-forward: entrenar hasta el mes *T*, evaluar en *T+1…T+h* sobre grupos no vistos. Es la situación del leaderboard: 60-80 empresas nuevas, probablemente en los mismos meses.
17. Informar de **AUC con IC bootstrap por grupo**, **Brier y curva de calibración por banda**, **KS**, **PSI** de score y features entre cortes temporales (con umbrales ajustados a n y B), y la **matriz de migración mensual** con el % de reversiones como métrica de estabilidad.
18. Con pocos positivos por evento, **las diferencias < 1-2 pp de AUC no son significativas** (Stein). No aceptar iteraciones del autoresearch por diferencias dentro del IC.

### 7.7 Explicabilidad

19. **Reason codes al estilo scorecard:** las 3-4 features con más puntos perdidos frente a una referencia fija (la mediana de las sanas), no frente al mes anterior. La descomposición del cambio mes a mes ya la tenemos; los reason codes explican el **nivel**.
20. **Validar las explicaciones con verdad sintética** (Alonso & Carbó): inyectar en empresas sintéticas perturbaciones conocidas (caída de cobros, estiramiento de pagos) y comprobar que la explicación señala la feature correcta y en qué porcentaje de casos. Es un argumento fuerte para el jurado.

### 7.8 Errores habituales que debemos evitar

| Error | Referencia | Cómo lo evitamos |
|---|---|---|
| Etiqueta definida con las mismas variables que las features (circularidad) | Kaufman et al. (2012); Tinoco & Wilson y Pindado como ejemplo de riesgo | Jueces con fuente distinta, hueco temporal, ablación, entradas desde sana |
| Validar con CV aleatoria sobre filas empresa-mes | Roberts et al. (2017) | Bloques por grupo **y** por tiempo |
| Muestreo por elección o rebalanceo que descalibra | Zmijewski (1984); Cheraghali et al. (2024): los GBM no lo necesitan; Sigrist & Hirnschall†: SMOTE no mejora | Entrenar con la prevalencia real y calibrar después |
| Modelo estático de un solo periodo | Shumway (2001); Balcaen & Ooghe (2006) | Panel empresa-mes con covariables cambiantes |
| Declarar ganador un modelo por diferencias no significativas | Hand (2006); Stein (2007) | IC bootstrap por grupo y DeLong |
| Creer que el ML suplirá la falta de información | Moscatelli et al. (2020)† | Invertir en features y eventos, no en complejidad de modelo |
| Tomar el DPO alto como riesgo sin contexto | Petersen & Rajan; Cuñat; Molina & Preve | Retraso sobre vencimiento, cruzado con cobros y póliza |
| Usar reglas fijas de PSI (0,1/0,25) sin mirar n | Yurdakul & Naranjo | Umbral por simulación o por su fórmula |
| Tratar lo anómalo como malo | — | El isolation forest solo para la confianza y el fuera-de-distribución |
| Confiar en SHAP sin comprobarlo | Alonso & Carbó (2022) | Test con perturbaciones sintéticas conocidas |
| Apagar la alerta en cuanto mejora un mes | EBA/GL/2016/07; Altman & Rijken (2004) | Periodo de prueba y umbral de migración |
