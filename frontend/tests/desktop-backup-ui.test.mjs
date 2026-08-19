import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import axios from 'axios'

const requests = []
const realCreate = axios.create

axios.create = (...args) => {
  const instance = realCreate(...args)
  instance.defaults.adapter = async config => {
    requests.push(config)
    return {
      config,
      data: { ok: true },
      headers: {},
      status: 200,
      statusText: 'OK'
    }
  }
  return instance
}

const api = await import('../src/api/index.js')
axios.create = realCreate

test('getBackupStatus requests the protected automatic backup status route', async () => {
  await api.getBackupStatus()

  const request = requests.at(-1)
  assert.deepEqual({ method: request.method, url: request.url, data: request.data }, {
    method: 'get', url: '/system/backup-status', data: undefined
  })
})

test('Settings loads automatic backup state with the manual backup list and exposes failures', async () => {
  const source = await readFile(new URL('../src/views/Settings.vue', import.meta.url), 'utf8')

  assert.match(source, /getBackupStatus/)
  assert.match(source, /backupStatus/)
  assert.match(source, /Promise\.all\(\[getBackups\(\), getBackupStatus\(\)\]\)/)
  assert.match(source, /backupStatus\?\.last_failure/)
  assert.match(source, /backupStatus\.retention_count/)
})
