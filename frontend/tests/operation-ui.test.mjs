import test from 'node:test'
import assert from 'node:assert/strict'

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
  assert.equal(writeTheme('light', storage), true)
  assert.equal(readTheme(storage), 'light')
  assert.equal(writeTheme('sepia', storage), false)
  assert.equal(readTheme(storage), 'light')
  storage.setItem(UI_STORAGE_KEYS.theme, 'unknown')
  assert.equal(readTheme(storage, 'dark'), 'dark')
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
