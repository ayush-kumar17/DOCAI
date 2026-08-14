"use client"

import { useState } from "react"
import { BookOpen, ChevronDown, ChevronUp } from "lucide-react"
import { Citation } from "@/types"

interface Props {
  citations: Citation[]
}

export default function CitationsPanel({ citations }: Props) {
  const [open, setOpen] = useState(false)

  if (!citations.length) return null

  return (
    <div className="w-full max-w-lg">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-xs font-medium
                   text-blue-600 dark:text-blue-400 hover:underline"
      >
        <BookOpen className="h-3.5 w-3.5" />
        {citations.length} source{citations.length > 1 ? "s" : ""}
        {open
          ? <ChevronUp className="h-3 w-3" />
          : <ChevronDown className="h-3 w-3" />
        }
      </button>

      {open && (
        <div className="mt-2 space-y-2 animate-fade-in">
          {citations.map((c, i) => (
            <CitationCard key={i} citation={c} index={i + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const confidence = Math.round(citation.confidence * 100)
  const barColor   = confidence >= 80
    ? "bg-green-500"
    : confidence >= 50
    ? "bg-yellow-500"
    : "bg-red-400"

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700
                    bg-white dark:bg-gray-800 p-3 text-xs">
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-medium text-gray-700 dark:text-gray-300">
          Source {index}
          {citation.page && ` · Page ${citation.page}`}
          {citation.section && ` · ${citation.section}`}
        </span>

        {/* Confidence bar */}
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-16 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${barColor}`}
              style={{ width: `${confidence}%` }}
            />
          </div>
          <span className="text-gray-400">{confidence}%</span>
        </div>
      </div>

      <p className="text-gray-600 dark:text-gray-400 leading-relaxed line-clamp-3">
        {citation.text_snippet}
      </p>
    </div>
  )
}