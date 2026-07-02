from backend.app.services.pdf_parser import build_sections_from_pages, detect_heading_level


def test_detect_numbered_heading_level():
    assert detect_heading_level("1 Introduction") == 1
    assert detect_heading_level("2.3 Training Objective") == 2
    assert detect_heading_level("A.1 Extra Results") == 2


def test_ignore_sentence_as_heading():
    assert detect_heading_level("This is a normal sentence with several words.") is None


def test_build_sections_uses_first_heading_when_page_starts_with_heading():
    sections = build_sections_from_pages(
        [
            (
                1,
                "1 Introduction\nThis paper introduces the problem.\n"
                "2 Method\nThe method has two stages.",
            )
        ]
    )

    assert [section.title for section in sections] == ["1 Introduction", "2 Method"]
    assert sections[0].number == "1"
    assert sections[0].page_start == 1
    assert "introduces the problem" in sections[0].text


def test_build_sections_ignores_blank_lines_before_first_heading():
    sections = build_sections_from_pages(
        [(1, "\n\n1 Introduction\nThis paper introduces the problem.")]
    )

    assert [section.title for section in sections] == ["1 Introduction"]
