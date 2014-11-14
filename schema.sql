-- CREATE TABLE todo (
--     id INT AUTO_INCREMENT,
--     title TEXT,
--     primary key (id)
-- );
-- INSERT INTO todo (title) VALUES ('Learn web.py');

CREATE TABLE classifications (
	uid INT,
	recipient VARCHAR(255),
	sender VARCHAR(255),
	subject VARCHAR(255),
	time DATETIME, 
	sentiment BOOLEAN,
	formality BOOLEAN,
	commercialism BOOLEAN,
	primary key (recipient)
);

CREATE TABLE tokens (
	address VARCHAR(255),
	auth TEXT,
	refresh TEXT,
	primary key (address)
);