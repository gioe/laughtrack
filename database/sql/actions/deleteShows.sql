DELETE FROM shows s USING clubs c WHERE s.club_id = c.id AND c.id = ${id};
