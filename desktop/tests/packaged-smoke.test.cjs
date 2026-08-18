const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')
const path = require('node:path')
const test = require('node:test')

const smokeScript = path.join(__dirname, 'packaged-smoke.cjs')

test('packaged smoke reports a missing NSIS installer as a non-success precondition', () => {
  const missingInstaller = path.join(__dirname, 'does-not-exist.exe')
  const completed = spawnSync(process.execPath, [smokeScript, '--installer', missingInstaller], {
    encoding: 'utf8',
  })

  assert.equal(completed.status, 2)
  assert.match(`${completed.stdout}${completed.stderr}`, /NSIS installer was not found/)
  assert.match(`${completed.stdout}${completed.stderr}`, /SellHelp Setup 1\.0\.0\.exe/)
})
