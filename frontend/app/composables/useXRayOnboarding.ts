import type { DriveStep, Driver } from 'driver.js'

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function openFirstPillar() {
  const first = document.querySelector<HTMLButtonElement>('[data-tour="xray-pillars"] button')
  if (first && first.getAttribute('aria-expanded') !== 'true') first.click()
}

const steps: DriveStep[] = [
  {
    element: '[data-tour="xray-gauge"]',
    waitForElement: 4000,
    popover: {
      title: 'El score de la empresa',
      description:
        'Una nota de 0 a 100 sobre el dinero que queda en la cuenta y cómo va el negocio. La banda —sano, vigilar o riesgo— es la lectura que un prestamista usaría para decidir.',
      side: 'right',
      align: 'center',
    },
  },
  {
    element: '[data-tour="xray-change"]',
    popover: {
      title: 'Cambio en 3 meses',
      description:
        'Si la nota sube o baja de verdad, no un mes suelto. Aquí ves la trayectoria, no solo la foto de hoy.',
      side: 'left',
      align: 'center',
    },
  },
  {
    element: '[data-tour="xray-sector"]',
    popover: {
      title: 'Frente al sector',
      description:
        'Tu score junto a la media o la mediana de empresas del mismo sector. Sirve para ver si el movimiento es vuestro o de todo el mercado.',
      side: 'top',
      align: 'center',
    },
  },
  {
    element: '[data-tour="xray-pillars"]',
    popover: {
      title: 'Cinco pilares',
      description:
        'Cada pilar responde una pregunta de prestamista: liquidez, cobros, deuda, disciplina de pago y estabilidad. El siguiente paso abre el primero para ver las señales.',
      side: 'top',
      align: 'center',
      onNextClick(_element, _step, { driver }) {
        openFirstPillar()
        window.setTimeout(() => driver.moveNext(), 60)
      },
    },
  },
  {
    element: '[data-tour="xray-pillar-detail"]:not([hidden])',
    waitForElement: 1500,
    popover: {
      title: 'Las señales del pilar',
      description:
        'Cada señal suma o resta puntos al score. El semáforo se queda en el arco; aquí está el porqué, en el lenguaje de la tesorería.',
      side: 'top',
      align: 'start',
    },
  },
]

export function useXRayOnboarding() {
  const instance = shallowRef<Driver | null>(null)

  function stop() {
    instance.value?.destroy()
    instance.value = null
  }

  async function start() {
    if (!import.meta.client) return
    stop()
    const { driver } = await import('driver.js')
    const tour = driver({
      steps,
      overlayColor: '#090c22',
      overlayOpacity: 0.62,
      stagePadding: 10,
      stageRadius: 12,
      popoverClass: 'xray-tour',
      popoverOffset: 12,
      showProgress: true,
      progressText: '{{current}} de {{total}}',
      nextBtnText: 'Siguiente',
      prevBtnText: 'Anterior',
      doneBtnText: 'Listo',
      animate: !prefersReducedMotion(),
      smoothScroll: !prefersReducedMotion(),
      allowKeyboardControl: true,
      disableActiveInteraction: true,
      skipMissingElement: true,
      onDestroyed() {
        instance.value = null
      },
    })
    instance.value = tour
    tour.drive()
  }

  onBeforeUnmount(stop)

  return { start, stop }
}
