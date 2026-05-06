/**
 * EventLog — renders the live stream of agent events.
 *
 * Each event type gets a distinct color and a human-readable summary.
 * useEffect + scrollIntoView auto-scrolls to the latest event.
 */

import { useRef, useEffect } from 'react'

// Visual config per event type
const TYPE_CFG = {
  AgentStartedEvent:    { label: 'Agent Started',     color: 'text-blue-400',   bg: 'bg-blue-900/20'   },
  AgentDoneEvent:       { label: 'Agent Done',        color: 'text-green-400',  bg: 'bg-green-900/20'  },
  TaskDispatchedEvent:  { label: 'Task Dispatched',   color: 'text-yellow-400', bg: 'bg-yellow-900/20' },
  ToolCalledEvent:      { label: 'Tool Called',       color: 'text-purple-400', bg: 'bg-purple-900/20' },
  ModelQueriedEvent:    { label: 'Model Queried',     color: 'text-cyan-400',   bg: 'bg-cyan-900/20'   },
  StepFailedEvent:      { label: 'Step Failed',       color: 'text-red-400',    bg: 'bg-red-900/20'    },
  PermissionDeniedEvent:{ label: 'Permission Denied', color: 'text-orange-400', bg: 'bg-orange-900/20' },
}

const DEFAULT_CFG = { label: 'Event', color: 'text-gray-400', bg: 'bg-gray-800/30' }

/** Extract the most relevant fields for a one-line summary */
function summarise(event) {
  switch (event.type) {
    case 'AgentStartedEvent':
      return `Goal: "${event.goal}"`
    case 'AgentDoneEvent':
      return `${String(event.success) === 'True' || event.success === true ? 'Success' : 'Failed'} — ${event.summary}`
    case 'TaskDispatchedEvent':
      return `${event.task_type} → ${event.runtime_id}`
    case 'ToolCalledEvent':
      return `${event.tool_id}  (${event.latency_ms} ms)`
    case 'ModelQueriedEvent':
      return `${event.provider} / ${event.model}  ·  ${event.input_tokens} in / ${event.output_tokens} out  ·  ${event.latency_ms} ms`
    case 'StepFailedEvent':
      return `[${event.error_type}] ${event.error_message}`
    case 'PermissionDeniedEvent':
      return `Denied: ${event.capability}  (requested by ${event.requested_by})`
    default:
      return JSON.stringify(event)
  }
}

function fmtTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleTimeString() }
  catch { return '' }
}

export default function EventLog({ events, running }) {
  const bottomRef = useRef(null)

  // Scroll to bottom whenever a new event arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  if (events.length === 0 && !running) return null

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">

      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-xs font-medium text-gray-400">Event Stream</span>
        {running && (
          <span className="flex items-center gap-1 text-xs text-indigo-400">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
            Live
          </span>
        )}
        <span className="ml-auto text-xs text-gray-600">{events.length} events</span>
      </div>

      {/* Event rows */}
      <div className="max-h-96 overflow-y-auto bg-gray-900 divide-y divide-gray-800">
        {events.length === 0 && running && (
          <div className="px-4 py-3 text-sm text-gray-600 italic">Waiting for first event…</div>
        )}

        {events.map((event, i) => {
          const cfg = TYPE_CFG[event.type] ?? DEFAULT_CFG
          return (
            <div key={i} className={`px-4 py-2.5 ${cfg.bg}`}>
              <div className="flex items-baseline gap-2">
                <span className={`text-xs font-mono font-semibold ${cfg.color}`}>
                  {cfg.label}
                </span>
                <span className="text-xs text-gray-600">{fmtTime(event.timestamp)}</span>
              </div>
              <div className="text-sm text-gray-300 mt-0.5 leading-snug">
                {summarise(event)}
              </div>
            </div>
          )
        })}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
