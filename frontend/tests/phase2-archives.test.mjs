import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const readView = name => fs.readFileSync(path.join(root, 'src', 'views', name), 'utf8')

test('archive workspaces expose the required archive contracts', () => {
  const products = readView('Products.vue')
  const customers = readView('Customers.vue')
  const suppliers = readView('Suppliers.vue')

  assert.match(products, /table-view|card-view|viewMode/, 'products need a visible table/card switch')
  assert.match(products, /localStorage/, 'products need local layout preferences')
  assert.match(products, /safe_stock/, 'products need safe stock visibility')
  assert.match(products, /near_expiry_stock|expiry|临期/, 'products need expiry risk visibility')
  assert.match(products, /dblclick|inline|inlineEdit/, 'products need guarded inline editing')
  assert.match(products, /remark|safe_stock/, 'inline editing scope must include note/safe stock fields')
  assert.match(products, /purchase_price|retail_price|wholesale_price|vip_price/, 'price fields remain formal fields')
  assert.match(products, /const inlineSaving = ref\(false\)/, 'inline edit requests need a pending-save guard')

  assert.match(customers, /晨升膳食|VIP/, 'customers need the named VIP marker')
  assert.match(customers, /current_debt/, 'customers need debt field and status')
  assert.match(customers, /total_consumption/, 'customers need consumption field')
  assert.match(suppliers, /contact_person/, 'suppliers need readable contact field')
  assert.match(suppliers, /cooperation_status/, 'suppliers need readable status field')
})

test('product inline saves serialize edit sessions before changing another row', () => {
  const products = readView('Products.vue')
  const start = products.indexOf('const startInlineEdit')
  const confirm = products.indexOf('const confirmInlineEdit')
  const gate = products.indexOf('if (inlineSaving.value)', start)
  const savingSet = products.indexOf('inlineSaving.value = true', confirm)
  const update = products.indexOf('await updateProduct', confirm)
  const rollback = products.indexOf('row[field] = previous', confirm)
  const savingClear = products.indexOf('inlineSaving.value = false', confirm)

  assert.ok(gate > start && gate < confirm, 'starting another inline edit must be blocked while a save is pending')
  assert.ok(savingSet > confirm && savingSet < update, 'the pending-save guard must be set before the API request')
  assert.ok(rollback > update && rollback < savingClear, 'a failed save must restore its captured value before unlocking')
  assert.ok(savingClear > update, 'the pending-save guard must clear after the API request settles')
})
