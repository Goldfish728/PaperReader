import { Trash2 } from "lucide-react";
import type { DocumentRead } from "../api/client";

interface DocumentListProps {
  documents: DocumentRead[];
  selectedId: string | null;
  onSelect(id: string): void;
  onDelete(id: string): void;
}

export function DocumentList({
  documents,
  selectedId,
  onSelect,
  onDelete
}: DocumentListProps) {
  return (
    <div className="document-list">
      {documents.map((document) => (
        <div
          key={document.id}
          className={`document-item ${selectedId === document.id ? "selected" : ""}`}
        >
          <button className="document-select" onClick={() => onSelect(document.id)}>
            <span className="document-title">{document.title}</span>
            <span className={`status status-${document.status}`}>{document.status}</span>
          </button>
          <button
            className="document-delete"
            onClick={() => onDelete(document.id)}
            title="删除"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
