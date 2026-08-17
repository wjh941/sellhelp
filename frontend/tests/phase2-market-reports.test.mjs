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

test('pricing only confirms loaded history records with a durable id', async () => {
  const source = await readView('Pricing')

  assert.match(source, /本次分析接口未返回可确认记录/)
  assert.match(source, /const confirmHistoryReference\s*=\s*async row =>/)
  assert.match(source, /confirmPricing\(row\.id,/)
  assert.doesNotMatch(source, /pricingReferenceId/)
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

test('reports maps categories from loaded products, guards CSV formulas, and excludes history from print', async () => {
  const source = await readView('Reports')
  const serializerSource = source.match(/const serializeCsvCell = value => \{[\s\S]*?\n\}/)?.[0]

  assert.match(source, /getProducts/)
  assert.match(source, /const productCategories\s*=\s*ref\(new Map\(\)\)/)
  assert.match(source, /const loadReportProducts\s*=\s*async/)
  assert.match(source, /productCategories\.value\.get\(String\(row\.product_id\)\)/)
  assert.match(source, /class="page-card screen-only"/)
  assert.match(source, /@media print[\s\S]*?\.screen-only\s*\{\s*display:\s*none !important;/)
  assert.ok(serializerSource, 'Reports.vue must serialize CSV cells safely')

  const serializeCsvCell = Function(`${serializerSource}; return serializeCsvCell`)()
  assert.equal(serializeCsvCell('=1+1'), `"'=1+1"`)
  assert.equal(serializeCsvCell('  @SUM(A1)'), `"  '@SUM(A1)"`)
  assert.equal(serializeCsvCell('plain "text"'), `"plain ""text"""`)
})
