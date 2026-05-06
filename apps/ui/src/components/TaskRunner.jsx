import { useState, useRef } from 'react'
import { api } from '../api'
import EventLog from './EventLog'

export default function TaskRunner({ agents }) {
  const [goal,      setGoal]      = useState('')
  const [agentId,   setAgentId]   = useState('main_agent')
  const [running,   setRunning]   = useState(false)
  const [events,    setEvents]    = useState([])
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const stopRef = useRef(null)

  function handleRun() {
    if (!goal.trim() || running) return
    setRunning(true)
    setEvents([])
    setResult(null)
    setError(null)
    setSessionId(null)

    const stop = api.streamTask(goal, agentId, {
      onSession: (id)       => setSessionId(id),
      onEvent:   (event)    => setEvents(prev => [...prev, event]),
      onDone:    (res, id)  => { setResult(res); setSessionId(id); setRunning(false) },
      onError:   (msg)      => { setError(msg); setRunning(false) },
    })
    stopRef.current = stop
  }

  function handleStop() {
    stopRef.current?.()
    setRunning(false)
  }

  return (
    <div className="max-w-3xl space-y-5">
      <h2 className="text-lg font-semibold text-gray-100">Task Runner</h2>

      <textarea
        value={goal}
        onChange={e => setGoal(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) handleRun() }}
        placeholder="Describe what you want the agent to do…"
        rows={4}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-gray-100
                   placeholder-gray-500 focus:outline-none focus:border-indigo-500 resize-none text-sm"
      />

      <div className="flex items-center gap-3">
        <select
          value={agentId}
          onChange={e => setAgentId(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2
                     text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
        >
          {agents.length === 0
            ? <option value="main_agent">main_agent</option>
            : agents.map(a => (
                <option key={a.id} value={a.id}>{a.id} ({a.role})</option>
              ))
          }
        </select>

        {!running ? (
          <button
            onClick={handleRun}
            disabled={!goal.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700
                       disabled:cursor-not-allowed px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Run <span className="text-indigo-300 text-xs ml-1">⌘↵</span>
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="bg-red-700 hover:bg-red-600 px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Stop
          </button>
        )}

        {sessionId && (
          <span className="text-xs text-gray-600 font-mono ml-auto">
            session: {sessionId}
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="bg-gray-800 border border-green-700 rounded-lg p-4">
          <div className="text-xs font-medium text-green-400 mb-2">Result</div>
          <pre className="text-sm text-gray-200 whitespace-pre-wrap font-mono">{result}</pre>
        </div>
      )}

      <EventLog events={events} running={running} />
    </div>
  )
}
