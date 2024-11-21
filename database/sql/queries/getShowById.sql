with complete_data as (
SELECT s.id as show_id, s.ticket_link, c.id as club_id, c.name as club_name  from shows s JOIN clubs c on s.club_id = c.id where s.id = ${id}
)
SELECT
	jsonb_build_object('show', jsonb_build_object('id', complete_data.show_id, 'ticket', jsonb_build_object('link', complete_data.ticket_link)), 'club', jsonb_build_object('id', complete_data.club_id, 'name', complete_data.club_name)) AS response
FROM
	complete_data
