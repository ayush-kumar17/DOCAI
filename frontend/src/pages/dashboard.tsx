import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { FileText, MessageSquare, HardDrive, Zap, Upload } from "lucide-react"
import Link from "next/link"
import AppShell from "@/components/layout/AppShell"
import api from "@/utils/api"
import { AnalyticsData } from "@/types"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

export default function DashboardPage() {
  const { data, isLoading } = useQuery<AnalyticsData>({
    queryKey: ["analytics"],
    queryFn:  () => api.get("/analytics").then((r) => r.data),
    refetchInterval: 30000,
  })

  const stats = [
    {
      label: "Total Documents",
      value: data?.documents.total ?? "—",
      icon:  FileText,
      color: "text-blue-600 bg-blue-50 dark:bg-blue-950/30",
    },
    {
      label: "Total Messages",
      value: data?.chat.total_messages ?? "—",
      icon:  MessageSquare,
      color: "text-purple-600 bg-purple-50 dark:bg-purple-950/30",
    },
    {
      label: "Storage Used",
      value: data ? `${data.documents.total_size_mb} MB` : "—",
      icon:  HardDrive,
      color: "text-green-600 bg-green-50 dark:bg-green-950/30",
    },
    {
      label: "Avg Response",
      value: data ? `${(data.chat.avg_latency_ms / 1000).toFixed(1)}s` : "—",
      icon:  Zap,
      color: "text-amber-600 bg-amber-50 dark:bg-amber-950/30",
    },
  ]

  return (
    <AppShell>
      <div className="p-6 space-y-6 max-w-6xl mx-auto">

        {/* Stats grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label}
                 className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200
                            dark:border-gray-800 p-5">
              <div className={`inline-flex p-2 rounded-lg ${s.color} mb-3`}>
                <s.icon className="h-5 w-5" />
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Document types chart */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200
                          dark:border-gray-800 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Documents by type
            </h3>
            {data?.documents.by_type.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.documents.by_type}>
                  <XAxis dataKey="type" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
                No documents yet
              </div>
            )}
          </div>

          {/* Recent uploads */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200
                          dark:border-gray-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Recent uploads
              </h3>
              <Link href="/documents"
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                View all
              </Link>
            </div>

            {data?.recent_uploads.length ? (
              <div className="space-y-3">
                {data.recent_uploads.map((doc, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 dark:text-white truncate">
                        {doc.filename}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                      ${doc.status === "ready"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                      }`}>
                      {doc.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-48 flex flex-col items-center justify-center gap-3">
                <Upload className="h-8 w-8 text-gray-300" />
                <p className="text-sm text-gray-400">No documents yet</p>
                <Link href="/documents"
                      className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                  Upload your first document
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}