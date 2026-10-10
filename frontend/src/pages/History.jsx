import { useCallback, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, RefreshCw, AlertTriangle } from 'lucide-react'
import { statisticsApi } from '../services/api'

const RANGES = [
  { key: 'today', label: 'Today' },
  { key: 'yesterday', label: 'Yesterday' },
  { key: '7d', label: 'Last 7 Days' },
  { key: '30d', label: 'Last 30 Days' },
  { key: 'custom', label: 'Custom Date' },
]

const SOURCE_BADGE = {
  webcam: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/25',
  image: 'bg-violet-500/10 text-violet-400 border-violet-500/25',
  video: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
}

export default function History() {
  const [range, setRange] = useState('today')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)

  const [data, setData] = useState({
    items: [],
    total: 0,
    page: 1,
    total_pages: 1,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { range, page, page_size: pageSize }
      if (range === 'custom') {
        if (start) params.start = start
        if (end) params.end = end
      }
      if (sourceType) params.source_type = sourceType

      const { data: res } = await statisticsApi.history(params)
      setData(res)
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setLoading(false)
    }
  }, [range, page, pageSize, sourceType, start, end])

  useEffect(() => {
    load()
  }, [load])

  // Reset page saat filter berubah
  useEffect(() => {
    setPage(1)
  }, [range, sourceType, start, end])

  const fmt = (iso) => {
    if (!iso) return '—'
    try {
      const d = new Date(iso)
      return d.toLocaleString('id-ID', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="space-y-5">
      {/* ============================ FILTERS ============================ */}
      <div className="card card-pad">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">
              Periode
            </label>
            <div className="flex flex-wrap gap-1.5">
              {RANGES.map((r) => (
                <button
                  key={r.key}
                  onClick={() => setRange(r.key)}
                  className={`rounded-xl px-3 py-2 text-xs font-medium border transition ${
                    range === r.key
                      ? 'bg-neon/10 text-neon border-neon/30'
                      : 'bg-ink-700 text-slate-400 border-white/5 hover:text-slate-200'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">
              Source
            </label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="input py-2 w-36"
            >
              <option value="">Semua</option>
              <option value="webcam">Webcam</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
            </select>
          </div>

          {range === 'custom' && (
            <>
              <div>
                <label className="block text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">
                  Dari
                </label>
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="input py-2 w-40"
                />
              </div>
              <div>
                <label className="block text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">
                  Sampai
                </label>
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="input py-2 w-40"
                />
              </div>
            </>
          )}

          <button onClick={load} className="btn-ghost ml-auto">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* ============================ ERROR ============================ */}
      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-rose-300">Gagal memuat riwayat</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* ============================ TABLE ============================ */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 bg-ink-900/60">
                <th className="table-head text-left px-5 py-3">Time</th>
                <th className="table-head text-left px-5 py-3">Source</th>
                <th className="table-head text-right px-5 py-3">People</th>
                <th className="table-head text-right px-5 py-3">Confidence</th>
                <th className="table-head text-left px-5 py-3">Session</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data.items.length && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-slate-600">
                    Memuat data...
                  </td>
                </tr>
              )}

              {!loading && !data.items.length && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-slate-600">
                    Tidak ada data untuk filter ini.
                  </td>
                </tr>
              )}

              {data.items.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-white/5 last:border-0 hover:bg-ink-700/40 transition"
                >
                  <td className="px-5 py-3 text-slate-300 tabular-nums">
                    {fmt(row.detected_at)}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`badge border ${
                        SOURCE_BADGE[row.source_type] ||
                        'bg-slate-500/10 text-slate-400 border-slate-500/25'
                      }`}
                    >
                      {row.source_type}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-white tabular-nums">
                    {row.person_count}
                  </td>
                  <td className="px-5 py-3 text-right text-slate-300 tabular-nums">
                    {Math.round((row.average_confidence || 0) * 100)}%
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-500 font-mono">
                    {row.session_id || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ============================ PAGINATION ============================ */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-white/5">
          <p className="text-xs text-slate-500">
            Total <span className="text-slate-300 font-medium">{data.total}</span> data ·
            Halaman <span className="text-slate-300 font-medium">{data.page}</span> dari{' '}
            <span className="text-slate-300 font-medium">{data.total_pages}</span>
          </p>

          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={data.page <= 1 || loading}
              className="btn-ghost text-xs px-3 py-2"
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              disabled={data.page >= data.total_pages || loading}
              className="btn-ghost text-xs px-3 py-2"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}