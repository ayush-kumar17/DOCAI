import { useEffect } from "react"
import { Plus, Trash2 } from "lucide-react"
import AppShell from "@/components/layout/AppShell"
import ChatInterface from "@/components/chat/ChatInterface"
import { useChatStore } from "@/store/chatStore"
import { useDocumentStore } from "@/store/documentStore"

export default function ChatPage() {
  const {
    sessions, activeSession, fetchSessions,
    createSession, setSession, deleteSession,
  } = useChatStore()

  const { documents, selectedIds, toggleSelected, fetchDocuments } = useDocumentStore()
  const readyDocs = documents.filter((d) => d.status === "ready")

  useEffect(() => {
    fetchSessions()
    fetchDocuments()
  }, [])

  return (
    <AppShell>
      <div className="flex h-full">

        {/* Left panel — sessions + doc selector */}
        <div className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-800
                        bg-white dark:bg-gray-900 flex flex-col">

          {/* New chat button */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-800">
            <button
              onClick={() => createSession(selectedIds)}
              className="w-full flex items-center justify-center gap-2
                         bg-blue-600 hover:bg-blue-700 text-white text-sm
                         font-medium py-2.5 rounded-lg transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </button>
          </div>

          {/* Document selector */}
          {readyDocs.length > 0 && (
            <div className="p-3 border-b border-gray-200 dark:border-gray-800">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                Documents
              </p>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {readyDocs.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => toggleSelected(doc.id)}
                    className={`w-full text-left flex items-center gap-2 px-2 py-1.5
                                rounded-lg text-xs transition-colors
                                ${selectedIds.includes(doc.id)
                                  ? "bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300"
                                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                                }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0
                      ${selectedIds.includes(doc.id) ? "bg-blue-500" : "bg-gray-300"}`}
                    />
                    <span className="truncate">{doc.filename}</span>
                  </button>
                ))}
              </div>
              {selectedIds.length > 0 && (
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                  {selectedIds.length} selected
                </p>
              )}
            </div>
          )}

          {/* Sessions list */}
          <div className="flex-1 overflow-y-auto p-3">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              History
            </p>
            {sessions.length === 0 ? (
              <p className="text-xs text-gray-400 px-2">No chats yet</p>
            ) : (
              <div className="space-y-1">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`group flex items-center gap-2 px-2 py-2 rounded-lg
                                cursor-pointer transition-colors text-xs
                                ${activeSession?.id === session.id
                                  ? "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"
                                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                                }`}
                    onClick={() => setSession(session)}
                  >
                    <span className="flex-1 truncate">{session.title}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteSession(session.id) }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity
                                 text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right panel — chat */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <ChatInterface />
        </div>
      </div>
    </AppShell>
  )
}