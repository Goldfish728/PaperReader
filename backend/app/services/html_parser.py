from pathlib import Path

import trafilatura
from bs4 import BeautifulSoup

from backend.app.services.pdf_parser import ParsedDocument, ParsedSection


def parse_html_article(path: Path) -> ParsedDocument:
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup, path)
    extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
    if not extracted:
        article = soup.find("article") or soup.body
        extracted = article.get_text("\n", strip=True) if article else ""
    raw_text = extracted.strip()
    if not raw_text:
        raise ValueError("Web page has no readable article text.")
    section = ParsedSection(
        number="S1",
        title=title,
        level=1,
        order=0,
        page_start=None,
        page_end=None,
        text=raw_text,
    )
    return ParsedDocument(title=title, raw_text=raw_text, sections=[section])


def extract_title(soup: BeautifulSoup, path: Path) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return path.stem
