import test from 'node:test'
import assert from 'node:assert/strict'

const desktopRuntime = await import('../src/utils/desktop.js').catch(() => null)

test('desktop restart helper is inert in a browser and delegates in Electron', async () => {
  assert.ok(desktopRuntime, 'desktop runtime helper must be available')
  assert.equal(await desktopRuntime.requestDesktopBackendRestart({}), false)
  assert.equal(
    await desktopRuntime.requestDesktopBackendRestart({ sellhelp: { restartBackend: async () => true } }),
    true,
  )
})
