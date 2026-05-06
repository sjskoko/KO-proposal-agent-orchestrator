/**
 * API module — wrappers around fetch() and EventSource.
 *
 * All paths start with '/api', which Vite proxies to the FastAPI server.
 */

const BASE = '/api'

async function _get(path) {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const api = {
  health:  () => _get('/health'),
  agents:  () => _get('/agents'),
  models:  () => _get('/models'),
  tasks:   () => _get('/tasks'),
  task:    (sessionId) => _get(`/tasks/${sessionId}`),

  /**
   * Stream a task via SSE.
   *
   * Emits:
   *   onSession(sessionId)  — immediately, before any events
   *   onEvent(eventObj)     — for each domain event
   *   onDone(result, sessionId)
   *   onError(message)
   *
   * Returns a stop() function to close the stream early.
   */
  streamTask(goal, agentId, { onSession, onEvent, onDone, onError }) {
    const params = new URLSearchParams({ goal, agent_id: agentId })
    const es = new EventSource(`${BASE}/tasks/stream?${params}`)

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      switch (data.type) {
        case 'session_started':
          onSession?.(data.session_id)
          break
        case 'done':
          onDone(data.result, data.session_id)
          es.close()
          break
        case 'error':
        case 'timeout':
          onError(data.message ?? 'Agent timed out')
          es.close()
          break
        default:
          onEvent(data)
      }
    }

    es.onerror = () => {
      onError('Connection to server lost')
      es.close()
    }

    return () => es.close()
  },
}
