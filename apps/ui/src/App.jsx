import { useState, useEffect } from 'react'
import { api } from './api'
import TaskRunner from './components/TaskRunner'
import AgentList from './components/AgentList'
import ModelStatus from './components/ModelStatus'
import TaskHistory from './components/TaskHistory'

const NAV = [
  { id: 'tasks',   label: 'Task Runner' },
  { id: 'history', label: 'History' },
  { id: 'agents',  label: 'Agents' },
  { id: 'models',  label: 'Models' },
]

export default function App() {
  const [activeView, setActiveView] = useState('tasks')
  const [agents, setAgents]         = useState([])
  const [models, setModels]         = useState(null)
  const [healthy, setHealthy]       = useState(null)

  useEffect(() => {
    api.health().then(h => setHealthy(h.status === 'ok')).catch(() => setHealthy(false))
    api.agents().then(setAgents).catch(() => {})
    api.models().then(setModels).catch(() => {})
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">

      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-800">
          <div className="text-sm font-semibold tracking-wide text-gray-100">Agent Orchestrator</div>
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${
              healthy === null ? 'bg-gray-500' : healthy ? 'bg-green-400' : 'bg-red-400'
            }`} />
            <span className="text-xs text-gray-500">
              {healthy === null ? 'connecting…' : healthy ? 'online' : 'offline'}
            </span>
          </div>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                activeView === item.id
                  ? 'bg-indigo-900/50 text-indigo-300'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-600">
          {agents.length} agent{agents.length !== 1 ? 's' : ''} loaded
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        {activeView === 'tasks'   && <TaskRunner agents={agents} />}
        {activeView === 'history' && <TaskHistory />}
        {activeView === 'agents'  && <AgentList agents={agents} />}
        {activeView === 'models'  && <ModelStatus models={models} />}
      </main>
    </div>
  )
}
