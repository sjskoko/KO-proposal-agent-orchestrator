/**
 * ModelStatus — shows all model providers and routing configuration.
 * Mirrors what's in config/models.yaml, fetched from GET /models.
 */

const TYPE_COLOR = {
  local: 'text-green-400',
  api:   'text-blue-400',
}

function ProviderCard({ id, cfg }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-2 hover:border-gray-600 transition-colors">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono font-semibold text-white">{id}</span>
        <span className={`text-xs font-medium ${TYPE_COLOR[cfg.type] ?? 'text-gray-400'}`}>
          {cfg.type}
        </span>
      </div>
      <div className="text-sm text-gray-300">{cfg.model}</div>
      {cfg.base_url && (
        <div className="text-xs text-gray-500 font-mono truncate">{cfg.base_url}</div>
      )}
      {cfg.priority != null && (
        <div className="text-xs text-gray-600">Priority {cfg.priority}</div>
      )}
      {cfg.context_window && (
        <div className="text-xs text-gray-600">
          Context: {(cfg.context_window / 1000).toFixed(0)}k tokens
        </div>
      )}
    </div>
  )
}

export default function ModelStatus({ models }) {
  if (!models) {
    return (
      <div className="space-y-5">
        <h2 className="text-lg font-semibold text-gray-100">Models</h2>
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    )
  }

  const providers    = models.providers    ?? {}
  const routing      = models.routing      ?? {}
  const fallback     = routing.fallback_chain ?? []
  const rules        = routing.rules          ?? []

  return (
    <div className="space-y-8 max-w-3xl">
      <h2 className="text-lg font-semibold text-gray-100">Models</h2>

      {/* Providers grid */}
      <section>
        <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
          Providers
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(providers).map(([id, cfg]) => (
            <ProviderCard key={id} id={id} cfg={cfg} />
          ))}
        </div>
      </section>

      {/* Fallback chain */}
      {fallback.length > 0 && (
        <section>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Fallback Chain
          </h3>
          <div className="flex items-center flex-wrap gap-2">
            {fallback.map((id, i) => (
              <div key={id} className="flex items-center gap-2">
                <span className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm font-mono text-gray-200">
                  {id}
                </span>
                {i < fallback.length - 1 && (
                  <span className="text-gray-600 text-sm">→</span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Routing rules */}
      {rules.length > 0 && (
        <section>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            Routing Rules
          </h3>
          <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Match</th>
                  <th className="text-left px-4 py-2.5 text-gray-500 font-medium">Prefer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {rules.map((rule, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 font-mono text-gray-400 text-xs">
                      {JSON.stringify(rule.match)}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-indigo-300">
                      {rule.prefer}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
