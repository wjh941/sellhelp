import net from 'node:net'

function validatePort(port, name) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new RangeError(`${name} must be an integer between 1 and 65535`)
  }
}

export function readE2ePort(value, fallback, name) {
  if (value === undefined || value === '') {
    return fallback
  }
  const port = Number(value)
  validatePort(port, name)
  return port
}

export function createManagedE2eRuntime({ backendPort, frontendPort }) {
  validatePort(backendPort, 'backendPort')
  validatePort(frontendPort, 'frontendPort')
  if (backendPort === frontendPort) {
    throw new RangeError('backendPort and frontendPort must be different')
  }

  const backendUrl = `http://127.0.0.1:${backendPort}`
  const frontendUrl = `http://127.0.0.1:${frontendPort}`
  return {
    backendPort,
    backendUrl,
    frontendPort,
    frontendUrl,
    childEnvironment: {
      SELLHELP_E2E_BACKEND_PORT: String(backendPort),
      SELLHELP_E2E_BACKEND_URL: backendUrl,
      SELLHELP_E2E_FRONTEND_PORT: String(frontendPort),
      SELLHELP_E2E_FRONTEND_URL: frontendUrl,
    },
  }
}

export function findLoopbackPort() {
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
