const assert = require('node:assert/strict')
const test = require('node:test')

const { createBackendLifecycle } = require('../backend-lifecycle.cjs')
const { createQuitCoordinator } = require('../lifecycle.cjs')

function deferred() {
  let resolve
  const promise = new Promise((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

test('shutdown joins a restart and cleans a newly started backend before final quit', async () => {
  const oldStopEntered = deferred()
  const oldStopReleased = deferred()
  const newStartEntered = deferred()
  const newStartReleased = deferred()
  const stoppedBackends = []
  let activeBackend = 'old'
  let quitCalls = 0
  const lifecycle = createBackendLifecycle({
    initiallyRunning: true,
    startBackend: async () => {
      newStartEntered.resolve()
      await newStartReleased.promise
      activeBackend = 'new'
      return 18101
    },
    stopBackend: async () => {
      stoppedBackends.push(activeBackend)
      if (activeBackend === 'old') {
        activeBackend = null
        oldStopEntered.resolve()
        await oldStopReleased.promise
        return
      }
      activeBackend = null
    },
  })
  const quitter = createQuitCoordinator({
    stopBackend: () => lifecycle.shutdown(),
    quit: () => {
      assert.equal(activeBackend, null)
      quitCalls += 1
    },
  })

  const restart = lifecycle.restart()
  await oldStopEntered.promise
  oldStopReleased.resolve()
  await newStartEntered.promise

  let prevented = false
  const quitting = quitter.beforeQuit({
    preventDefault: () => {
      prevented = true
    },
  })
  assert.equal(prevented, true)
  assert.equal(quitCalls, 0)

  newStartReleased.resolve()
  assert.equal(await restart, false)
  await quitting

  assert.deepEqual(stoppedBackends, ['old', 'new'])
  assert.equal(activeBackend, null)
  assert.equal(quitCalls, 1)
})
