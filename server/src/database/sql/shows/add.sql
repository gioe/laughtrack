INSERT INTO shows(club_id, date_time, ticket_link) 
VALUES(${club_id}, ${date_time}, ${ticket_link})
ON CONFLICT (club_id, date_Time) DO UPDATE
SET club_id = EXCLUDED.club_id, date_Time = EXCLUDED.date_Time,  ticket_link = EXCLUDED.ticket_link 
RETURNING id;