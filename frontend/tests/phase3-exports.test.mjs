import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const readSource = path => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('phase 3 provides protected binary report downloads and their working views', async () => {
  const [api, reports, stock, stockTakes, customerHistory, config, router, auth] = await Promise.all([
    readSource('api/index.js'), readSource('views/Reports.vue'), readSource('views/Stock.vue'), readSource('views/StockTakeHistory.vue'), readSource('views/CustomerSalesHistory.vue'), readSource('views/SystemConfig.vue'), readSource('router/index.js'), readSource('stores/auth.js'),
  ])

  assert.match(api, /responseType: 'blob'/)
  assert.match(api, /downloadWeeklyReport/)
  assert.match(api, /downloadStockTakeHistory/)
  assert.match(api, /downloadSalesHistory/)
  assert.match(reports, /downloadWeeklyReport/)
  assert.match(reports, /auth\.hasRole\('owner'\)/)
  assert.match(stockTakes, /getStockTakes/)
  assert.match(stockTakes, /downloadStockTakeHistory/)
  assert.match(stock, /exportStockReport/)
  assert.match(stock, /auth\.hasRole\('owner'\)/)
  assert.match(customerHistory, /getCustomerSales/)
  assert.match(customerHistory, /exportCustomerStatement/)
  assert.match(customerHistory, /downloadSalesHistory/)
  assert.match(config, /getSystemConfig/)
  assert.match(config, /updateSystemConfig/)
  assert.match(router, /StockTakeHistory/)
  assert.match(router, /CustomerSalesHistory/)
  assert.match(router, /SystemConfig/)
  assert.match(auth, /StockTakeHistory: \['owner', 'warehouse_operator'\]/)
  assert.match(auth, /CustomerSalesHistory: \['owner'\]/)
  assert.match(auth, /SystemConfig: \['owner'\]/)
})
