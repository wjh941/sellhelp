const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const { createBackendLifecycle } = require('./backend-lifecycle.cjs')
const { selectedDirectory } = require('./directory-picker.cjs')
const { createQuitCoordinator } = require('./lifecycle.cjs')
const {
  backendCommand,
  findLoopbackPort,
  resolveDesktopDataDirectory,
  waitForHealth,
} = require('./runtime.cjs')

const BACKEND_HEALTH_TIMEOUT_MS = 30_000
let backendChild = null
let backendPort = null
let backendStartPromise = null
let mainWindow = null
let restartPromise = null
let shuttingDown = false
let windowCreationPromise = null

function desktopDataDirectory() {
  const override = process.env.SELLHELP_DESKTOP_DATA_DIR
  return resolveDesktopDataDirectory({
    developmentDataDirectory: !app.isPackaged && override ? path.resolve(override) : undefined,
    isPackaged: app.isPackaged,
    localAppData: process.env.LOCALAPPDATA,
  })
}

function bundledResourcesDirectory() {
  const override = process.env.SELLHELP_DESKTOP_RESOURCES_DIR
  if (!app.isPackaged && override) {
    return path.resolve(override)
  }
  return process.resourcesPath
}

function appendDesktopLog(dataDirectory, message) {
  try {
    const logPath = path.join(dataDirectory, 'logs', 'desktop-shell.log')
    fs.mkdirSync(path.dirname(logPath), { recursive: true })
    fs.appendFileSync(logPath, `${new Date().toISOString()} ${message}\n`, 'utf8')
  } catch {
    // Logging failures must not prevent an error dialog or child cleanup.
  }
}

function backendUrl(port) {
  return `http://127.0.0.1:${port}`
}

function watchBackend(child, dataDirectory) {
  child.stderr.setEncoding('utf8')
  child.stderr.on('data', (data) => {
    appendDesktopLog(dataDirectory, `[backend stderr] ${data.trimEnd()}`)
  })
  child.on('error', (error) => {
    appendDesktopLog(dataDirectory, `[backend error] ${error.message}`)
  })
  child.on('exit', (code, signal) => {
    appendDesktopLog(dataDirectory, `[backend exit] code=${code} signal=${signal}`)
    if (backendChild === child) {
      backendChild = null
      backendPort = null
    }
  })
}

function waitForBackendExit(child) {
  return new Promise((resolve, reject) => {
    if (child.exitCode !== null) {
      resolve()
      return
    }

    const fallback = setTimeout(() => {
      try {
        child.kill('SIGKILL')
      } catch {
        // The child may have already exited between the timeout and kill call.
      }
      setTimeout(() => {
        if (child.exitCode === null) {
          reject(new Error('Desktop backend did not exit after forced termination'))
        }
      }, 1_000)
    }, 5_000)

    child.once('exit', () => {
      clearTimeout(fallback)
      resolve()
    })

    try {
      child.kill()
    } catch {
      clearTimeout(fallback)
      if (child.exitCode === null) {
        reject(new Error('Could not terminate desktop backend'))
      } else {
        resolve()
      }
    }
  })
}

async function stopBackend() {
  const child = backendChild
  backendChild = null
  backendPort = null
  if (child) {
    await waitForBackendExit(child)
  }
}

function waitForHealthyChild(child, healthUrl) {
  return new Promise((resolve, reject) => {
    const onError = (error) => reject(error)
    const onExit = (code, signal) => {
      reject(new Error(`Desktop backend exited before health check (code=${code}, signal=${signal})`))
    }
    const cleanup = () => {
      child.removeListener('error', onError)
      child.removeListener('exit', onExit)
    }

    child.once('error', onError)
    child.once('exit', onExit)
    waitForHealth(healthUrl, BACKEND_HEALTH_TIMEOUT_MS).then(
      () => {
        cleanup()
        resolve()
      },
      (error) => {
        cleanup()
        reject(error)
      },
    )
  })
}

async function startBackend() {
  if (backendChild && backendChild.exitCode === null && backendPort) {
    return backendPort
  }
  if (backendStartPromise) {
    return backendStartPromise
  }

  const dataDirectory = desktopDataDirectory()
  backendStartPromise = (async () => {
    const port = await findLoopbackPort()
    const command = backendCommand(bundledResourcesDirectory(), dataDirectory, port)
    appendDesktopLog(dataDirectory, `[backend start] ${command.command}`)

    const child = spawn(command.command, command.args, {
      detached: false,
      shell: false,
      stdio: ['ignore', 'ignore', 'pipe'],
      windowsHide: true,
    })
    backendChild = child
    backendPort = port
    watchBackend(child, dataDirectory)

    try {
      await waitForHealthyChild(child, `${backendUrl(port)}/api/health`)
      return port
    } catch (error) {
      try {
        await stopBackend()
      } catch (stopError) {
        appendDesktopLog(dataDirectory, `[backend stop failure] ${stopError.message}`)
      }
      throw error
    }
  })()

  try {
    return await backendStartPromise
  } finally {
    backendStartPromise = null
  }
}

const backendLifecycle = createBackendLifecycle({ startBackend, stopBackend })
const quitCoordinator = createQuitCoordinator({
  stopBackend: () => backendLifecycle.shutdown(),
  quit: () => app.quit(),
  onStopError: (error) => {
    appendDesktopLog(desktopDataDirectory(), `[backend stop failure] ${error.message}`)
  },
})

function isCurrentLocalUrl(navigationUrl) {
  try {
    const parsed = new URL(navigationUrl)
    return (
      parsed.protocol === 'http:' &&
      parsed.hostname === '127.0.0.1' &&
      parsed.port === String(backendPort)
    )
  } catch {
    return false
  }
}

function secureWindow(window) {
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event, navigationUrl) => {
    if (!isCurrentLocalUrl(navigationUrl)) {
      event.preventDefault()
    }
  })
  window.webContents.on('will-redirect', (event, navigationUrl) => {
    if (!isCurrentLocalUrl(navigationUrl)) {
      event.preventDefault()
    }
  })
  window.webContents.on('will-attach-webview', (event) => event.preventDefault())
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => {
    callback(false)
  })
}

function focusMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return
  }
  if (mainWindow.isMinimized()) {
    mainWindow.restore()
  }
  mainWindow.focus()
}

async function loadLocalInterface(window, port) {
  await window.loadURL(`${backendUrl(port)}/`)
}

async function createMainWindow() {
  const port = await backendLifecycle.start()
  if (port === false || shuttingDown) {
    return
  }
  const window = new BrowserWindow({
    show: false,
    icon: path.join(__dirname, 'resources', 'icon.ico'),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.cjs'),
      sandbox: true,
    },
  })

  mainWindow = window
  secureWindow(window)
  window.once('ready-to-show', () => window.show())
  window.on('closed', () => {
    if (mainWindow === window) {
      mainWindow = null
    }
  })
  await loadLocalInterface(window, port)
}

async function ensureMainWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    focusMainWindow()
    return mainWindow
  }
  if (windowCreationPromise) {
    return windowCreationPromise
  }

  windowCreationPromise = createMainWindow()
  try {
    return await windowCreationPromise
  } finally {
    windowCreationPromise = null
  }
}

function reportStartupFailure(error) {
  let logPath = null
  try {
    const dataDirectory = desktopDataDirectory()
    logPath = path.join(dataDirectory, 'logs', 'desktop-shell.log')
    appendDesktopLog(dataDirectory, `[startup failure] ${error.stack || error.message}`)
  } catch {
    // A missing LOCALAPPDATA value must not hide the original startup error.
  }
  const details = error?.message === 'LOCALAPPDATA must be set to run SellHelp on Windows'
    ? error.message
    : 'The local service did not become available.'
  dialog.showErrorBox(
    'SellHelp could not start',
    logPath ? `${details} See ${logPath}.` : details,
  )
}

async function restartBackend(event) {
  if (!mainWindow || event.sender !== mainWindow.webContents) {
    return false
  }
  if (restartPromise) {
    return restartPromise
  }

  restartPromise = (async () => {
    try {
      const port = await backendLifecycle.restart()
      if (port === false || shuttingDown || !mainWindow || mainWindow.isDestroyed()) {
        return false
      }
      await loadLocalInterface(mainWindow, port)
      return !shuttingDown
    } catch (error) {
      reportStartupFailure(error)
      return false
    }
  })()

  try {
    return await restartPromise
  } finally {
    restartPromise = null
  }
}

async function selectBackupDirectory(event) {
  if (!mainWindow || mainWindow.isDestroyed() || event.sender !== mainWindow.webContents) {
    return null
  }
  return selectedDirectory(await dialog.showOpenDialog(mainWindow, {
    title: 'Choose backup replica directory',
    properties: ['openDirectory'],
  }))
}

async function shutdown() {
  shuttingDown = true
  return quitCoordinator.requestQuit()
}

ipcMain.handle('sellhelp:restart-backend', restartBackend)
ipcMain.handle('sellhelp:select-backup-directory', selectBackupDirectory)

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => focusMainWindow())
  app.on('activate', () => {
    if (!shuttingDown && BrowserWindow.getAllWindows().length === 0) {
      ensureMainWindow().catch((error) => {
        reportStartupFailure(error)
        void shutdown()
      })
    }
  })
  app.on('window-all-closed', () => {
    void shutdown()
  })
  app.on('before-quit', (event) => {
    shuttingDown = true
    void quitCoordinator.beforeQuit(event)
  })
  app.whenReady().then(
    () => ensureMainWindow(),
    (error) => {
      reportStartupFailure(error)
      void shutdown()
    },
  ).catch((error) => {
    reportStartupFailure(error)
    void shutdown()
  })
}
