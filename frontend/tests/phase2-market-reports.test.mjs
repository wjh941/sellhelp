import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const readView = name => readFile(new URL(`../src/views/${name}.vue`, import.meta.url), 'utf8')

test('market timeline filters loaded records locally and keeps full remarks accessible', async () => {
  const source = await readView('Market')

  assert.match(source, /const filteredRecords\s*=\s*computed/)
  assert.match(source, /filterDate\.value\?\.length === 2/)
  assert.match(source, /<el-timeline/)
  assert.match(source, /expand|展开|收起/)
  assert.doesNotMatch(source, /@click="loadData"/)
})

test('pricing simulation calculates margin locally and never submits simulated prices', async () => {
  const source = await readView('Pricing')

  assert.match(source, /const simulationPrices\s*=\s*reactive/)
  assert.match(source, /const simulationMarginRate\s*=\s*computed/)
  assert.match(source, /仅供参考，不会自动修改商品售价/)
  assert.match(source, /模拟预览/)
  assert.match(source, /confirmPricing\(/)
  assert.doesNotMatch(source, /updateProduct\(/)
})

test('reports provides local filtering plus export and print controls', async () => {
  const source = await readView('Reports')

  assert.match(source, /const selectedCategory\s*=\s*ref/)
  assert.match(source, /const filteredHotProducts\s*=\s*computed/)
  assert.match(source, /const exportReport\s*=\s*\(\)\s*=>/)
  assert.match(source, /window\.print\(\)/)
  assert.match(source, /@click="exportReport"/)
  assert.match(source, /@click="printReport"/)
})
