INSERT INTO shows(club_id, date_time, ticket_link, name) 
VALUES(${club_id}, ${date_time}, ${ticket_link}, ${name})
ON CONFLICT (club_id, date_Time) DO UPDATE
SET club_id = EXCLUDED.club_id, date_Time = EXCLUDED.date_Time, ticket_link = EXCLUDED.ticket_link, name = EXCLUDED.name 
RETURNING id;