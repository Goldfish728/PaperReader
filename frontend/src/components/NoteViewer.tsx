import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, type DocumentRead } from "../api/client";

interface NoteViewerProps {
  document: DocumentRead | null;
}

export function NoteViewer({ document }: NoteViewerProps) {
  const [tab, setTab] = useState<"structured_reading" | "deep_reading">(
    "structured_reading"
  );
  const [markdown, setMarkdown] = useState("");

  useEffect(() => {
    let cancelled = false;
    setMarkdown("");
    if (!document || document.status !== "completed") return;
    api
      .getNote(document.id, tab)
      .then((note) => {
        if (!cancelled) setMarkdown(note.markdown);
      })
      .catch((error) => {
        if (!cancelled) setMarkdown(`无法读取笔记：${error.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [document, tab]);

  if (!document) {
    return <div className="empty-state">选择或导入一篇文章</div>;
  }

  if (document.status === "failed") {
    return <div className="error-state">{document.error_message}</div>;
  }

  if (document.status !== "completed") {
    return <div className="empty-state">处理中：{document.status}</div>;
  }

  return (
    <div className="note-viewer">
      <div className="tabs">
        <button
          className={tab === "structured_reading" ? "active" : ""}
          onClick={() => setTab("structured_reading")}
        >
          全文理解
        </button>
        <button
          className={tab === "deep_reading" ? "active" : ""}
          onClick={() => setTab("deep_reading")}
        >
          整篇精读
        </button>
      </div>
      <article className="markdown-body">
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </article>
    </div>
  );
}
