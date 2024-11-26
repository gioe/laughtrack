with filtered_data as (
    SELECT
        c.id, name, address, website
    from
        clubs c
    LEFT JOIN tagged_clubs tcl ON c.id = tcl.club_id
	LEFT JOIN tags t ON tcl.tag_id = t.id
    WHERE name ILIKE ${query}
    AND (${tagsEmpty} = TRUE) OR (t.value IN (${tags:csv}))
    ORDER BY ${sort_by:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(c.id) AS total
    from
        clubs c
    LEFT JOIN tagged_clubs tcl ON c.id = tcl.club_id
	LEFT JOIN tags t ON tcl.tag_id = t.id
    WHERE name ILIKE ${query}
    AND (${tagsEmpty} = TRUE) OR (t.value IN (${tags:csv}))
)
SELECT
    JSONB_BUILD_OBJECT(
        'data',
        COALESCE(jsonb_agg(jsonb_build_object('id', id, 'name', name, 'address', address, 'website', website)) FILTER (where id IS NOT NULL), '[]'),
        'total',
        (
            SELECT
                total
            FROM
                total_count
        )
    ) as response
FROM
    filtered_data
