/**
 * AgentList — shows all agent definitions as cards.
 * Data is fetched once in App.jsx and passed here as a prop.
 */

const ROLE_BADGE = {
  orchestrator:  'bg-indigo-900/40 text-indigo-300  border-indigo-800',
  researcher:    'bg-blue-900/40   text-blue-300    border-blue-800',
  coder:         'bg-purple-900/40 text-purple-300  border-purple-800',
  file_worker:   'bg-yellow-900/40 text-yellow-300  border-yellow-800',
  tool_operator: 'bg-green-900/40  text-green-300   border-green-800',
}

function Tag({ label, className }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-mono ${className}`}>
      {label}
    </span>
  )
}

function AgentCard({ agent }) {
  const badgeCls = ROLE_BADGE[agent.role] ?? 'bg-gray-800 text-gray-400 border-gray-700'

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-3 hover:border-gray-600 transition-colors">

      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono font-semibold text-white">{agent.id}</span>
        <span className={`text-xs px-2 py-0.5 rounded border ${badgeCls} flex-shrink-0`}>
          {agent.role}
        </span>
      </div>

      {/* Goal */}
      <p className="text-sm text-gray-400 leading-relaxed">{agent.goal}</p>

      {/* Tools */}
      {agent.tools?.length > 0 && (
        <div>
          <div className="text-xs text-gray-600 mb-1.5">Tools</div>
          <div className="flex flex-wrap gap-1">
            {agent.tools.map(t => (
              <Tag key={t} label={t} className="bg-gray-900 text-gray-300" />
            ))}
          </div>
        </div>
      )}

      {/* Sub-agents */}
      {agent.sub_agents?.length > 0 && (
        <div>
          <div className="text-xs text-gray-600 mb-1.5">Sub-agents</div>
          <div className="flex flex-wrap gap-1">
            {agent.sub_agents.map(sa => (
              <Tag key={sa} label={sa} className="bg-indigo-900/30 text-indigo-300" />
            ))}
          </div>
        </div>
      )}

      {/* Runtime access */}
      {agent.runtime_access?.length > 0 && (
        <div>
          <div className="text-xs text-gray-600 mb-1.5">Runtime access</div>
          <div className="flex flex-wrap gap-1">
            {agent.runtime_access.map(r => (
              <Tag key={r} label={r} className="bg-green-900/30 text-green-300" />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function AgentList({ agents }) {
  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold text-gray-100">Agents</h2>

      {agents.length === 0 ? (
        <p className="text-sm text-gray-500">No agents found — is the server running?</p>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {agents.map(a => <AgentCard key={a.id} agent={a} />)}
        </div>
      )}
    </div>
  )
}
