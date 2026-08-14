"use client"

import { useRouter } from "next/router"
import { LogOut, User } from "lucide-react"
import { useAuthStore } from "@/store/authStore"

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/documents": "Documents",
  "/chat":      "Chat",
  "/analytics": "Analytics",
}

export default function Topbar() {
  const router   = useRouter()
  const { user, logout } = useAuthStore()
  const title    = PAGE_TITLES[router.pathname] || "DocAI"

  return (
    <header className="h-14 flex items-center justify-between px-6
                       border-b border-gray-200 dark:border-gray-800
                       bg-white dark:bg-gray-900 flex-shrink-0">
      <h1 className="text-base font-semibold text-gray-900 dark:text-white">
        {title}
      </h1>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <div className="h-7 w-7 rounded-full bg-blue-100 dark:bg-blue-900
                          flex items-center justify-center">
            <User className="h-4 w-4 text-blue-600 dark:text-blue-300" />
          </div>
          <span>{user?.username}</span>
        </div>

        <button
          onClick={logout}
          className="flex items-center gap-1.5 text-sm text-gray-500
                     hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </header>
  )
}