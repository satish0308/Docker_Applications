


After starting your cluster with docker-compose up --build, you can access Hue in your browser at:
http://localhost:8888



Hue should automatically detect your HiveServer2 service through its internal network. 
If needed, you can configure Hue to use the correct HiveServer2 Thrift endpoint by 
editing hue/desktop/conf/hue.ini (mounted from ./hue/ on the host).

```editorconfig
[beeswax]
hive_server_host=namenode
hive_server_port=10000

```


NameNode UI: http://localhost:9870
DataNode UI: http://localhost:9864
Postgres SQL (PGAdmin): http://localhost:8081
    - admin@admin.com
    - admin

psql -h localhost -p 5432 -U hiveuser -d metastore

beeline -u jdbc:hive2://localhost:10000



# Create table in hive

CREATE DATABASE sample_db;

SHOW DATABASES;

USE sample_db;

CREATE TABLE employees (
    emp_id INT,
    name STRING,
    position STRING,
    salary FLOAT
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
STORED AS TEXTFILE;


INSERT INTO employees VALUES
    (1, 'John Doe', 'Software Engineer', 75000.00),
    (2, 'Jane Smith', 'Data Scientist', 95000.00),
    (3, 'Mike Johnson', 'DevOps Engineer', 85000.00);


SELECT * FROM employees;




# Where to see table details in hive metastore. Which database, which table 

Key tables in the Hive Metastore:

DBS: Contains information about Hive databases.
TBLS: Contains information about Hive tables.
SDS: Stores information about table storage descriptors.
COLUMNS_V2: Contains details about the table columns (schema).
PARTITIONS: Stores partition details if your table is partitioned.
BUCKETING_COLS: Information about bucketed columns (if used).

select * from public."DBS";
SELECT * FROM TBLS WHERE db_id IN (SELECT db_id FROM DBS WHERE name = 'sample_db');
SELECT * FROM COLUMNS_V2 WHERE cd_id IN (SELECT sd_id FROM SDS WHERE tbl_id IN (SELECT tbl_id FROM TBLS WHERE tbl_name = 'employees'));

SELECT * FROM TBLS WHERE db_id = (SELECT db_id FROM DBS WHERE name = 'sample_db') AND tbl_name = 'employees';
SELECT * FROM COLUMNS_V2 WHERE cd_id = (SELECT sd_id FROM SDS WHERE tbl_id = (SELECT tbl_id FROM TBLS WHERE tbl_name = 'employees'));




http://localhost:8888/hue
admin
admin


1. Check if HiveServer2 is running
ps aux | grep hiveserver2



