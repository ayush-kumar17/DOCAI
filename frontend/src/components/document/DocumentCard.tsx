"use client"

import { FileText, File, Table, Image, Trash2, CheckSquare, Square } from "lucide-react"
import { Document } from "@/types"
import { useDocumentStore } from "@/store/documentStore"

const TYPE_ICONS: Record<string, React.ReactNode> = {
  pdf:  <FileText className="h-5 w-5 text-red-500" />,
  docx: <FileText className="h-5 w-5 text-blue-500" />,
  pptx: <FileText className="h-5 w-5 text-orange-500" />,
  xlsx: <Table     className="h-5 w-5 text-green-500" />,
  csv:  <Table     className="h-5 w-5 text-green-400" />,
  png:  <Image     className="h-5 w-5 text-purple-500" />,
  jpg:  <Image     className="h-5 w-5 text-purple-500" />,
}

const STATUS_STYLES = {
  pending:    "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  processing: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  ready:      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  failed:     "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
}

interface Props {
  doc: Document
}

export default function DocumentCard({ doc }: Props) {
  const { selectedIds, toggleSelected, deleteDocument } = useDocumentStore()
  const isSelected = selectedIds.includes(doc.id)

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`Delete "${doc.filename}"?`)) {
      await deleteDocument(doc.id)
    }
  }

  return (
    <div
      onClick={() => doc.status === "ready" && toggleSelected(doc.id)}
      className={`group relative flex items-start gap-4 rounded-xl border p-4
                  transition-all duration-150 cursor-pointer
                  ${isSelected
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30 dark:border-blue-600"
                    : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600"
                  }
                  ${doc.status !== "ready" ? "opacity-75 cursor-default" : ""}`}
    >
      {/* Select checkbox */}
      <div className="flex-shrink-0 mt-0.5">
        {doc.status === "ready" ? (
          isSelected
            ? <CheckSquare className="h-5 w-5 text-blue-600" />
            : <Square className="h-5 w-5 text-gray-300 dark:text-gray-600 group-hover:text-gray-400" />
        ) : (
          <div className="h-5 w-5 rounded border border-gray-200 dark:border-gray-700" />
        )}
      </div>

      {/* Icon */}
      <div className="flex-shrink-0">
        {TYPE_ICONS[doc.type] || <File className="h-5 w-5 text-gray-400" />}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {doc.filename}
        </p>
        <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
          <span>{doc.size_mb} MB</span>
          {doc.page_count > 0 && <span>{doc.page_count} pages</span>}
          {doc.chunk_count > 0 && <span>{doc.chunk_count} chunks</span>}
        </div>

        {/* Status + processing animation */}
        <div className="mt-2 flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[doc.status]}`}>
            {doc.status === "processing" && (
              <span className="h-1.5 w-1.5 rounded-full bg-yellow-500 animate-pulse" />
            )}
            {doc.status}
          </span>
          <span className="text-xs text-gray-400">
            {new Date(doc.uploaded_at).toLocaleDateString()}
          </span>
        </div>

        {doc.status === "failed" && doc.error_message && (
          <p className="mt-1 text-xs text-red-500 truncate">{doc.error_message}</p>
        )}
      </div>

      {/* Delete button */}
      <button
        onClick={handleDelete}
        className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                   p-1 rounded text-gray-400 hover:text-red-500"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  )
}