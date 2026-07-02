import { X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";

interface SettingsDialogProps {
  open: boolean;
  onClose(): void;
}

export function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [chatModel, setChatModel] = useState("");
  const [timeout, setTimeoutValue] = useState(120);
  const [temperature, setTemperature] = useState(0.2);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.getSettings().then((settings) => {
      setApiBaseUrl(settings.api_base_url);
      setChatModel(settings.chat_model);
      setTimeoutValue(settings.request_timeout_seconds);
      setTemperature(settings.temperature);
      setApiKey("");
    });
  }, [open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.updateSettings({
        api_base_url: apiBaseUrl,
        api_key: apiKey,
        chat_model: chatModel,
        request_timeout_seconds: timeout,
        temperature
      });
      onClose();
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;
  return (
    <div className="dialog-backdrop">
      <form className="settings-dialog" onSubmit={submit}>
        <header>
          <h2>模型设置</h2>
          <button type="button" onClick={onClose} title="关闭">
            <X size={18} />
          </button>
        </header>
        <label>
          Base URL
          <input
            value={apiBaseUrl}
            onChange={(event) => setApiBaseUrl(event.target.value)}
          />
        </label>
        <label>
          API Key
          <input
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            type="password"
            aria-label="API Key"
          />
        </label>
        <label>
          Chat Model
          <input value={chatModel} onChange={(event) => setChatModel(event.target.value)} />
        </label>
        <label>
          Timeout Seconds
          <input
            value={timeout}
            onChange={(event) => setTimeoutValue(Number(event.target.value))}
            type="number"
            min={5}
            max={600}
          />
        </label>
        <label>
          Temperature
          <input
            value={temperature}
            onChange={(event) => setTemperature(Number(event.target.value))}
            type="number"
            min={0}
            max={2}
            step={0.1}
          />
        </label>
        <button type="submit" disabled={busy}>
          保存
        </button>
      </form>
    </div>
  );
}
