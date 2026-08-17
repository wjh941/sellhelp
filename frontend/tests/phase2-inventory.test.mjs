import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const readView = name => readFile(new URL(`../src/views/${name}`, import.meta.url), 'utf8')

test('inventory views expose batch risks, return limits, and stocktake variance states', async () => {
  const [stock, returns, analysis] = await Promise.all([
    readView('Stock.vue'),
    readView('Returns.vue'),
    readView('StockAnalysis.vue'),
  ])

  assert.match(stock, /风险状态/)
  assert.match(stock, /批次号/)
  assert.match(stock, /生产日期/)
  assert.match(stock, /到期日期/)
  assert.match(stock, /function batchRisk/)
  assert.match(stock, /<el-tag[^>]*:type="batchRisk\(row\)\.type"/)
  assert.match(stock, /class="table-scroll"/)

  assert.match(returns, /const maxReturnQuantity\s*=\s*computed/)
  assert.match(returns, /const returnQuantityError\s*=\s*computed/)
  assert.match(returns, /:max="maxReturnQuantity"/)
  assert.match(returns, /v-if="returnQuantityError"/)
  assert.match(returns, /returnQuantityError\.value/)
  assert.match(returns, /const varianceStatus\s*=\s*row\s*=>/)
  assert.match(returns, /盘亏/)
  assert.match(returns, /盘盈/)
  assert.match(returns, /盘平/)
  assert.match(returns, /<el-tag[^>]*:type="varianceStatus\(row\)\.type"/)

  assert.match(analysis, /categorySummary/)
  assert.match(analysis, /riskSummary/)
  assert.match(analysis, /chart-empty/)
  assert.match(analysis, /onBeforeUnmount/)
})

test('inventory keeps supported product paging, return-partner traceability, and finite stocktake quantities', async () => {
  const [stock, returns] = await Promise.all([readView('Stock.vue'), readView('Returns.vue')])

  assert.match(stock, /getProducts\(\{ page_size: 100, is_active: true \}\)/)
  assert.doesNotMatch(stock, /page_size: 1000/)

  assert.match(returns, /getCustomers/)
  assert.match(returns, /getSuppliers/)
  assert.match(returns, /partner_id: null/)
  assert.match(returns, /客户退货需要选择客户/)
  assert.match(returns, /供应商退货需要选择供应商/)
  assert.match(returns, /createReturn\(returnForm\)/)

  const predicateSource = returns.match(/function isFiniteNonNegative\(value\) \{[\s\S]*?\n\}/)?.[0]
  assert.ok(predicateSource, 'Returns.vue must define a finite stocktake-quantity predicate')
  const isFiniteNonNegative = Function(`${predicateSource}; return isFiniteNonNegative`)()
  for (const value of [null, undefined, '', '   ', NaN, Infinity, -Infinity, -1]) {
    assert.equal(isFiniteNonNegative(value), false, `expected ${String(value)} to be rejected`)
  }
  assert.equal(isFiniteNonNegative(0), true)
  assert.equal(isFiniteNonNegative('2.5'), true)

  assert.match(returns, /const stockTakeQuantityError\s*=\s*row\s*=>/)
  assert.match(returns, /v-if="stockTakeQuantityError\(row\)"/)
  assert.match(returns, /if \(hasStockTakeErrors\.value\)/)
  assert.match(returns, /actual_quantity: Number\(item\.actual_quantity\)/)
})
