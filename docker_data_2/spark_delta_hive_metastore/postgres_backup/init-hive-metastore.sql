--DATABASE IS ALREADY CREATED BY docker-compose. So this sql script becomes redundant.
--Hence commenting this.


CREATE DATABASE hue;
CREATE USER hueuser WITH PASSWORD 'huepassword';
GRANT ALL PRIVILEGES ON DATABASE hue TO hueuser;



