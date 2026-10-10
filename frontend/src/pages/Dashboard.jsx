import { useEffect, useState } from 'react'
import {
  Users,
  TrendingUp,
  Activity,
  Camera,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import { PeopleTimelineChart } from '../components/Charts'
import DetectionList from '../components/DetectionList'
import { statisticsApi } from '../services/api'
import { useDetectionStore } from '../store/detectionStore'

const RANGES = [
  { key: 'today', label: 'Hari Ini' },
  { key: 'yesterday', label: 'Kemarin' },
  { key: '7d', label: '7 Hari' },
  { key: '30d', label: '30 Hari' },
]

export default function Dashboard() {
  const [range, setRange] = useState('today')
  const [summary, setSummary] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [bucketMinutes, setBucketMinutes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const personCount = useDetectionStore((s) => s.personCount)
  const detections = useDetectionStore((s) => s.detections)
  const cameraStatus = useDetectionStore((s) => s.cameraStatus)
  const wsStatus = useDetectionStore((s) => s.wsStatus)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [sumRes, tlRes] = await Promise.all([
        statisticsApi.summary({ range }),
        statisticsApi.timeline({ range }),
      ])
      setSummary(sumRes.data)
      setTimeline(tlRes.data.points || [])
      setBucketMinutes(tlRes.data.bucket_minutes || null)
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 30000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range])

  return (
    <div className="space-y-6">
      {/* Range selector */}
      <div className="flex flex-wrap items-center gap-2">
        {RANGES.map((r) => (
          <button
            key={r.key}
            onClick={() => setRange(r.key)}
            className={`rounded-xl px-3.5 py-2 text-xs font-medium border transition ${
              range === r.key
                ? 'bg-neon/10 text-neon border-neon/30'
                : 'bg-ink-700 text-slate-400 border-white/5 hover:text-slate-200'
            }`}
          >
            {r.label}
          </button>
        ))}
        <button
          onClick={load}
          className="btn-ghost text-xs px-3 py-2 ml-auto"
          disabled={loading}
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-rose-300">Gagal memuat data statistik</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
          <button onClick={load} className="btn-ghost text-xs">
            <RefreshCw size={13} /> Retry
          </button>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label="Total People Now"
          value={personCount}
          hint={cameraStatus === 'ONLINE' ? 'Live dari kamera' : 'Kamera offline'}
          accent="neon"
        />
        <StatCard
          icon={TrendingUp}
          label="Peak People"
          value={summary?.peak_people ?? 0}
          hint={
            summary?.peak_time
              ? `Pada ${new Date(summary.peak_time).toLocaleString('id-ID', {
                  day: '2-digit',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })}`
              : '—'
          }
          accent="amber"
        />
        <StatCard
          icon={Activity}
          label="Average People"
          value={summary?.average_people ?? 0}
          hint={`${summary?.total_records ?? 0} pencatatan`}
          accent="violet"
        />
        <StatCard
          icon={Camera}
          label="Detection Records"
          value={summary?.total_records ?? 0}
          hint={`${summary?.webcam_records ?? 0} webcam · ${summary?.image_records ?? 0} image · ${summary?.video_records ?? 0} video`}
          accent="green"
        />
      </div>

      {/* Chart + detections */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="card card-pad xl:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-white">People Detection Timeline</h2>
              <p className="text-xs text-slate-500">
                Rata-rata &amp; peak jumlah orang per periode
              </p>
            </div>
            <span className="badge bg-ink-700 text-slate-400 border border-white/5">
              {wsStatus === 'connected' ? 'Realtime' : 'Snapshot'}
            </span>
          </div>

          {loading && !timeline.length ? (
            <div className="h-[280px] flex items-center justify-center text-slate-600 text-sm">
              Memuat data...
            </div>
          ) : timeline.length ? (
            <PeopleTimelineChart
              data={timeline}
              height={280}
              bucketMinutes={bucketMinutes}
            />
          ) : (
            <div className="h-[280px] flex flex-col items-center justify-center text-slate-600 text-sm gap-2">
              <p>Belum ada data deteksi pada periode ini.</p>
              <p className="text-xs text-slate-700">
                Jalankan kamera atau upload gambar/video untuk mulai mengumpulkan data.
              </p>
            </div>
          )}
        </div>

        <div className="card card-pad">
          <h2 className="text-sm font-semibold text-white mb-3">Current Detections</h2>
          <DetectionList
            detections={detections}
            emptyText={
              cameraStatus === 'ONLINE'
                ? 'Tidak ada person terdeteksi.'
                : 'Kamera offline.'
            }
          />
        </div>
      </div>
    </div>
  )
}