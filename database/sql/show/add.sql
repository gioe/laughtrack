INSERT INTO shows(club_id, date_time, ticket_link, name, price, last_scrape_time) 
VALUES(${club_id}, ${date_time}, ${ticket_link}, ${name}, ${price}, ${last_scrape_time})
ON CONFLICT (club_id, date_Time) DO UPDATE
SET club_id = EXCLUDED.club_id, date_Time = EXCLUDED.date_Time, 
ticket_link = EXCLUDED.ticket_link, last_scrape_time = EXCLUDED.last_scrape_time,
name = EXCLUDED.name, price = EXCLUDED.price 
RETURNING id;
