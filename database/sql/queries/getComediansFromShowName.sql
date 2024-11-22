SELECT c.name, uuid from comedians c WHERE position(c.name in ${showName}) > 0;
