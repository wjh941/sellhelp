import assert from 'node:assert/strict'
import test from 'node:test'
import axios from 'axios'

const realCreate = axios.create
const requests = []

axios.create = (...args) => {
  const instance = realCreate(...args)
  instance.defaults.adapter = async (config) => {
    requests.push(config)
    return {
      config,
      data: { ok: true },
      headers: {},
      status: 200,
      statusText: 'OK'
    }
  }
  return instance
}

const externalMarketApi = await import('../src/api/index.js')
axios.create = realCreate

const lastRequest = () => requests.at(-1)
const body = (config) => config.data ? JSON.parse(config.data) : undefined

test('getExternalMarketQuotes sends quote filters as query parameters', async () => {
  await externalMarketApi.getExternalMarketQuotes({
    status: 'pending', product_id: 7, quote_kind: 'retail_sku', region: 'Dongguan, Guangdong'
  })

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'get', url: '/external-market-quotes',
    params: { status: 'pending', product_id: 7, quote_kind: 'retail_sku', region: 'Dongguan, Guangdong' }, data: undefined
  })
})

test('syncExternalMarketQuotes sends a bodyless sync request', async () => {
  await externalMarketApi.syncExternalMarketQuotes()

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'post', url: '/external-market-quotes/sync', params: undefined, data: undefined
  })
})

test('acceptExternalMarketQuote sends edited review values in the request body', async () => {
  await externalMarketApi.acceptExternalMarketQuote(12, {
    product_id: 7, price: 13.5, unit: 'box', trend: 'up', remark: 'verified', operator: 'Lin'
  })

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'post', url: '/external-market-quotes/12/accept', params: undefined,
    data: { product_id: 7, price: 13.5, unit: 'box', trend: 'up', remark: 'verified', operator: 'Lin' }
  })
})

test('dismissExternalMarketQuote sends its remark in the request body', async () => {
  await externalMarketApi.dismissExternalMarketQuote(12, { remark: 'not applicable' })

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'post', url: '/external-market-quotes/12/dismiss', params: undefined,
    data: { remark: 'not applicable' }
  })
})

test('getExternalMarketSyncStatus uses its fixed status path', async () => {
  await externalMarketApi.getExternalMarketSyncStatus()

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'get', url: '/external-market-sync/status', params: undefined, data: undefined
  })
})

test('updateExternalMarketSyncSchedule sends strict time data in the request body', async () => {
  await externalMarketApi.updateExternalMarketSyncSchedule({ sync_time: '02:15' })

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'put', url: '/external-market-sync/schedule', params: undefined, data: { sync_time: '02:15' }
  })
})

test('getClearSuggestion posts to the existing suggestion generator route', async () => {
  await externalMarketApi.getClearSuggestion(12)

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url, params: lastRequest().params, data: body(lastRequest()) }, {
    method: 'post', url: '/system/slow-products/12/clear-suggestion', params: undefined, data: undefined
  })
})
