export type DocumentStatus =
  | "queued"
  | "fetching"
  | "parsing"
  | "extracting_figures"
  | "generating_structured_reading"
  | "generating_deep_reading"
  | "indexing"
  | "completed"
  | "failed";

export type SourceType = "uploaded_pdf" | "pdf_url" | "arxiv" | "html_article";

export interface DocumentRead {
  id: string;
  title: string;
  source_type: SourceType;
  original_url: string | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface NoteRead {
  document_id: string;
  kind: "structured_reading" | "deep_reading";
  markdown: string;
}

export interface RelatedChunkRead {
  chunk_id: string;
  section_label: string | null;
  page_start: number | null;
  page_end: number | null;
  text: string;
}

export interface ChatMessageRead {
  id: string;
  document_id: string;
  role: "user" | "assistant";
  content: string;
  related_chunks: RelatedChunkRead[];
  created_at: string;
}

export interface ChatResponse {
  answer: string;
  related_chunks: RelatedChunkRead[];
}

export interface SettingsRead {
  api_base_url: string;
  chat_model: string;
  request_timeout_seconds: number;
  temperature: number;
  api_key_configured: boolean;
}

export interface SettingsUpdate {
  api_base_url: string;
  api_key: string;
  chat_model: string;
  request_timeout_seconds: number;
  temperature: number;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestNoContent(url: string, options?: RequestInit): Promise<void> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
}

export const api = {
  listDocuments: () => request<DocumentRead[]>("/api/documents"),
  getDocument: (id: string) => request<DocumentRead>(`/api/documents/${id}`),
  importUrl: (value: string) =>
    request<DocumentRead>("/api/documents/import-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value })
    }),
  uploadPdf: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentRead>("/api/documents/upload", {
      method: "POST",
      body: form
    });
  },
  deleteDocument: (id: string) =>
    requestNoContent(`/api/documents/${id}`, { method: "DELETE" }),
  getNote: (id: string, kind: "structured_reading" | "deep_reading") =>
    request<NoteRead>(`/api/documents/${id}/notes/${kind}`),
  listChat: (id: string) => request<ChatMessageRead[]>(`/api/documents/${id}/chat`),
  sendChat: (id: string, question: string) =>
    request<ChatResponse>(`/api/documents/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    }),
  getSettings: () => request<SettingsRead>("/api/settings"),
  updateSettings: (payload: SettingsUpdate) =>
    request<SettingsRead>("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
};
