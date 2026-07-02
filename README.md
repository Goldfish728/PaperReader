# PaperReader

PaperReader is a local web app for reading English papers and technical articles in Chinese.

First-version capabilities:

- Upload text-based PDF files.
- Import PDF URLs, arXiv links, arXiv IDs, and readable web article URLs.
- Generate two Chinese notes: `全文理解` and `整篇精读`.
- Ask questions about the current document.
- Store source files, generated notes, figures, and chat history locally.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.app.main:app --reload
```

The frontend setup is added in a later task.
