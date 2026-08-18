import { expect, test } from '@playwright/test'

const backendUrl = process.env.SELLHELP_E2E_BACKEND_URL || 'http://127.0.0.1:8005'
const password = 'sellhelp-e2e-password'
let saleOrderNo = ''

async function requestJson(path, options = {}) {
  const response = await fetch(`${backendUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  expect(response.ok, `${options.method || 'GET'} ${path} should succeed`).toBeTruthy()
  return response.status === 204 ? null : response.json()
}

async function signIn(page, username) {
  await page.goto('/login')
  await page.waitForTimeout(500)
  await page.locator('input').nth(0).fill(username)
  await page.locator('input').nth(1).fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL(/\/$/)
  const identity = await page.evaluate(async () => {
    const token = localStorage.getItem('sellhelp.auth.token')
    const response = await fetch('/api/auth/me', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    return { token, status: response.status, body: await response.text() }
  })
  expect(identity.token).toBeTruthy()
  expect(identity.status, identity.body).toBe(200)
}

async function signOut(page) {
  await page.locator('.user-avatar').click()
  await page.getByRole('menuitem', { name: '退出登录' }).click()
  await expect(page).toHaveURL(/\/login$/)
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function chooseOption(page, dialog, index, optionName) {
  await dialog.locator('.el-select').nth(index).click()
  const primaryLabel = escapeRegExp(optionName)
  await page.getByRole('option', { name: new RegExp(`^${primaryLabel}(?=\\s|$|当前库存)`) }).click()
}

test.describe.serial('critical inventory workflow', () => {
  test.beforeAll(async () => {
    for (const account of [
      { username: 'e2e-owner', display_name: 'E2E Owner', role_codes: ['owner'] },
      { username: 'e2e-warehouse', display_name: 'E2E Warehouse', role_codes: ['warehouse_operator'] },
      { username: 'e2e-sales', display_name: 'E2E Sales', role_codes: ['sales_clerk'] },
    ]) {
      await requestJson('/api/auth/users', { method: 'POST', body: JSON.stringify({ ...account, password }) })
    }
    await requestJson('/api/suppliers', { method: 'POST', body: JSON.stringify({ name: 'E2E 供应商' }) })
    await requestJson('/api/products', {
      method: 'POST',
      body: JSON.stringify({ name: 'E2E 测试商品', unit: '箱', purchase_price: 10, wholesale_price: 15, retail_price: 18 }),
    })
    await requestJson('/api/customers', {
      method: 'POST',
      body: JSON.stringify({ name: 'E2E 客户', customer_type: '小店', credit_limit: 10_000 }),
    })
    await requestJson('/api/system/config/standalone_mode?value=false&description=Playwright%20isolated%20test', { method: 'PUT' })
  })

  test('warehouse stock-in, sales clerk sale, warehouse return and count, owner export', async ({ page }) => {
    const apiFailures = []
    page.on('response', response => {
      if (new URL(response.url()).pathname.startsWith('/api/') && response.status() >= 400) {
        apiFailures.push(`${response.status()} ${new URL(response.url()).pathname}`)
      }
    })
    await signIn(page, 'e2e-warehouse')
    await page.goto('/purchase')
    await page.waitForTimeout(1_000)
    expect(apiFailures.filter(failure => failure !== '401 /api/auth/me')).toEqual([])
    await page.getByRole('button', { name: '新建入库单' }).click()
    const purchaseDialog = page.getByRole('dialog', { name: '新建入库单' })
    await chooseOption(page, purchaseDialog, 0, 'E2E 供应商')
    await chooseOption(page, purchaseDialog, 1, 'E2E 测试商品')
    const purchaseLine = purchaseDialog.locator('.purchase-line')
    await purchaseLine.getByRole('textbox', { name: '批次号' }).fill('E2E-BATCH-001')
    await purchaseLine.getByRole('spinbutton', { name: '入库数量' }).fill('12')
    await purchaseLine.getByRole('spinbutton', { name: '入库单价' }).fill('10')
    await purchaseDialog.getByRole('button', { name: '确认入库' }).click()
    await page.getByRole('button', { name: '确认提交' }).click()
    await expect(purchaseDialog).toBeHidden()
    await expect(page.getByRole('row', { name: /E2E 供应商/ })).toBeVisible()

    await signOut(page)
    await signIn(page, 'e2e-sales')
    await page.goto('/sales')
    await page.getByRole('button', { name: '新建销售单' }).click()
    const salesDialog = page.getByRole('dialog', { name: '新建销售单' })
    await chooseOption(page, salesDialog, 0, 'E2E 客户')
    await chooseOption(page, salesDialog, 1, 'E2E 测试商品')
    await salesDialog.getByRole('button', { name: '确认开单' }).click()
    await page.getByRole('button', { name: '确认提交' }).click()
    await expect(salesDialog).toBeHidden()
    saleOrderNo = (await page.locator('.business-table .el-table__body tbody tr').first().locator('td').first().innerText()).trim()
    expect(saleOrderNo).toMatch(/^SO/)

    await signOut(page)
    await signIn(page, 'e2e-warehouse')
    await page.goto('/returns')
    await page.getByRole('button', { name: '客户退货' }).click()
    const returnDialog = page.getByRole('dialog', { name: '客户退货' })
    await returnDialog.getByPlaceholder('原销售单/入库单号').fill(saleOrderNo)
    await chooseOption(page, returnDialog, 0, 'E2E 客户')
    await chooseOption(page, returnDialog, 1, 'E2E 测试商品')
    await returnDialog.locator('.el-input-number input').fill('1')
    await returnDialog.getByRole('button', { name: '确认退货' }).click()
    await expect(returnDialog).toBeHidden()
    await expect(page.getByText(saleOrderNo, { exact: true })).toBeVisible()

    await page.getByRole('button', { name: '库存盘点' }).click()
    const stockTakeDialog = page.getByRole('dialog', { name: '库存盘点' })
    await expect(stockTakeDialog.getByText('E2E 测试商品', { exact: true })).toBeVisible()
    await stockTakeDialog.getByRole('button', { name: '确认盘点结果' }).click()
    await page.getByRole('button', { name: '确认提交' }).click()
    await expect(stockTakeDialog).toBeHidden()

    await signOut(page)
    await signIn(page, 'e2e-owner')
    await page.goto('/stock')
    await expect(page.getByRole('button', { name: '导出' })).toBeVisible()
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出' }).click()
    await page.getByRole('menuitem', { name: '下载 XLSX' }).click()
    expect((await download).suggestedFilename()).toMatch(/\.xlsx$/)
  })

  test('authenticated reload keeps the JWT for product data requests', async ({ page }) => {
    const failures = []
    page.on('response', response => {
      if (new URL(response.url()).pathname.startsWith('/api/') && response.status() >= 400) {
        failures.push(`${response.status()} ${new URL(response.url()).pathname}`)
      }
    })

    await signIn(page, 'e2e-owner')
    failures.length = 0
    await page.goto('/products')
    await expect(page).toHaveURL(/\/products$/)
    await page.waitForTimeout(500)
    expect(failures).toEqual([])
  })

  test('warehouse dashboard does not fail on owner-only slow-product data', async ({ page }) => {
    const failures = []
    page.on('response', response => {
      if (new URL(response.url()).pathname === '/api/system/slow-products') {
        failures.push(response.status())
      }
    })

    await signIn(page, 'e2e-warehouse')
    await page.goto('/')
    await expect(page.getByText('数据未能完整加载，请检查服务后重试。')).toHaveCount(0)
    expect(failures).toEqual([])
  })

  test('expanded sidebar scrolls to every navigation group', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 })
    await signIn(page, 'e2e-owner')

    await page.locator('.el-sub-menu__title').last().click()
    await page.waitForTimeout(300)
    await page.locator('.el-sub-menu__title').first().click()
    await page.waitForTimeout(300)

    const aside = page.locator('.app-aside')
    await expect.poll(() => aside.evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true)
    await aside.hover()
    await page.mouse.wheel(0, 600)
    await expect.poll(() => aside.evaluate(element => element.scrollTop)).toBeGreaterThan(0)
    await expect(page.getByText('审计日志', { exact: true })).toBeVisible()
  })

  test('non-owner roles cannot access owner navigation, pages, or exports', async ({ page }) => {
    await signIn(page, 'e2e-warehouse')
    await expect(page.getByText('报表中心', { exact: true })).toHaveCount(0)
    await page.goto('/reports')
    await expect(page).toHaveURL(/\/$/)
    await page.goto('/stock')
    await expect(page.getByRole('button', { name: '导出' })).toHaveCount(0)

    await signOut(page)
    await signIn(page, 'e2e-sales')
    await expect(page.getByText('库存查询', { exact: true })).toHaveCount(0)
    await page.goto('/stock')
    await expect(page).toHaveURL(/\/$/)
    await page.goto('/reports')
    await expect(page).toHaveURL(/\/$/)
  })
})
