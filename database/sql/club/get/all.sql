SELECT * from clubs
WHERE
    city = ${location}
ORDER BY ${order_clause}
LIMIT ${size}
