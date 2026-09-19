## Eventos - regla binaria que marca un episodio de estrés; es la diana que el score intenta prever. Muchos de estos eventos son propuestas, hay que hacer modificaciones e implementaciones.

estrés de liquidez - lo definimos como poliza credito + caja. Problema 1) la empresa ya está endeudada y por lo tanto la parte de la poliza hace que le queramos dar más dinero 2) para un 65,6% de los casos no estamos prediciendo nada porque ya estaba estresada la empresa. Solución usamos tension_np_raw : calcular el estrés con la caja propia, sin sumar la póliza y sin marcar automáticamente como sanas a las empresas financiadas por su grupo. Para medir anticipación, usar además  entrada_estres_2m  o  rompe_caja_2m , limitado a empresas sanas  hoy. La tensión agregada del grupo se añade aparte como diagnóstico para la decisión de crédito.
obligación impagada: una empresa deja de pagar una obligación que pagaba regularmente, como nómina, Seguridad Social, impuesto o cuota. Solo se evalúa cuando existe suficiente historial de pagos y se conoce la periodicidad. El consejo detectó que la etiqueta agregada mezcla  obligaciones distintas y que parte de su señal es mecánica cuando la falta de pago ya ha ocurrido. La solución es separar el impago por  tipo, exigir regularidad, distinguir impago actual de impago futuro y marcar como no verificables los casos sin calendario suficiente. La  ausencia de nómina habitual se mantiene además como veto de decisión, separado del evento usado para calibrar el score:
   •  impago_nomina_6m  — deja de pagar una nómina habitual.
   •  impago_ss_6m  — deja de pagar Seguridad Social.
   •  impago_iva_6m  — deja de pagar IVA u otro impuesto habitual.
   •  impago_cuota_6m  — deja de pagar una cuota de deuda habitual.
   •  impago_ap_6m  — mantiene facturas de proveedores vencidas durante el umbral definido.

cura_3m  — la empresa sale del estrés.
recaida_6m  — vuelve a entrar en estrés después de recuperarse. Es más una marca de fragilidad que un evento principal.
caida de cobros - cambiar a caida_3m_corto para tener más empresas
crecimiento - cambiar a expansion_3m y probar
añadir `cura_3m` / `recaida_6m`
balance negativo - meter rompe caja 2m
- **balance negativo** (`cash_end < 0`) — Balance negativo = estado de alerta y posible evento de liquidez. No es un veto automático. El veto depende de la persistencia, la cobertura de cobros pendientes y la capacidad del grupo para cubrir el desfase.

## Vetos — regla que decide hoy, por encima del score: si salta, no se presta.

nómina ausente → no prestar hasta ver la siguiente
póliza agotada con caja corta → no ampliar
 Son reglas que se aplican hoy, por encima del score:

veto_caja_negativa 
veto_nomina_ausente 
veto_ss_ausente 
veto_iva_ausente 
veto_cuota_ausente 
veto_poliza_agotada 
veto_grupo_en_estres 