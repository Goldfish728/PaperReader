import httpx
import pytest

from backend.app.services.fetcher import download_html, download_pdf


def _transport_for(
    *,
    content: bytes,
    content_type: str,
    status_code: int = 200,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            content=content,
            headers={"content-type": content_type},
            request=request,
        )

    return httpx.MockTransport(handler)


async def test_download_pdf_accepts_pdf_magic_bytes_with_octet_stream_content_type():
    pdf_bytes = b"%PDF-1.7\nfake pdf bytes"
    transport = _transport_for(
        content=pdf_bytes,
        content_type="application/octet-stream",
    )

    path = await download_pdf("pdf-octet-stream", "https://example.test/paper", transport=transport)

    assert path.name == "original.pdf"
    assert path.read_bytes() == pdf_bytes


async def test_download_pdf_rejects_pdf_content_type_without_pdf_magic_bytes():
    transport = _transport_for(
        content=b"not actually a pdf",
        content_type="application/pdf",
    )

    with pytest.raises(ValueError, match="URL did not return a PDF file."):
        await download_pdf("bad-pdf", "https://example.test/paper.pdf", transport=transport)


async def test_download_pdf_propagates_http_status_errors():
    transport = _transport_for(
        content=b"missing",
        content_type="text/plain",
        status_code=404,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await download_pdf("missing-pdf", "https://example.test/missing.pdf", transport=transport)


async def test_download_html_writes_normal_html_response():
    html = b"<html><body><h1>Paper</h1></body></html>"
    transport = _transport_for(
        content=html,
        content_type="text/html; charset=utf-8",
    )

    path = await download_html("html-page", "https://example.test/paper", transport=transport)

    assert path.name == "source.html"
    assert path.read_text(encoding="utf-8") == html.decode("utf-8")


async def test_download_html_rejects_pdf_response():
    transport = _transport_for(
        content=b"%PDF-1.7\nfake pdf bytes",
        content_type="application/pdf",
    )

    with pytest.raises(ValueError, match="URL did not return an HTML document."):
        await download_html("pdf-not-html", "https://example.test/paper", transport=transport)
