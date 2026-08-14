import { useEffect } from "react"
import { Plus, RefreshCw } from "lucide-react"
import AppShell from "@/components/layout/AppShell"
import UploadZone from "@/components/document/UploadZone"
import DocumentCard from "@/components/document/DocumentCard"
import { useDocumentStore } from "@/store/documentStore"
import { useChatStore } from "@/store/chatStore"
import { useRouter } from "next/router"

export default function DocumentsPage() {
  const router = useRouter()
  const { documents, selectedIds, fetchDocuments, isLoading, clearSelected } = useDocumentStore()
  const { createSession } = useChatStore()

  useEffect(() => {
    fetchDocuments()
    const interval = setInterval(fetchDocuments, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleChatWithSelected = async () => {
    const sessionId = await createSession(selectedIds)
    clearSelected()
    router.push("/chat")
  }

  const ready      = documents.filter((d) => d.status === "ready")
  const processing = documents.filter((d) => d.status === "processing" || d.status === "pending")
  const failed     = documents.filter((d) => d.status === "failed")

  return (
    <AppShell>
      <div className="p-6 max-w-5xl mx-auto space-y-6">

        {/* Upload zone */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200
                        dark:border-gray-800 p-6">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Upload Documents
          </h2>
          <UploadZone />
        </div>

        {/* Action bar */}
        {selectedIds.length > 0 && (
          <div className="flex items-center justify-between bg-blue-50 dark:bg-blue-950/30
                          border border-blue-200 dark:border-blue-800 rounded-xl px-5 py-3">
            <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
              {selectedIds.length} document{selectedIds.length > 1 ? "s" : ""} selected
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={clearSelected}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Clear
              </button>
              <button
                onClick={handleChatWithSelected}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700
                           text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
              >
                <Plus className="h-4 w-4" />
                Chat with selected
              </button>
            </div>
          </div>
        )}

        {/* Document lists */}
        {isLoading && documents.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p>No documents yet. Upload one above to get started.</p>
          </div>
        ) : (
          <div className="space-y-6">

            {/* Processing */}
            {processing.length > 0 && (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider
                               text-gray-400 mb-3 flex items-center gap-2">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Processing ({processing.length})
                </h3>
                <div className="grid gap-3">
                  {processing.map((doc) => <DocumentCard key={doc.id} doc={doc} />)}
                </div>
              </section>
            )}

            {/* Ready */}
            {ready.length > 0 && (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
                  Ready ({ready.length})
                </h3>
                <div className="grid gap-3">
                  {ready.map((doc) => <DocumentCard key={doc.id} doc={doc} />)}
                </div>
              </section>
            )}

            {/* Failed */}
            {failed.length > 0 && (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-3">
                  Failed ({failed.length})
                </h3>
                <div className="grid gap-3">
                  {failed.map((doc) => <DocumentCard key={doc.id} doc={doc} />)}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}