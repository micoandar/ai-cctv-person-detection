import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export const useDetectionStore = create(
  persist(
    (set) => ({
      // ============================================================
      // KONEKSI
      // ============================================================
      wsStatus: 'disconnected',
      error: null,

      // ============================================================
      // KAMERA / LIVE DETECTION
      // ============================================================
      cameraStatus: 'OFFLINE',
      sessionId: null,

      personCount: 0,
      fps: 0,
      averageConfidence: 0,
      detections: [],
      frame: null,
      lastUpdate: null,

      // ============================================================
      // VIDEO TASK (upload & progress)
      // ============================================================
      videoTask: null,
      videoResult: null,

      // ============================================================
      // IMAGE RESULT (persist agar tidak hilang saat refresh)
      // ============================================================
      imageResult: null,

      // ============================================================
      // ACTIONS - Umum
      // ============================================================
      setWsStatus: (wsStatus) => set({ wsStatus }),
      setError: (error) => set({ error }),

      reset: () =>
        set({
          cameraStatus: 'OFFLINE',
          personCount: 0,
          fps: 0,
          averageConfidence: 0,
          detections: [],
          frame: null,
          lastUpdate: null,
        }),

      // ============================================================
      // ACTIONS - Video
      // ============================================================
      setVideoTask: (videoTask) => set({ videoTask }),
      setVideoResult: (videoResult) => set({ videoResult }),
      resetVideo: () => set({ videoTask: null, videoResult: null }),

      // ============================================================
      // ACTIONS - Image
      // ============================================================
      setImageResult: (imageResult) => set({ imageResult }),
      resetImage: () => set({ imageResult: null }),

      // ============================================================
      // SOCKET MESSAGE HANDLER
      // ============================================================
      handleSocketMessage: (msg) => {
        if (!msg || !msg.type) return

        if (msg.type === 'detection') {
          set((state) => ({
            cameraStatus: msg.camera_status || state.cameraStatus,
            personCount: msg.person_count ?? 0,
            fps: msg.fps ?? 0,
            averageConfidence: msg.average_confidence ?? 0,
            detections: msg.detections ?? [],
            lastUpdate: msg.timestamp ?? null,
            sessionId: msg.session_id ?? state.sessionId,
            frame: msg.frame ? msg.frame : state.frame,
          }))
          return
        }

        if (msg.type === 'status') {
          set((state) => ({
            cameraStatus: msg.camera_status || state.cameraStatus,
            sessionId: msg.session_id ?? state.sessionId,
            frame: msg.camera_status === 'OFFLINE' ? null : state.frame,
            personCount: msg.camera_status === 'OFFLINE' ? 0 : state.personCount,
            fps: msg.camera_status === 'OFFLINE' ? 0 : state.fps,
            averageConfidence:
              msg.camera_status === 'OFFLINE' ? 0 : state.averageConfidence,
            detections: msg.camera_status === 'OFFLINE' ? [] : state.detections,
          }))
          return
        }

        if (msg.type === 'video_progress') {
          set((state) => ({
            videoTask: {
              ...(state.videoTask || {}),
              task_id: msg.task_id,
              status: msg.status || 'processing',
              progress: msg.progress ?? state.videoTask?.progress ?? 0,
              processed_frames:
                msg.processed_frames ?? state.videoTask?.processed_frames ?? 0,
              total_frames:
                msg.total_frames ?? state.videoTask?.total_frames ?? 0,
              current_people:
                msg.current_people ?? state.videoTask?.current_people ?? 0,
              elapsed_seconds:
                msg.elapsed_seconds ?? state.videoTask?.elapsed_seconds ?? 0,
              eta_seconds: msg.eta_seconds ?? state.videoTask?.eta_seconds ?? null,
            },
          }))
          return
        }

        if (msg.type === 'video_completed') {
          set({ videoTask: null, videoResult: msg.result })
          return
        }

        if (msg.type === 'video_failed') {
          set((state) => ({
            videoTask: {
              ...(state.videoTask || {}),
              task_id: msg.task_id,
              status: 'failed',
              error: msg.error,
            },
          }))
          return
        }
      },
    }),
    {
      name: 'ai-cctv-store',
      storage: createJSONStorage(() => localStorage),
      // Hanya persist data yang perlu bertahan saat refresh
      partialize: (state) => ({
        videoTask: state.videoTask,
        videoResult: state.videoResult,
        imageResult: state.imageResult,
      }),
    }
  )
)