import type { DocumentRead } from "../api/client";

interface DocumentListProps {
  documents: DocumentRead[];
  selectedId: string | null;
  onSelect(id: string): void;
}

export function DocumentList({ documents, selectedId, onSelect }: DocumentListProps) {
  return (
    <div className="document-list">
      {documents.map((document) => (
        <button
          key={document.id}
          className={`document-item ${selectedId === document.id ? "selected" : ""}`}
          onClick={() => onSelect(document.id)}
        >
          <span className="document-title">{document.title}</span>
          <span className={`status status-${document.status}`}>{document.status}</span>
        </button>
      ))}
    </div>
  );
}
