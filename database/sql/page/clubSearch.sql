with filtered_data as (
    SELECT
        id, name, address, website
    from
        clubs
    Where name ILIKE ${query}
    ORDER BY ${sort_by:name} ${direction:value}
    LIMIT ${size} 
    OFFSET ${page}
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
