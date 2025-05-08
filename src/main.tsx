import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { AuthProvider } from './contexts/AuthContext.tsx'
import { AssetProvider } from './contexts/AssetContext.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <AssetProvider>
        <App />
      </AssetProvider>
    </AuthProvider>
  </React.StrictMode>,
)
