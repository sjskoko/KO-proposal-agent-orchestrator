import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// React 18 entry point.
// ReactDOM.createRoot replaces the old ReactDOM.render.
// StrictMode runs every component twice in dev to surface side-effect bugs.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
