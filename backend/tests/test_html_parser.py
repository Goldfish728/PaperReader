from pathlib import Path

from backend.app.services.html_parser import parse_html_article


def test_parse_html_article_extracts_title_and_text(tmp_path: Path):
    html_path = tmp_path / "source.html"
    html_path.write_text(
        """
        <html>
          <head><title>Readable Article</title></head>
          <body>
            <article>
              <h1>Readable Article</h1>
              <p>This article explains a method for paper reading.</p>
              <p>The method has three stages and a final evaluation.</p>
            </article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    parsed = parse_html_article(html_path)

    assert parsed.title == "Readable Article"
    assert "paper reading" in parsed.raw_text
    assert len(parsed.sections) == 1
    assert parsed.sections[0].title == "Readable Article"
