"""Tests for the comedian bio extractor used by update_comedian_bios."""

from laughtrack.utilities.domain.comedian.bio_enrichment import extract_bio


def test_extracts_bio_when_description_mentions_comedian():
    payload = {
        "type": "standard",
        "title": "Dave Chappelle",
        "description": "American stand-up comedian (born 1973)",
        "extract": (
            "David Khari Webber Chappelle is an American actor and stand-up "
            "comedian. His style is widely influential."
        ),
    }
    bio = extract_bio(payload)
    assert bio is not None
    assert "David Khari Webber Chappelle" in bio
    assert "stand-up" in bio


def test_extracts_bio_when_only_extract_mentions_comedy():
    payload = {
        "type": "standard",
        "title": "Some Person",
        "description": "American performer",
        "extract": "Some Person is a sketch and improv performer from Chicago.",
    }
    assert extract_bio(payload) is not None


def test_rejects_disambiguation_page():
    payload = {
        "type": "disambiguation",
        "title": "John Smith",
        "description": "Topics referred to by the same term",
        "extract": "John Smith may refer to: John Smith, a stand-up comedian ...",
    }
    assert extract_bio(payload) is None


def test_rejects_page_without_comedy_keyword():
    payload = {
        "type": "standard",
        "title": "Michael Jordan",
        "description": "American basketball player",
        "extract": "Michael Jeffrey Jordan is an American businessman and former basketball player.",
    }
    assert extract_bio(payload) is None


def test_rejects_empty_or_missing_extract():
    assert extract_bio({"type": "standard", "extract": ""}) is None
    assert extract_bio({"type": "standard"}) is None


def test_rejects_non_dict_input():
    assert extract_bio(None) is None
    assert extract_bio("not a dict") is None  # type: ignore[arg-type]
    assert extract_bio([]) is None  # type: ignore[arg-type]


def test_truncates_to_sentence_boundary_under_max_length():
    # Build an extract > 600 chars with clear sentence boundaries.
    long_extract = " ".join(
        f"Alice is a stand-up comedian with career highlight number {i}."
        for i in range(1, 40)
    )
    assert len(long_extract) > 600
    payload = {
        "type": "standard",
        "description": "American stand-up comedian",
        "extract": long_extract,
    }
    bio = extract_bio(payload)
    assert bio is not None
    assert len(bio) <= 600
    # Truncation should end on a sentence boundary (period + no trailing chars).
    assert bio.endswith(".")


def test_collapses_whitespace_in_extract():
    payload = {
        "type": "standard",
        "description": "American comedian",
        "extract": "Alice   is   a\n\ncomedian.\tShe tours.",
    }
    bio = extract_bio(payload)
    assert bio == "Alice is a comedian. She tours."


def test_accepts_case_insensitive_comedy_keyword():
    payload = {
        "type": "standard",
        "description": "British Comedian",
        "extract": "Bob is a COMEDIAN known for sharp delivery.",
    }
    assert extract_bio(payload) is not None


def test_hard_truncates_single_long_sentence_with_ellipsis():
    # Single sentence longer than 600 chars — no sentence boundary to cut at.
    long_single = "Alice is a comedian and " + ("very " * 200) + "funny"
    assert len(long_single) > 600
    payload = {
        "type": "standard",
        "description": "American comedian",
        "extract": long_single,
    }
    bio = extract_bio(payload)
    assert bio is not None
    assert len(bio) <= 600
    assert bio.endswith("\u2026")


def test_short_extract_returned_verbatim():
    payload = {
        "type": "standard",
        "description": "American comedian",
        "extract": "Alice is a stand-up comedian.",
    }
    assert extract_bio(payload) == "Alice is a stand-up comedian."
