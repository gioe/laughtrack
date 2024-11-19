DELETE FROM shows s JOIN clubs c on shows.club_id = clubs.id WHERE c.name = ${slug}
