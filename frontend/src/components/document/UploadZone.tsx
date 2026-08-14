"use client"

import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, File, CheckCircle, XCircle, Loader2, X } from "lucide-react"
import { useDocumentStore } from "@/store/documentStore"

interface UploadItem {
  file:     File
  progress: number
  status:   "uploading" | "done" | "error"
  error?:   string
}

const ACCEPTED = {
  "application/pdf":                  [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "text/plain":   [".txt"],
  "text/csv":     [".csv"],
  "text/markdown":[".md"],
  "image/png":    [".png"],
  "image/jpeg":   [".jpg", ".jpeg"],
}

export default function UploadZone() {
  const uploadDocument = useDocumentStore((s) => s.uploadDocument)
  const [queue, setQueue] = useState<UploadItem[]>([])

  const updateItem = (file: File, updates: Partial<UploadItem>) => {
    setQueue((q) => q.map((i) => i.file === file ? { ...i, ...updates } : i))
  }

  const onDrop = useCallback(async (accepted: File[]) => {
    const newItems: UploadItem[] = accepted.map((f) => ({
      file:     f,
      progress: 0,
      status:   "uploading",
    }))
    setQueue((q) => [...q, ...newItems])

    for (const item of newItems) {
      try {
        await uploadDocument(item.file, (pct) => {
          updateItem(item.file, { progress: pct })
        })
        updateItem(item.file, { status: "done", progress: 100 })
      } catch (err: any) {
        updateItem(item.file, {
          status: "error",
          error:  err.response?.data?.detail || "Upload failed",
        })
      }
    }
  }, [uploadDocument])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept:   ACCEPTED,
    multiple: true,
    maxSize:  50 * 1024 * 1024,   // 50MB
  })

  const removeItem = (file: File) => {
    setQueue((q) => q.filter((i) => i.file !== file))
  }

  return (
    <div className="space-y-4">

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-xl p-12 text-center
                    cursor-pointer transition-all duration-200
                    ${isDragActive
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30 scale-[1.01]"
                      : "border-gray-300 dark:border-gray-700 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                    }`}
      >
        <input {...getInputProps()} />
        <Upload className={`mx-auto mb-4 h-10 w-10 transition-colors
                            ${isDragActive ? "text-blue-500" : "text-gray-400"}`} />
        <p className="text-base font-medium text-gray-700 dark:text-gray-300">
          {isDragActive ? "Drop files here" : "Drag & drop files here"}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          or <span className="text-blue-600 dark:text-blue-400 font-medium">click to browse</span>
        </p>
        <p className="mt-3 text-xs text-gray-400">
          PDF · DOCX · PPTX · XLSX · CSV · TXT · MD · PNG · JPG · Max 50MB
        </p>
      </div>

      {/* Upload queue */}
      {queue.length > 0 && (
        <div className="space-y-2">
          {queue.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-lg border border-gray-200
                         dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3"
            >
              <File className="h-5 w-5 flex-shrink-0 text-gray-400" />

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-gray-900 dark:text-white">
                  {item.file.name}
                </p>
                <p className="text-xs text-gray-500">
                  {(item.file.size / 1024).toFixed(0)} KB
                </p>

                {/* Progress bar */}
                {item.status === "uploading" && (
                  <div className="mt-1.5 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-300"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                )}

                {item.status === "error" && (
                  <p className="text-xs text-red-500 mt-0.5">{item.error}</p>
                )}
              </div>

              {/* Status icon */}
              <div className="flex-shrink-0">
                {item.status === "uploading" && (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                )}
                {item.status === "done" && (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                )}
                {item.status === "error" && (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
              </div>

              <button
                onClick={() => removeItem(item.file)}
                className="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}