import { create } from "zustand"
import { persist } from "zustand/middleware"
import api from "@/utils/api"
import { User } from "@/types"

interface AuthStore {
  token:    string | null
  user:     User | null
  login:    (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout:   () => void
  isAuthed: () => boolean
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      token: null,
      user:  null,

      login: async (email, password) => {
        const form = new FormData()
        form.append("username", email)
        form.append("password", password)

        const res = await api.post("/auth/login", form)
        const { access_token, user_id, username, email: userEmail } = res.data

        localStorage.setItem("token", access_token)

        set({
          token: access_token,
          user: {
            id:         user_id,
            email:      userEmail,
            username:   username,
            created_at: new Date().toISOString(),
          },
        })
      },

      register: async (email, username, password) => {
        const res = await api.post("/auth/register", { email, username, password })
        const { access_token, user_id, email: userEmail } = res.data

        localStorage.setItem("token", access_token)

        set({
          token: access_token,
          user: {
            id:         user_id,
            email:      userEmail,
            username:   username,
            created_at: new Date().toISOString(),
          },
        })
      },

      logout: () => {
        localStorage.removeItem("token")
        localStorage.removeItem("user")
        set({ token: null, user: null })
        window.location.href = "/login"
      },

      isAuthed: () => !!get().token,
    }),
    {
      name:       "auth-store",
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
)