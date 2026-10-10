import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Circle, Wifi, WifiOff, Loader2, Database } from 'lucide-react'
import { useDetectionStore } from '../store/detectionStore'
import { healthApi } from '../services/api'

const TITLES = {
  '/dashboard': { title: 'Dashboard', subtitle: 'Ringkasan aktivitas deteksi person' },
  '/live': { title: 'Live Monitoring', subtitle: 'Deteksi person real-time dari webcam' },
  '/image-detection': {
    title: 'Image Detection',
    subtitle: 'Deteksi person dari gambar yang di-upload',
  },
  '/video-detection': {
    title: 'Video Detection',
    subtitle: 'Deteksi person dari video yang di-upload',
  },
  '/history': { title: 'History', subtitle: 'Riwayat seluruh deteksi tersimpan' },
  '/statistics': { title: 'Statistics', subtitle: 'Analitik & tren jumlah orang' },
  '/settings': { title: 'Settings', subtitle: 'Konfigurasi deteksi dan kamera' },
}

export default function Header() {
  const { pathname } = useLocation()
  const meta = TITLES[pathname] || { title: 'AI CCTV', subtitle: '' }

  const wsStatus = useDetectionStore((s) => s.wsStatus)
  const cameraStatus = useDetectionStore((s) => s.cameraStatus)

  const [dbOk, setDbOk] = useState(null)

  // Tampilkan badge kamera hanya di halaman Live Monitoring
  const showCameraBadge = pathname === '/live'

  useEffect(() => {
    let alive = true
    const ping = async () => {
      try {
        const { data } = await healthApi.check()
        if (alive) setDbOk(Boolean(data.database?.connected))
      } catch {
        if (alive) setDbOk(false)
      }
    }
    ping()
    const timer = setInterval(ping, 15000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const wsBadge =
    wsStatus === 'connected'
      ? {
          cls: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25',
          icon: Wifi,
          label: 'WS Connected',
        }
      : wsStatus === 'connecting'
      ? {
          cls: 'bg-amber-500/10 text-amber-400 border border-amber-500/25',
          icon: Loader2,
          label: 'Connecting',
        }
      : {
          cls: 'bg-rose-500/10 text-rose-400 border border-rose-500/25',
          icon: WifiOff,
          label: 'WS Offline',
        }

  const WsIcon = wsBadge.icon

  return (
    <header className="h-16 shrink-0 flex items-center justify-between px-6 border-b border-white/5 bg-ink-900/60 backdrop-blur">
      <div>
        <h1 className="text-base font-semibold text-white">{meta.title}</h1>
        <p className="text-xs text-slate-500">{meta.subtitle}</p>
      </div>

      <div className="flex items-center gap-2">
        {/* DB */}
        <span
          className={`badge border ${
            dbOk
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
              : dbOk === false
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/25'
              : 'bg-slate-500/10 text-slate-400 border-slate-500/25'
          }`}
        >
          <Database size={12} />
          MySQL {dbOk ? 'OK' : dbOk === false ? 'ERR' : '...'}
        </span>

        {/* WebSocket */}
        <span className={`badge ${wsBadge.cls}`}>
          <WsIcon size={12} className={wsStatus === 'connecting' ? 'animate-spin' : ''} />
          {wsBadge.label}
        </span>

        {/* Camera — hanya di halaman Live Monitoring */}
        {showCameraBadge && (
          <span
            className={`badge border ${
              cameraStatus === 'ONLINE'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                : 'bg-slate-500/10 text-slate-400 border-slate-500/25'
            }`}
          >
            <Circle
              size={8}
              className={
                cameraStatus === 'ONLINE'
                  ? 'fill-emerald-400 animate-live-pulse'
                  : 'fill-slate-500'
              }
            />
            {cameraStatus}
          </span>
        )}
      </div>
    </header>
  )
}