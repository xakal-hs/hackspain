import { listEmployees, toPublic } from '../../utils/embatEmployees'

export default defineEventHandler(async () => {
  const employees = (await listEmployees()).map(toPublic)
  return {
    employees,
    counts: {
      account_management: employees.filter((row) => row.team === 'account_management').length,
      customer_success: employees.filter((row) => row.team === 'customer_success').length,
    },
  }
})
