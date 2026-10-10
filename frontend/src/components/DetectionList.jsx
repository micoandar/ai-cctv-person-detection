import { User, ScanFace } from 'lucide-react'

export default function DetectionList({ detections = [], emptyText = 'Belum ada deteksi.' }) {
  if (!detections.length) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-slate-600">
        <ScanFace size={26} />
        <p className="mt-2 text-sm">{emptyText}</p>
      </div>
    )
  }

  return (
    <ul className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
      {detections.map((det, idx) => {
        const conf = Math.round((det.confidence || 0) * 100)
        const b = det.bbox || {}
        return (
          <li
            key={idx}
            className="flex items-center gap-3 rounded-xl bg-ink-900/70 border border-white/5 px-3.5 py-2.5"
          >
            <div className="w-8 h-8 rounded-lg bg-neon/10 border border-neon/20 flex items-center justify-center">
              <User size={15} className="text-neon" />
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200">
                Person #{idx + 1}
                <span className="ml-2 text-[11px] uppercase tracking-wide text-slate-500">
                  {det.class || 'person'}
                </span>
              </p>
              <p className="text-[11px] text-slate-500 tabular-nums truncate">
                bbox [{Math.round(b.x1 ?? 0)}, {Math.round(b.y1 ?? 0)}] → [
                {Math.round(b.x2 ?? 0)}, {Math.round(b.y2 ?? 0)}]
              </p>
            </div>

            <span
              className={`badge border ${
                conf >= 80
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                  : conf >= 60
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/25'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/25'
              }`}
            >
              {conf}%
            </span>
          </li>
        )
      })}
    </ul>
  )
}