import { useState } from 'react'
import {
  RotateCcw,
  Users,
  Target,
  Clock,
  AlertTriangle,
  ImageIcon,
} from 'lucide-react'
import ImageUploader from '../components/ImageUploader'
import DetectionList from '../components/DetectionList'
import StatCard from '../components/StatCard'
import { detectionApi } from '../services/api'
import { useDetectionStore } from '../store/detectionStore'

export default function ImageDetection() {
  // Persist result di Zustand — tidak hilang saat refresh
  const imageResult = useDetectionStore((s) => s.imageResult)
  const setImageResult = useDetectionStore((s) => s.setImageResult)
  const resetImage = useDetectionStore((s) => s.resetImage)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFile = (selected, validationError) => {
    if (validationError) {
      setError(validationError)
      return
    }
    if (!selected) return
    setError(null)
    runDetection(selected)
  }

  const runDetection = async (f) => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await detectionApi.uploadImage(f)
      setImageResult(data)
    } catch (err) {
      setError(err.friendlyMessage)
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setError(null)
    resetImage()
  }

  const hasResult = Boolean(imageResult)
  const preview = imageResult?.original_image

  return (
    <div className="space-y-6">
      {/* Error */}
      {error && (
        <div className="card card-pad border-rose-500/25 bg-rose-500/5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-rose-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-rose-300">Gagal memproses gambar</p>
            <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Header aksi — di ATAS, mudah dilihat */}
      {hasResult && (
        <div className="card card-pad flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Hasil Deteksi Gambar</h2>
            <p className="text-xs text-slate-500">
              {imageResult.detected_at
                ? new Date(imageResult.detected_at).toLocaleString('id-ID')
                : 'Tersimpan'}
              {imageResult.inference_ms != null && (
                <> · Inference {imageResult.inference_ms} ms</>
              )}
            </p>
          </div>
          <button onClick={reset} className="btn-primary">
            <RotateCcw size={15} /> Upload Another Image
          </button>
        </div>
      )}

      {/* Uploader — hanya tampil kalau belum ada result */}
      {!hasResult && (
        <ImageUploader onFile={handleFile} loading={loading} />
      )}

      {/* Loading state saat upload berikutnya */}
      {hasResult && loading && (
        <div className="card card-pad flex items-center gap-3 text-slate-300">
          <div className="w-5 h-5 border-2 border-neon/30 border-t-neon rounded-full animate-spin" />
          <span className="text-sm">Memproses gambar baru...</span>
        </div>
      )}

      {/* Hasil */}
      {hasResult && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Original */}
            <div className="card overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/5 flex items-center gap-2">
                <ImageIcon size={14} className="text-slate-500" />
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Original Image
                </span>
              </div>
              <div className="bg-black/40 flex items-center justify-center min-h-[260px]">
                {preview ? (
                  <img src={preview} alt="Original" className="w-full h-full object-contain" />
                ) : (
                  <span className="text-slate-600 text-sm">Tidak ada gambar</span>
                )}
              </div>
            </div>

            {/* Processed */}
            <div className="card overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/5 flex items-center gap-2">
                <Target size={14} className="text-neon" />
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Detection Result
                </span>
              </div>
              <div className="bg-black/40 flex items-center justify-center min-h-[260px]">
                {imageResult.processed_image ? (
                  <img
                    src={imageResult.processed_image}
                    alt="Processed"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <span className="text-slate-600 text-sm">Belum ada hasil</span>
                )}
              </div>
            </div>
          </div>

          {/* Statistik */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard
              icon={Users}
              label="People Detected"
              value={imageResult.person_count}
              accent="neon"
            />
            <StatCard
              icon={Target}
              label="Average Confidence"
              value={`${Math.round((imageResult.average_confidence || 0) * 100)}%`}
              accent="green"
            />
            <StatCard
              icon={Clock}
              label="Inference Time"
              value={imageResult.inference_ms ?? 0}
              unit="ms"
              accent="violet"
            />
          </div>

          {/* Detection list */}
          <div className="card card-pad">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">Detection Results</h2>
              <span className="text-xs text-slate-500">
                {(imageResult.detections || []).length} objek
              </span>
            </div>
            <DetectionList
              detections={imageResult.detections}
              emptyText="Tidak ada person terdeteksi pada gambar ini."
            />
          </div>
        </>
      )}
    </div>
  )
}