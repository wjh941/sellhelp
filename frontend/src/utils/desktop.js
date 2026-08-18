export async function requestDesktopBackendRestart(runtimeWindow = globalThis.window) {
  const restartBackend = runtimeWindow?.sellhelp?.restartBackend
  return typeof restartBackend === 'function' ? Boolean(await restartBackend()) : false
}
