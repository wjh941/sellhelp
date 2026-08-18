const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const test = require('node:test')

const packagePath = path.join(__dirname, '..', 'package.json')

test('desktop package creates an x64 NSIS installer from bundled resources', () => {
  const manifest = JSON.parse(readFileSync(packagePath, 'utf8'))
  const build = manifest.build

  assert.equal(build.appId, 'com.sellhelp.desktop')
  assert.deepEqual(build.win.target, ['nsis'])
  assert.equal(Object.hasOwn(build.win, 'arch'), false)
  assert.match(manifest.scripts.dist, /--win nsis --x64/)
  assert.equal(build.nsis.deleteAppDataOnUninstall, false)
  assert.equal(build.directories.output, 'release')

  assert.deepEqual(build.extraResources, [
    { from: '../backend/dist/SellHelpBackend', to: 'backend', filter: ['**/*'] },
    { from: '../frontend/dist', to: 'frontend', filter: ['**/*'] },
  ])
})

test('desktop build script propagates a failing native command', () => {
  const scriptPath = path.join(__dirname, '..', '..', 'scripts', 'build-desktop.ps1')
  const powershell = [
    "$ErrorActionPreference = 'Stop'",
    `. '${scriptPath.replace(/'/g, "''")}' -SkipBuild`,
    "Invoke-Checked -Description 'intentional failure' -Command { cmd.exe /c exit 7 }",
  ].join('; ')
  const completed = spawnSync(
    'powershell.exe',
    ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', powershell],
    { encoding: 'utf8' },
  )

  assert.notEqual(completed.status, 0)
  assert.match(`${completed.stdout}${completed.stderr}`, /intentional failure failed with exit code 7/)
})
