export default function StatCard({ icon: Icon, label, value, unit, hint, accent = 'neon' }) {
  const accents = {
    neon: 'text-neon bg-neon/10 border-neon/20',
    green: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    violet: 'text-violet-400 bg-violet-500/10 border-violet-500/20',
  }

  return (
    <div className="card card-pad animate-fade-up">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-3xl font-semibold text-white tabular-nums">{value}</span>
            {unit && <span className="text-sm text-slate-500">{unit}</span>}
          </div>
          {hint && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
        </div>

        {Icon && (
          <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${accents[accent]}`}>
            <Icon size={18} />
          </div>
        )}
      </div>
    </div>
  )
}