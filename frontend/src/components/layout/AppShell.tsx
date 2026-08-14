"use client"

import { useEffect } from "react"
import { useRouter } from "next/router"
import { useAuthStore } from "@/store/authStore"
import Sidebar from "./Sidebar"
import Topbar  from "./Topbar"

interface AppShellProps {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const router  = useRouter()
  const isAuthed = useAuthStore((s) => s.isAuthed)

  useEffect(() => {
    if (!isAuthed()) {
      router.replace("/login")
    }
  }, [])

  if (!isAuthed()) return null

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}