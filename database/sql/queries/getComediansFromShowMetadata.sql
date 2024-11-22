SELECT c.name, uuid from comedians c WHERE position(c.name in ${showName}) > 0 OR position(c.name in ${showDescription}) > 0
