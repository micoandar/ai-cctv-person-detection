import { useDetectionStore } from '../store/detectionStore'

let socket = null
let reconnectTimer = null
let shouldReconnect = true
let retryCount = 0

function buildUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/detection`
}

export function connectDetectionSocket() {
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return socket
  }

  shouldReconnect = true
  const store = useDetectionStore.getState()
  store.setWsStatus('connecting')

  let ws
  try {
    ws = new WebSocket(buildUrl())
  } catch (e) {
    store.setWsStatus('disconnected')
    store.setError('Gagal membuat koneksi WebSocket.')
    return null
  }

  socket = ws

  ws.onopen = () => {
    if (socket !== ws) return
    retryCount = 0
    useDetectionStore.getState().setWsStatus('connected')
    useDetectionStore.getState().setError(null)
  }

  ws.onmessage = (event) => {
    if (socket !== ws) return
    try {
      const data = JSON.parse(event.data)
      useDetectionStore.getState().handleSocketMessage(data)
    } catch (err) {
      console.error('WebSocket message parse error:', err)
    }
  }

  ws.onerror = () => {
    if (socket !== ws) return
    useDetectionStore.getState().setError('Koneksi WebSocket bermasalah.')
  }

  ws.onclose = () => {
    if (socket !== ws) return
    socket = null
    useDetectionStore.getState().setWsStatus('disconnected')

    if (shouldReconnect) {
      retryCount += 1
      const delay = Math.min(1000 * retryCount, 5000)
      reconnectTimer = setTimeout(connectDetectionSocket, delay)
    }
  }

  return ws
}

export function disconnectDetectionSocket() {
  shouldReconnect = false
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (socket) {
    const ws = socket
    socket = null
    try {
      ws.close()
    } catch (e) {
      /* noop */
    }
  }
  useDetectionStore.getState().setWsStatus('disconnected')
}