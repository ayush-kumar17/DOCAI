"use client"

import Link from "next/link"
import { useRouter } from "next/router"
import {
  LayoutDashboard, FileText, MessageSquare,
  BarChart2, Settings, ChevronRight,
} from "lucide-react"
import { useChatStore } from "@/store/chatStore"
import { useEffect } from "react"

const NAV = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/documents", icon: FileText,         label: "Documents" },
  { href: "/chat",      icon: MessageSquare,    label: "Chat" },
  { href: "/analytics", icon: BarChart2,        label: "Analytics" },
]

export default function Sidebar() {
  const router   = useRouter()
  const { sessions, fetchSessions, setSession, activeSession } = useChatStore()

  useEffect(() => {
    fetchSessions()
  }, [])

  return (
    <aside className="w-64 flex flex-col border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">

      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b border-gray-200 dark:border-gray-800">
        <span className="text-lg font-semibold text-gray-900 dark:text-white">
          DocAI
        </span>
        <span className="ml-2 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 px-2 py-0.5 rounded-full">
          Beta
        </span>
      </div>

      {/* Nav links */}
      <nav className="p-3 space-y-1">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = router.pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                ${active
                  ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Recent chat sessions */}
      {sessions.length > 0 && (
        <div className="flex-1 overflow-y-auto p-3 border-t border-gray-200 dark:border-gray-800">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider px-3 mb-2">
            Recent Chats
          </p>
          <div className="space-y-1">
            {sessions.slice(0, 10).map((session) => (
              <button
                key={session.id}
                onClick={() => {
                  setSession(session)
                  router.push("/chat")
                }}
                className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors
                  ${activeSession?.id === session.id
                    ? "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
              >
                <MessageSquare className="h-3.5 w-3.5 flex-shrink-0 opacity-50" />
                <span className="truncate flex-1">{session.title}</span>
                <ChevronRight className="h-3 w-3 opacity-30 flex-shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}

    </aside>
  )
}