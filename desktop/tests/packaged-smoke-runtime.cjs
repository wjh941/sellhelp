function findPackagedWindowTarget(targets, origin) {
  return targets.find((target) => {
    if (target.type !== 'page' || typeof target.url !== 'string' || typeof target.webSocketDebuggerUrl !== 'string') {
      return false
    }
    try {
      return new URL(target.url).origin === origin
    } catch {
      return false
    }
  })
}

function isReadyPackagedWindowState(state, origin) {
  return state?.origin === origin && Number.isInteger(state.appChildCount) && state.appChildCount > 0
}

module.exports = {
  findPackagedWindowTarget,
  isReadyPackagedWindowState,
}
