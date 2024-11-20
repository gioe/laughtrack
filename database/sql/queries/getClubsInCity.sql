SELECT cl.id, cl.name from clubs cl JOIN cities ci on cl.city_id = ci.id WHERE ci.id = ${id}
