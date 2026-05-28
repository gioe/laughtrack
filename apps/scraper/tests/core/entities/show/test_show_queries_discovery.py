from sql.show_queries import ShowQueries


def test_batch_insert_show_uses_database_default_for_first_discovered_at():
    insert_columns = ShowQueries.BATCH_INSERT_SHOWS.split("VALUES", maxsplit=1)[0]

    assert "first_discovered_at" not in insert_columns


def test_batch_insert_show_does_not_update_first_discovered_at_on_conflict():
    conflict_update = ShowQueries.BATCH_INSERT_SHOWS.split("DO UPDATE SET", maxsplit=1)[1].split(
        "RETURNING", maxsplit=1
    )[0]

    assert "first_discovered_at" not in conflict_update
