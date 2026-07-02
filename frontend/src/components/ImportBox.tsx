import { Link, Upload } from "lucide-react";
import { FormEvent, useState } from "react";

interface ImportBoxProps {
  onImportUrl(value: string): Promise<void>;
  onUpload(file: File): Promise<void>;
}

export function ImportBox({ onImportUrl, onUpload }: ImportBoxProps) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitUrl(event: FormEvent) {
    event.preventDefault();
    if (!value.trim()) return;
    setBusy(true);
    try {
      await onImportUrl(value.trim());
      setValue("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="import-box">
      <form onSubmit={submitUrl} className="import-row">
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          aria-label="arXiv、PDF 或网页链接"
        />
        <button type="submit" disabled={busy} title="导入链接">
          <Link size={18} />
        </button>
      </form>
      <label className="upload-button" title="上传 PDF">
        <Upload size={18} />
        <span>上传 PDF</span>
        <input
          type="file"
          accept="application/pdf"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void onUpload(file);
          }}
        />
      </label>
    </div>
  );
}
