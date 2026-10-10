import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Bot, Send, Sparkles, User, X, Loader2, Info } from 'lucide-react'
import { chatApi } from '../services/api'

// Peta path → context
function pathToContext(pathname) {
  if (pathname.startsWith('/live')) return 'live'
  if (pathname.startsWith('/video-detection')) return 'video'
  if (pathname.startsWith('/image-detection')) return 'image'
  return 'general'
}

const CONTEXT_LABEL = {
  live: 'Live Monitoring',
  video: 'Video Detection',
  image: 'Image Detection',
  general: 'AI CCTV',
}

const SUGGESTIONS_BY_CONTEXT = {
  live: [
    'Berapa orang sekarang?',
    'Status kamera?',
    'Apakah jumlah orang meningkat?',
  ],
  video: [
    'Berapa orang di video terakhir?',
    'Video terakhir diproses kapan?',
    'Berapa rata-rata orang hari ini?',
  ],
  image: [
    'Berapa orang di gambar terakhir?',
    'Gambar terakhir diproses kapan?',
    'Berapa jumlah orang terbanyak hari ini?',
  ],
  general: [
    'Berapa orang sekarang?',
    'Berapa jumlah orang terbanyak hari ini?',
    'Jam berapa jumlah orang paling banyak?',
    'Berapa rata-rata orang hari ini?',
    'Apakah jumlah orang sedang meningkat?',
  ],
}

const INITIAL_MESSAGE = {
  live: 'Halo! Saya CCTV AI Assistant. Tanyakan apa saja tentang monitoring kamera live.',
  video: 'Halo! Saya CCTV AI Assistant. Tanyakan apa saja tentang deteksi video yang di-upload.',
  image: 'Halo! Saya CCTV AI Assistant. Tanyakan apa saja tentang deteksi gambar yang di-upload.',
  general: 'Halo! Saya CCTV AI Assistant. Tanyakan apa saja tentang monitoring, statistik, atau tren deteksi.',
}

export default function Chatbot() {
  const { pathname } = useLocation()
  const pageContext = pathToContext(pathname)

  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([])

  const endRef = useRef(null)

  // Reset percakapan ketika pindah halaman konteks
  useEffect(() => {
    setMessages([
      { role: 'assistant', content: INITIAL_MESSAGE[pageContext] || INITIAL_MESSAGE.general },
    ])
  }, [pageContext])

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, loading])

  const send = async (text) => {
    const question = (text ?? input).trim()
    if (!question || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setInput('')
    setLoading(true)

    try {
      const { data } = await chatApi.send(question, pageContext)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          intent: data.intent,
          context: data.page_context,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          error: true,
          content:
            err.friendlyMessage ||
            'Maaf, terjadi kesalahan saat menghubungi server chatbot.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const suggestions = SUGGESTIONS_BY_CONTEXT[pageContext] || SUGGESTIONS_BY_CONTEXT.general

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-2xl
                     bg-neon text-ink-950 px-4 py-3 font-semibold shadow-glow
                     hover:bg-cyan-300 transition-all duration-200 hover:scale-[1.03]"
        >
          <Bot size={18} />
          <span className="text-sm">CCTV AI</span>
        </button>
      )}

      {open && (
        <div
          className="fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)]
                     h-[600px] max-h-[calc(100vh-3rem)] flex flex-col
                     card overflow-hidden animate-fade-up"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-ink-900">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-neon/15 border border-neon/30 flex items-center justify-center">
                <Sparkles size={15} className="text-neon" />
              </div>
              <div className="leading-tight">
                <p className="text-sm font-semibold text-white">CCTV AI Assistant</p>
                <p className="text-[11px] text-slate-500">
                  Konteks: <span className="text-neon">{CONTEXT_LABEL[pageContext]}</span>
                </p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-ink-700"
            >
              <X size={16} />
            </button>
          </div>

          {/* Context banner */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-ink-800/60 border-b border-white/5">
            <Info size={11} className="text-slate-500" />
            <span className="text-[10px] text-slate-500">
              Jawaban disesuaikan dengan halaman{' '}
              <span className="text-slate-300">{CONTEXT_LABEL[pageContext]}</span>
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex gap-2.5 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div
                  className={`w-7 h-7 shrink-0 rounded-lg flex items-center justify-center border ${
                    m.role === 'user'
                      ? 'bg-violet-500/10 border-violet-500/25 text-violet-400'
                      : 'bg-neon/10 border-neon/25 text-neon'
                  }`}
                >
                  {m.role === 'user' ? <User size={13} /> : <Bot size={13} />}
                </div>

                <div
                  className={`max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-violet-500/15 text-violet-100 border border-violet-500/20'
                      : m.error
                      ? 'bg-rose-500/10 text-rose-200 border border-rose-500/20'
                      : 'bg-ink-900 text-slate-200 border border-white/5'
                  }`}
                >
                  {m.content}
                  {m.intent && m.role === 'assistant' && !m.error && (
                    <p className="mt-1.5 text-[10px] uppercase tracking-wider text-slate-600">
                      intent: {m.intent}
                    </p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-2.5">
                <div className="w-7 h-7 shrink-0 rounded-lg bg-neon/10 border border-neon/25 flex items-center justify-center">
                  <Bot size={13} className="text-neon" />
                </div>
                <div className="rounded-2xl px-3.5 py-2.5 bg-ink-900 border border-white/5">
                  <Loader2 size={14} className="animate-spin text-slate-500" />
                </div>
              </div>
            )}

            <div ref={endRef} />
          </div>

          {/* ============================================================
              SUGGESTIONS — selalu tampil, horizontal scroll
             ============================================================ */}
          <div className="border-t border-white/5 bg-ink-800/40">
            <div className="flex items-center justify-between px-3 pt-2 pb-1">
              <span className="text-[10px] uppercase tracking-wider text-slate-500">
                Saran Pertanyaan
              </span>
            </div>
            <div className="flex gap-1.5 overflow-x-auto px-3 pb-2.5 scrollbar-thin">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  disabled={loading}
                  className="shrink-0 text-[11px] rounded-full px-3 py-1.5 bg-ink-700 text-slate-300
                             border border-white/5 hover:border-neon/40 hover:text-neon
                             hover:bg-neon/5 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="p-3 border-t border-white/5 bg-ink-900">
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    send()
                  }
                }}
                placeholder={`Tanya tentang ${CONTEXT_LABEL[pageContext]}...`}
                className="input py-2.5"
                disabled={loading}
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim()}
                className="btn-primary px-3.5 py-2.5"
              >
                <Send size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}