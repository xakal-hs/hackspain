# Contrato de medición · qué medimos, con qué y cómo

> **Qué es este fichero.** La consolidación de lo que hoy medimos en X-Ray: **los eventos**, **las features**,
> **las reglas de decisión** y **cómo se mide** (métricas, intervalos, trampas). Es un documento **vivo**:
> v0.1, a 19/09, antes del veredicto del radar. Cada afirmación cuantitativa lleva su número y su `file:line`.
> Cuando un debate cambie algo, se actualiza **aquí** además de en su salida.
>
> **Regla del contrato.** Ninguna afirmación entra sin medición (`n`, tasa, AUC, lift) o sin `file:line`.
> Si no se puede medir, se declara `no_verificable` con el motivo. El consenso cómodo es un fallo.

## 0 · La cadena, de arriba abajo

```
preguntas del prestamista (14)  →  columnas del panel  →  features (17)  →  nota 0-100
                                                                              ↓
                                        reglas de decisión (C0-C9)  ←  banda sano/vigilar/riesgo
                                                                              ↓
                                     medido contra los EVENTOS (anclas) con AUC + IC por grupo
```

**El eslabón débil medido es la flecha `nota → eventos`** (no las preguntas, que son bottom-up). Ver §4.

---

## 1 · Los eventos (anclas)

Fuente: `research/src/targets.py`. **No los diseñamos nosotros**: se heredaron del trabajo previo (R05) y
están anclados al lenguaje del reto. Todas las etiquetas son a 6 meses (`H=6`, `targets.py:22`), con `null`
si el futuro no es observable.

### 1.1 Las cuatro anclas oficiales (`evaluate.py` `EVENTS`)

| ancla | definición (`targets.py`) | tasa | cob. | n / emp / grp | ¿existe mes 0? | `score_oof` |
|---|---|---|---|---|---|---|
| `tension_6m` (E1) | liquidez < 0,25 meses de gasto en ≥2 de 3 meses (`:82-103`) | 0,274 | 0,52 | 11 223 / 1 002 / 192 | **sí** | **0,695** |
| `incumplimiento_6m` (E2) | una obligación recurrente (nómina/cuota/IVA) deja de pagarse (`:105-121`) | 0,123 | 0,31 | 6 690 / 701 / 153 | no (0,13) | 0,572 |
| `caida_6m` (E3) | caída estructural de cobros, sin apagado ni rebote (`:123-131`) | 0,102 | 0,27 | 5 721 / 763 / 142 | **no (0,00)** | 0,621 |
| `expansion_6m` (E4) | expansión sostenida y autofinanciada (`:133-141`) | 0,058 | 0,38 | 8 219 / 878 / 160 | no (0,11) | 0,566 |

`tension_entrada_6m` (anticipación, `:98-99`): tasa **0,023**, **140 positivos / 39 emp / 31 grp** → n pequeño,
todo con IC obligatorio. `tension_onset` (confirmado): **45**.

### 1.2 Tres problemas confirmados por el consejo (Q1-Q3)

1. **Circularidad.** `tension_6m` suma la **póliza no usada** (`lc_limit − lc_drawn`, `:84-85`) a la liquidez,
   y `lc_util = lc_drawn / lc_limit` (`features.py:46`) es su complemento. Medido: quitar la póliza de la
   definición deja `lc_util` en **0,633 → 0,525** (el **81 % de su señal era la definición**). Y excluir las
   `group_funded` con `0` (no `null`, `:93,101`) **censura 2 513 filas (22 %)** y cuesta **0,05 de AUC**
   (con `null` el score sube a **0,745**).
2. **Medibilidad.** Con `month_idx < 6`: `caida` cob. **0,00**, `incumplimiento` 0,13 (AUC 0,517), `expansion`
   0,11 (0,509). Solo `tension_6m` (AUC 0,738). El test oculto son **empresas nuevas** → 3 de 4 anclas no se
   pueden auditar en su perfil.
3. **Horizonte.** 6 → 3 meses **no cambia** la conclusión (score 0,762 / 0,764 / 0,767 a 6/3/2 m; acuerdo
   3m/6m 94,8 %); a 3 m se etiquetan 1 281 empresas vs 1 002. Se heredó `H=6`, nadie lo justificó.

### 1.3 Variantes y etiquetas propuestas (aún **no** en el código)

- `tension_6m_nopol` — tensión **sin** la póliza (quita la circularidad de `lc_util`). Medida: score 0,699.
- `tension_raw_6m` — tensión **sin censurar** las `group_funded`. Medida: **0,759** (1 112 filas / 143 emp con
  tensión real y etiqueta 0).
- `rompe_caja_2m` — «sana hoy, entra en tensión en m+1..m+2»: tasa **8,3 %**, `runway` 0,670 vs score 0,583,
  cobertura mes 0-5 **0,53**. Es la etiqueta que la demo necesita.
- `cura_3m` / `recaida_6m` — vuelve a caja ≥ 0 en ≤1 m / ≤3 m: **44 % / 69 %**; recae 30-36 % → es **marca**,
  no evento de salud.
- Variantes de historia corta (`caida_3m_corto`, `expansion_3m_corto`, obligación 3 de 6).
- **Elkano D1-D4** (radar, terceros): evento de impago observable. Construible aquí → `default_6m` (tasa 58 %,
  1 194 emp, **existe mes 0**). **Nuestro score lo separa con 0,505 = azar** (anticipación 0,467). Ver §5.

---

## 2 · Las features

Fuente: `research/src/features.py`. 17 features puntúan (`SCORE_FEATURES`), con pilar, dirección económica y
**peso calibrado** (media de las repeticiones, `metrics_ar007.json`). El score es la media ponderada de
sub-scores por percentil → **explicación aditiva exacta** (`score = Σ ec_f`).

| feature | pilar | dir. | peso ar007 | qué mide (en lenguaje llano) |
|---|---|---|---|---|
| `runway` | liquidez | +1 | **0,1546** | meses de gasto que le quedan en la cuenta (`log(1+caja/gasto)`) |
| `lc_util` | liquidez | −1 | 0,1010 | qué parte de la póliza ha gastado |
| `growth_vs_12m` | rentabilidad | +1 | 0,0173 | cobra más o menos que su media anual |
| `debt_burden` | solvencia | −1 | 0,0406 | cuotas + intereses sobre entradas |
| `payroll_cv` | solvencia | −1 | 0,1015 | nóminas que faltan o bajan (regularidad, no peso) |
| `ap_late_share` | disciplina | −1 | 0,0079 | paga tarde a proveedores |
| `ar_late_share` | disciplina | −1 | 0,0364 | le pagan tarde los clientes |
| `ap_overdue_ratio` | disciplina | −1 | 0,0042 | deuda vencida con proveedores |
| `ar_overdue_90_ratio` | disciplina | −1 | 0,0161 | clientes morosos >60 días |
| `refund_rate` | disciplina | −1 | **0,1183** | devoluciones de cobros (⚠ criticado: «bono casi constante») |
| `activity_trend` | estabilidad | +1 | **0,1577** | se mueve más o menos que su media anual |
| `transfer_dep` | estabilidad | −1 | 0,0474 | vive de transferencias no operativas |
| `hhi_ar_6m` | estabilidad | −1 | 0,0208 | concentración de clientes |
| `net_vol_6m` | estabilidad | −1 | 0,0157 | volatilidad a la baja del flujo neto |
| `cust_trend` | estabilidad | +1 | 0,0442 | amplitud de clientes |
| `lost_share` | estabilidad | −1 | 0,0334 | facturación de clientes perdidos |
| `oper_persistence_6m` | estabilidad | +1 | 0,0830 | meses con cobros operativos normales |

Contexto (no puntúan, alimentan OOD/forecaster): `net_margin_6m` (salió, D29), `log_scale`, `fx_share`,
`uncat_share`, `activity_log`, `month_idx`, `dormant`, `months_since_last_tx`.

**Aviso medido (Q4):** `runway` tiene coeficiente **3,414** para tensión y **0,000** para expansión; el promedio
lo diluye a ~0,85. Quitar `runway` del score lo deja en **0,522** → **la nota es esencialmente un score de
liquidez**. Remedio aprobado: **notas separadas** por evento/comprador (los seis).

---

## 3 · Las reglas de decisión (knockouts C0-C9)

Fuente: `politica_prestamo.md` §3 y `proactive.py:decide()`. **Precedencia**: la primera que aplica manda; las
siguientes solo pueden endurecer. Los **«big NO»** son C1 y C5.

| regla | disparador | acción | evidencia |
|---|---|---|---|
| **C0** | dato no fiable (`dq_cash_sentinel`/`has_drift`/`dq_cash_implausible`), `n_tx < 5`, o ≥2 meses sin movimientos | **sin nota** (con motivo) | 53 emp / 242 filas con caja implausible llegaban al mejor tramo |
| **C1** | `cash_end < 0` | **no prestar** deuda nueva; ≥3 meses → solo colateral | tensión 61,7 % vs 26,1 % (lift 2,55); cura 54 % en 1 m. Pero **no** predice impago (×1,13) ni caída |
| **C5** | `payroll ≤ 10 %` de su mediana 6m, empresa activa | **no prestar** hasta ver la nómina siguiente | impago ×1,48 en risk-set limpio; caída **×2,5** (independiente). 1 mes → ⚠ falso positivo trimestral |
| **C2** | `mc < 0,25` (y `growth < −0,2` → no prestar) | no prestar circulante sin colateral / vigilar | tensión 45 % con caída, 60 % sin colchón |
| **C4** | `lc_util > 0,9` y `mc < 0,5` | **no ampliar / no prestar** | tensión 52,9 %; lift 1,45 |
| **C3** | `growth < −0,2` con `mc ≥ 2` | `activity_trend < −0,3` → vigilar; si no → prestar | caída 27,8 % (×2,7) vs 7,2 % |
| **C6** | filial `mc < 0,5`, `intragroup_share_3m > 0,2`, caja de grupo > 0 | prestar **al grupo** con garantía cruzada; caja ≤ 0 → no prestar | caja del grupo predice su impago mejor que la propia (0,601 vs 0,532) |
| **C7** | 1 mes sin movimientos | vigilar; `mc` **no puntúa** ese mes | no predice tensión (×0,96) ni impago (×0,77), sí caída (×2,1) |
| **C8** | sin ERP / `uncat_share > 0,5` / `fx_share > 0,5` / historia < 3 m | **recorta el importe, no la nota** | lift 0,95 sobre tensión = cobertura, no salud |
| **C9** | `mc ≥ 2`, sin C1-C7 | prestar, mejor precio; `activity_trend > 0,2` → ampliar | tensión 5,3-5,7 %; **no es cero**: incumplimiento 7,5-10,3 % |

Bandas de la nota (`xray.py:49`): `riesgo < 35 ≤ vigilar < 65 ≤ sano`.

**Diferencia con Elkano (radar):** él convierte los knockouts (D1-D4) en **la etiqueta medible**; nosotros los
tenemos **codificados en la decisión** pero calibramos el score contra **otra** etiqueta (`tension_6m`).
Pregunta abierta en el debate del radar (R7).

---

## 4 · Cómo medimos

### 4.1 La métrica

- **AUC es la base** (sentido «separa el evento»; 0,5 = azar). El **Gini es un extra** opcional (`2·AUC − 1`),
  **no** la métrica titular.
- **PM** (`puntuacion.py`) = media del AUC del nivel contra E1-E4. ⚠ **Es la métrica que el consejo tumbó**:
  divide por 4 cualquier mejora dirigida a un comprador. Sustituto aprobado: **objetivo por evento/comprador**.
- **AUC de estado vs anticipación**: `tension_6m` es un **estado** (incluye seguir en tensión); la anticipación
  se mide contra `tension_entrada_6m` / `rompe_caja_2m` / entrada en estrés desde sana. Nuestro score es 0,695
  de **estado** y ≈0,5-0,6 de **anticipación**; `runway` es al revés (0,79 de estado, 0,67 de entrada a 2 m).

### 4.2 Los intervalos y las unidades

- **IC 95 % por bootstrap de `group_id`** (250 grupos) en **todo** AUC y tasa. Factor de diseño medido:
  **2,1-4,0×** el error iid; `se(PM)` **0,0173** vs 0,0058 declarado.
- **Unidades efectivas**: todo AUC/tasa publica `n`, `n_empresas`, `n_grupos`, `n_nulos`.
- **Un episodio ≠ una fila**: filtrar a episodios sube `se(AUC)` a ~0,043; el bootstrap por grupo sobre todas
  las filas usa más información (`se` 0,0234).

### 4.3 Las tres trampas (todas ya pagadas)

1. **Circularidad**: medir una feature contra una etiqueta que la contiene. Se resuelve con la etiqueta
   **no circular** (`tension_nopol`, `group_funded = null`).
2. **Feature gemela**: la columna que **define** el evento (p. ej. `ap_overdue_ratio` vs el impago por factura
   vencida: AUC **0,827**, rho 0,62). Se controla quitándola (con D1 y D3 fuera → 0,510).
3. **Fuga temporal**: `late_share` filtrado por `due_date` sin `issuance_date < m_end` (D05); mora **as-of**
   (`panel.py:151-152,165`, ya corregida: naive 0,171 vs as-of 0,426; as-of separa el impago 0,730 vs 0,613).

### 4.4 Aceptación de un cambio (fase 3)

Un cambio entra si **mejora la nota del evento objetivo fuera del IC** y **no empeora otra fuera de un error
típico**. **Meseta = 4 candidatos independientes sin mejora material**, nunca antes de agotar los remedios.

---

## 5 · Lo que está en duda (medido, sin cerrar)

| hecho medido | número | consecuencia |
|---|---|---|
| El score es `runway` | sin `runway`: **0,522** | «nota única» ≈ score de liquidez |
| El score **no** separa el impago observable de Elkano | `default_6m` **0,505** (IC [0,459, 0,545]) | nuestros knockouts y nuestro score miran cosas distintas |
| Los eventos adversos son **independientes** | `tensión & incumplimiento` ratio **1,01**; los tres **0,46** | no hay factor latente de salud (LABEL-VIABILITY) |
| La etiqueta de tensión es circular por la póliza | `lc_util` 0,633 → 0,525 | toda premisa `lc_util`↔tensión está inflada |
| El intragrupo está **censurado** como 0 | 2 513 filas (22 %); con `null` +0,05 AUC | intragrupo hoy es **infalsable** |
| 3 de 4 anclas no existen para empresas nuevas | `caida` cob. 0,00 | no se puede auditar en el perfil del test |
| El bucle entero cabe en el ruido | ganancia +0,0076 = **0,44 se** | la «meseta» era ruido |

---

## 6 · Conclusiones (debates cerrados) y plan

### 6.1 Lo que decidió el consejo (Q1-Q12 + R1-R8)

1. **La métrica es interna, no la nota del jurado.** Verificado en `context/challenge.md`: la
   evaluación son tres bloques **cualitativos**. El AUC/PM sirve para **decidir internamente** y para
   **sostener conclusiones en la demo** — no para maximizar un promedio.
2. **Tres cifras con nombre** (no una): **estado** (0,70), **anticipación desde sana** (0,55-0,59, con
   `n` y adelanto) y **cobertura**. Se **retira** «anticipación 0,70» y `tension_entrada_6m` (39 empresas).
3. **Dos capas**: política de **vetos auditable** (C1/C5/C4) **encima** del ranking de supervivientes;
   cada capa contra **su** evento (banda→tensión, veto→impago). Aporta Δ pérdida **+0,278** sobre lo que
   la nota sola rechazaba. C5 exige `regular(payroll)`, no duración.
4. **No promediar los pesos por evento** (`xray.py:101`): notas por evento con signo restringido =
   **+0,095** en tensión. Es Q4, Byte_Me y el re-weight a la vez.
5. **El radar no cambia el diagnóstico**: unidad = entidad legal; anclas E1-E4 para el nivel; el evento
   de Elkano (D1-D4) es, en nuestros datos, `ap_overdue_ratio` re-umbralizada (estado crónico, cura 2,8 %).

### 6.2 El plan, en orden (fase 3 y producto)

| # | qué | por qué primero | estado |
|---|---|---|---|
| **A** | **Instrumentar** en el derivado: `D1`, `D1_estricto`, `default_6m`, `knockout_mes`/`_6m`, `entrada_estres_6m_desde_sana`, `nomina_mensual`, `perdida_6m`, `mirror2`/`nm`, `mc`, `mc_grupo`, `cash_share_g`, `rotura_covenant_mes`, `arcov_3m`, `episodio_<evento>`, `libro_no_nulo` | sin ellas, **12 de las 19 premisas nuevas son `no_verificable`** | pendiente |
| **B** | **Notas por evento** (no promediar `xray.py:101`) | el remedio **más barato**: +0,095, sin romper monotonicidad | pendiente |
| **C** | **Etiquetas limpias**: `tension_nopol`, `tension_raw_6m`, `group_funded → null` (+0,05), `rompe_caja_2m`, `cura_3m`, variantes cortas | sin diana limpia no se puede verificar nada más | pendiente |
| **D** | **Capa de vetos publicada** (C1/C5/C4 con `regular()` e histéresis) + traducción a producto (colateral, importe ≤ 0,25 m, revisión 30 d) | +0,278 de pérdida; auditable ante Embat | pendiente |
| **E** | **Declarar las tres cifras** en documento y demo; PM congelada con etiqueta o retirada | honestidad + lo que juzga el jurado | pendiente |

### 6.3 Las dos preguntas que quedan para el dueño

1. **¿`group_funded → null` entra ya?** (medido: +0,05; es el primer candidato del debate anterior).
2. **¿PM congelada con etiqueta o retirada?** (decisión del consejo, no de datos).

## 7 · Estado y deudas

- **Premisas**: 270 en `salida/premisas.jsonl`, todas con `evidencia`.
- **Medido y en pie**: aditividad exacta (`Σec = nota`, max 0,0), sin sobreajuste de grupo, neutralidad al
  tamaño (Spearman −0,024), monotonicidad de `ec_lc_util`.
- **Deuda de instrumento** (bloquea discutir umbrales): `mc`, `mc_grupo`, `cash_share_g`,
  `rotura_covenant_mes`, `arcov_3m`, `episodio_<evento>`, `libro_no_nulo` **no son columnas**; avales / comfort
  letters / pignoraciones: **0 datos**.
- **Pendiente**: veredicto del radar (R1-R8) → actualizar §1.3, §2 y §5.

---

*Fuentes: `targets.py`, `features.py`, `xray.py`, `proactive.py`, `politica_prestamo.md`,
`salida/consejo/debate_veredicto.md`, `debate_veredicto_seguimiento.md`,
`scratch/orquestador/radar_medidas.txt`, `research/reports/metrics_ar007.json`.*
