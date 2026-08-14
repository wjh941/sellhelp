import assert from 'node:assert/strict'
import test from 'node:test'

import { sanitizeExternalSourceUrl } from '../src/utils/externalMarket.js'

test('sanitizeExternalSourceUrl allows an absolute HTTPS source URL', () => {
  assert.equal(sanitizeExternalSourceUrl('https://source.example.test/quotes/1'), 'https://source.example.test/quotes/1')
})

test('sanitizeExternalSourceUrl rejects unsafe and non-absolute URLs', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,unsafe', 'https://%', '/quotes/1']) {
    assert.equal(sanitizeExternalSourceUrl(value), null)
  }
})
