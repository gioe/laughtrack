INSERT INTO shows(club_id, date, ticket_link, name, price, last_scraped_date, description) 
VALUES(${club_id}, ${date}, ${ticket_link}, ${name}, ${price}, ${last_scraped_date}, ${description})
ON CONFLICT (club_id, date) DO UPDATE
SET club_id = EXCLUDED.club_id,
ticket_link = EXCLUDED.ticket_link, last_scraped_date = EXCLUDED.last_scraped_date,
name = EXCLUDED.name, price = EXCLUDED.price, description = EXCLUDED.description
RETURNING id;
