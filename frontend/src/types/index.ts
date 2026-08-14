export interface User {
  id:         string
  email:      string
  username:   string
  created_at: string
}

export interface Document {
  id:           string
  filename:     string
  type:         string
  size_bytes:   number
  size_mb:      number
  status:       "pending" | "processing" | "ready" | "failed"
  page_count:   number
  chunk_count:  number
  tags:         string[]
  uploaded_at:  string
  processed_at: string | null
  error_message?: string
}

export interface Citation {
  doc_id:       string
  page:         number | null
  section:      string
  confidence:   number
  text_snippet: string
  rerank_score: number
}

export interface Message {
  id:          string
  role:        "user" | "assistant"
  content:     string
  citations:   Citation[]
  latency_ms:  number | null
  created_at:  string
  // frontend-only
  streaming?:  boolean
  tempId?:     string
}

export interface ChatSession {
  id:         string
  title:      string
  doc_ids:    string[]
  created_at: string
}

export interface AnalyticsData {
  documents: {
    total:         number
    ready:         number
    processing:    number
    total_size_mb: number
    total_chunks:  number
    by_type:       { type: string; count: number }[]
  }
  chat: {
    total_messages: number
    avg_latency_ms: number
  }
  recent_uploads: {
    filename:    string
    type:        string
    status:      string
    uploaded_at: string
  }[]
}

export interface SSEEvent {
  type: "intent" | "chunks" | "token" | "citations" | "done" | "error" | "refining"
  data: any
}