const assert = require('node:assert/strict')
const test = require('node:test')

const { createQuitCoordinator } = require('../lifecycle.cjs')

test('external quit waits for one backend stop before allowing one final quit', async () => {
  let allowStop
  const stopped = new Promise((resolve) => {
    allowStop = resolve
  })
  let stopCalls = 0
  let quitCalls = 0
  let prevented = false
  const coordinator = createQuitCoordinator({
    stopBackend: () => {
      assert.equal(prevented, true)
      stopCalls += 1
      return stopped
    },
    quit: () => {
      quitCalls += 1
    },
  })
  const event = {
    preventDefault: () => {
      prevented = true
    },
  }

  const firstQuit = coordinator.beforeQuit(event)
  const repeatedQuit = coordinator.beforeQuit(event)
  assert.equal(firstQuit, repeatedQuit)
  await Promise.resolve()
  assert.equal(stopCalls, 1)
  assert.equal(quitCalls, 0)

  allowStop()
  await firstQuit
  assert.equal(quitCalls, 1)

  let finalPrevented = false
  await coordinator.beforeQuit({
    preventDefault: () => {
      finalPrevented = true
    },
  })
  assert.equal(finalPrevented, false)
  assert.equal(stopCalls, 1)
  assert.equal(quitCalls, 1)
})
