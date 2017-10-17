CREATE USER 'webconsole'@'localhost' IDENTIFIED BY 'webconsole1234';
CREATE DATABASE ceph_web_console;
GRANT ALL PRIVILEGES ON ceph_web_console.* TO 'webconsole'@'localhost' IDENTIFIED BY 'webconsole1234';

