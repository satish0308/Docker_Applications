-- Switch to the MySQL system database
USE mysql;

-- Create the 'admin' user and allow access from any host (%)
CREATE USER IF NOT EXISTS 'admin'@'%' IDENTIFIED BY 'admin';

-- Grant all privileges to 'admin' user on all databases
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'%' WITH GRANT OPTION;

-- Apply changes
FLUSH PRIVILEGES;
