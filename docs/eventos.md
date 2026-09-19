# Reglas para definir los eventos

## 1. Qué medimos

No hay etiquetas de "salud" en los datos. Definimos salud como **ausencia de un evento futuro de estrés financiero material** y validamos el score contra ese evento. El score es `100 × (1 − P(evento))`.

Tres niveles, que no se mezclan:

| Nivel | Qué es | Ejemplo |
|---|---|---|
| Métrica | Algo que se calcula de los datos | runway, % vencido |
| **Evento** | Una regla binaria: un episodio concreto de estrés | saldo negativo 5 días |
| Evento final | Alguno de los eventos admitidos ocurre en los próximos *h* meses | `estrés_3m` |

## 2. Qué es un evento

Una regla que, para una empresa y un mes *t*, responde **sí**, **no** o **no aplicable**.

1. Se calcula **solo con datos hasta el fin del mes *t***. Nunca mira el futuro.
2. **No aplicable** es una respuesta válida: si la empresa no tiene los datos necesarios (por ejemplo, no tiene facturas), no se evalúa. Nunca se cuenta como "no" ni se imputa.
3. Cada evento pertenece a una dimensión (pago, liquidez, caja, deuda) y tiene una gravedad (baja, media, alta).

## 3. Filtros de admisión

Un evento entra en el evento final solo si cumple los seis:

| # | Filtro | Pregunta |
|---|---|---|
| 1 | Observable | ¿Se ve directamente en los datos, sin interpretar? |
| 2 | Material | ¿Es un problema real de la empresa, no ruido contable? |
| 3 | Frecuente pero no común | ¿Ocurre entre un 2 y un 15 % de los casos aplicables? |
| 4 | Limpio | ¿Se distingue de un fallo de los datos? Si una vez que salta no se apaga nunca (persistencia muy alta), sospechar de un artefacto |
| 5 | Sin fuga | ¿Usa solo información disponible en ese mes? |
| 6 | Distinto | ¿Aporta algo que no dice ya otro evento? |

## 4. Cómo se fijan los umbrales

- Con **criterio de dominio** (por ejemplo, 90 días de impago es la convención bancaria) y con la **tasa base** que resulta.
- **Nunca** por lo bien que el score los prediga. Si se ajusta el evento hasta que la validación salga bien, la validación deja de valer.
- Cada ajuste se anota con su motivo (qué umbral, qué tasa daba antes y después).
- Una vez decididos, se **congelan**. Si se cambia algo después, se vuelve a evaluar todo.

## 5. Evento final

- `estrés_h` = **al menos un evento admitido** ocurre en alguno de los meses *t+1 … t+h*. Se usan varios horizontes (1, 3 y 6 meses).
- Objetivo de tasa base del evento final: entre el **5 y el 20 %** de los casos. Si sale fuera, se revisan los umbrales de los eventos individuales antes de evaluar nada.
- Se informa siempre de la **tasa de cada evento por separado**, para saber qué lo mueve.

## 6. Recuperación (la otra dirección)

Una empresa se **recupera** cuando estuvo en estrés al menos 2 meses y lleva al menos 3 meses seguidos sin ningún evento. Permite medir si el score detecta la mejora, no solo el deterioro.

## 7. Catálogo de candidatos

| Evento | Dimensión | Gravedad | Regla | Se aplica a |
|---|---|---|---|---|
| Obligación regular que falta | pago | alta | Falta la nómina, la seguridad social o el impuesto que se pagaba al menos 5 de los 6 meses anteriores | Empresas con pagos regulares y actividad ese mes |
| Factura de proveedor vencida | pago | media | Facturas recibidas vencidas entre 90 y 180 días y sin pagar, por un importe de al menos el 25 % de las salidas mensuales | Empresas con facturas |
| Saldo negativo | liquidez | alta | Saldo de las cuentas de banco negativo durante 5 días o más del mes | Empresas con saldo reconstruible |
| Caja agotándose | caja | alta | Flujo operativo negativo 3 meses seguidos y saldo que cubre menos de 1 mes de salidas | Empresas con saldo y flujo |
| Coste financiero disparado | deuda | media | Intereses y comisiones más de 3 veces su mediana de 6 meses y más del 2 % de las salidas | Empresas con 6 meses de historia |

Estado de la decisión de cada uno:
- **Admitidos por ahora:** obligación regular que falta, coste financiero disparado.
- **A revisar:** factura de proveedor vencida (sospecha de facturas que el ERP nunca cierra), saldo negativo (puede ser un descubierto real o un error de reconstrucción) y caja agotándose (parece describir una situación normal en muchas pymes, hay que endurecerla o descartarla).

## 8. Decisiones abiertas

1. Umbrales definitivos de los tres eventos a revisar.
2. Unidad del evento y del score: empresa o grupo (pendiente de confirmar con la organización).
3. Horizonte principal del evento final.

## 9. Limitaciones que se dicen con honestidad

- El evento lo construimos nosotros con los mismos datos que las variables: un buen resultado demuestra que el score anticipa **estas reglas**, no la salud en general. Al evaluar se excluyen las variables gemelas del evento.
- Un mes con flujo negativo es normal (la empresa típica lo tiene la mitad del tiempo). Los eventos miran obligaciones incumplidas y episodios sostenidos, no un mal mes.
