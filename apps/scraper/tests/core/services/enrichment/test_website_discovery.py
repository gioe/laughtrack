from laughtrack.core.services.enrichment import website_discovery


def test_candidate_queries_skip_aliases_and_stub_records():
    queries = [
        website_discovery._GET_COMEDIANS_WITHOUT_WEBSITE,
        website_discovery._GET_COMEDIANS_WITHOUT_WEBSITE_LIMITED,
        website_discovery._COUNT_COMEDIANS_WITHOUT_WEBSITE,
    ]

    for query in queries:
        assert "parent_comedian_id IS NULL" in query
        assert "total_shows > 0" in query
        assert "NULLIF(BTRIM(name), '') IS NOT NULL" in query
        assert "website_discovery_source != 'none_found'" in query


def test_discover_websites_logs_effective_quota_and_remaining_candidates(monkeypatch):
    info_messages = []

    class FakeClient:
        is_configured = True
        source_name = "brave_search"

        @property
        def queries_remaining(self):
            return 7

        def search(self, query, num_results=10):
            return []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self._last_query = query

        def fetchone(self):
            assert "COUNT(*)" in self._last_query
            return (12,)

        def fetchall(self):
            return []

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(website_discovery, "_create_search_client", lambda: FakeClient())
    monkeypatch.setattr(website_discovery, "create_connection", lambda autocommit: FakeConnection())
    monkeypatch.setattr(website_discovery.Logger, "info", lambda message: info_messages.append(message))

    assert website_discovery.discover_websites(limit=5, dry_run=True) == []

    assert any(
        "effective_query_cap=5" in message
        and "queries_remaining=7" in message
        and "remaining_candidate_count=12" in message
        for message in info_messages
    )
