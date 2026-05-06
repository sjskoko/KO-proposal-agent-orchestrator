/**
 * TaskHistory — shows all tasks run this session with their event logs.
 * Polls GET /tasks every 5 seconds so in-progress tasks update automatically.
 */

import { useState, useEffect } from 'react'
import { api } from '../api'
import EventLog from './EventLog'

const STATUS_BADGE = {
  running: 'bg-indigo-900/40 text-indigo-300 border-indigo-800',
  done:    'bg-green-900/40  text-green-300  border-green-800',
  error:   'bg-red-900/40   text-red-300   border-red-800',
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function TaskRow({ task, expanded, onToggle }) {
  const badge = STATUS_BADGE[task.status] ?? 'bg-gray-800 text-gray-400 border-gray-700'

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      {/* Summary row */}
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-start gap-4 hover:bg-gray-750 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs text-gray-500">{task.session_id}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded border ${badge}`}>
              {task.status}
            </span>
          </div>
          <div className="text-sm text-gray-200 truncate">{task.goal}</div>
          <div className="text-xs text-gray-500 mt-1">
            {task.agent_id} · {fmtDate(task.started_at)}
            {task.finished_at && ` → ${fmtDate(task.finished_at)}`}
          </div>
        </div>
        <span className="text-gray-600 text-xs mt-1">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-700 px-5 py-4 space-y-4">
          {task.result && (
            <div>
              <div className="text-xs font-medium text-green-400 mb-1">Result</div>
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono bg-gray-900 rounded p-3">
                {task.result}
              </pre>
            </div>
          )}
          {task.error && (
            <div className="text-sm text-red-300 bg-red-900/20 rounded p-3">{task.error}</div>
          )}
          <EventLog events={task.events} running={task.status === 'running'} />
        </div>
      )}
    </div>
  )
}

export default function TaskHistory() {
  const [tasks,    setTasks]    = useState([])
  const [expanded, setExpanded] = useState({})
  const [loading,  setLoading]  = useState(true)

  function refresh() {
    api.tasks()
      .then(t => { setTasks(t); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [])

  function toggle(id) {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">History</h2>
        <button
          onClick={refresh}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}

      {!loading && tasks.length === 0 && (
        <p className="text-sm text-gray-500">No tasks yet. Run one in Task Runner.</p>
      )}

      <div className="space-y-3">
        {tasks.map(task => (
          <TaskRow
            key={task.session_id}
            task={task}
            expanded={!!expanded[task.session_id]}
            onToggle={() => toggle(task.session_id)}
          />
        ))}
      </div>
    </div>
  )
}
