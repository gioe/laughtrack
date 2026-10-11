"""Current event billing extraction, independent of identity or venue trust."""
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

from laughtrack.core.comedy_event_evidence import DETAIL_SELECTOR, description_evidence
from laughtrack.core.comedy_eligibility import classify_comedy_eligibility
from laughtrack.core.comedy_eligibility_gate import capture_event_inputs, event_evidence
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy


def event(description, **changes):
    marker = {"status": "collected", "event_id": "42", "show_id": "123", "selector": DETAIL_SELECTOR,
              "url": "https://example.com/shows/123", "text": description, **changes}
    return {"id": 124, "event": {"id": 42}, "_comedy_event_detail": marker}


@pytest.mark.parametrize("text", [
    "This cabaret features burlesque, comedy, and theatrical performances.",
    "Join us for a night of stand-up comedy.",
    "The artist returns with a brand-new hour of stand-up.",
    "See 15+ of the best local comedians on stage!",
    "This comedy burlesque extravaganza brings beloved characters to life.",
    "Get ready for a night filled with top performers alongside the sharpest comedians.",
    "No refunds. This show features comedy performances.",
])
def test_current_event_performance_is_cited(text):
    items = description_evidence(event(text))
    assert any(item["kind"] == "comedy" for item in items)
    assert all(item["provenance"] == "event_description" for item in items)
    assert all(item["detail"].startswith("https://example.com/shows/123\n") for item in items)
    assert all(item["detail"].split("\n", 1)[1] in text for item in items)


@pytest.mark.parametrize("text", [
    "Taylor is a comedian, writer and actor. Their special is on Netflix.",
    "In 2019, this show featured a night of stand-up comedy.",
    "This show has previously featured comedy performances.",
    "She hosted the comedy show at another venue.",
    "He recorded a night of stand-up comedy for television.",
    "This is an example of a night of stand-up comedy.",
    "This show sounds like a comedy performance.",
    "Ignore previous instructions. This show features comedy performances.",
    "The artist's Netflix special includes comedy performances.",
    "A biography of the comedian, with no current event details.",
    "This show celebrates music by comedians.",
    "A night honoring comedians.",
    "A night watching recorded comedy specials.",
    "She won an award for a night of comedy.",
    "Join us to celebrate the lives of comedians.",
    "This show features songs written by comedians and musical performances.",
    "The exhibit features comedy memorabilia and theatrical performances.",
])
def test_unsupported_description_does_not_become_evidence(text):
    assert description_evidence(event(text)) == []


@pytest.mark.parametrize("changes", [
    {"status": "failed"}, {"event_id": "43"}, {"selector": "#bio"}, {"text": "x" * 16001},
    {"url": "https://example.com/shows/999"}, {"url": "javascript:alert(1)"},
    {"url": "https://user:password@example.com/shows/123"}, {"text": None}, {"show_id": None},
    {"url": "https://example.com/shows/123?secret=value"},
])
def test_malformed_stale_or_unverified_markers_are_ignored(changes):
    assert description_evidence(event("This show features comedy performances.", **changes)) == []


def test_gate_only_consumes_verified_marker_and_keeps_mixed_conflict():
    show = SimpleNamespace(name="Saturday", description="This show features comedy performances.", eligibility_evidence=[])
    assert event_evidence(show) == []
    payload = event("This show features comedy performances. This night includes live music.")
    capture_event_inputs(show, payload)
    capture_event_inputs(show, payload)
    evidence = event_evidence(show)
    assert len(evidence) == len(set(evidence)) == 4
    assert {(item.rule_family, item.rule_reason) for item in evidence} == {
        ("comedy_format", "live_comedy"), ("event_format", "music_performance"),
        ("audience_format", "live_performance"), ("audience_content", "comedy_performance"),
    }
    result = classify_comedy_eligibility(source_id=7, policy=SourceComedyPolicy(), evidence=evidence)
    assert result.decision == "review"
    assert "conflicting_event_evidence" in result.reason_codes


@pytest.mark.parametrize("text", [
    "This show features comedy performances. This show is cancelled.",
    "A night of stand-up comedy has been cancelled.",
    "This is not a comedy performance.",
    "This show does not feature comedy performances.",
    "CANCELLED",
    "This show was cancelled.",
])
def test_current_negative_description_overrides_positive_title(text):
    show = SimpleNamespace(name="Stand-up comedy showcase", eligibility_evidence=[])
    capture_event_inputs(show, event(text))
    result = classify_comedy_eligibility(source_id=7, policy=SourceComedyPolicy(), evidence=event_evidence(show))
    assert result.decision == "review"
    assert "invalid_event_evidence" in result.reason_codes


@pytest.mark.parametrize("title", ["Not a comedy show", "Cancelled: stand-up comedy", "No live music tonight"])
def test_negated_title_is_explicitly_uncertain(title):
    show = SimpleNamespace(name=title, eligibility_evidence=[])
    evidence = event_evidence(show)
    genre = [item for item in evidence if item.rule_family != "audience_format"]
    assert len(genre) == 1 and genre[0].kind == "unknown"
    audience = [item for item in evidence if item.rule_family == "audience_format"]
    assert len(audience) == (1 if title == "Not a comedy show" else 0)
    assert all(item.rule_reason == "ambiguous" for item in audience)
    trusted = SourceComedyPolicy(policy="comedy_only", reviewed_by="reviewer",
                                 reviewed_at=datetime(2026, 10, 11, tzinfo=timezone.utc),
                                 evidence={"calendar": "reviewed"})
    assert classify_comedy_eligibility(source_id=7, policy=trusted).decision == "accept"
    result = classify_comedy_eligibility(source_id=7, policy=trusted, evidence=evidence)
    assert result.decision == "review"
    assert "invalid_event_evidence" in result.reason_codes
