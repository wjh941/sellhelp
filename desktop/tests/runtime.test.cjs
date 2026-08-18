const assert = require('node:assert/strict')
const test = require('node:test')

const { backendCommand, waitForHealth } = require('../runtime.cjs')

test('backend command targets the packaged executable and loopback arguments', () => {
  const result = backendCommand(
    'C:/app/resources',
    'C:/Users/a/AppData/Local/SellHelp',
    18101,
  )

  assert.equal(result.command, 'C:/app/resources/backend/SellHelpBackend.exe')
  assert.deepEqual(result.args, [
    '--data-dir',
    'C:/Users/a/AppData/Local/SellHelp',
    '--static-dir',
    'C:/app/resources/frontend',
    '--port',
    '18101',
  ])
})

test('health wait rejects with the final cause after its deadline', async () => {
  await assert.rejects(
    waitForHealth('http://127.0.0.1:9/api/health', 25),
    /Desktop backend did not become healthy/,
  )
})
