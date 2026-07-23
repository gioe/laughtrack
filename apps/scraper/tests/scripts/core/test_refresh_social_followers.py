from unittest.mock import MagicMock, patch

import pytest

from scripts.core import refresh_social_followers


def test_valid_csv_refreshes_stable_deduplicated_ids(tmp_path):
    csv_path = tmp_path / "comedian_ids.csv"
    csv_path.write_text("id,note\n7,first\n7,duplicate\n9,second\n", encoding="utf-8")
    service = MagicMock()
    service.refresh_instagram_followers.return_value = 2

    with patch.object(refresh_social_followers, "ComedianService", return_value=service):
        refresh_social_followers.main(["--platform", "instagram", "--ids-csv", str(csv_path)])

    service.refresh_instagram_followers.assert_called_once_with(limit=None, stale_days=None, comedian_ids=[7, 9])


@pytest.mark.parametrize(
    "contents, message",
    [
        ("name\ncomic\n", "must include an id header"),
        ("id\n", "does not contain any comedian IDs"),
        ("id\nabc\n", "invalid comedian id"),
        ("id\n0\n", "invalid comedian id"),
        ("id\n-1\n", "invalid comedian id"),
    ],
)
def test_invalid_csv_exits_before_constructing_service(tmp_path, contents, message, capsys):
    csv_path = tmp_path / "comedian_ids.csv"
    csv_path.write_text(contents, encoding="utf-8")

    with (
        patch.object(refresh_social_followers, "ComedianService") as service_class,
        pytest.raises(SystemExit) as exc_info,
    ):
        refresh_social_followers.main(["--platform", "instagram", "--ids-csv", str(csv_path)])

    assert exc_info.value.code == 2
    assert message in capsys.readouterr().err
    service_class.assert_not_called()


def test_missing_csv_exits_before_constructing_service(tmp_path):
    csv_path = tmp_path / "missing.csv"

    with (
        patch.object(refresh_social_followers, "ComedianService") as service_class,
        pytest.raises(SystemExit) as exc_info,
    ):
        refresh_social_followers.main(["--platform", "instagram", "--ids-csv", str(csv_path)])

    assert exc_info.value.code == 2
    service_class.assert_not_called()


@pytest.mark.parametrize(
    "argv",
    [
        ["--ids-csv", "ids.csv"],
        ["--platform", "youtube", "--ids-csv", "ids.csv"],
        ["--platform", "instagram", "--ids-csv", "ids.csv", "--limit", "1"],
        [
            "--platform",
            "instagram",
            "--ids-csv",
            "ids.csv",
            "--stale-days",
            "0",
        ],
    ],
)
def test_csv_targeting_rejects_incompatible_options_before_file_read(argv):
    with (
        patch.object(refresh_social_followers, "ComedianService") as service_class,
        patch.object(refresh_social_followers, "_read_comedian_ids_csv") as read_csv,
        pytest.raises(SystemExit) as exc_info,
    ):
        refresh_social_followers.main(argv)

    assert exc_info.value.code == 2
    read_csv.assert_not_called()
    service_class.assert_not_called()
