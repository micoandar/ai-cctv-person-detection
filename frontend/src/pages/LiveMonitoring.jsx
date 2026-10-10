import { useEffect, useState } from 'react'
import { Play, Square, Users, Gauge, Target, Radio, AlertTriangle } from 'lucide-react'
import CameraFeed from '../components/CameraFeed'
import DetectionList from '../components/DetectionList'
import StatCard from '../components/StatCard'
import { webcamApi } from '../services/api'
import { useDetectionStore } from '../store/detectionStore'

export default function LiveMonitoring() {
  const personCount = useDetectionStore((s) => s.personCount)
  const fps = useDetectionStore((s) => s.fps)
  const averageConfidence = useDetectionStore((s) => s.averageConfidence)
  const detections = useDetectionStore((s) => s.detections)
  const cameraStatus = useDetectionStore((s) => s.cameraStatus)

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const isLive = cameraStatus === 'ONLINE'

  useEffect(() => {
    // sinkronkan status awal dari backend
    webcamApi
      .status()
      .then(({ data }) => {
        useDetectionStore.setState({ cameraStatus: data.camera_status })
      })
      .catch(() => {})
  }, [])

  const start = async () => {
    setBusy(true)
    setError(null)
    try {
      await webcamApi.start()
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setBusy(false)
    }
  }

  const stop = async () => {
    setBusy(true)
    setError(null)
    try {
      await webcamApi.stop()
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-rose-300">Kamera gagal dijalankan</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
            <p className="text-xs text-slate-500 mt-1.5">
              Pastikan webcam tidak sedang dipakai aplikasi lain dan beri izin kamera pada sistem.
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`badge border ${
              isLive
                ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                : 'bg-slate-500/10 text-slate-400 border-slate-500/25'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isLive ? 'bg-rose-400 animate-live-pulse' : 'bg-slate-500'
              }`}
            />
            {isLive ? 'LIVE' : 'OFFLINE'}
          </span>
          <span className="text-xs text-slate-500">
            Camera: <span className={isLive ? 'text-emerald-400' : 'text-slate-500'}>{cameraStatus}</span>
          </span>
        </div>

        <div className="flex gap-2">
          <button onClick={start} disabled={busy || isLive} className="btn-primary">
            <Play size={15} /> Start Camera
          </button>
          <button onClick={stop} disabled={busy || !isLive} className="btn-danger">
            <Square size={15} /> Stop Camera
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <CameraFeed className="aspect-video" />
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <StatCard icon={Users} label="Current People" value={personCount} accent="neon" />
            <StatCard icon={Gauge} label="FPS" value={fps.toFixed(1)} accent="green" />
            <StatCard
              icon={Target}
              label="Avg Confidence"
              value={`${Math.round(averageConfidence * 100)}%`}
              accent="amber"
            />
            <StatCard
              icon={Radio}
              label="Detection Status"
              value={isLive ? 'ACTIVE' : 'IDLE'}
              accent={isLive ? 'green' : 'rose'}
            />
          </div>
        </div>
      </div>

      <div className="card card-pad">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-white">Current Detections</h2>
          <span className="text-xs text-slate-500">{detections.length} objek</span>
        </div>
        <DetectionList
          detections={detections}
          emptyText={isLive ? 'Tidak ada person terdeteksi saat ini.' : 'Kamera tidak aktif.'}
        />
      </div>
    </div>
  )
}