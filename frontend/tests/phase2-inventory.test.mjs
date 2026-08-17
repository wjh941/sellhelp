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
