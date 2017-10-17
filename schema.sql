SET SESSION time_zone = "+8:00";
ALTER DATABASE CHARACTER SET "utf8";

DROP TABLE IF EXISTS applications;
CREATE TABLE applications (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    radosgw_user_id INT NOT NULL,
    radosgw_user_access_key VARCHAR(100) NOT NULL,
    radosgw_user_secret_key VARCHAR(100) NOT NULL,    
    published DATETIME NOT NULL,
    updated TIMESTAMP NOT NULL,
    KEY (published)
) ENGINE = INNODB;

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(100) NOT NULL
) ENGINE = INNODB;
