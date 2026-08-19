const assert = require('node:assert/strict')
const { spawn, spawnSync } = require('node:child_process')
const { existsSync, mkdtempSync, rmSync } = require('node:fs')
const path = require('node:path')

const { findLoopbackPort } = require('../runtime.cjs')
const {
  findPackagedWindowTarget,
  isReadyPackagedWindowState,
} = require('./packaged-smoke-runtime.cjs')
const {
  isOwnedSmokeDirectory,
  smokeDirectoryPrefix,
} = require('./packaged-smoke-paths.cjs')

const PRECONDITION_EXIT_CODE = 2
const DEFAULT_INSTALLER = path.resolve(__dirname, '..', 'release', 'SellHelp Setup 1.0.0.exe')

class SmokePreconditionError extends Error {
  constructor(message) {
    super(message)
    this.exitCode = PRECONDITION_EXIT_CODE
  }
}

function parseInstallerPath(argv) {
  if (argv.length === 0) {
    return process.env.SELLHELP_DESKTOP_INSTALLER || DEFAULT_INSTALLER
  }
  if (argv.length === 2 && argv[0] === '--installer') {
    return argv[1]
  }
  throw new SmokePreconditionError('Usage: node tests/packaged-smoke.cjs [--installer <path-to-nsis-exe>]')
}

function requireInstaller(argv) {
  if (process.platform !== 'win32') {
    throw new SmokePreconditionError('Packaged smoke is Windows-only and must run against a Windows NSIS installer.')
  }
  const installerPath = path.resolve(parseInstallerPath(argv))
  if (!existsSync(installerPath)) {
    throw new SmokePreconditionError(
      `NSIS installer was not found: ${installerPath}. Expected release artifact: ${DEFAULT_INSTALLER}.`,
    )
  }
  return installerPath
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function waitForExit(child, timeoutMs, description) {
  return new Promise((resolve, reject) => {
    if (child.exitCode !== null) {
      resolve(child.exitCode)
      return
    }
    const timer = setTimeout(() => {
      reject(new Error(`${description} did not exit within ${timeoutMs}ms`))
    }, timeoutMs)
    child.once('error', (error) => {
      clearTimeout(timer)
      reject(error)
    })
    child.once('exit', (code) => {
      clearTimeout(timer)
      resolve(code ?? 1)
    })
  })
}

async function runChecked(command, args, options, description) {
  const child = spawn(command, args, { windowsHide: true, ...options })
  const exitCode = await waitForExit(child, 90_000, description)
  if (exitCode !== 0) {
    throw new Error(`${description} failed with exit code ${exitCode}`)
  }
}

async function stopProcessTree(child) {
  if (!child?.pid || child.exitCode !== null) {
    return
  }
  const killer = spawn('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {
    stdio: 'ignore',
    windowsHide: true,
  })
  await waitForExit(killer, 15_000, `taskkill for ${child.pid}`)
  await waitForExit(child, 15_000, `application process ${child.pid}`)
}

function temporaryDirectory() {
  return mkdtempSync(smokeDirectoryPrefix(process.env.LOCALAPPDATA))
}

function cleanTemporaryDirectory(directory) {
  if (!isOwnedSmokeDirectory(directory, process.env.LOCALAPPDATA)) {
    throw new Error(`Refusing to remove non-smoke directory: ${path.resolve(directory)}`)
  }
  rmSync(directory, { force: true, recursive: true })
}

function powershellText(script) {
  const completed = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script], {
    encoding: 'utf8',
    windowsHide: true,
  })
  if (completed.status !== 0) {
    throw new Error(`PowerShell inspection failed: ${completed.stderr || completed.stdout}`)
  }
  return completed.stdout.trim()
}

function backendProcessId(applicationPid) {
  const output = powershellText(
    `$children = Get-CimInstance Win32_Process -Filter 'ParentProcessId = ${applicationPid}'; $children | Where-Object { $_.Name -eq 'SellHelpBackend.exe' } | Select-Object -First 1 -ExpandProperty ProcessId`,
  )
  return /^\d+$/.test(output) ? Number(output) : null
}

function listeningPort(processId) {
  const output = powershellText(
    `Get-NetTCPConnection -State Listen -OwningProcess ${processId} | Where-Object { $_.LocalAddress -eq '127.0.0.1' } | Select-Object -First 1 -ExpandProperty LocalPort`,
  )
  return /^\d+$/.test(output) ? Number(output) : null
}

async function waitForBackendEndpoint(applicationPid) {
  const deadline = Date.now() + 45_000
  let lastError
  while (Date.now() < deadline) {
    try {
      const processId = backendProcessId(applicationPid)
      const port = processId ? listeningPort(processId) : null
      if (port) {
        const origin = `http://127.0.0.1:${port}`
        const health = await fetch(`${origin}/api/health`)
        if (health.ok) {
          return { origin, processId }
        }
        lastError = new Error(`Health endpoint returned ${health.status}`)
      }
    } catch (error) {
      lastError = error
    }
    await wait(250)
  }
  throw new Error(`Packaged backend did not become healthy${lastError ? `: ${lastError.message}` : ''}`)
}

async function waitForDebuggerPort(port) {
  const deadline = Date.now() + 20_000
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (response.ok) {
        return response.json()
      }
    } catch {
      // Electron has not opened its local debugger yet.
    }
    await wait(200)
  }
  throw new Error('Electron remote debugger did not become available for graceful shutdown')
}

function evaluatePackagedWindow(target) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(target.webSocketDebuggerUrl)
    const timeout = setTimeout(() => {
      socket.close()
      reject(new Error('Timed out evaluating the packaged Electron window'))
    }, 10_000)
    socket.addEventListener('open', () => {
      socket.send(JSON.stringify({
        id: 1,
        method: 'Runtime.evaluate',
        params: {
          expression: '({ origin: location.origin, appChildCount: document.querySelector("#app")?.childElementCount ?? 0 })',
          returnByValue: true,
        },
      }))
    }, { once: true })
    socket.addEventListener('error', () => {
      clearTimeout(timeout)
      reject(new Error('Could not connect to the packaged Electron window'))
    }, { once: true })
    socket.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.id !== 1) {
          return
        }
        clearTimeout(timeout)
        socket.close()
        resolve(message.result?.result?.value)
      } catch (error) {
        clearTimeout(timeout)
        socket.close()
        reject(error)
      }
    })
  })
}

async function waitForPackagedWindow(origin, debugPort) {
  const deadline = Date.now() + 30_000
  let lastError
  while (Date.now() < deadline) {
    try {
      const targets = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((response) => response.json())
      const target = findPackagedWindowTarget(targets, origin)
      if (target) {
        const state = await evaluatePackagedWindow(target)
        if (isReadyPackagedWindowState(state, origin)) {
          return
        }
        lastError = new Error('Packaged Electron window has not rendered the application root')
      }
    } catch (error) {
      lastError = error
    }
    await wait(250)
  }
  throw new Error(`Packaged Electron window did not render the local UI${lastError ? `: ${lastError.message}` : ''}`)
}

async function closeElectronGracefully(debugPort) {
  const version = await waitForDebuggerPort(debugPort)
  const socket = new WebSocket(version.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Timed out opening Electron debugger connection')), 10_000)
    socket.addEventListener('open', () => {
      clearTimeout(timeout)
      resolve()
    }, { once: true })
    socket.addEventListener('error', () => {
      clearTimeout(timeout)
      reject(new Error('Could not open Electron debugger connection'))
    }, { once: true })
  })
  socket.send(JSON.stringify({ id: 1, method: 'Browser.close' }))
  await Promise.race([
    new Promise((resolve) => socket.addEventListener('close', resolve, { once: true })),
    wait(10_000).then(() => {
      throw new Error('Electron did not close after Browser.close')
    }),
  ])
}

function processExists(processId) {
  const completed = spawnSync('tasklist.exe', ['/FI', `PID eq ${processId}`, '/NH'], {
    encoding: 'utf8',
    windowsHide: true,
  })
  return completed.status === 0 && completed.stdout.includes(String(processId))
}

async function verifyInstalledApplication(applicationPath, localAppData, debugPort, username, password) {
  const application = spawn(applicationPath, [`--remote-debugging-port=${debugPort}`], {
    env: {
      ...process.env,
      LOCALAPPDATA: localAppData,
      SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER: '1',
    },
    stdio: 'ignore',
    windowsHide: true,
  })
  let endpoint
  try {
    endpoint = await waitForBackendEndpoint(application.pid)
    await waitForPackagedWindow(endpoint.origin, debugPort)
    const health = await fetch(`${endpoint.origin}/api/health`)
    assert.equal(health.ok, true, 'health must be served by the loopback origin')
    const interfaceResponse = await fetch(`${endpoint.origin}/`)
    assert.equal(interfaceResponse.ok, true, 'frontend must be served by the same loopback origin')
    assert.match(interfaceResponse.headers.get('content-type') || '', /text\/html/i)
    const bootstrap = await fetch(`${endpoint.origin}/api/auth/bootstrap-status`).then((response) => response.json())
    if (bootstrap.can_initialize) {
      const created = await fetch(`${endpoint.origin}/api/auth/bootstrap-owner`, {
        body: JSON.stringify({ username, display_name: 'Packaged Smoke Owner', password }),
        headers: { 'content-type': 'application/json' },
        method: 'POST',
      })
      assert.equal(created.status, 201, 'first launch must persist an initial owner')
    }
    const loggedIn = await fetch(`${endpoint.origin}/api/auth/login`, {
      body: JSON.stringify({ username, password }),
      headers: { 'content-type': 'application/json' },
      method: 'POST',
    })
    assert.equal(loggedIn.ok, true, 'the installed application must authenticate the persisted owner')
    const { access_token: accessToken } = await loggedIn.json()
    assert.ok(accessToken, 'owner authentication must issue a local access token')
    const authorization = { authorization: `Bearer ${accessToken}` }

    if (bootstrap.can_initialize) {
      const productResponse = await fetch(`${endpoint.origin}/api/products`, {
        body: JSON.stringify({
          code: `SMOKE-${process.pid}`,
          name: `Packaged Smoke Product ${process.pid}`,
          purchase_price: 1,
          retail_price: 2,
          unit: 'item',
          wholesale_price: 1.5,
        }),
        headers: { 'content-type': 'application/json', ...authorization },
        method: 'POST',
      })
      assert.equal(productResponse.status, 200, 'first launch must persist a minimal product')
    } else {
      const productName = encodeURIComponent(`Packaged Smoke Product ${process.pid}`)
      const products = await fetch(`${endpoint.origin}/api/products?keyword=${productName}`, {
        headers: authorization,
      }).then((response) => response.json())
      assert.equal(products.total, 1, 'second launch must read the product stored before restart')
      assert.equal(products.items[0].name, `Packaged Smoke Product ${process.pid}`)

      const exported = await fetch(`${endpoint.origin}/api/export/stock-report?include_empty=true&format=xlsx`, {
        headers: authorization,
      })
      assert.equal(exported.ok, true, 'owner must export an XLSX report after restart')
      assert.match(exported.headers.get('content-type') || '', /spreadsheetml\.sheet/i)
      assert.ok((await exported.arrayBuffer()).byteLength > 100, 'XLSX export must contain document bytes')
    }
    await closeElectronGracefully(debugPort)
    const exitCode = await waitForExit(application, 20_000, 'gracefully closed SellHelp application')
    assert.equal(exitCode, 0, 'SellHelp should exit cleanly after the main window closes')
    assert.equal(processExists(endpoint.processId), false, 'backend child must exit with the Electron parent')
    return endpoint.origin
  } finally {
    await stopProcessTree(application)
  }
}

async function main() {
  const installer = requireInstaller(process.argv.slice(2))
  const root = temporaryDirectory()
  let uninstallerPath = null
  try {
    const installDirectory = path.join(root, 'application')
    const localAppData = path.join(root, 'local-app-data')
    await runChecked(installer, ['/S', `/D=${installDirectory}`], { stdio: 'ignore' }, 'NSIS installation')
    const applicationPath = path.join(installDirectory, 'SellHelp.exe')
    if (!existsSync(applicationPath)) {
      throw new Error(`NSIS installer did not create ${applicationPath}`)
    }
    uninstallerPath = path.join(installDirectory, 'Uninstall SellHelp.exe')

    const username = `packaged-smoke-${process.pid}`
    const password = `SellHelp-smoke-${process.pid}-password`
    const firstDebugPort = await findLoopbackPort()
    let secondDebugPort = await findLoopbackPort()
    while (secondDebugPort === firstDebugPort) {
      secondDebugPort = await findLoopbackPort()
    }
    await verifyInstalledApplication(applicationPath, localAppData, firstDebugPort, username, password)
    await verifyInstalledApplication(applicationPath, localAppData, secondDebugPort, username, password)
    const dataDatabase = path.join(localAppData, 'SellHelp', 'data', 'sellhelp.db')
    assert.equal(existsSync(dataDatabase), true, 'desktop data must exist before uninstallation')
    if (!existsSync(uninstallerPath)) {
      throw new Error(`NSIS installer did not create ${uninstallerPath}`)
    }
    await runChecked(uninstallerPath, ['/S'], { stdio: 'ignore' }, 'NSIS uninstallation')
    assert.equal(existsSync(dataDatabase), true, 'NSIS uninstallation must preserve desktop data')
    console.log('Packaged smoke passed: same-origin startup, persistence, XLSX export, child cleanup, and uninstall data preservation verified.')
  } finally {
    if (uninstallerPath && existsSync(uninstallerPath)) {
      await runChecked(uninstallerPath, ['/S'], { stdio: 'ignore' }, 'NSIS cleanup uninstallation')
    }
    cleanTemporaryDirectory(root)
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exitCode = error.exitCode || 1
})
