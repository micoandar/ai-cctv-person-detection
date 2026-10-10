import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts'

const gridStroke = 'rgba(255,255,255,0.06)'
const axisStyle = { fill: '#64748B', fontSize: 11 }

const tooltipProps = {
  contentStyle: {
    background: '#0D1220',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 12,
    fontSize: 12,
    color: '#E2E8F0',
    boxShadow: '0 10px 30px -12px rgba(0,0,0,0.8)',
  },
  labelStyle: { color: '#94A3B8', fontSize: 11, marginBottom: 4 },
  itemStyle: { color: '#E2E8F0' },
}


// ======================================================================
// Custom Tooltip untuk People Timeline
// ======================================================================
function PeopleTimelineTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null

  const p = payload[0].payload
  const peak = p.peak_people ?? 0
  const avg = p.person_count ?? 0
  const samples = p.samples ?? 0
  const conf = p.average_confidence ?? 0

  // Hitung mundur: total orang-dalam-frame = avg × samples
  const totalSum = Math.round(avg * samples)

  // Estimasi interval snapshot (menit ke detik)
  const bucketMinutes = p._bucket_minutes || 15
  const intervalSec =
    samples > 0 ? Math.max(1, Math.round((bucketMinutes * 60) / samples)) : null

  // Format jam: "07 Okt, 17:15"
  const timeLabel = p.timestamp
    ? new Date(p.timestamp).toLocaleString('id-ID', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      })
    : label

  return (
    <div className="rounded-xl border border-white/10 bg-ink-800/95 backdrop-blur px-4 py-3 shadow-soft min-w-[280px] max-w-[340px]">
      {/* Header: waktu */}
      <p className="text-[11px] text-slate-400 mb-3 font-medium">{timeLabel}</p>

      {/* PEAK */}
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-[11px] text-slate-500">Peak People</span>
        <span className="text-sm font-semibold text-amber-400 tabular-nums">
          {peak} orang
        </span>
      </div>

      {/* AVERAGE dengan formula */}
      <div className="mb-3 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between gap-3 mb-1">
          <span className="text-[11px] text-slate-500">Average</span>
          <span className="text-sm font-semibold text-neon tabular-nums">
            {avg.toFixed(2)} orang
          </span>
        </div>

        {/* Formula transparan */}
        <div className="mt-1.5 px-2 py-1.5 rounded-lg bg-ink-900/60 border border-white/5">
          <p className="text-[10px] text-slate-500 leading-relaxed">
            <span className="text-slate-400 font-medium">Cara hitung:</span>
            <br />
            <span className="font-mono text-slate-300">
              {totalSum} orang ÷ {samples} snapshot = {avg.toFixed(2)}
            </span>
          </p>
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-[11px] text-slate-500">Avg Confidence</span>
        <span className="text-xs text-emerald-400 tabular-nums">
          {Math.round(conf * 100)}%
        </span>
      </div>

      {/* Pencatatan dengan penjelasan */}
      <div className="mb-3 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between gap-3 mb-1">
          <span className="text-[11px] text-slate-500">Total Snapshot</span>
          <span className="text-xs text-slate-300 tabular-nums font-medium">
            {samples}×
          </span>
        </div>
        <p className="text-[10px] text-slate-600 leading-relaxed mt-1">
          {intervalSec
            ? `Rata-rata 1 snapshot setiap ~${intervalSec} detik. Dalam periode ini terkumpul `
            : 'Dalam periode ini terkumpul '}
          <span className="text-slate-400 font-medium">{samples} snapshot</span>.
        </p>
      </div>

      {/* Info bawah */}
      <div className="text-[10px] text-slate-600 leading-relaxed space-y-1">
        <p>
          <span className="text-amber-400 font-medium">Peak</span> = jumlah orang{' '}
          <strong>terbanyak</strong> yang muncul bersamaan dalam 1 frame.
        </p>
        <p>
          <span className="text-neon font-medium">Average</span> = rata-rata{' '}
          <strong>seluruh snapshot</strong>. Nilai {avg.toFixed(2)} berarti mayoritas
          waktu kosong / 1 orang, tapi sesekali ada {peak} orang.
        </p>
      </div>
    </div>
  )
}


// ======================================================================
// Chart 1 — People Detection Timeline
// ======================================================================
export function PeopleTimelineChart({ data = [], height = 280, bucketMinutes = null }) {
  const bucketLabel = (() => {
    if (!bucketMinutes) return null
    if (bucketMinutes < 60) return `${bucketMinutes} menit`
    if (bucketMinutes < 1440) return `${bucketMinutes / 60} jam`
    return `${bucketMinutes / 1440} hari`
  })()

  // Suntikkan _bucket_minutes ke setiap titik agar tooltip bisa hitung interval
  const enriched = data.map((d) => ({ ...d, _bucket_minutes: bucketMinutes || 15 }))

  return (
    <div className="space-y-2">
      {bucketLabel && (
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <span className="inline-block w-2 h-2 rounded-full bg-neon" />
          <span>
            Setiap titik = ringkasan{' '}
            <strong className="text-slate-300">{bucketLabel}</strong>. Arahkan kursor ke
            titik untuk detail (peak, average, cara hitung, jumlah snapshot).
          </span>
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={enriched} margin={{ top: 10, right: 14, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="peopleFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22D3EE" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#22D3EE" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
          <XAxis
            dataKey="time"
            tick={axisStyle}
            tickLine={false}
            axisLine={false}
            minTickGap={24}
          />
          <YAxis
            tick={axisStyle}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            width={44}
          />
          <Tooltip content={<PeopleTimelineTooltip />} />
          <Area
            type="monotone"
            dataKey="person_count"
            name="Average People"
            stroke="#22D3EE"
            strokeWidth={2}
            fill="url(#peopleFill)"
            dot={false}
            activeDot={{ r: 5, fill: '#22D3EE', stroke: '#0A0F1A', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}


// ======================================================================
// Chart 2 — Detection Activity
// ======================================================================
export function DetectionActivityChart({ data = [], height = 260 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 14, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
        <XAxis
          dataKey="time"
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          minTickGap={24}
        />
        <YAxis
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
          width={44}
        />
        <Tooltip {...tooltipProps} />
        <Bar
          dataKey="samples"
          name="Snapshots"
          fill="#38BDF8"
          radius={[6, 6, 0, 0]}
          maxBarSize={26}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}


// ======================================================================
// Chart 3 — Hourly Average
// ======================================================================
export function HourlyAverageChart({ data = [], height = 260 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 14, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
        <XAxis
          dataKey="hour"
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          minTickGap={16}
        />
        <YAxis
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          width={44}
        />
        <Tooltip {...tooltipProps} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#94A3B8' }} />
        <Line
          type="monotone"
          dataKey="average_people"
          name="Avg People / Hour"
          stroke="#A78BFA"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}