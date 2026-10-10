import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// ============================================================
// Interceptor: ubah error menjadi pesan yang mudah dipahami
// ============================================================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'Terjadi kesalahan yang tidak diketahui.'

    if (error.code === 'ECONNABORTED') {
      message = 'Permintaan timeout. Server tidak merespons.'
    } else if (!error.response) {
      message =
        'Tidak dapat terhubung ke backend. Pastikan server FastAPI sudah berjalan di http://localhost:8000.'
    } else {
      const detail = error.response.data?.detail
      if (typeof detail === 'string') message = detail
      else if (Array.isArray(detail)) message = detail.map((d) => d.msg).join(', ')
      else if (detail) message = JSON.stringify(detail)
      else message = `Error ${error.response.status}`
    }

    error.friendlyMessage = message
    return Promise.reject(error)
  }
)

// ============================================================
// HEALTH
// ============================================================
export const healthApi = {
  check: () => api.get('/health'),
}

// ============================================================
// DETECTION (Image & Video)
// ============================================================
export const detectionApi = {
  /**
   * Upload gambar untuk deteksi person.
   * @param {File} file
   * @param {number} [confidence] - opsional, 0.05..0.95
   */
  uploadImage: (file, confidence) => {
    const form = new FormData()
    form.append('file', file)
    if (confidence != null) form.append('confidence', confidence)
    return api.post('/detection/image', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * Upload video untuk deteksi person (diproses di background).
   * @param {File} file
   * @param {(evt: ProgressEvent) => void} [onUploadProgress]
   */
  uploadVideo: (file, onUploadProgress) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/detection/video', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0, // upload besar tidak boleh timeout
      onUploadProgress,
    })
  },

  /**
   * Cek status & hasil deteksi video berdasarkan task_id.
   * @param {string} taskId
   */
  getVideoResult: (taskId) => api.get(`/detection/video/${taskId}`),
}

// ============================================================
// WEBCAM
// ============================================================
export const webcamApi = {
  start: (payload = {}) => api.post('/webcam/start', payload),
  stop: () => api.post('/webcam/stop'),
  status: () => api.get('/webcam/status'),
}

// ============================================================
// STATISTICS
// ============================================================
export const statisticsApi = {
  current: () => api.get('/statistics/current'),
  summary: (params = {}) => api.get('/statistics/summary', { params }),
  history: (params = {}) => api.get('/statistics/history', { params }),
  timeline: (params = {}) => api.get('/statistics/timeline', { params }),
  hourly: (params = {}) => api.get('/statistics/hourly', { params }),
}

// ============================================================
// ============================================================
// CHATBOT
// ============================================================
export const chatApi = {
  /**
   * Kirim pertanyaan ke chatbot.
   * @param {string} message
   * @param {string} pageContext - "live" | "video" | "image" | "general"
   */
  send: (message, pageContext = 'general') =>
    api.post('/chat', { message, page_context: pageContext }),
}

// ============================================================
// SETTINGS
// ============================================================
export const settingsApi = {
  get: () => api.get('/settings'),
  update: (payload) => api.put('/settings', payload),
}

export default api