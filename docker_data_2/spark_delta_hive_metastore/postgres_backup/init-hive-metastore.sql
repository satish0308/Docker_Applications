SELECT 'CREATE DATABASE metastore' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'metastore')\gexec
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hiveuser') THEN
      CREATE ROLE hiveuser LOGIN PASSWORD 'hivepassword';
   END IF;
END
$$;
GRANT ALL PRIVILEGES ON DATABASE metastore TO hiveuser;

SELECT 'CREATE DATABASE hue' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hue')\gexec
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hueuser') THEN
      CREATE ROLE hueuser LOGIN PASSWORD 'hivepassword';
   END IF;
END
$$;
GRANT ALL PRIVILEGES ON DATABASE hue TO hueuser;
