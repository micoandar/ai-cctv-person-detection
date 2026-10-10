import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Chatbot from './components/Chatbot'

import Dashboard from './pages/Dashboard'
import LiveMonitoring from './pages/LiveMonitoring'
import ImageDetection from './pages/ImageDetection'
import History from './pages/History'
import Statistics from './pages/Statistics'
import Settings from './pages/Settings'
import VideoDetection from './pages/VideoDetection'
import { connectDetectionSocket, disconnectDetectionSocket } from './services/websocket'

export default function App() {
  useEffect(() => {
    connectDetectionSocket()
    return () => disconnectDetectionSocket()
  }, [])

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />

        <div className="flex-1 flex flex-col min-w-0">
          <Header />

          <main className="flex-1 overflow-y-auto p-5 lg:p-6 bg-ink-950">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/live" element={<LiveMonitoring />} />
              <Route path="/image-detection" element={<ImageDetection />} />
              <Route path="/history" element={<History />} />
              <Route path="/statistics" element={<Statistics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
              <Route path="/video-detection" element={<VideoDetection />} />
            </Routes>
          </main>
        </div>

        <Chatbot />
      </div>
    </BrowserRouter>
  )
}