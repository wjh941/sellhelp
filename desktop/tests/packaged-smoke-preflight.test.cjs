const assert = require('node:assert/strict')
const test = require('node:test')

const { registeredSellHelpInstallations } = require('./packaged-smoke-preflight.cjs')

test('packaged smoke detects every registered SellHelp installation before invoking NSIS', () => {
  const registrations = JSON.stringify([
    { DisplayName: 'SellHelp', InstallLocation: 'C:\\Program Files\\SellHelp' },
    { DisplayName: 'SellHelp 1.0.0', InstallLocation: 'C:\\Program Files\\SellHelp 1.0.0' },
    { DisplayName: 'Another Application', InstallLocation: 'C:\\Program Files\\Other' },
    { DisplayName: 'sellhelp', InstallLocation: 'C:\\Users\\tester\\AppData\\Local\\SellHelp' },
  ])

  assert.deepEqual(registeredSellHelpInstallations(registrations), [
    'C:\\Program Files\\SellHelp',
    'C:\\Program Files\\SellHelp 1.0.0',
    'C:\\Users\\tester\\AppData\\Local\\SellHelp',
  ])
})

test('packaged smoke treats an empty uninstall registry query as no existing installation', () => {
  assert.deepEqual(registeredSellHelpInstallations(''), [])
  assert.deepEqual(registeredSellHelpInstallations('[]'), [])
})
