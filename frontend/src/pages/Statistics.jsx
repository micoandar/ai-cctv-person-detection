import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Hash,
  Clock,
  AlertTriangle,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import {
  PeopleTimelineChart,
  DetectionActivityChart,
  HourlyAverageChart,
} from '../components/Charts'
import { statisticsApi } from '../services/api'

const RANGES = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: '7d', label: 'Last 7 Days' },
  { key: '30d', label: 'Last 30 Days' },
]

export default function Statistics() {
  const [range, setRange] = useState('today')
  const [summary, setSummary] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [hourly, setHourly] = useState([])
  const [bucketMinutes, setBucketMinutes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [sumRes, tlRes, hrRes] = await Promise.all([
          statisticsApi.summary({ range }),
          statisticsApi.timeline({ range }),
          statisticsApi.hourly({ range }),
        ])
        if (!alive) return
        setSummary(sumRes.data)
        setTimeline(tlRes.data.points || [])
        setBucketMinutes(tlRes.data.bucket_minutes || null)
        setHourly(hrRes.data.items || [])
      } catch (err) {
        if (alive) setError(err.friendlyMessage)
      } finally {
        if (alive) setLoading(false)
      }
    }

    load()
    return () => {
      alive = false
    }
  }, [range])

  const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString('id-ID') : '—')

  return (
    <div className="space-y-6">
      {/* Range selector */}
      <div className="flex flex-wrap gap-1.5">
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
      </div>

      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-rose-300">Gagal memuat statistik</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <StatCard
          icon={TrendingUp}
          label="Maximum People"
          value={summary?.peak_people ?? 0}
          accent="amber"
        />
        <StatCard
          icon={TrendingDown}
          label="Minimum People"
          value={summary?.min_people ?? 0}
          accent="green"
        />
        <StatCard
          icon={Activity}
          label="Average People"
          value={summary?.average_people ?? 0}
          accent="violet"
        />
        <StatCard
          icon={Hash}
          label="Total Detections"
          value={summary?.total_records ?? 0}
          hint={`${summary?.total_people_detected ?? 0} total orang`}
          accent="neon"
        />
        <StatCard
          icon={Clock}
          label="Peak Detection Time"
          value={
            summary?.peak_time
              ? new Date(summary.peak_time).toLocaleTimeString('id-ID')
              : '—'
          }
          hint={fmtTime(summary?.peak_time)}
          accent="rose"
        />
      </div>

      {/* Charts */}
      <div className="card card-pad">
        <h2 className="text-sm font-semibold text-white mb-1">
          People Count Over Time
        </h2>
        <p className="text-xs text-slate-500 mb-4">
          Rata-rata & peak jumlah orang per periode
        </p>
        {timeline.length ? (
          <PeopleTimelineChart
            data={timeline}
            height={300}
            bucketMinutes={bucketMinutes}
          />
        ) : (
          <EmptyChart loading={loading} />
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="card card-pad">
          <h2 className="text-sm font-semibold text-white mb-1">
            Detection Activity
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Jumlah pencatatan deteksi per bucket waktu
          </p>
          {timeline.length ? (
            <DetectionActivityChart data={timeline} />
          ) : (
            <EmptyChart loading={loading} />
          )}
        </div>

        <div className="card card-pad">
          <h2 className="text-sm font-semibold text-white mb-1">
            Average People per Hour
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            Rata-rata jumlah orang per jam
          </p>
          {hourly.some((h) => h.samples > 0) ? (
            <HourlyAverageChart data={hourly} />
          ) : (
            <EmptyChart loading={loading} />
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyChart({ loading }) {
  return (
    <div className="h-[260px] flex items-center justify-center text-slate-600 text-sm">
      {loading ? 'Memuat data...' : 'Belum ada data pada rentang ini.'}
    </div>
  )
}