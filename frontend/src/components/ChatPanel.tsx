import { Send } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { api, type ChatMessageRead, type DocumentRead } from "../api/client";

interface ChatPanelProps {
  document: DocumentRead | null;
}

export function ChatPanel({ document }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setMessages([]);
    if (!document) return;
    api.listChat(document.id).then((items) => {
      if (!cancelled) setMessages(items);
    });
    return () => {
      cancelled = true;
    };
  }, [document]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!document || !question.trim()) return;
    const text = question.trim();
    setQuestion("");
    setBusy(true);
    try {
      const response = await api.sendChat(document.id, text);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          document_id: document.id,
          role: "user",
          content: text,
          related_chunks: [],
          created_at: new Date().toISOString()
        },
        {
          id: crypto.randomUUID(),
          document_id: document.id,
          role: "assistant",
          content: response.answer,
          related_chunks: response.related_chunks,
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            {message.content}
          </div>
        ))}
      </div>
      <form onSubmit={submit} className="chat-form">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-label="问当前文章"
          disabled={!document || document.status !== "completed"}
        />
        <button type="submit" disabled={busy || !question.trim()} title="发送">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
