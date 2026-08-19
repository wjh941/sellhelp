const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const test = require('node:test')

const { selectedDirectory } = require('../directory-picker.cjs')


test('directory picker returns exactly one selected directory', () => {
  assert.equal(
    selectedDirectory({ canceled: false, filePaths: ['D:/SellHelp copies'] }),
    'D:/SellHelp copies',
  )
  assert.equal(selectedDirectory({ canceled: true, filePaths: ['D:/ignored'] }), null)
  assert.equal(selectedDirectory({ canceled: false, filePaths: [] }), null)
  assert.equal(selectedDirectory({ canceled: false, filePaths: [42] }), null)
})


test('desktop bridge exposes a fixed no-argument picker only to the main window', () => {
  const preload = readFileSync(path.join(__dirname, '..', 'preload.cjs'), 'utf8')
  const main = readFileSync(path.join(__dirname, '..', 'main.cjs'), 'utf8')

  assert.match(
    preload,
    /selectBackupDirectory: async \(\) => ipcRenderer\.invoke\('sellhelp:select-backup-directory'\)/,
  )
  assert.doesNotMatch(preload, /invoke\('sellhelp:select-backup-directory',/)
  assert.match(main, /event\.sender !== mainWindow\.webContents/)
  assert.match(main, /ipcMain\.handle\('sellhelp:select-backup-directory', selectBackupDirectory\)/)
})
