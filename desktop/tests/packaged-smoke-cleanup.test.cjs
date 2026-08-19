const assert = require('node:assert/strict')
const test = require('node:test')

const { shouldRunCleanupUninstaller } = require('./packaged-smoke-cleanup.cjs')

test('packaged smoke runs the finally uninstaller only when normal uninstall did not complete', () => {
  assert.equal(shouldRunCleanupUninstaller({ uninstalled: true, uninstallerExists: true }), false)
  assert.equal(shouldRunCleanupUninstaller({ uninstalled: false, uninstallerExists: true }), true)
  assert.equal(shouldRunCleanupUninstaller({ uninstalled: false, uninstallerExists: false }), false)
})
