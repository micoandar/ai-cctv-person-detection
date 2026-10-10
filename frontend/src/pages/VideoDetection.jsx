import { useEffect, useState } from 'react'
import {
  Film,
  Users,
  Target,
  Clock,
  AlertTriangle,
  RotateCcw,
  TrendingUp,
  Play,
  Loader2,
  FilmIcon,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
  ResponsiveContainer,
} from 'recharts'

import VideoUploader from '../components/VideoUploader'
import StatCard from '../components/StatCard'
import { detectionApi } from '../services/api'
import { useDetectionStore } from '../store/detectionStore'

export default function VideoDetection() {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState(null)

  const videoTask = useDetectionStore((s) => s.videoTask)
  const videoResult = useDetectionStore((s) => s.videoResult)
  const resetVideo = useDetectionStore((s) => s.resetVideo)

  // Fallback polling jika WebSocket tidak menerima event
  useEffect(() => {
    if (!videoTask?.task_id) return
    if (videoTask.status === 'completed' || videoTask.status === 'failed') return

    const timer = setInterval(async () => {
      try {
        const { data } = await detectionApi.getVideoResult(videoTask.task_id)
        if (data.status === 'completed') {
          useDetectionStore.getState().setVideoTask(null)
          useDetectionStore.getState().setVideoResult(data)
        } else if (data.status === 'failed') {
          useDetectionStore.setState({
            videoTask: { ...videoTask, status: 'failed', error: data.error },
          })
        } else {
          useDetectionStore.setState({ videoTask: { ...videoTask, ...data } })
        }
      } catch {
        /* noop */
      }
    }, 2000)

    return () => clearInterval(timer)
  }, [videoTask?.task_id, videoTask?.status])

  const handleFile = (selected, validationError) => {
    if (validationError) {
      setError(validationError)
      return
    }
    if (!selected) return

    setError(null)
    resetVideo()
    upload(selected)
  }

  const upload = async (f) => {
    setUploading(true)
    setUploadProgress(0)
    setError(null)
    try {
      const { data } = await detectionApi.uploadVideo(f, (evt) => {
        if (evt.total) setUploadProgress(Math.round((evt.loaded / evt.total) * 100))
      })
      useDetectionStore.setState({ videoTask: data, videoResult: null })
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setUploading(false)
    }
  }

  const reset = () => {
    setError(null)
    setUploadProgress(0)
    resetVideo()
  }

  const isProcessing =
    videoTask && videoTask.status !== 'completed' && videoTask.status !== 'failed'
  const hasResult = videoResult?.status === 'completed'

  return (
    <div className="space-y-6">
      {/* Error */}
      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-rose-300">Gagal memproses video</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Header aksi — di ATAS */}
      {hasResult && (
        <div className="card card-pad flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Hasil Deteksi Video</h2>
            <p className="text-xs text-slate-500">
              {videoResult.filename}
              {videoResult.fps ? ` · ${videoResult.fps} FPS` : ''}
              {videoResult.total_frames ? ` · ${videoResult.total_frames} frame` : ''}
              {videoResult.transcode_ok ? ' · H.264 ✓' : ''}
            </p>
          </div>
          <button onClick={reset} className="btn-primary">
            <RotateCcw size={15} /> Upload Another Video
          </button>
        </div>
      )}

      {/* Uploader */}
      {!hasResult && !isProcessing && !uploading && (
        <VideoUploader onFile={handleFile} loading={uploading} />
      )}

      {/* Upload progress */}
      {uploading && (
        <div className="card card-pad">
          <div className="flex items-center gap-3">
            <Loader2 size={18} className="animate-spin text-neon" />
            <div className="flex-1">
              <p className="text-sm text-slate-200">Meng-upload video... {uploadProgress}%</p>
              <div className="mt-2 h-1.5 bg-ink-900 rounded-full overflow-hidden">
                <div
                  className="h-full bg-neon transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Processing / Transcoding */}
      {isProcessing && (
        <div className="card card-pad space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-neon/10 border border-neon/25 flex items-center justify-center">
                <Film size={16} className="text-neon" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">
                  {videoTask.status === 'transcoding'
                    ? 'Mengoptimasi video (H.264)...'
                    : 'Memproses video...'}
                </p>
                <p className="text-xs text-slate-500">
                  Frame {videoTask.processed_frames} / {videoTask.total_frames} ·{' '}
                  {videoTask.current_people} orang
                </p>
              </div>
            </div>
            <span className="badge bg-neon/10 text-neon border border-neon/25">
              {Math.round(videoTask.progress || 0)}%
            </span>
          </div>

          <div className="h-2 bg-ink-900 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-neon transition-all duration-300"
              style={{ width: `${videoTask.progress || 0}%` }}
            />
          </div>

          <p className="text-xs text-slate-500">
            Estimasi sisa:{' '}
            {videoTask.eta_seconds != null ? `${videoTask.eta_seconds}s` : '—'} · Elapsed:{' '}
            {videoTask.elapsed_seconds || 0}s
          </p>
        </div>
      )}

      {/* Hasil */}
      {hasResult && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Original Video */}
            <div className="card overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/5 flex items-center gap-2">
                <Film size={14} className="text-slate-500" />
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Original Video
                </span>
              </div>
              {videoResult.original_video_url ? (
                <video
                  src={videoResult.original_video_url}
                  controls
                  preload="metadata"
                  className="w-full bg-black aspect-video"
                />
              ) : (
                <div className="w-full aspect-video bg-black/40 flex flex-col items-center justify-center text-slate-600 gap-2">
                  <FilmIcon size={28} />
                  <p className="text-xs">Video original sudah dihapus (hemat disk)</p>
                  <p className="text-[11px] text-slate-700">
                    Hasil deteksi tetap tersimpan di kanan
                  </p>
                </div>
              )}
            </div>

            {/* Detection Result */}
            <div className="card overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/5 flex items-center gap-2">
                <Play size={14} className="text-neon" />
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Detection Result
                </span>
              </div>
              <video
                src={videoResult.video_url}
                controls
                preload="metadata"
                className="w-full bg-black aspect-video"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={Users}
              label="Peak People"
              value={videoResult.peak_people}
              hint={`Pada ${formatTime(videoResult.peak_time_seconds)}`}
              accent="amber"
            />
            <StatCard
              icon={TrendingUp}
              label="Average People"
              value={videoResult.average_people}
              accent="neon"
            />
            <StatCard
              icon={Target}
              label="Avg Confidence"
              value={`${Math.round((videoResult.average_confidence || 0) * 100)}%`}
              accent="green"
            />
            <StatCard
              icon={Clock}
              label="Duration"
              value={formatTime(videoResult.duration)}
              hint={`${videoResult.fps} FPS · ${videoResult.total_frames} frame`}
              accent="violet"
            />
          </div>

          {/* Chart */}
          {videoResult.samples?.length > 0 && (
            <div className="card card-pad">
              <h2 className="text-sm font-semibold text-white mb-1">
                People Count Timeline
              </h2>
              <p className="text-xs text-slate-500 mb-4">
                Sampling tiap 1 detik selama video diproses
              </p>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart
                  data={videoResult.samples.map((s) => ({
                    time: formatTime(s.timestamp),
                    person_count: s.person_count,
                  }))}
                  margin={{ top: 10, right: 14, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="vidFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22D3EE" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#22D3EE" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.06)"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="time"
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    minTickGap={24}
                  />
                  <YAxis
                    tick={{ fill: '#64748B', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                    width={44}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#0D1220',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="person_count"
                    name="People"
                    stroke="#22D3EE"
                    strokeWidth={2}
                    fill="url(#vidFill)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* Failed */}
      {videoTask?.status === 'failed' && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-rose-300">Pemrosesan video gagal</p>
              <p className="text-xs text-rose-400/80 mt-0.5">
                {videoTask.error || 'Unknown error'}
              </p>
            </div>
            <button onClick={reset} className="btn-ghost text-xs">
              <RotateCcw size={13} /> Coba Lagi
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function formatTime(seconds) {
  if (seconds == null || isNaN(seconds)) return '—'
  const s = Math.floor(seconds)
  const m = Math.floor(s / 60)
  const sec = s % 60
  if (m > 0) return `${m}:${String(sec).padStart(2, '0')}`
  return `${sec}s`
}