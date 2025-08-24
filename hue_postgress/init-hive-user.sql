-- Create hiveuser role with password
CREATE ROLE hiveuser WITH LOGIN PASSWORD 'hivepassword';

-- Allow hiveuser to create databases
ALTER ROLE hiveuser CREATEDB;

-- Create the Hive metastore database
CREATE DATABASE metastore OWNER hiveuser;

-- Grant privileges to hiveuser
GRANT ALL PRIVILEGES ON DATABASE metastore TO hiveuser;
