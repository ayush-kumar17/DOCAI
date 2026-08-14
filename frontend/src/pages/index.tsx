import { useEffect } from "react"
import { useRouter } from "next/router"
import { useAuthStore } from "@/store/authStore"

export default function Home() {
  const router   = useRouter()
  const isAuthed = useAuthStore((s) => s.isAuthed)

  useEffect(() => {
    router.replace(isAuthed() ? "/dashboard" : "/login")
  }, [])

  return null
}