from backend.app.db.models import SourceType
from backend.app.services.source_detector import detect_text_source, normalize_arxiv_id


def test_detect_arxiv_abs_url():
    detected = detect_text_source("https://arxiv.org/abs/2401.12345")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345"


def test_detect_arxiv_pdf_url():
    detected = detect_text_source("https://arxiv.org/pdf/2401.12345")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345"


def test_detect_www_arxiv_pdf_url_with_suffix_query_and_fragment():
    detected = detect_text_source("https://www.arxiv.org/pdf/2401.12345v2.pdf?download=1#page=2")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345v2"


def test_reject_arxiv_like_url_on_different_host():
    detected = detect_text_source("https://notarxiv.org/abs/2401.12345")

    assert detected.source_type == SourceType.HTML_ARTICLE


def test_reject_arxiv_url_with_invalid_id():
    detected = detect_text_source("https://arxiv.org/abs/not-an-id")

    assert detected.source_type == SourceType.HTML_ARTICLE


def test_detect_plain_arxiv_id():
    detected = detect_text_source("2401.12345v2")

    assert detected.source_type == SourceType.ARXIV
    assert detected.normalized_value == "2401.12345v2"


def test_detect_pdf_url():
    detected = detect_text_source("https://example.com/paper.pdf")

    assert detected.source_type == SourceType.PDF_URL
    assert detected.normalized_value == "https://example.com/paper.pdf"


def test_detect_pdf_url_with_fragment():
    detected = detect_text_source("https://example.com/paper.pdf#page=2")

    assert detected.source_type == SourceType.PDF_URL
    assert detected.normalized_value == "https://example.com/paper.pdf#page=2"


def test_detect_html_article_url():
    detected = detect_text_source("https://example.com/posts/paper-reader")

    assert detected.source_type == SourceType.HTML_ARTICLE


def test_normalize_old_style_arxiv_id():
    assert normalize_arxiv_id("cs/9901001") == "cs/9901001"


def test_normalize_old_style_arxiv_id_with_subject_class():
    assert normalize_arxiv_id("physics.acc-ph/9901001") == "physics.acc-ph/9901001"
