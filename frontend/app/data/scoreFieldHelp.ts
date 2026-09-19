/** Definiciones contrastadas con backend/preprocessing.py FEATURES/build_features
 * y backend/etl.py (ventanas de facturas). Mantener junto al catálogo del score.
 * Las etiquetas son la clave disponible en el contrato actual de drivers.
 */
export const scoreFieldHelp: Record<string, { meaning: string; reading: string }> = {
  'Meses de caja': {
    meaning: 'Cuántos meses de pagos cubre el dinero que queda en las cuentas. Divide la caja entre el mayor gasto mensual medio de los últimos 3 o 12 meses.',
    reading: 'Más meses indican mayor colchón; un valor negativo indica caja negativa. El modelo transforma esta proporción con un logaritmo.',
  },
  'Uso de líneas de crédito': {
    meaning: 'Parte del límite de las pólizas de crédito que ya se ha dispuesto: importe utilizado dividido entre el límite disponible.',
    reading: 'Un porcentaje alto deja menos margen para afrontar pagos. Sin un límite de crédito registrado, no hay dato.',
  },
  'Tendencia de cobros': {
    meaning: 'Compara los cobros operativos medios mensuales de los últimos 3 meses con los de los últimos 12. No incluye transferencias ni financiación como cobros del negocio.',
    reading: 'Un valor positivo indica más cobros recientes; uno negativo, menos. El modelo usa el logaritmo de esa relación.',
  },
  'Carga de deuda': {
    meaning: 'Proporción de las entradas de dinero dedicada a cuotas e intereses de deuda durante los últimos 3 meses.',
    reading: 'Cuanto mayor es, menos dinero queda para el resto de los pagos.',
  },
  'Regularidad de nóminas': {
    meaning: 'Mide las caídas de los pagos de nóminas respecto a su media de 6 meses, en proporción a esa media. Solo cuenta las desviaciones a la baja.',
    reading: 'Un valor bajo indica menos caídas en los pagos. Las subidas de nómina no penalizan esta señal. Sin nóminas, no aplica.',
  },
  'Continuidad de nóminas': {
    meaning: 'Proporción de meses con algún pago de nóminas en una ventana de 6 meses, para empresas en las que se observan nóminas.',
    reading: 'Un valor alto indica mayor continuidad de pagos. No mide su importe. Sin nóminas observadas, no aplica.',
  },
  'Pagos tardíos a proveedores': {
    meaning: 'Porcentaje por número de facturas recibidas que siguen sin pagar o se pagaron con más de 15 días de retraso. Usa vencimientos recientes de la ventana de 3 meses, con más de 15 días transcurridos al cierre.',
    reading: 'Un porcentaje alto indica más retrasos al pagar a proveedores; no es un porcentaje del importe adeudado.',
  },
  'Cobros tardíos de clientes': {
    meaning: 'Porcentaje por número de facturas emitidas que siguen sin cobrar o se cobraron con más de 15 días de retraso. Usa vencimientos recientes de la ventana de 3 meses, con más de 15 días transcurridos al cierre.',
    reading: 'Un porcentaje alto indica más retrasos de clientes; no expresa cuántos días tardan de media en pagar.',
  },
  'Deuda vencida con proveedores': {
    meaning: 'Importe de facturas de proveedores vencidas y pendientes, dividido entre las salidas mensuales medias de los últimos 3 meses. El saldo recoge vencimientos de los últimos 12 meses.',
    reading: 'Se expresa en meses de pagos: 0,2 equivale a una quinta parte de un mes de salidas. Cuanto menor, menos deuda vencida.',
  },
  'Clientes morosos >60 días': {
    meaning: 'Importe pendiente de clientes con vencimiento anterior al corte de dos meses, dividido entre las entradas mensuales medias de los últimos 3 meses. Se consideran vencimientos de los últimos 12 meses.',
    reading: 'Se expresa en meses de cobros. Un valor alto indica más dinero retenido en facturas antiguas; el corte se calcula por meses de calendario.',
  },
  'Devoluciones de cobros': {
    meaning: 'Importe de las devoluciones dividido entre los cobros operativos de los últimos 3 meses.',
    reading: 'Un porcentaje alto indica que se devuelve una mayor parte del dinero cobrado.',
  },
  'Tendencia de actividad': {
    meaning: 'Compara el número medio mensual de movimientos bancarios de los últimos 3 meses con el de los últimos 12.',
    reading: 'Un valor positivo indica más movimientos recientes; uno negativo, menos. Mide frecuencia, no importe ni beneficio.',
  },
  'Dependencia de transferencias': {
    meaning: 'Proporción de las entradas de dinero de los últimos 3 meses que procede de transferencias no operativas.',
    reading: 'Un porcentaje alto indica mayor dependencia de entradas ajenas a los cobros ordinarios del negocio.',
  },
  'Concentración de clientes': {
    meaning: 'Mide cuánto depende la facturación de unos pocos clientes en los últimos 6 meses. Suma el cuadrado de la cuota de facturación de cada cliente (índice HHI).',
    reading: 'Cuanto más cerca de 1, mayor concentración; 1 significa un único cliente. Un valor menor indica más diversificación.',
  },
  'Volatilidad a la baja': {
    meaning: 'Mide la magnitud de los meses en los que sale más dinero del que entra durante los últimos 6 meses: raíz de la media de los déficits al cuadrado, dividida entre el gasto mensual de referencia.',
    reading: 'Un valor alto indica déficits más grandes o frecuentes. Los meses con saldo de flujos positivo no penalizan esta señal.',
  },
  'Amplitud de clientes': {
    meaning: 'Compara los clientes distintos facturados en los últimos 3 meses con los de los últimos 12. El cálculo añade uno a ambos recuentos antes de tomar su relación logarítmica.',
    reading: 'Cuanto más cerca de cero, mayor parte de la base anual sigue activa. Un valor negativo no implica por sí solo una caída frente al trimestre anterior.',
  },
  'Facturación de clientes perdidos': {
    meaning: 'Porcentaje de la facturación de hace 3 a 12 meses que correspondía a clientes sin nuevas facturas en los últimos 3 meses.',
    reading: 'Un porcentaje alto indica más facturación histórica ligada a clientes inactivos; no demuestra que se hayan perdido definitivamente. Requiere al menos 3 clientes previos.',
  },
  'Persistencia de cobros': {
    meaning: 'Proporción de meses de los últimos 6 en los que los cobros operativos alcanzan al menos la mitad de su mediana móvil de 12 meses.',
    reading: 'Un porcentaje alto indica cobros más sostenidos. El 100 % significa que se supera ese umbral en todos los meses evaluados, no que se cobren todas las facturas.',
  },
  'Varias señales a la vez': {
    meaning: 'Resumen simulado de varias señales activas al mismo tiempo en el escenario de demostración.',
    reading: 'No es una variable individual del modelo ni tiene una fórmula propia en el catálogo del score.',
  },
}
