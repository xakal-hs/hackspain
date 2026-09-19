export const useWorkspaceStore = defineStore('workspace', () => {
  const selectedPeriod = ref<'1m' | '3m' | '6m'>('3m')
  const compactMode = ref(false)

  function setPeriod(period: '1m' | '3m' | '6m') {
    selectedPeriod.value = period
  }

  function toggleDensity() {
    compactMode.value = !compactMode.value
  }

  return { selectedPeriod, compactMode, setPeriod, toggleDensity }
})
