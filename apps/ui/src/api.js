/**
 * API module — thin wrappers around fetch() and EventSource.
 *
 * BASE = '/api' resolves to the Vite proxy, which forwards to the FastAPI server.
 * In production (FastAPI serves the built app) '/api' hits FastAPI directly.
 */

const BASE = '/api'

export const api = {
  /** GET /health */
  async health() {
    const r = await fetch(`${BASE}/health`)
    return r.json()
  },

  /** GET /agents — returns list of agent definitions */
  async agents() {
    const r = await fetch(`${BASE}/agents`)
    if (!r.ok) throw new Error('Failed to load agents')
    return r.json()
  },

  /** GET /models — returns full models.yaml */
  async models() {
    const r = await fetch(`${BASE}/models`)
    if (!r.ok) throw new Error('Failed to load models')
    return r.json()
  },

  /**
   * Stream a task via Server-Sent Events (SSE).
   *
   * SSE is a browser API (EventSource) that opens a persistent HTTP connection.
   * The server pushes newline-delimited JSON events, which arrive one by one
   * as they happen — similar to tail -f on a log file.
   *
   * Returns a `stop` function you can call to close the connection early.
   */
  streamTask(goal, agentId, { onEvent, onDone, onError }) {
    const params = new URLSearchParams({ goal, agent_id: agentId })
    const url = `${BASE}/tasks/stream?${params}`

    const es = new EventSource(url)

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'done') {
        onDone(data.result)
        es.close()
      } else if (data.type === 'error' || data.type === 'timeout') {
        onError(data.message ?? 'Agent timed out')
        es.close()
      } else {
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
