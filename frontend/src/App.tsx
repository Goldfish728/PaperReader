import { Settings } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, type DocumentRead } from "./api/client";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentList } from "./components/DocumentList";
import { ImportBox } from "./components/ImportBox";
import { NoteViewer } from "./components/NoteViewer";
import { SettingsDialog } from "./components/SettingsDialog";

export function App() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  async function refreshDocuments() {
    const list = await api.listDocuments();
    setDocuments(list);
    setSelectedId((current) => current ?? list[0]?.id ?? null);
  }

  useEffect(() => {
    void refreshDocuments();
    const timer = window.setInterval(() => void refreshDocuments(), 3000);
    return () => window.clearInterval(timer);
  }, []);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? null,
    [documents, selectedId]
  );

  return (
    <main className="app-shell">
      <section className="sidebar">
        <header className="sidebar-header">
          <h1>PaperReader</h1>
          <button onClick={() => setSettingsOpen(true)} title="模型设置">
            <Settings size={18} />
          </button>
        </header>
        <ImportBox
          onImportUrl={async (value) => {
            const document = await api.importUrl(value);
            await refreshDocuments();
            setSelectedId(document.id);
          }}
          onUpload={async (file) => {
            const document = await api.uploadPdf(file);
            await refreshDocuments();
            setSelectedId(document.id);
          }}
        />
        <DocumentList
          documents={documents}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
      </section>
      <section className="reader">
        <NoteViewer document={selectedDocument} />
      </section>
      <section className="chat">
        <ChatPanel document={selectedDocument} />
      </section>
      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </main>
  );
}
