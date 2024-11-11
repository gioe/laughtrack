with filtered_data as (
    SELECT
        *
    from
        clubs
    ORDER BY
        name ASC
    LIMIT
        ${rows} OFFSET ${offset}
),
total_count as (
    SELECT
        COUNT(c.id) AS total
    FROM
        clubs c
)
SELECT
    JSONB_BUILD_OBJECT(
        'data',
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'id',
                id, 
                'name', name,
                'address', address,
                'website', website
            )
        ),
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
