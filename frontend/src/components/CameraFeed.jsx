import { VideoOff, Loader2 } from 'lucide-react'
import { useDetectionStore } from '../store/detectionStore'

export default function CameraFeed({ className = '' }) {
  const frame = useDetectionStore((s) => s.frame)
  const cameraStatus = useDetectionStore((s) => s.cameraStatus)
  const wsStatus = useDetectionStore((s) => s.wsStatus)

  const isLive = cameraStatus === 'ONLINE'

  return (
    <div className={`relative rounded-2xl overflow-hidden bg-black border border-white/5 ${className}`}>
      {/* Video / Placeholder */}
      {frame ? (
        <img src={frame} alt="Live camera feed" className="w-full h-full object-contain bg-black" />
      ) : (
        <div className="w-full h-full min-h-[280px] flex flex-col items-center justify-center gap-3 text-slate-600">
          {wsStatus === 'connecting' ? (
            <>
              <Loader2 size={34} className="animate-spin" />
              <p className="text-sm">Menghubungkan ke server...</p>
            </>
          ) : (
            <>
              <VideoOff size={34} />
              <p className="text-sm">
                {isLive ? 'Menunggu frame dari kamera...' : 'Kamera tidak aktif'}
              </p>
              <p className="text-xs text-slate-700">Tekan “Start Camera” untuk memulai</p>
            </>
          )}
        </div>
      )}

      {/* Overlay: LIVE */}
      {isLive && (
        <div className="absolute top-3 left-3 flex items-center gap-2">
          <span className="badge bg-rose-500/20 text-rose-300 border border-rose-500/40 backdrop-blur">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-live-pulse" />
            LIVE
          </span>
          <span className="badge bg-black/50 text-emerald-300 border border-emerald-500/30 backdrop-blur">
            Camera: ONLINE
          </span>
        </div>
      )}

      {/* Overlay: FPS */}
      {isLive && <FpsOverlay />}
    </div>
  )
}

function FpsOverlay() {
  const fps = useDetectionStore((s) => s.fps)
  return (
    <div className="absolute top-3 right-3 badge bg-black/50 text-slate-300 border border-white/10 backdrop-blur">
      {fps.toFixed(1)} FPS
    </div>
  )
}