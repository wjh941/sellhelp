const assert = require('node:assert/strict')
const test = require('node:test')

const {
  backendCommand,
  resolveDesktopDataDirectory,
  waitForHealth,
} = require('../runtime.cjs')

test('desktop data directory uses Windows LOCALAPPDATA and only permits development overrides', () => {
  assert.equal(
    resolveDesktopDataDirectory({
      isPackaged: true,
      localAppData: 'C:/Users/a/AppData/Local',
    }),
    'C:/Users/a/AppData/Local/SellHelp',
  )
  assert.equal(
    resolveDesktopDataDirectory({
      developmentDataDirectory: 'C:/temporary/SellHelp',
      isPackaged: false,
      localAppData: 'C:/Users/a/AppData/Local',
    }),
    'C:/temporary/SellHelp',
  )
  assert.equal(
    resolveDesktopDataDirectory({
      developmentDataDirectory: 'C:/temporary/SellHelp',
      isPackaged: true,
      localAppData: 'C:/Users/a/AppData/Local',
    }),
    'C:/Users/a/AppData/Local/SellHelp',
  )
})

test('desktop data directory rejects a missing Windows LOCALAPPDATA value', () => {
  assert.throws(
    () => resolveDesktopDataDirectory({ isPackaged: true }),
    /LOCALAPPDATA must be set/,
  )
})

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
