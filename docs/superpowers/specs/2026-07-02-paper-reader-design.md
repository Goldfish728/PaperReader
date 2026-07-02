# PaperReader Design

Date: 2026-07-02

## Goal

PaperReader is a local web workspace for reading English papers and technical articles in Chinese. The user can upload a PDF, paste a PDF URL, paste an arXiv link or ID, or paste a normal article URL. The app fetches and parses the source, generates two complementary Chinese reading artifacts, extracts useful original figures, and supports natural question answering about the current document.

The first version is optimized for one-document-at-a-time reading. It should help the user understand a paper deeply, ask follow-up questions, and keep all generated material locally. It is not a multi-paper literature management system, cloud sync service, or full PDF reader.

## Product Scope

The first version supports:

- Uploaded text-based English PDF files.
- Direct PDF URLs.
- arXiv `abs` URLs, `pdf` URLs, and plain arXiv IDs.
- Normal web article URLs with extractable text.
- Local persistence for source files, parsed text, images, generated notes, processing state, model configuration snapshots, and chat history.
- A three-column reading workspace with document history, notes, and chat.
- A configurable OpenAI-compatible chat API through `.env` defaults and in-app overrides.
- Current-document question answering using local full-text retrieval over parsed chunks.

The first version does not support:

- Scanned PDF OCR.
- Embedded side-by-side PDF reading.
- Manual editing of parsed sections, figures, or notes.
- Multi-document or cross-paper question answering.
- Account systems, cloud sync, sharing, or collaboration.
- Export to Markdown, HTML, or PDF from the UI.
- Batch import.
- Persistent vector databases.

## User Flow

1. The user opens the local web app.
2. The user uploads a PDF or submits a URL/arXiv ID.
3. The backend creates a document record and starts a background processing job.
4. The frontend shows progress states:
   - `queued`
   - `fetching`
   - `parsing`
   - `extracting_figures`
   - `generating_structured_reading`
   - `generating_deep_reading`
   - `indexing`
   - `completed`
   - `failed`
5. After completion, the middle reading area shows two tabs:
   - `全文理解`
   - `整篇精读`
6. The user can ask questions in the right-side chat. The app retrieves relevant chunks from the current document and asks the configured model to answer naturally in Chinese.
7. The user can delete a document or regenerate its notes. Manual editing is out of scope for the first version.

## Reading Outputs

### 1. Structured Full-Text Understanding

This artifact is a structure-preserving Chinese reading map of the original document. It is close to a condensed translation, but it must not reproduce the full text sentence by sentence.

Requirements:

- Preserve the original heading hierarchy exactly when headings can be detected.
- Preserve original section numbers such as `1 Introduction`, `2.3 Method`, and appendix labels.
- If the original has no reliable section numbers, assign stable internal labels such as `S1`, `S1.1`, and `S2`.
- Preserve meaningful list hierarchy, method steps, experimental setup hierarchy, and argument structure.
- Explain each section in Chinese while keeping important English terms in parentheses or inline where useful.
- Preserve references to figures, tables, formulas, algorithms, and appendices.
- Make every major section addressable in chat. The user should be able to ask questions such as "解释一下第 3.2 节" or "第 S4.1 的实验设置是什么意思".

Suggested filename:

```text
structured_reading_note.md
```

### 2. Deep Reading Note

This artifact is a higher-level expert reading guide. It should help the user understand what the paper is doing and why it matters.

Typical sections:

- 这篇文章解决什么问题
- 核心贡献
- 方法细读
- 实验与证据
- 关键图表解读
- 局限与可追问点
- 读完应掌握的要点

The exact structure can adapt to the source type. A web article without experiments should use sections such as core claim, argument chain, evidence, concepts, and doubtful points.

Suggested filename:

```text
deep_reading_note.md
```

## Source Ingestion

The app treats all inputs as document sources and normalizes them into a common internal document model.

### Source Detector

The detector classifies input as one of:

- `uploaded_pdf`
- `pdf_url`
- `arxiv`
- `html_article`

Detection rules:

- Uploaded files are accepted only as PDFs in the first version.
- arXiv detection handles `arxiv.org/abs/...`, `arxiv.org/pdf/...`, and plain arXiv IDs.
- URL inputs are probed through response headers and file signatures. If the content is PDF, the app treats it as `pdf_url`; otherwise it attempts web article extraction.

### Fetcher

The fetcher obtains and stores original sources:

- Uploaded PDFs are copied into the local document directory.
- PDF URLs are downloaded and saved as `original.pdf`.
- arXiv sources download the PDF and fetch metadata such as title, authors, abstract, categories, and publication date.
- Web articles are saved as an HTML snapshot where possible.

### Parser

The parser converts each source into a normalized document structure.

For PDFs:

- Extract title and author candidates.
- Extract page-level text.
- Detect section headings and hierarchy where possible.
- Extract figure/table images and nearby captions.
- Associate captions and figures with page numbers and nearby sections.

For arXiv:

- Use arXiv metadata for title, authors, abstract, and source URL.
- Parse body text and figures from the downloaded PDF.

For web articles:

- Extract title, author, publication date, main text, and inline images using readability-style extraction.
- Treat web images as figure candidates.
- Skip PDF-only concepts such as page numbers.

## Normalized Document Model

The app should normalize sources into a structure with these fields:

```ts
Document {
  id: string
  title: string
  authors?: string[]
  sourceType: "uploaded_pdf" | "pdf_url" | "arxiv" | "html_article"
  originalUrl?: string
  abstract?: string
  sections: Section[]
  figures: Figure[]
  references?: Reference[]
  rawText: string
}

Section {
  id: string
  documentId: string
  number?: string
  title: string
  level: number
  parentId?: string
  order: number
  pageStart?: number
  pageEnd?: number
  text: string
}

Figure {
  id: string
  documentId: string
  sectionId?: string
  label?: string
  caption?: string
  page?: number
  imagePath: string
  order: number
}
```

## Local Storage

SQLite stores structured data:

- `documents`: title, authors, source type, original URL, status, timestamps, and error information.
- `document_assets`: original PDF, HTML snapshot, extracted images, and note files.
- `sections`: parsed heading hierarchy.
- `chunks`: text chunks for full-text retrieval and chat grounding.
- `figures`: extracted figures or web images.
- `notes`: generated note records for `structured_reading` and `deep_reading`.
- `chat_messages`: per-document chat history.
- `settings`: in-app model configuration overrides.

The filesystem stores large source and generated files:

```text
data/
  app.db
  documents/
    <document_id>/
      original.pdf
      source.html
      figures/
        figure-001.png
        figure-002.png
      structured_reading_note.md
      deep_reading_note.md
```

The app should keep all source material, notes, images, and chats on the local machine. Only the necessary source excerpts and prompt context are sent to the configured cloud model API.

## Retrieval and Chat

The first version uses SQLite FTS5/BM25 for current-document retrieval. It does not build or persist a vector database.

Rationale:

- The primary use case is reading one article deeply, often only once.
- Persistent embeddings add model cost, storage, compatibility work, and processing time.
- SQLite FTS5 is local, simple, fast enough, and fits the single-document question-answering workflow.

Chat retrieval flow:

1. Receive the user question.
2. If the question is in Chinese, generate or derive English search keywords suitable for English paper text.
3. Search the current document's chunks with SQLite FTS5.
4. Rank chunks using BM25 and lightweight metadata boosts such as section title, caption match, and exact section number references.
5. Send the selected chunks plus document metadata to the chat model.
6. Return a natural Chinese answer.
7. Optionally show a collapsed "相关内容" area with source snippets, section labels, and page numbers when available.

The retrieval layer should have a small interface boundary so optional embedding retrieval can be added later without rewriting the chat engine.

## Note Generation Strategy

The backend generates the two reading artifacts as separate outputs.

### Structured Full-Text Understanding Generation

The generator uses the parsed section tree as the primary skeleton. It should preserve heading hierarchy and generate section-by-section Chinese explanations. Long sections may be internally summarized in subchunks, then merged back under the same original heading.

If heading detection fails, the system falls back in order:

1. Page-based sections.
2. Paragraph/chunk-based synthetic sections with stable labels.

### Deep Reading Note Generation

The generator uses:

- Document metadata.
- Parsed abstract and sections.
- Intermediate section summaries.
- Captions and selected figures.
- The structured full-text understanding where useful.

The output should be a coherent Chinese Markdown guide, not a list of disconnected summaries.

### Figure Placement

The app should not insert every extracted image. It should prioritize figures and tables that are important to understanding the method, experiments, results, or argument structure.

Placement rules:

- Prefer captions that explicitly mention figure/table labels.
- Associate figures with nearby sections and references such as "Figure 2 shows...".
- Insert selected figures near the related explanation in the note.
- Add concise Chinese explanation next to each inserted figure.

## Backend Architecture

The backend is a FastAPI service with these modules:

- `source_detector`: classifies submitted sources.
- `fetcher`: saves uploads and downloads remote content.
- `parser`: parses PDF and HTML sources into normalized structures.
- `figure_extractor`: extracts and stores useful images and captions.
- `chunker`: creates section-aware chunks for retrieval.
- `fts_indexer`: maintains SQLite FTS5 indexes for chunks.
- `note_generator`: generates structured and deep reading notes.
- `chat_engine`: retrieves context and calls the chat model.
- `job_manager`: runs processing tasks and records status.
- `settings_service`: resolves `.env` defaults and in-app overrides.
- `model_client`: wraps OpenAI-compatible chat requests.

The first version can use an in-process background task manager. A separate worker queue is not required unless processing reliability becomes a problem.

## Frontend Architecture

The frontend is a React/Vite app with a three-column workspace.

### Left Column

- Import form for PDF upload and URL/arXiv input.
- Document list with title, source type, status, and creation time.
- Actions for selecting, deleting, and regenerating a document.

### Middle Column

- Reading area with two tabs:
  - `全文理解`
  - `整篇精读`
- Markdown rendering with images.
- Failed-state display with failed step and readable error.
- Button to open the original file or HTML snapshot.

### Right Column

- Chat scoped to the selected document.
- Natural Chinese answers.
- Preserved chat history.
- Collapsible related-source snippets.

### Settings

- `base_url`
- `api_key`
- chat model
- optional request timeout and temperature

The backend reads `.env` defaults. In-app settings override those defaults and are stored locally.

## Error Handling

Each document records its processing status and a human-readable error when failed.

Expected failure cases:

- URL download fails.
- URL is neither a PDF nor a readable web article.
- PDF contains no extractable text.
- Section detection is weak or fails.
- Figure extraction fails.
- Model API request fails.
- Generated note is empty or structurally invalid.

Section detection failure should degrade rather than abort when text is still available. PDF text extraction failure should stop with a clear message suggesting that scanned PDFs are not supported in the first version.

## Testing Strategy

The first implementation should verify four main paths:

1. Upload a text-based PDF and generate both reading artifacts.
2. Submit an arXiv link and generate both reading artifacts with metadata.
3. Submit a normal web article URL and generate both reading artifacts.
4. Ask a question about the current document and receive an answer grounded in FTS-retrieved chunks.

Additional tests should cover:

- Source type detection.
- PDF URL detection through headers and file signatures.
- arXiv ID normalization.
- FTS search over chunks.
- Settings resolution between `.env` and in-app overrides.
- Failure states and retry/regeneration behavior.

## GitHub Repository

The project should use this remote repository:

```text
git@github.com:Goldfish728/PaperReader.git
```

Local development should keep commits intentional and push project progress to this repository after user approval.

## Open Questions Deferred From V1

- Whether to add OCR for scanned PDFs.
- Whether to add optional embedding retrieval for repeated or cross-document use.
- Whether to add Markdown, HTML, or PDF export.
- Whether to add an embedded PDF reader for side-by-side comparison.
- Whether to add manual correction of parsed sections and figures.
