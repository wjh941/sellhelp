const assert = require('node:assert/strict')
const { spawnSync } = require('node:child_process')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const test = require('node:test')

const packagePath = path.join(__dirname, '..', 'package.json')
const buildRequirementsPath = path.join(__dirname, '..', '..', 'backend', 'requirements-build.txt')
const productionRequirementsPath = path.join(__dirname, '..', '..', 'backend', 'requirements.txt')
const buildScriptPath = path.join(__dirname, '..', '..', 'scripts', 'build-desktop.ps1')

test('desktop package creates an x64 NSIS installer from bundled resources', () => {
  const manifest = JSON.parse(readFileSync(packagePath, 'utf8'))
  const build = manifest.build

  assert.equal(build.appId, 'com.sellhelp.desktop')
  assert.deepEqual(build.win.target, ['nsis'])
  assert.equal(Object.hasOwn(build.win, 'arch'), false)
  assert.equal(build.win.signAndEditExecutable, false)
  assert.match(manifest.scripts.dist, /--win nsis --x64/)
  assert.equal(build.nsis.deleteAppDataOnUninstall, false)
  assert.equal(build.directories.output, 'release')

  assert.deepEqual(build.extraResources, [
    { from: '../backend/dist/SellHelpBackend', to: 'backend', filter: ['**/*'] },
    { from: '../frontend/dist', to: 'frontend', filter: ['**/*'] },
  ])
})

test('desktop build script propagates a failing native command', () => {
  const powershell = [
    "$ErrorActionPreference = 'Stop'",
    `. '${buildScriptPath.replace(/'/g, "''")}' -SkipBuild`,
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

test('desktop build installs a complete exact Python dependency closure without resolving', () => {
  const buildScript = readFileSync(buildScriptPath, 'utf8')
  const buildRequirements = readFileSync(buildRequirementsPath, 'utf8')
  const productionRequirements = readFileSync(productionRequirementsPath, 'utf8')

  assert.match(
    buildScript,
    /python -m pip install --no-deps -r backend\\requirements-build\.txt/,
  )
  assert.doesNotMatch(buildScript, /--require-hashes/)
  assert.doesNotMatch(buildScript, /-r backend\\requirements\.txt/)

  const lockEntries = buildRequirements
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith('#'))
  assert.ok(lockEntries.length > 12)
  assert.ok(lockEntries.every((line) => /^[a-z0-9][a-z0-9_.-]*==[^\s]+$/.test(line)))

  const sourceRoots = productionRequirements
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith('#'))
    .map((line) => line.split('==')[0].toLowerCase())
  for (const packageName of [...sourceRoots, 'pyinstaller', 'altgraph', 'pefile', 'pyinstaller-hooks-contrib', 'pywin32-ctypes']) {
    assert.ok(lockEntries.some((entry) => entry.startsWith(`${packageName}==`)))
  }
})
