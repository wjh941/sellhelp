import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

process.env.TZ = 'Asia/Shanghai'

import {
  UI_STORAGE_KEYS,
  readTheme,
  writeTheme,
  readJson,
  writeJson,
  removeKey,
  getCustomerUnitPrice,
  getOrderTotals,
  getDaysToExpiry,
  buildSalesPayload,
  buildPurchasePayload,
} from '../src/utils/operationUi.js'

class MemoryStorage {
  #values = new Map()

  getItem(key) { return this.#values.has(key) ? this.#values.get(key) : null }
  setItem(key, value) { this.#values.set(key, String(value)) }
  removeItem(key) { this.#values.delete(key) }
}

test('uses local-only storage keys and safely handles invalid JSON', () => {
  assert.deepEqual(UI_STORAGE_KEYS, {
    theme: 'yingtai.ui.theme',
    salesDraft: 'yingtai.draft.sales',
    purchaseDraft: 'yingtai.draft.purchase',
    ignoredRisks: 'yingtai.ignored.dashboard-risks',
  })
  const storage = new MemoryStorage()
  storage.setItem('broken', '{not json')
  assert.deepEqual(readJson(storage, 'broken', { fallback: true }), { fallback: true })
  assert.deepEqual(readJson(null, 'broken', ['fallback']), ['fallback'])
})

test('accepts only light and dark themes without overwriting invalid values', () => {
  const storage = new MemoryStorage()
  storage.setItem(UI_STORAGE_KEYS.theme, 'dark')
  assert.equal(readTheme(storage, 'light'), 'dark')
  assert.equal(writeTheme('dark', storage), true)
  assert.equal(storage.getItem(UI_STORAGE_KEYS.theme), 'dark')
  assert.equal(readTheme(storage), 'dark')
  assert.equal(writeTheme('light', storage), true)
  assert.equal(readTheme(storage), 'light')
  assert.equal(writeTheme('sepia', storage), false)
  assert.equal(readTheme(storage), 'light')
  storage.setItem(UI_STORAGE_KEYS.theme, 'unknown')
  assert.equal(readTheme(storage, 'dark'), 'dark')
})

test('persists a dark theme preference', () => {
  const storage = new MemoryStorage()
  assert.equal(writeTheme('dark', storage), true)
  assert.equal(readTheme(storage), 'dark')
})

test('defines complete Element Plus dark theme tokens', async () => {
  const styles = await readFile(new URL('../src/styles/main.scss', import.meta.url), 'utf8')
  const darkTheme = styles.match(/:root\[data-theme='dark'\]\s*\{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(darkTheme, /--el-bg-color-overlay: #2C313A;/)
  assert.match(darkTheme, /--el-fill-color: #2C313A;/)
  assert.match(darkTheme, /--el-fill-color-disabled: #2C313A;/)
  const darkStatusTokens = {
    primary: ['92, 145, 255', '#5C91FF', '#2F63C7', '#254A96', '#1D376B', '#192E58', '#152541', '#7AA6FF'],
    success: ['69, 212, 131', '#45D483', '#278F59', '#246D46', '#1D5036', '#1A442F', '#173B2A', '#6BE09B'],
    warning: ['255, 174, 87', '#FFAE57', '#B97031', '#8A572B', '#644020', '#53371D', '#463019', '#FFC477'],
    danger: ['255, 120, 120', '#FF7878', '#B9474B', '#8A393D', '#652D31', '#54282B', '#472326', '#FF9696'],
    error: ['255, 120, 120', '#FF7878', '#B9474B', '#8A393D', '#652D31', '#54282B', '#472326', '#FF9696'],
  }

  for (const [color, [rgb, base, light3, light5, light7, light8, light9, dark2]] of Object.entries(darkStatusTokens)) {
    assert.match(darkTheme, new RegExp(`--el-color-${color}: ${base};`))
    assert.match(darkTheme, new RegExp(`--el-color-${color}-rgb: ${rgb};`))
    for (const [shade, value] of [[3, light3], [5, light5], [7, light7], [8, light8], [9, light9]]) {
      assert.match(darkTheme, new RegExp(`--el-color-${color}-light-${shade}: ${value};`))
    }
    assert.match(darkTheme, new RegExp(`--el-color-${color}-dark-2: ${dark2};`))
  }
})

test('writes and removes JSON values without throwing on unavailable storage', () => {
  const storage = new MemoryStorage()
  assert.equal(writeJson(storage, 'draft', { count: 2 }), true)
  assert.deepEqual(readJson(storage, 'draft', null), { count: 2 })
  assert.equal(removeKey(storage, 'draft'), true)
  assert.equal(readJson(storage, 'draft', null), null)
  assert.equal(writeJson(null, 'draft', { count: 2 }), false)
  assert.equal(removeKey(null, 'draft'), false)
})

test('keeps the sales draft local until a successful order submission clears it', () => {
  const storage = new MemoryStorage()
  const draft = {
    customer_id: 7,
    payment_type: '赊账',
    items: [{ product_id: 11, quantity: 2, unit_price: 8 }],
  }

  assert.equal(writeJson(storage, UI_STORAGE_KEYS.salesDraft, draft), true)
  assert.deepEqual(readJson(storage, UI_STORAGE_KEYS.salesDraft, null), draft)
  assert.equal(removeKey(storage, UI_STORAGE_KEYS.salesDraft), true)
  assert.equal(readJson(storage, UI_STORAGE_KEYS.salesDraft, null), null)
})

test('sales workspace keeps its create-order safety contract', async () => {
  const source = await readFile(new URL('../src/views/Sales.vue', import.meta.url), 'utf8')

  assert.match(source, /<el-dialog[\s\S]*?draggable/)
  assert.match(source, /const onWindowKeydown\s*=\s*event\s*=>/)
  assert.match(source, /window\.removeEventListener\('keydown',\s*onWindowKeydown\)/)
  assert.match(source, /createSalesOrder\(buildSalesPayload\(newOrder\)\)/)
  assert.match(source, /window\.print\(\)/)
  assert.doesNotMatch(source, /createSalesOrder\(newOrder\)/)
})

test('persists ignored dashboard risks and restores only the dashboard preference', () => {
  const storage = new MemoryStorage()
  const ignored = ['expiry:batch-17', 'low-stock:product-4']
  assert.equal(writeJson(storage, UI_STORAGE_KEYS.ignoredRisks, ignored), true)
  assert.deepEqual(readJson(storage, UI_STORAGE_KEYS.ignoredRisks, []), ignored)
  storage.setItem(UI_STORAGE_KEYS.salesDraft, '{"customer_id": 9}')
  assert.equal(removeKey(storage, UI_STORAGE_KEYS.ignoredRisks), true)
  assert.deepEqual(readJson(storage, UI_STORAGE_KEYS.ignoredRisks, []), [])
  assert.equal(storage.getItem(UI_STORAGE_KEYS.salesDraft), '{"customer_id": 9}')
})

test('falls back when a legacy ignored-risk preference is valid JSON but not an array', () => {
  const storage = new MemoryStorage()
  storage.setItem(UI_STORAGE_KEYS.ignoredRisks, '{"legacy":true}')
  const saved = readJson(storage, UI_STORAGE_KEYS.ignoredRisks, [])
  const ignored = Array.isArray(saved) ? saved : []
  assert.deepEqual(ignored, [])
})

test('dashboard uses a named resize listener with unmount cleanup', async () => {
  const source = await readFile(new URL('../src/views/Dashboard.vue', import.meta.url), 'utf8')
  assert.match(source, /const onWindowResize\s*=\s*\(\)\s*=>/)
  assert.match(source, /window\.addEventListener\('resize',\s*onWindowResize\)/)
  assert.match(source, /onBeforeUnmount\(\(\)\s*=>\s*\{[\s\S]*window\.removeEventListener\('resize',\s*onWindowResize\)[\s\S]*\}\)/)
})

test('dashboard mounts chart containers before rendering chart instances', async () => {
  const source = await readFile(new URL('../src/views/Dashboard.vue', import.meta.url), 'utf8')
  const loadBlock = source.match(/const loadData = async \(\) => \{[\s\S]*?\n\}/)?.[0] || ''
  assert.ok(loadBlock.indexOf('loading.value = false') < loadBlock.indexOf('await nextTick()'))
  assert.ok(loadBlock.indexOf('await nextTick()') < loadBlock.indexOf('renderCharts()'))
})

test('dashboard gives hot and slow product rows semantic status tags', async () => {
  const source = await readFile(new URL('../src/views/Dashboard.vue', import.meta.url), 'utf8')
  assert.match(source, /v-for="row in hotProducts\.slice\(0, 3\)"[\s\S]*?<el-tag type="success"[^>]*>热销<\/el-tag>/)
  assert.match(source, /v-for="row in slowProducts\.slice\(0, 3\)"[\s\S]*?<el-tag type="warning"[^>]*>30 天滞销<\/el-tag>/)
})

test('dashboard resizes the product trend chart only after expanding it', async () => {
  const source = await readFile(new URL('../src/views/Dashboard.vue', import.meta.url), 'utf8')
  const toggleBlock = source.match(/const toggleSection = async section => \{[\s\S]*?\n\}/)?.[0] || ''
  assert.match(toggleBlock, /section === 'productTrend' && !collapsed\.value\.productTrend/)
  assert.ok(toggleBlock.indexOf('await nextTick()') < toggleBlock.indexOf('productTrendChart?.resize()'))
  const afterTick = toggleBlock.slice(toggleBlock.indexOf('await nextTick()'))
  assert.match(afterTick, /if \(!collapsed\.value\.productTrend\) \{\s*productTrendChart\?\.resize\(\)/)
})

test('dashboard normalizes a non-array ignored-risk preference before creating reactive state', async () => {
  const source = await readFile(new URL('../src/views/Dashboard.vue', import.meta.url), 'utf8')
  assert.match(source, /const savedIgnoredRiskIds = readJson\(window\.localStorage, UI_STORAGE_KEYS\.ignoredRisks, \[\]\)/)
  assert.match(source, /const ignoredRiskIds = ref\(Array\.isArray\(savedIgnoredRiskIds\) \? savedIgnoredRiskIds : \[\]\)/)
})

test('selects VIP, retail, and wholesale customer prices', () => {
  const product = { vip_price: 7, retail_price: 9, wholesale_price: 5 }
  assert.equal(getCustomerUnitPrice(product, { is_vip: true, customer_type: '散户' }), 7)
  assert.equal(getCustomerUnitPrice(product, { is_vip: false, customer_type: 'VIP' }), 7)
  assert.equal(getCustomerUnitPrice(product, { customer_type: '散户' }), 9)
  assert.equal(getCustomerUnitPrice(product, { customer_type: '批发' }), 5)
})

test('calculates order amount and profit from numeric item values', () => {
  assert.deepEqual(getOrderTotals([
    { quantity: 2, unit_price: 10, cost_price: 6 },
    { quantity: '3', unit_price: '4.5', cost_price: '2' },
  ]), { amount: 33.5, profit: 15.5 })
  assert.deepEqual(getOrderTotals([]), { amount: 0, profit: 0 })
})

test('returns whole calendar days to expiry and null for no expiry', () => {
  assert.equal(getDaysToExpiry('2026-08-20', '2026-08-14T23:59:00+08:00'), 6)
  assert.equal(getDaysToExpiry('2026-08-13', '2026-08-14T00:01:00+08:00'), -1)
  assert.equal(getDaysToExpiry('2026-08-20', new Date('2026-08-14T01:00:00+08:00')), 6)
  assert.equal(getDaysToExpiry(null, '2026-08-14'), null)
})

test('strips UI-only fields from sales payload and conditionally includes paid amount', () => {
  const order = {
    customer_id: 3, sale_date: '2026-08-14', operator: 'A', remark: 'note',
    payment_type: '部分结账', paid_amount: 12, product_info: { name: 'x' },
    items: [{ product_id: 9, quantity: 2, unit_price: 4, cost_price: 3, product_info: {} }],
  }
  assert.deepEqual(buildSalesPayload(order), {
    customer_id: 3, sale_date: '2026-08-14', operator: 'A', remark: 'note',
    payment_type: '部分结账', paid_amount: 12,
    items: [{ product_id: 9, quantity: 2, unit_price: 4 }],
  })
  assert.equal(Object.hasOwn(buildSalesPayload({ ...order, payment_type: '现结' }), 'paid_amount'), false)
})

test('preserves purchase batch fields while stripping UI-only fields', () => {
  assert.deepEqual(buildPurchasePayload({
    supplier_id: 2, purchase_date: '2026-08-14', operator: 'B', remark: 'buy',
    items: [{ product_id: 8, batch_no: 'B-1', production_date: '2026-01-01', expiry_date: '2027-01-01', quantity: 5, unit_price: 11, remark: 'cold', cost_price: 9, product_info: {} }],
  }), {
    supplier_id: 2, purchase_date: '2026-08-14', operator: 'B', remark: 'buy',
    items: [{ product_id: 8, batch_no: 'B-1', production_date: '2026-01-01', expiry_date: '2027-01-01', quantity: 5, unit_price: 11, remark: 'cold' }],
  })
})
