function createQuitCoordinator({ stopBackend, quit, onStopError = () => {} }) {
  let finalQuitRequested = false
  let shutdownPromise = null

  function requestQuit() {
    if (finalQuitRequested) {
      return shutdownPromise || Promise.resolve()
    }
    if (shutdownPromise) {
      return shutdownPromise
    }

    let stopPromise
    try {
      stopPromise = Promise.resolve(stopBackend())
    } catch (error) {
      stopPromise = Promise.reject(error)
    }
    shutdownPromise = stopPromise
      .catch((error) => {
        try {
          onStopError(error)
        } catch {
          // A logging failure must not prevent the application from quitting.
        }
      })
      .then(() => {
        finalQuitRequested = true
        quit()
      })
    return shutdownPromise
  }

  function beforeQuit(event) {
    if (finalQuitRequested) {
      return shutdownPromise || Promise.resolve()
    }
    event.preventDefault()
    return requestQuit()
  }

  return {
    beforeQuit,
    requestQuit,
  }
}

module.exports = { createQuitCoordinator }
