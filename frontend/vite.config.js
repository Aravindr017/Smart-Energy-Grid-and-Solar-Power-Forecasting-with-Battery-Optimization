import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const frontendDir = fileURLToPath(new URL('.', import.meta.url))
const projectRoot = resolve(frontendDir, '..')
const apiUrl = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

function backendPlugin() {
  let backendProcess
  let startupPromise
  let shuttingDown = false

  const statusUrl = `${apiUrl}/api/status`
  const python = process.env.PYTHON
    || [
      resolve(projectRoot, '.venv', 'Scripts', 'python.exe'),
      resolve(projectRoot, 'venv', 'Scripts', 'python.exe'),
      resolve(projectRoot, '.venv', 'bin', 'python'),
      resolve(projectRoot, 'venv', 'bin', 'python'),
    ].find((candidate) => existsSync(candidate))
    || (process.platform === 'win32' ? 'python' : 'python3')

  async function isApiReady() {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 2_000)
    try {
      const response = await fetch(statusUrl, { signal: controller.signal })
      return response.ok
    } catch {
      return false
    } finally {
      clearTimeout(timeout)
    }
  }

  async function ensureBackend() {
    if (startupPromise) return startupPromise

    startupPromise = (async () => {
      if (await isApiReady()) return

      if (!backendProcess || backendProcess.exitCode !== null) {
        backendProcess = spawn(
          python,
          ['-m', 'uvicorn', 'src.api.server:app', '--host', '127.0.0.1', '--port', '8000'],
          { cwd: projectRoot, stdio: 'inherit', windowsHide: true },
        )
      }

      const child = backendProcess
      let startupError
      child.once('error', (error) => {
        startupError = error
      })

      const deadline = Date.now() + 60_000
      while (Date.now() < deadline) {
        if (startupError) {
          throw new Error(`Could not start the SOLARIS API with "${python}": ${startupError.message}`)
        }
        if (child.exitCode !== null) {
          backendProcess = null
          throw new Error(`The SOLARIS API exited with code ${child.exitCode} during startup.`)
        }
        if (await isApiReady()) return
        await new Promise((resolvePromise) => setTimeout(resolvePromise, 500))
      }

      child.kill()
      backendProcess = null
      throw new Error('The SOLARIS API did not become ready on port 8000 within 60 seconds.')
    })()

    try {
      await startupPromise
    } finally {
      startupPromise = null
    }
  }

  return {
    name: 'solaris-backend',
    async configureServer(server) {
      if (process.env.VITE_API_TARGET) return

      const stopBackend = () => {
        shuttingDown = true
        if (backendProcess && backendProcess.exitCode === null) {
          backendProcess.kill()
        }
      }
      server.httpServer?.once('close', stopBackend)
      process.once('exit', stopBackend)

      server.middlewares.use('/api', (_request, _response, next) => {
        if (shuttingDown) return next(new Error('The SOLARIS development server is shutting down.'))
        ensureBackend().then(() => next(), next)
      })

      await ensureBackend()
    },
  }
}

export default defineConfig({
  plugins: [react(), backendPlugin()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
