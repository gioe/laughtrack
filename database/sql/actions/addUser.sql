INSERT INTO users(email, password, role) 
VALUES(${email}, ${password}, ${role})
RETURNING id;
