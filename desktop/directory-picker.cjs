function selectedDirectory(result) {
  const first = result?.canceled ? null : result?.filePaths?.[0]
  return typeof first === 'string' && first.length > 0 ? first : null
}

module.exports = { selectedDirectory }
