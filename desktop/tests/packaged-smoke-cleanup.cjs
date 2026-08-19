function shouldRunCleanupUninstaller({ uninstalled, uninstallerExists }) {
  return !uninstalled && uninstallerExists
}

module.exports = {
  shouldRunCleanupUninstaller,
}
