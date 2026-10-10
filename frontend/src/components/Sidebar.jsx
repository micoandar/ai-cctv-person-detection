import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Video,
  Film,
  Image as ImageIcon,
  History,
  BarChart3,
  Settings as SettingsIcon,
  ScanEye,
} from 'lucide-react'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/live', label: 'Live Monitoring', icon: Video },
  { to: '/image-detection', label: 'Image Detection', icon: ImageIcon },
  { to: '/video-detection', label: 'Video Detection', icon: Film },
  { to: '/history', label: 'History', icon: History },
  { to: '/statistics', label: 'Statistics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

export default function Sidebar() {
  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col bg-ink-900 border-r border-white/5">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 h-16 border-b border-white/5">
        <div className="w-9 h-9 rounded-xl bg-neon/15 border border-neon/30 flex items-center justify-center">
          <ScanEye size={18} className="text-neon" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-white">AI CCTV</p>
          <p className="text-[11px] text-slate-500">Person Detection</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-neon/10 text-neon border border-neon/25 shadow-glow'
                  : 'text-slate-400 hover:bg-ink-700 hover:text-slate-200 border border-transparent'
              }`
            }
          >
            <Icon size={17} />
            <span className="font-medium">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <p className="text-[11px] text-slate-600 leading-relaxed">
          Local Mode
          <br />
          YOLO · FastAPI · MySQL
        </p>
      </div>
    </aside>
  )
}