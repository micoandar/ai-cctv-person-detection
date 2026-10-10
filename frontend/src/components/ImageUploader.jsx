import { useCallback, useRef, useState } from 'react'
import { UploadCloud, ImageIcon, Loader2 } from 'lucide-react'

export default function ImageUploader({ onFile, loading = false, disabled = false }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = useCallback(
    (files) => {
      if (disabled || loading) return
      const file = files?.[0]
      if (!file) return
      if (!file.type.startsWith('image/')) {
        onFile(null, 'File harus berupa gambar (JPG, PNG, WEBP, BMP).')
        return
      }
      onFile(file, null)
    },
    [onFile, loading, disabled]
  )

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFiles(e.dataTransfer.files)
      }}
      onClick={() => !disabled && !loading && inputRef.current?.click()}
      className={`card card-pad cursor-pointer transition-all duration-200 border-2 border-dashed
        ${
          dragging
            ? 'border-neon/60 bg-neon/5'
            : 'border-white/10 hover:border-neon/40 hover:bg-ink-700/40'
        }
        ${disabled || loading ? 'opacity-60 cursor-not-allowed' : ''}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="w-14 h-14 rounded-2xl bg-neon/10 border border-neon/25 flex items-center justify-center">
          {loading ? (
            <Loader2 size={22} className="text-neon animate-spin" />
          ) : (
            <UploadCloud size={22} className="text-neon" />
          )}
        </div>

        <p className="mt-4 text-sm font-medium text-slate-200">
          {loading ? 'Memproses gambar...' : 'Drag & Drop Image'}
        </p>
        <p className="mt-1 text-xs text-slate-500">atau klik untuk memilih gambar dari komputer</p>

        <span className="mt-4 btn-ghost text-xs pointer-events-none">
          <ImageIcon size={14} />
          Choose Image
        </span>

        <p className="mt-3 text-[11px] text-slate-600">JPG, JPEG, PNG, BMP, WEBP — maksimal 15 MB</p>
      </div>
    </div>
  )
}