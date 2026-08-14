export const UI_STORAGE_KEYS = Object.freeze({
  theme: 'yingtai.ui.theme',
  salesDraft: 'yingtai.draft.sales',
  purchaseDraft: 'yingtai.draft.purchase',
  ignoredRisks: 'yingtai.ignored.dashboard-risks',
})

export function readTheme(storage, fallback = 'light') {
  let theme = fallback
  try {
    if (storage && typeof storage.getItem === 'function') theme = storage.getItem(UI_STORAGE_KEYS.theme) || fallback
  } catch {
    theme = fallback
  }
  return theme === 'light' || theme === 'dark' ? theme : fallback
}

export function writeTheme(theme, storage) {
  if (theme !== 'light' && theme !== 'dark') return false
  return writeJson(storage, UI_STORAGE_KEYS.theme, theme)
}

export function readJson(storage, key, fallback) {
  try {
    if (!storage || typeof storage.getItem !== 'function') return fallback
    const value = storage.getItem(key)
    return value == null ? fallback : JSON.parse(value)
  } catch {
    return fallback
  }
}

export function writeJson(storage, key, value) {
  try {
    if (!storage || typeof storage.setItem !== 'function') return false
    storage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export function removeKey(storage, key) {
  try {
    if (!storage || typeof storage.removeItem !== 'function') return false
    storage.removeItem(key)
    return true
  } catch {
    return false
  }
}

export function getCustomerUnitPrice(product = {}, customer = {}) {
  if (customer.is_vip || customer.customer_type === 'VIP') return product.vip_price
  if (customer.customer_type === '散户') return product.retail_price
  return product.wholesale_price
}

export function getOrderTotals(items = []) {
  return items.reduce((totals, item = {}) => {
    const quantity = Number(item.quantity) || 0
    const unitPrice = Number(item.unit_price) || 0
    const costPrice = Number(item.cost_price) || 0
    totals.amount += quantity * unitPrice
    totals.profit += quantity * (unitPrice - costPrice)
    return totals
  }, { amount: 0, profit: 0 })
}

function calendarDate(value) {
  if (value instanceof Date) return value.toISOString().slice(0, 10)
  if (typeof value !== 'string' || !value) return null
  return value.slice(0, 10)
}

export function getDaysToExpiry(expiryDate, now = new Date()) {
  const expiry = calendarDate(expiryDate)
  if (!expiry) return null
  const current = calendarDate(now)
  if (!current) return null
  return Math.round((Date.parse(`${expiry}T00:00:00Z`) - Date.parse(`${current}T00:00:00Z`)) / 86400000)
}

export function buildSalesPayload(order = {}) {
  const payload = {
    customer_id: order.customer_id,
    sale_date: order.sale_date,
    operator: order.operator,
    remark: order.remark,
    payment_type: order.payment_type,
    items: (order.items || []).map(({ product_id, quantity, unit_price }) => ({ product_id, quantity, unit_price })),
  }
  if (order.payment_type === '部分结账') payload.paid_amount = order.paid_amount
  return payload
}

export function buildPurchasePayload(order = {}) {
  return {
    supplier_id: order.supplier_id,
    purchase_date: order.purchase_date,
    operator: order.operator,
    remark: order.remark,
    items: (order.items || []).map(({ product_id, batch_no, production_date, expiry_date, quantity, unit_price, remark }) => ({
      product_id, batch_no, production_date, expiry_date, quantity, unit_price, remark,
    })),
  }
}
