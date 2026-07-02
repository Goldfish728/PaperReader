# PaperReader

PaperReader is a local web app for reading English papers and technical articles in Chinese.

First-version capabilities:

- Upload text-based PDF files.
- Import PDF URLs, arXiv links, arXiv IDs, and readable web article URLs.
- Generate two Chinese notes: `全文理解` and `整篇精读`.
- Ask questions about the current document.
- Store source files, generated notes, figures, and chat history locally.

## Local Development

### Install Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### Run Backend

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Model Configuration

The backend reads `.env` defaults:

```bash
PAPER_READER_API_BASE_URL=https://api.openai.com/v1
PAPER_READER_API_KEY=...
PAPER_READER_CHAT_MODEL=gpt-4.1-mini
```

The settings dialog can override these values locally.

## Supported Inputs

- Text-based PDF upload.
- PDF URL.
- arXiv link or ID.
- Readable web article URL.

Scanned PDFs without extractable text are not supported in the first version.
