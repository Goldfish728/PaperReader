import { X } from "lucide-react";

interface SettingsDialogProps {
  open: boolean;
  onClose(): void;
}

export function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  if (!open) return null;
  return (
    <div className="dialog-backdrop">
      <section className="settings-dialog">
        <header>
          <h2>模型设置</h2>
          <button onClick={onClose} title="关闭">
            <X size={18} />
          </button>
        </header>
      </section>
    </div>
  );
}
