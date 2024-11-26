SELECT t.id from tags t WHERE t.type = 'show' AND position(t.pattern in ${showName}) > 0;
