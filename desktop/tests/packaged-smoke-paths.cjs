const path = require('node:path')

const TEST_DIRECTORY_PREFIX = 'sellhelp-packaged-smoke-'

function localAppDataParent(localAppData) {
  if (typeof localAppData !== 'string' || localAppData.trim() === '') {
    throw new Error('LOCALAPPDATA must be set for the packaged smoke installation root')
  }
  return path.resolve(localAppData)
}

function smokeDirectoryPrefix(localAppData) {
  return path.join(localAppDataParent(localAppData), TEST_DIRECTORY_PREFIX)
}

function isOwnedSmokeDirectory(directory, localAppData) {
  const resolved = path.resolve(directory)
  const parent = localAppDataParent(localAppData)
  return path.dirname(resolved) === parent && path.basename(resolved).startsWith(TEST_DIRECTORY_PREFIX)
}

module.exports = {
  isOwnedSmokeDirectory,
  smokeDirectoryPrefix,
}
