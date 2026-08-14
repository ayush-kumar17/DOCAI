import { create } from "zustand"
import api, { API_URL } from "@/utils/api"
import { ChatSession, Message, Citation } from "@/types"
import { useAuthStore } from "./authStore"

interface ChatStore {
  sessions:      ChatSession[]
  activeSession: ChatSession | null
  messages:      Message[]
  isStreaming:   boolean
  streamStatus:  string

  fetchSessions:   () => Promise<void>
  createSession:   (docIds?: string[]) => Promise<string>
  setSession:      (session: ChatSession) => Promise<void>
  deleteSession:   (id: string) => Promise<void>
  renameSession:   (id: string, title: string) => Promise<void>
  sendMessage:     (content: string, docIds: string[]) => Promise<void>
  clearMessages:   () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions:      [],
  activeSession: null,
  messages:      [],
  isStreaming:   false,
  streamStatus:  "",

  fetchSessions: async () => {
    const res = await api.get("/chat/sessions")
    set({ sessions: res.data })
  },

  createSession: async (docIds = []) => {
    const res = await api.post("/chat/sessions", {
      title:   "New Chat",
      doc_ids: docIds,
    })
    const session: ChatSession = {
      id:         res.data.session_id,
      title:      res.data.title,
      doc_ids:    res.data.doc_ids,
      created_at: res.data.created_at,
    }
    set((s) => ({
      sessions:      [session, ...s.sessions],
      activeSession: session,
      messages:      [],
    }))
    return session.id
  },

  setSession: async (session) => {
    set({ activeSession: session, messages: [], isStreaming: false })
    const res = await api.get(`/chat/sessions/${session.id}/history`)
    set({ messages: res.data })
  },

  deleteSession: async (id) => {
    await api.delete(`/chat/sessions/${id}`)
    set((s) => {
      const sessions = s.sessions.filter((s) => s.id !== id)
      const active   = s.activeSession?.id === id ? null : s.activeSession
      return { sessions, activeSession: active, messages: active ? s.messages : [] }
    })
  },

  renameSession: async (id, title) => {
    await api.patch(`/chat/sessions/${id}`, { title })
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, title } : sess
      ),
      activeSession:
        s.activeSession?.id === id
          ? { ...s.activeSession, title }
          : s.activeSession,
    }))
  },

  sendMessage: async (content, docIds) => {
    const { activeSession, createSession } = get()
    const token = useAuthStore.getState().token

    // Create session if none exists
    let sessionId = activeSession?.id
    if (!sessionId) {
      sessionId = await createSession(docIds)
    }

    // Add user message optimistically
    const userMsg: Message = {
      id:         `temp-${Date.now()}`,
      role:       "user",
      content,
      citations:  [],
      latency_ms: null,
      created_at: new Date().toISOString(),
    }

    // Add assistant placeholder
    const assistantTempId = `streaming-${Date.now()}`
    const assistantMsg: Message = {
      id:         assistantTempId,
      role:       "assistant",
      content:    "",
      citations:  [],
      latency_ms: null,
      created_at: new Date().toISOString(),
      streaming:  true,
    }

    set((s) => ({
      messages:    [...s.messages, userMsg, assistantMsg],
      isStreaming: true,
      streamStatus:"Thinking...",
    }))

    // Stream from backend
    try {
      const response = await fetch(
        `${API_URL}/api/chat/sessions/${sessionId}/message`,
        {
          method: "POST",
          headers: {
            "Content-Type":  "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({ content, doc_ids: docIds }),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader  = response.body!.getReader()
      const decoder = new TextDecoder()
      let   citations: Citation[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text  = decoder.decode(value, { stream: true })
        const lines = text.split("\n").filter((l) => l.startsWith("data: "))

        for (const line of lines) {
          try {
            const event = JSON.parse(line.slice(6))

            switch (event.type) {
              case "intent":
                set({ streamStatus: `Understanding intent: ${event.data}` })
                break

              case "chunks":
                set({ streamStatus: `Reading ${event.data} relevant passages...` })
                break

              case "refining":
                set({ streamStatus: "Refining search..." })
                break

              case "token":
                set((s) => ({
                  messages: s.messages.map((m) =>
                    m.id === assistantTempId
                      ? { ...m, content: m.content + event.data }
                      : m
                  ),
                  streamStatus: "Writing answer...",
                }))
                break

              case "citations":
                citations = event.data
                break

              case "done":
                set((s) => ({
                  messages: s.messages.map((m) =>
                    m.id === assistantTempId
                      ? {
                          ...m,
                          streaming:  false,
                          citations,
                          latency_ms: event.data?.latency_ms ?? null,
                        }
                      : m
                  ),
                  isStreaming:  false,
                  streamStatus: "",
                }))
                break

              case "error":
                set((s) => ({
                  messages: s.messages.map((m) =>
                    m.id === assistantTempId
                      ? { ...m, content: `Error: ${event.data}`, streaming: false }
                      : m
                  ),
                  isStreaming:  false,
                  streamStatus: "",
                }))
                break
            }
          } catch {
            // Malformed SSE line — skip
          }
        }
      }
    } catch (err: any) {
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantTempId
            ? { ...m, content: `Failed to get response: ${err.message}`, streaming: false }
            : m
        ),
        isStreaming:  false,
        streamStatus: "",
      }))
    }
  },

  clearMessages: () => set({ messages: [] }),
}))