import { spawn } from 'node:child_process'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const backendRoot = path.resolve(frontendRoot, '../backend')
const backendUrl = 'http://127.0.0.1:8005'
const frontendUrl = 'http://127.0.0.1:5187'
const testDatabase = path.join(tmpdir(), `sellhelp-playwright-${Date.now()}-${process.pid}.db`).replaceAll('\\', '/')

const wait = (milliseconds) => new Promise(resolve => setTimeout(resolve, milliseconds))

function start(command, args, options) {
  return spawn(command, args, { stdio: 'ignore', windowsHide: true, ...options })
}

async function waitFor(url, child) {
  const deadline = Date.now() + 60_000
  let lastError

  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`${url} exited before becoming ready`)
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch (error) {
      lastError = error
    }
    await wait(250)
  }

  throw new Error(`Timed out waiting for ${url}${lastError ? `: ${lastError.message}` : ''}`)
}

function waitForExit(child) {
  return new Promise((resolve, reject) => {
    child.once('error', reject)
    child.once('exit', code => resolve(code ?? 1))
  })
}

async function stopProcessTree(child) {
  if (!child?.pid || child.exitCode !== null) return
  child.kill('SIGTERM')
  const stopped = await Promise.race([
    waitForExit(child).then(() => true, () => false),
    wait(5_000).then(() => false),
  ])
  if (!stopped && process.platform === 'win32') {
    console.error(`Timed out stopping process ${child.pid}`)
    const killer = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { detached: true, stdio: 'ignore', windowsHide: true })
    killer.unref()
  }
}

async function runToCompletion(command, args, options) {
  const child = start(command, args, options)
  const exitCode = await waitForExit(child)
  if (exitCode !== 0) throw new Error(`${command} ${args.join(' ')} exited with code ${exitCode}`)
}

async function run() {
  const backendEnv = {
    ...process.env,
    SELLHELP_DATABASE_URL: `sqlite:///${testDatabase}`,
    SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER: '1',
    SELLHELP_JWT_SECRET: 'sellhelp-playwright-secret-key-000000',
  }
  await runToCompletion('python', ['-m', 'alembic', 'upgrade', 'head'], { cwd: backendRoot, env: backendEnv, stdio: 'inherit' })
  const backend = start('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8005'], {
    cwd: backendRoot,
    env: backendEnv,
  })
  let frontend

  try {
    await waitFor(`${backendUrl}/api/health`, backend)
    frontend = start(process.execPath, ['tests/e2e/start-frontend.mjs'], { cwd: frontendRoot, env: process.env })
    await waitFor(frontendUrl, frontend)
    const playwright = start(process.execPath, ['node_modules/playwright/cli.js', 'test', ...process.argv.slice(2)], {
      cwd: frontendRoot,
      env: { ...process.env, SELLHELP_E2E_MANAGED_SERVERS: '1' },
      stdio: 'inherit',
    })
    return await waitForExit(playwright)
  } finally {
    await stopProcessTree(frontend)
    await stopProcessTree(backend)
  }
}

try {
  process.exitCode = await run()
} catch (error) {
  console.error(error)
  process.exitCode = 1
}
