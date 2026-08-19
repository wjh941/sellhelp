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

test('backup replica helpers use the protected system routes', async () => {
  await api.getBackupReplicaStatus()
  await api.configureBackupReplica('D:/copies')
  await api.disableBackupReplica()

  assert.deepEqual(requests.slice(-3).map(request => ({
    method: request.method,
    url: request.url,
    params: request.params
  })), [
    { method: 'get', url: '/system/backup-replica-status', params: undefined },
    { method: 'put', url: '/system/backup-replica', params: { directory: 'D:/copies' } },
    { method: 'delete', url: '/system/backup-replica', params: undefined }
  ])
})

test('Settings uses the fixed desktop picker and exposes the redacted target name only', async () => {
  const source = await readFile(new URL('../src/views/Settings.vue', import.meta.url), 'utf8')

  assert.match(source, /getBackupReplicaStatus/)
  assert.match(source, /window\.sellhelp\?\.selectBackupDirectory\?\.\(\)/)
  assert.match(source, /replicaStatus\.directory_name/)
  assert.match(source, /replicaStatus\?\.last_failure/)
  assert.doesNotMatch(source, /replicaStatus\.directory(?:[^_A-Za-z0-9]|$)/)
})
