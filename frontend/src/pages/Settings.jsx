import { useEffect, useState } from 'react'
import { Save, Play, Square, AlertTriangle, CheckCircle2, Cpu, Camera, Sliders } from 'lucide-react'
import { settingsApi, webcamApi } from '../services/api'
import { useDetectionStore } from '../store/detectionStore'

export default function Settings() {
  const [form, setForm] = useState({
    confidence_threshold: 0.5,
    detection_fps: 10,
    camera_index: 0,
    camera_width: 1280,
    camera_height: 720,
  })
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const cameraStatus = useDetectionStore((s) => s.cameraStatus)
  const isLive = cameraStatus === 'ONLINE'

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await settingsApi.get()
      setMeta(data)
      setForm({
        confidence_threshold: data.confidence_threshold,
        detection_fps: data.detection_fps,
        camera_index: data.camera_index,
        camera_width: data.camera_width,
        camera_height: data.camera_height,
      })
      useDetectionStore.setState({ cameraStatus: data.camera_running ? 'ONLINE' : 'OFFLINE' })
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const save = async () => {
    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const { data } = await settingsApi.update({
        confidence_threshold: Number(form.confidence_threshold),
        detection_fps: Number(form.detection_fps),
        camera_index: Number(form.camera_index),
        camera_width: Number(form.camera_width),
        camera_height: Number(form.camera_height),
      })
      setMeta(data.settings)
      setMessage('Pengaturan berhasil disimpan.')
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setSaving(false)
    }
  }

  const startCamera = async () => {
    setBusy(true)
    setError(null)
    try {
      await webcamApi.start({
        camera_index: Number(form.camera_index),
        confidence: Number(form.confidence_threshold),
        width: Number(form.camera_width),
        height: Number(form.camera_height),
        target_fps: Number(form.detection_fps),
      })
      setMessage('Kamera berhasil dijalankan.')
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setBusy(false)
    }
  }

  const stopCamera = async () => {
    setBusy(true)
    try {
      await webcamApi.stop()
      setMessage('Kamera dihentikan.')
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <div className="card card-pad text-slate-500 text-sm">Memuat pengaturan...</div>
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {message && (
        <div className="card card-pad border-emerald-500/25 bg-emerald-500/5 flex items-center gap-3">
          <CheckCircle2 size={18} className="text-emerald-400" />
          <p className="text-sm text-emerald-300">{message}</p>
        </div>
      )}

      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-rose-300">Terjadi kesalahan</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Detection settings */}
      <div className="card card-pad">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="w-9 h-9 rounded-xl bg-neon/10 border border-neon/25 flex items-center justify-center">
            <Sliders size={16} className="text-neon" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Detection Settings</h2>
            <p className="text-xs text-slate-500">Konfigurasi inference YOLO</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">
              Confidence Threshold
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0.05"
                max="0.95"
                step="0.05"
                value={form.confidence_threshold}
                onChange={(e) =>
                  setForm((f) => ({ ...f, confidence_threshold: Number(e.target.value) }))
                }
                className="flex-1 accent-cyan-400"
              />
              <span className="w-14 text-right text-sm font-semibold text-neon tabular-nums">
                {Number(form.confidence_threshold).toFixed(2)}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] text-slate-600">
              Semakin tinggi → semakin sedikit false positive.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">
              Detection FPS (maksimum)
            </label>
            <input
              type="number"
              min="1"
              max="30"
              value={form.detection_fps}
              onChange={(e) => setForm((f) => ({ ...f, detection_fps: e.target.value }))}
              className="input"
            />
            <p className="mt-1.5 text-[11px] text-slate-600">
              Batasi FPS inference agar penggunaan CPU tetap wajar.
            </p>
          </div>
        </div>
      </div>

      {/* Camera settings */}
      <div className="card card-pad">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/25 flex items-center justify-center">
            <Camera size={16} className="text-violet-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Camera Settings</h2>
            <p className="text-xs text-slate-500">Sumber video: kamera laptop</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Camera Index</label>
            <input
              type="number"
              min="0"
              max="10"
              value={form.camera_index}
              onChange={(e) => setForm((f) => ({ ...f, camera_index: e.target.value }))}
              className="input"
            />
            <p className="mt-1.5 text-[11px] text-slate-600">0 = kamera laptop default.</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Width</label>
            <input
              type="number"
              value={form.camera_width}
              onChange={(e) => setForm((f) => ({ ...f, camera_width: e.target.value }))}
              className="input"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Height</label>
            <input
              type="number"
              value={form.camera_height}
              onChange={(e) => setForm((f) => ({ ...f, camera_height: e.target.value }))}
              className="input"
            />
          </div>
        </div>

        <p className="mt-3 text-xs text-slate-500">
          Resolusi:{' '}
          <span className="text-slate-300 font-medium">
            {form.camera_width} × {form.camera_height}
          </span>
        </p>
      </div>

      {/* Model info */}
      <div className="card card-pad">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center">
            <Cpu size={16} className="text-amber-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Model Information</h2>
            <p className="text-xs text-slate-500">Status model YOLO</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <Info label="Model Path" value={meta?.model_path} mono />
          <Info
            label="Status"
            value={meta?.model_loaded ? 'LOADED' : meta?.model_exists ? 'NOT LOADED' : 'NOT FOUND'}
            accent={meta?.model_loaded ? 'text-emerald-400' : 'text-rose-400'}
          />
          <Info label="Classes" value={(meta?.class_names || []).join(', ') || '—'} />
          <Info label="Stats Save Interval" value={`${meta?.stats_save_interval ?? 5} detik`} />
        </div>

        {meta?.model_error && (
          <p className="mt-3 text-xs text-rose-400">{meta.model_error}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2.5">
        <button onClick={save} disabled={saving} className="btn-primary">
          <Save size={15} /> {saving ? 'Menyimpan...' : 'Save Settings'}
        </button>
        <button onClick={startCamera} disabled={busy || isLive} className="btn-ghost">
          <Play size={15} /> Start Camera
        </button>
        <button onClick={stopCamera} disabled={busy || !isLive} className="btn-danger">
          <Square size={15} /> Stop Camera
        </button>
      </div>
    </div>
  )
}

function Info({ label, value, mono = false, accent = '' }) {
  return (
    <div className="rounded-xl bg-ink-900/60 border border-white/5 px-3.5 py-2.5">
      <p className="text-[11px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 text-sm ${mono ? 'font-mono text-xs' : ''} ${accent || 'text-slate-200'} break-all`}>
        {value || '—'}
      </p>
    </div>
  )
}