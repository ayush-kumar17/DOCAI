"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Bot, User, Loader2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { useChatStore } from "@/store/chatStore"
import { useDocumentStore } from "@/store/documentStore"
import { Message } from "@/types"
import CitationsPanel from "./CitationsPanel"

const SUGGESTIONS = [
  "Summarize the key points",
  "What are the main conclusions?",
  "List all dates and deadlines",
  "Compare the documents",
  "What risks are mentioned?",
  "Generate interview questions",
]

export default function ChatInterface() {
  const { messages, isStreaming, streamStatus, sendMessage } = useChatStore()
  const { selectedIds } = useDocumentStore()
  const [input, setInput]   = useState("")
  const bottomRef           = useRef<HTMLDivElement>(null)
  const textareaRef         = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [input])

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    const text = input.trim()
    setInput("")
    await sendMessage(text, selectedIds)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState onSuggest={(s) => sendMessage(s, selectedIds)} />
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {/* Stream status indicator */}
        {isStreaming && streamStatus && (
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 animate-pulse">
            <Loader2 className="h-4 w-4 animate-spin" />
            {streamStatus}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Selected docs indicator */}
      {selectedIds.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-100 dark:border-gray-800
                        bg-blue-50 dark:bg-blue-950/20">
          <p className="text-xs text-blue-600 dark:text-blue-400">
            Searching in {selectedIds.length} selected document{selectedIds.length > 1 ? "s" : ""}
          </p>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-gray-200 dark:border-gray-800
                      bg-white dark:bg-gray-900 p-4">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isStreaming ? "Waiting for response..." : "Ask a question about your documents…"}
            disabled={isStreaming}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-4 py-3 text-sm text-gray-900 dark:text-white
                       placeholder-gray-400 outline-none focus:ring-2 focus:ring-blue-500
                       focus:border-transparent disabled:opacity-50
                       min-h-[48px] max-h-[200px] leading-relaxed"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="flex-shrink-0 h-12 w-12 rounded-xl bg-blue-600 hover:bg-blue-700
                       disabled:opacity-40 disabled:cursor-not-allowed
                       flex items-center justify-center transition-colors"
          >
            {isStreaming
              ? <Loader2 className="h-5 w-5 text-white animate-spin" />
              : <Send className="h-5 w-5 text-white" />
            }
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <div className={`flex gap-3 max-w-4xl mx-auto animate-fade-in
                     ${isUser ? "flex-row-reverse" : ""}`}>

      {/* Avatar */}
      <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center
                       ${isUser
                         ? "bg-blue-600"
                         : "bg-gray-200 dark:bg-gray-700"
                       }`}>
        {isUser
          ? <User className="h-4 w-4 text-white" />
          : <Bot  className="h-4 w-4 text-gray-600 dark:text-gray-300" />
        }
      </div>

      {/* Bubble + citations */}
      <div className={`flex flex-col gap-2 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
                         ${isUser
                           ? "bg-blue-600 text-white rounded-tr-sm"
                           : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white rounded-tl-sm"
                         }`}>
          {message.streaming && !message.content
            ? <TypingDots />
            : isUser
              ? <p>{message.content}</p>
              : (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                </div>
              )
          }
        </div>

        {/* Latency badge */}
        {message.latency_ms && (
          <span className="text-xs text-gray-400">
            {(message.latency_ms / 1000).toFixed(1)}s
          </span>
        )}

        {/* Citations */}
        {!message.streaming && message.citations && message.citations.length > 0 && (
          <CitationsPanel citations={message.citations} />
        )}
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}

function EmptyState({ onSuggest }: { onSuggest: (s: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full py-20 gap-6 text-center">
      <div className="h-16 w-16 rounded-full bg-blue-50 dark:bg-blue-950
                      flex items-center justify-center">
        <Bot className="h-8 w-8 text-blue-500" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Ask anything about your documents
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Select documents from the sidebar, then ask a question below
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="px-4 py-2 rounded-full border border-gray-200 dark:border-gray-700
                       text-sm text-gray-600 dark:text-gray-400
                       hover:bg-gray-50 dark:hover:bg-gray-800
                       hover:border-gray-300 dark:hover:border-gray-600
                       transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}