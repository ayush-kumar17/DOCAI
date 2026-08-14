import { create } from "zustand"
import api from "@/utils/api"
import { Document } from "@/types"

interface DocumentStore {
  documents:    Document[]
  selectedIds:  string[]
  isLoading:    boolean

  fetchDocuments:  () => Promise<void>
  uploadDocument:  (file: File, onProgress?: (pct: number) => void) => Promise<Document>
  deleteDocument:  (id: string) => Promise<void>
  toggleSelected:  (id: string) => void
  setSelected:     (ids: string[]) => void
  clearSelected:   () => void
  pollStatus:      (docId: string) => Promise<void>
}

export const useDocumentStore = create<DocumentStore>((set, get) => ({
  documents:   [],
  selectedIds: [],
  isLoading:   false,

  fetchDocuments: async () => {
    set({ isLoading: true })
    try {
      const res = await api.get("/documents")
      set({ documents: res.data })
    } finally {
      set({ isLoading: false })
    }
  },

  uploadDocument: async (file, onProgress) => {
    const form = new FormData()
    form.append("file", file)

    const res = await api.post("/documents/upload", form, {
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      },
    })

    // Add to list immediately as pending
    const newDoc: Document = {
      id:           res.data.doc_id,
      filename:     res.data.filename,
      type:         res.data.type,
      size_bytes:   0,
      size_mb:      0,
      status:       "pending",
      page_count:   0,
      chunk_count:  0,
      tags:         [],
      uploaded_at:  new Date().toISOString(),
      processed_at: null,
    }

    set((s) => ({ documents: [newDoc, ...s.documents] }))

    // Start polling for status
    get().pollStatus(res.data.doc_id)

    return newDoc
  },

  deleteDocument: async (id) => {
    await api.delete(`/documents/${id}`)
    set((s) => ({
      documents:   s.documents.filter((d) => d.id !== id),
      selectedIds: s.selectedIds.filter((sid) => sid !== id),
    }))
  },

  toggleSelected: (id) => {
    set((s) => ({
      selectedIds: s.selectedIds.includes(id)
        ? s.selectedIds.filter((sid) => sid !== id)
        : [...s.selectedIds, id],
    }))
  },

  setSelected: (ids) => set({ selectedIds: ids }),
  clearSelected: ()  => set({ selectedIds: [] }),

  pollStatus: async (docId) => {
    // Poll every 3 seconds until status is ready or failed
    const poll = async () => {
      try {
        const res = await api.get(`/documents/${docId}/status`)
        const { status, page_count, chunk_count } = res.data

        set((s) => ({
          documents: s.documents.map((d) =>
            d.id === docId
              ? { ...d, status, page_count, chunk_count }
              : d
          ),
        }))

        if (status === "pending" || status === "processing") {
          setTimeout(poll, 3000)
        }
      } catch {
        // Document might have been deleted — stop polling
      }
    }

    setTimeout(poll, 2000)
  },
}))