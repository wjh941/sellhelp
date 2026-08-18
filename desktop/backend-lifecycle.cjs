function createBackendLifecycle({
  startBackend,
  stopBackend,
  initiallyRunning = false,
}) {
  let backendRunning = initiallyRunning
  let closing = false
  let restartPromise = null
  let shutdownPromise = null
  let startPromise = null

  async function stopCurrentBackend() {
    if (!backendRunning) {
      return
    }
    await stopBackend()
    backendRunning = false
  }

  async function start() {
    if (closing) {
      return false
    }
    if (startPromise) {
      return startPromise
    }

    const operation = (async () => {
      const port = await startBackend()
      backendRunning = true
      if (closing) {
        await stopCurrentBackend()
        return false
      }
      return port
    })()
    startPromise = operation
    try {
      return await operation
    } finally {
      if (startPromise === operation) {
        startPromise = null
      }
    }
  }

  async function restart() {
    if (closing) {
      return false
    }
    if (restartPromise) {
      return restartPromise
    }

    const operation = (async () => {
      await stopCurrentBackend()
      if (closing) {
        return false
      }

      const port = await startBackend()
      backendRunning = true
      if (closing) {
        await stopCurrentBackend()
        return false
      }
      return port
    })()
    restartPromise = operation
    try {
      return await operation
    } finally {
      if (restartPromise === operation) {
        restartPromise = null
      }
    }
  }

  function shutdown() {
    closing = true
    if (shutdownPromise) {
      return shutdownPromise
    }

    const pendingRestart = restartPromise
    const pendingStart = startPromise
    shutdownPromise = (async () => {
      let operationError = null
      if (pendingRestart) {
        try {
          await pendingRestart
        } catch (error) {
          operationError = error
        }
      }
      if (pendingStart) {
        try {
          await pendingStart
        } catch (error) {
          operationError ||= error
        }
      }
      try {
        await stopCurrentBackend()
      } catch (error) {
        operationError ||= error
      }
      if (operationError) {
        throw operationError
      }
    })()
    return shutdownPromise
  }

  return {
    restart,
    shutdown,
    start,
  }
}

module.exports = { createBackendLifecycle }
