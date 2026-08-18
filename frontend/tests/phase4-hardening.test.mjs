import test from 'node:test'
import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'

const root = new URL('../src/', import.meta.url)

async function sourceFiles(directory = root) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = await Promise.all(entries.map(async entry => {
    const path = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, directory)
    return entry.isDirectory() ? sourceFiles(path) : [path]
  }))
  return files.flat().filter(path => /\.(js|vue)$/.test(path.pathname))
}

test('phase 4 keeps the E2E proxy configurable and removes obsolete chart runtime', async () => {
  const [viteConfig, packageJson] = await Promise.all([
    readFile(new URL('../vite.config.js', import.meta.url), 'utf8'),
    readFile(new URL('../package.json', import.meta.url), 'utf8'),
  ])

  assert.match(viteConfig, /VITE_API_PROXY_TARGET/)
  assert.doesNotMatch(packageJson, /"vue-echarts"/)
})

test('production Vue source contains no console debug calls or debugger statements', async () => {
  const source = await Promise.all((await sourceFiles()).map(file => readFile(file, 'utf8')))

  assert.doesNotMatch(source.join('\n'), /\bconsole\.(?:log|debug|info|warn|error)\s*\(|\bdebugger\s*;/)
})
