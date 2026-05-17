from __future__ import annotations

from scripts.core import podcast_auto_acceptance_spot_check_report as mod


def test_build_report_samples_auto_accepted_rows_and_counts_drift():
    rows = [
        mod.AutoAcceptedReviewRow(
            candidate_id=i,
            comedian_name=f"Comedian {i}",
            podcast_title="Comedy Talk",
            episode_title=f"Episode {i}",
            confidence=0.97,
            rule_id="high_confidence_title_name",
            drift_flag=i in {3, 5},
        )
        for i in range(1, 101)
    ]

    report = mod.build_report(rows, sample_rate=0.02)

    assert report.total_auto_accepted == 100
    assert report.rule_counts == {"high_confidence_title_name": 100}
    assert report.drift_flags == 2
    assert len(report.sample_rows) == 2
    assert [row.candidate_id for row in report.sample_rows] == [
        row.candidate_id for row in mod.build_report(rows, sample_rate=0.02).sample_rows
    ]
