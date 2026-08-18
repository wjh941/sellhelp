const http = require('node:http')
const net = require('node:net')
const path = require('node:path')

function findLoopbackPort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()

    server.once('error', reject)
    server.listen({ host: '127.0.0.1', port: 0, exclusive: true }, () => {
      const address = server.address()
      if (!address || typeof address === 'string') {
        server.close()
        reject(new Error('Could not determine an available loopback port'))
        return
      }

      server.close((error) => (error ? reject(error) : resolve(address.port)))
    })
  })
}

function backendCommand(resourcesPath, dataDir, port) {
  if (typeof resourcesPath !== 'string' || resourcesPath.length === 0) {
    throw new TypeError('resourcesPath must be a non-empty string')
  }
  if (typeof dataDir !== 'string' || dataDir.length === 0) {
    throw new TypeError('dataDir must be a non-empty string')
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new RangeError('port must be an integer between 1 and 65535')
  }

  const join = resourcesPath.includes('\\') ? path.win32.join : path.posix.join
  return {
    command: join(resourcesPath, 'backend', 'SellHelpBackend.exe'),
    args: [
      '--data-dir',
      dataDir,
      '--static-dir',
      join(resourcesPath, 'frontend'),
      '--port',
      String(port),
    ],
  }
}

function requestHealth(healthUrl, timeoutMs) {
  return new Promise((resolve, reject) => {
    const request = http.get(healthUrl, { timeout: timeoutMs }, (response) => {
      response.resume()
      if (response.statusCode >= 200 && response.statusCode < 300) {
        resolve()
        return
      }
      reject(new Error(`Health endpoint returned HTTP ${response.statusCode}`))
    })

    request.once('timeout', () => {
      request.destroy(new Error('Health endpoint request timed out'))
    })
    request.once('error', reject)
  })
}

function validateHealthUrl(healthUrl) {
  const parsed = new URL(healthUrl)
  const isLoopback = parsed.hostname === '127.0.0.1' || parsed.hostname === '::1'
  if (parsed.protocol !== 'http:' || !isLoopback || parsed.username || parsed.password) {
    throw new TypeError('Health URL must use unauthenticated loopback HTTP')
  }
}

function delay(timeoutMs) {
  return new Promise((resolve) => setTimeout(resolve, timeoutMs))
}

async function waitForHealth(healthUrl, timeoutMs) {
  validateHealthUrl(healthUrl)
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new RangeError('timeoutMs must be greater than zero')
  }

  const deadline = Date.now() + timeoutMs
  let lastError

  while (Date.now() < deadline) {
    try {
      await requestHealth(healthUrl, Math.max(1, Math.min(1000, deadline - Date.now())))
      return
    } catch (error) {
      lastError = error
    }

    const remaining = deadline - Date.now()
    if (remaining > 0) {
      await delay(Math.min(100, remaining))
    }
  }

  const detail = lastError ? `: ${lastError.message}` : ''
  const failure = new Error(
    `Desktop backend did not become healthy within ${timeoutMs}ms${detail}`,
  )
  if (lastError) {
    failure.cause = lastError
  }
  throw failure
}

module.exports = {
  backendCommand,
  findLoopbackPort,
  waitForHealth,
}
