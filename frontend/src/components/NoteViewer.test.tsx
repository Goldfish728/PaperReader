import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, type DocumentRead } from "../api/client";
import { NoteViewer } from "./NoteViewer";

vi.mock("../api/client", async () => ({
  api: {
    getNote: vi.fn()
  }
}));

function completedDocument(overrides: Partial<DocumentRead> = {}): DocumentRead {
  return {
    id: "doc-1",
    title: "Paper",
    source_type: "uploaded_pdf",
    original_url: null,
    status: "completed",
    error_message: null,
    created_at: "2026-07-03T00:00:00",
    updated_at: "2026-07-03T00:00:00",
    ...overrides
  };
}

describe("NoteViewer", () => {
  it("does not reload the note when polling returns the same completed document", async () => {
    vi.mocked(api.getNote).mockResolvedValue({
      document_id: "doc-1",
      kind: "structured_reading",
      markdown: "# 阅读内容"
    });

    const { rerender } = render(
      <NoteViewer document={completedDocument({ updated_at: "first" })} />
    );

    expect(await screen.findByText("阅读内容")).toBeTruthy();

    rerender(<NoteViewer document={completedDocument({ updated_at: "second" })} />);
    await new Promise((resolve) => window.setTimeout(resolve, 20));

    expect(api.getNote).toHaveBeenCalledTimes(1);
    expect(screen.getByText("阅读内容")).toBeTruthy();
  });
});
