const assert = require('node:assert/strict')
const path = require('node:path')
const test = require('node:test')

const {
  isOwnedSmokeDirectory,
  smokeDirectoryPrefix,
} = require('./packaged-smoke-paths.cjs')

test('packaged smoke creates and cleans only its own LocalAppData directory', () => {
  const localAppData = path.join('C:', 'Users', 'tester', 'AppData', 'Local')
  const directory = path.join(localAppData, 'sellhelp-packaged-smoke-12345')

  assert.equal(smokeDirectoryPrefix(localAppData), path.join(localAppData, 'sellhelp-packaged-smoke-'))
  assert.equal(isOwnedSmokeDirectory(directory, localAppData), true)
  assert.equal(isOwnedSmokeDirectory(localAppData, localAppData), false)
  assert.equal(isOwnedSmokeDirectory(path.join(localAppData, 'other-directory'), localAppData), false)
})

test('packaged smoke requires a LocalAppData parent for executable installation', () => {
  assert.throws(() => smokeDirectoryPrefix(''), /LOCALAPPDATA must be set/)
})
